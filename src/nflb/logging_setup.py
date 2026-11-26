"""Logs estructurados en JSON. Por defecto NUNCA se registra el contenido de los mensajes."""

from __future__ import annotations

import logging

import structlog

from nflb.config import get_settings

_CONTENT_KEYS = {"text", "content", "transcript", "message", "answer", "image", "audio"}


def _drop_content(_logger, _name, event_dict):
    if not get_settings().debug_log_content:
        for key in list(event_dict):
            if key in _CONTENT_KEYS:
                event_dict[key] = "[omitido]"
    return event_dict


def setup_logging() -> None:
    level = getattr(logging, get_settings().log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(message)s")
    # httpx registra la URL de Telegram, que contiene el token del bot.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _drop_content,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
    )


def get_logger(name: str = "nflb"):
    return structlog.get_logger(name)
