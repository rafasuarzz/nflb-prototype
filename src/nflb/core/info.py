"""Consultas informativas ancladas a fuentes (RAG) con verificación de citas y guardarraíles."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from nflb.core import guardrails
from nflb.core.prompts import INFO_CORRECTION, INFO_SYSTEM
from nflb.core.safety import SAFE_GENERIC
from nflb.core.texts import NO_SE
from nflb.llm.base import LLMError, LLMProvider
from nflb.rag.retriever import HybridRetriever, Retrieved


class InfoOut(BaseModel):
    respuesta: str = Field(description="Respuesta para la persona, con citas [id]")
    citas: list[str] = Field(default_factory=list, description="Identificadores citados")
    sin_informacion: bool = Field(
        default=False, description="true si el contexto no contiene la respuesta"
    )
    es_pregunta_aclaratoria: bool = False


@dataclass
class InfoResult:
    text: str
    status: str  # ok | aclaratoria | sin_info | bloqueada | error
    citations: list[str] = field(default_factory=list)
    retrieved: list[str] = field(default_factory=list)
    attempts: int = 0
    raw: str = ""  # respuesta del modelo antes de renderizar (para la evaluación)
    issues: list[str] = field(default_factory=list)


def build_context(items: list[Retrieved]) -> str:
    parts = []
    for it in items:
        m = it.meta
        parts.append(
            f'<fragmento id="{it.id}">\n[{it.id}] {m["documento"]} — {m["seccion"]}\n'
            f"{it.chunk.text}\n</fragmento>"
        )
    return "<contexto>\n" + "\n".join(parts) + "\n</contexto>"


def _source_label(meta: dict) -> str:
    seccion = meta["seccion"].split(" (parte")[0].rstrip(".")
    return f"{meta['documento']}, {seccion}"


def render(out: InfoOut, items: list[Retrieved]) -> tuple[str, list[str]]:
    by_id = {it.id: it for it in items}
    ids = [i for i in dict.fromkeys(guardrails.cited_ids(out.respuesta) + out.citas) if i in by_id]
    body = guardrails.strip_citations(out.respuesta)
    labels = list(dict.fromkeys(_source_label(by_id[i].meta) for i in ids))
    sources = "\n".join(f"📄 Fuente: {lbl}" for lbl in labels)
    text = f"{body}\n\n{sources}" if sources else body
    return guardrails.ensure_closing(guardrails.mask_pii(text)), ids


def _problems(out: InfoOut, allowed: set[str]) -> list[str]:
    probs = []
    bad = guardrails.find_forbidden(out.respuesta)
    if bad:
        probs.append(f"usa expresiones prohibidas: {', '.join(bad)}")
    invalid = guardrails.invalid_citations(out.respuesta, out.citas, allowed)
    if invalid:
        probs.append(f"cita identificadores que no están en el contexto: {', '.join(invalid)}")
    valid = [i for i in guardrails.cited_ids(out.respuesta) + out.citas if i in allowed]
    if not out.sin_informacion and not out.es_pregunta_aclaratoria and not valid:
        probs.append("no cita ninguna fuente del contexto")
    return probs


def answer(
    llm: LLMProvider,
    retriever: HybridRetriever,
    question: str,
    search_query: str | None = None,
    history: list[dict] | None = None,
) -> InfoResult:
    query = f"{search_query}\n{question}" if search_query and search_query != question else question
    res = retriever.retrieve(query)
    retrieved = [it.id for it in res.items]
    if not res.sufficient:
        return InfoResult(NO_SE, "sin_info", retrieved=retrieved)

    allowed = set(retrieved)
    messages = [*(history or [])[-6:]]
    messages.append(
        {
            "role": "user",
            "content": f"{build_context(res.items)}\n\n<pregunta>\n{question}\n</pregunta>",
        }
    )

    issues: list[str] = []
    for attempt in (1, 2):  # un intento + una regeneración con instrucción correctiva
        try:
            out = llm.structured(INFO_SYSTEM, messages, InfoOut, max_tokens=3000)
        except LLMError as e:
            return InfoResult(SAFE_GENERIC, "error", retrieved=retrieved, attempts=attempt,
                              issues=[str(e)])  # fmt: skip
        if out.sin_informacion:
            return InfoResult(NO_SE, "sin_info", retrieved=retrieved, attempts=attempt,
                              raw=out.respuesta, issues=issues)  # fmt: skip
        probs = _problems(out, allowed)
        if not probs:
            text, ids = render(out, res.items)
            status = "aclaratoria" if out.es_pregunta_aclaratoria else "ok"
            if status == "aclaratoria":
                text = guardrails.mask_pii(guardrails.strip_citations(out.respuesta))
            return InfoResult(text, status, ids, retrieved, attempt, out.respuesta, issues)
        issues += probs
        messages = [
            *messages,
            {"role": "assistant", "content": out.model_dump_json()},
            {"role": "user", "content": INFO_CORRECTION.format(problema="; ".join(probs))},
        ]

    # Tras dos intentos fallidos: si el fallo es de citas → "no tengo esa información";
    # si es de lenguaje de elegibilidad → respuesta segura genérica.
    blocked_lang = any("prohibidas" in p for p in issues[-len(probs) :])
    text = SAFE_GENERIC if blocked_lang else NO_SE
    return InfoResult(text, "bloqueada", retrieved=retrieved, attempts=2, raw=out.respuesta,
                      issues=issues)  # fmt: skip
