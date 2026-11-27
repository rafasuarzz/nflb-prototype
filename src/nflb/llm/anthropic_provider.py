"""Implementación de LLMProvider con la API de Claude (SDK oficial `anthropic`).

Notas sobre el modelo por defecto (claude-sonnet-5-5):
- No acepta `temperature` distinta de la de por defecto (400). La estabilidad del formato se
  consigue con salidas estructuradas y con esfuerzo bajo (`output_config.effort`).
- Las salidas estructuradas usan `client.messages.parse(output_format=Modelo)`.
- Si el modelo rechaza una petición (`stop_reason == "refusal"`) se lanza LLMError y el
  núcleo responde con un mensaje seguro; nunca se inventa una respuesta.
"""

from __future__ import annotations

import anthropic

from nflb.config import get_settings
from nflb.llm.base import LLMError, LLMProvider, T


def _to_anthropic(messages: list[dict]) -> list[dict]:
    out = []
    for m in messages:
        content = m["content"]
        if isinstance(content, list):
            parts = []
            for p in content:
                if p["type"] == "text":
                    parts.append({"type": "text", "text": p["text"]})
                elif p["type"] == "image":
                    parts.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": p["media_type"],
                                "data": p["data"],
                            },
                        }
                    )
                elif p["type"] == "pdf":
                    parts.append(
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": p["data"],
                            },
                        }
                    )
            content = parts
        out.append({"role": m["role"], "content": content})
    return out


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, model: str | None = None, client: anthropic.Anthropic | None = None):
        settings = get_settings()
        self.model = model or settings.anthropic_model
        key = settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else None
        self.client = client or anthropic.Anthropic(api_key=key, timeout=60.0, max_retries=2)

    def _check(self, response) -> None:
        if response.stop_reason == "refusal":
            raise LLMError("refusal")
        if response.stop_reason == "max_tokens":
            raise LLMError("max_tokens")

    def complete(self, system, messages, *, max_tokens=1500, effort="low") -> str:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=_to_anthropic(messages),
                output_config={"effort": effort},
            )
        except anthropic.APIError as e:
            raise LLMError(type(e).__name__) from e
        self._check(response)
        return "".join(b.text for b in response.content if b.type == "text").strip()

    def structured(self, system, messages, schema: type[T], *, max_tokens=4000, effort="low") -> T:
        try:
            response = self.client.messages.parse(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=_to_anthropic(messages),
                output_format=schema,
                output_config={"effort": effort},
            )
        except anthropic.APIError as e:
            raise LLMError(type(e).__name__) from e
        self._check(response)
        if response.parsed_output is None:
            raise LLMError("sin salida estructurada")
        return response.parsed_output
