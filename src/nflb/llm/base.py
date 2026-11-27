"""Interfaz LLMProvider: el núcleo no depende de ningún proveedor concreto.

Los mensajes usan un formato neutro:
    {"role": "user" | "assistant", "content": str | list[Part]}
    Part = {"type": "text", "text": str}
         | {"type": "image", "media_type": "image/jpeg", "data": <base64>}
         | {"type": "pdf", "data": <base64>}
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """Fallo del proveedor (red, cuota, rechazo). El núcleo responde con un mensaje seguro."""


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def complete(
        self, system: str, messages: list[dict], *, max_tokens: int = 1500, effort: str = "low"
    ) -> str:
        """Respuesta de texto libre."""

    @abstractmethod
    def structured(
        self,
        system: str,
        messages: list[dict],
        schema: type[T],
        *,
        max_tokens: int = 4000,
        effort: str = "low",
    ) -> T:
        """Respuesta validada contra un modelo pydantic (salida estructurada)."""
