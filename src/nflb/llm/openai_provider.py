"""Esqueleto de proveedor OpenAI.

La candidatura menciona modelos de OpenAI para el producto final. Este esqueleto demuestra
que el núcleo solo depende de la interfaz LLMProvider: implementar estos dos métodos basta
para cambiar de proveedor (LLM_PROVIDER=openai). No se implementa en el prototipo.
"""

from __future__ import annotations

from nflb.llm.base import LLMProvider, T


class OpenAIProvider(LLMProvider):
    name = "openai"

    def complete(self, system, messages, *, max_tokens=1500, effort="low") -> str:
        raise NotImplementedError("OpenAIProvider: pendiente (Fase 2)")

    def structured(self, system, messages, schema: type[T], *, max_tokens=4000, effort="low") -> T:
        raise NotImplementedError("OpenAIProvider: pendiente (Fase 2)")


def get_provider(name: str | None = None) -> LLMProvider:
    from nflb.config import get_settings

    name = name or get_settings().llm_provider
    if name == "anthropic":
        from nflb.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider()
    if name == "openai":
        return OpenAIProvider()
    raise ValueError(f"Proveedor desconocido: {name}")
