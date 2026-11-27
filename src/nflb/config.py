"""Configuración central, leída de variables de entorno / .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Secretos
    telegram_bot_token: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    user_id_salt: SecretStr = SecretStr("cambia-esta-sal-en-el-env")

    # Modelos
    anthropic_model: str = "claude-sonnet-5-5"
    judge_model: str | None = None
    llm_provider: str = "anthropic"
    whisper_model: str = "small"
    embedding_model: str = "intfloat/multilingual-e5-base"

    # Almacenamiento
    database_url: str = f"sqlite:///{(ROOT_DIR / 'var' / 'nflb.db').as_posix()}"
    vector_backend: str = "sqlite"  # sqlite | pgvector
    data_dir: Path = ROOT_DIR / "var"

    # RAG
    rag_top_k: int = 6
    # Similitud coseno mínima del mejor fragmento (E5). Calibrado el 2026-11-26: E5 comprime
    # las similitudes (0,79-0,91), así que solo filtra lo claramente ajeno. La abstención
    # fina la hacen el prompt y la verificación de citas (ver README).
    rag_min_score: float = 0.80

    # Idioma de la interfaz y de las respuestas: "es" (por defecto) o "en" (solo para demos).
    # La base de conocimiento sigue en español; en "en" el asistente traduce al responder.
    bot_language: Literal["es", "en"] = "es"

    # Conversación y retención
    history_turns: int = 10
    retention_days: int = 30

    # Acceso y depuración
    allowed_user_ids: Annotated[list[int], NoDecode] = Field(default_factory=list)
    debug_log_content: bool = False
    log_level: str = "INFO"

    @field_validator("allowed_user_ids", mode="before")
    @classmethod
    def _parse_ids(cls, v: object) -> object:
        if isinstance(v, str):
            return [int(x) for x in v.replace(";", ",").split(",") if x.strip()]
        if isinstance(v, int):
            return [v]
        return v

    @property
    def effective_judge_model(self) -> str:
        return self.judge_model or self.anthropic_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
