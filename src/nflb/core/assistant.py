"""Fachada del núcleo: lo único que usan los canales (Telegram u otro).

Recibe texto ya normalizado (las notas de voz llegan transcritas) y devuelve una respuesta.
No sabe nada del canal.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from functools import cached_property

from nflb.core import info, safety, users
from nflb.core.router import Route, route
from nflb.llm.base import LLMProvider
from nflb.logging_setup import get_logger

log = get_logger("nflb.core")


@dataclass
class Reply:
    text: str
    intent: str
    status: str = "ok"
    citations: list[str] = field(default_factory=list)
    retrieved: list[str] = field(default_factory=list)
    latency_ms: int = 0
    raw: str = ""
    attempts: int = 0


class Assistant:
    def __init__(self, llm: LLMProvider | None = None, retriever=None):
        self._llm = llm
        self._retriever = retriever

    @cached_property
    def llm(self) -> LLMProvider:
        if self._llm is None:
            from nflb.llm.openai_provider import get_provider

            self._llm = get_provider()
        return self._llm

    @cached_property
    def retriever(self):
        if self._retriever is None:
            from nflb.rag.embeddings import get_embedder
            from nflb.rag.retriever import HybridRetriever
            from nflb.rag.store import get_store

            self._retriever = HybridRetriever(get_store(), get_embedder())
        return self._retriever

    def warm_up(self) -> None:
        """Carga el modelo de embeddings y la KB antes del primer mensaje."""
        self.retriever.retrieve("ayuda")

    def respond(self, text: str, history: list[dict] | None = None) -> Reply:
        """Responde sin persistir nada (lo usan la evaluación y handle_text)."""
        t0 = time.perf_counter()
        r: Route = route(self.llm, text, history)
        if r.intencion == "urgente":
            reply = Reply(safety.urgent_block(), "urgente", "derivada")
        elif r.intencion == "estado_expediente":
            reply = Reply(safety.EXPEDIENTE, "estado_expediente")
        elif r.intencion == "saludo":
            reply = Reply(safety.SALUDO, "saludo")
        elif r.intencion == "fuera_de_alcance":
            reply = Reply(safety.OUT_OF_SCOPE, "fuera_de_alcance")
        else:
            res = info.answer(self.llm, self.retriever, text, r.consulta_busqueda, history)
            reply = Reply(res.text, "informativa", res.status, res.citations, res.retrieved,
                          raw=res.raw, attempts=res.attempts)  # fmt: skip
        reply.latency_ms = int((time.perf_counter() - t0) * 1000)
        log.info("respuesta", intencion=reply.intent, estado=reply.status,
                 citas=len(reply.citations), intentos=reply.attempts,
                 ms=reply.latency_ms)  # fmt: skip
        return reply

    def handle_text(self, user_hash: str, text: str) -> Reply:
        history = users.get_history(user_hash)
        reply = self.respond(text, history)
        users.add_turn(user_hash, "user", text)
        users.add_turn(user_hash, "assistant", reply.text)
        return reply
