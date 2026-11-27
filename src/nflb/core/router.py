"""Clasificación de intención con salida estructurada (más reglas deterministas de urgencia)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from nflb.core.prompts import ROUTER_SYSTEM
from nflb.core.safety import is_urgent_by_rules
from nflb.llm.base import LLMError, LLMProvider

Intent = Literal["urgente", "informativa", "estado_expediente", "saludo", "fuera_de_alcance"]


class Route(BaseModel):
    intencion: Intent
    consulta_busqueda: str = Field(
        default="", description="Consulta breve para buscar en la normativa (si es informativa)"
    )
    por_reglas: bool = False


class _RouterOut(BaseModel):
    intencion: Intent
    consulta_busqueda: str


def route(llm: LLMProvider, text: str, history: list[dict] | None = None) -> Route:
    if is_urgent_by_rules(text):
        return Route(intencion="urgente", por_reglas=True)
    ctx = ""
    if history:
        last = [h for h in history[-4:] if h["role"] == "user"]
        if last:
            ctx = "Mensajes anteriores de la persona:\n" + "\n".join(
                f"- {h['content'][:300]}" for h in last
            )
    prompt = f"{ctx}\n\nMensaje a clasificar:\n<mensaje>\n{text}\n</mensaje>".strip()
    try:
        out = llm.structured(
            ROUTER_SYSTEM, [{"role": "user", "content": prompt}], _RouterOut, max_tokens=1000
        )
    except LLMError:
        # Si el clasificador falla, tratamos el mensaje como consulta informativa: el paso
        # informativo sigue anclado a fuentes y, sin contexto suficiente, se abstiene.
        return Route(intencion="informativa", consulta_busqueda=text)
    return Route(intencion=out.intencion, consulta_busqueda=out.consulta_busqueda or text)
