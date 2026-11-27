"""Idioma de la interfaz (BOT_LANGUAGE=es|en). El inglés es solo para demostraciones.

- `t(es, en)` elige el texto fijo según el idioma configurado.
- `llm_language_rule()` se añade a los prompts que producen texto para la persona: la base de
  conocimiento está en español y el modelo traduce al responder (sin añadir nada).
- Las consultas de búsqueda siguen en español, porque la base de conocimiento lo está.
"""

from __future__ import annotations

from nflb.config import get_settings


def lang() -> str:
    return get_settings().bot_language


def is_en() -> bool:
    return lang() == "en"


def t(es: str, en: str) -> str:
    return en if is_en() else es


_EN_RULE = """

LANGUAGE: The person writes in English. Write every text meant for the person (answers, questions, document names, summary fields, instructions) in clear, plain English, even though the context documents are in Spanish. Translate faithfully: do not add anything that is not in the context. Keep official names of benefits and laws in Spanish and add a short English gloss the first time (e.g. "Ingreso Mínimo Vital (minimum living income)"). Do not change JSON field names, enum values or citation identifiers. The rules above also apply to their English equivalents: never say "you are entitled", "you qualify", "you are eligible", "you meet the requirements", "you will get it" or similar, not even negated; say "you could ask about" instead."""


def llm_language_rule() -> str:
    return _EN_RULE if is_en() else ""
