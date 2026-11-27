"""Dobles de prueba: LLM programable y recuperador fijo."""

from __future__ import annotations

from nflb.llm.base import LLMError, LLMProvider
from nflb.rag.retriever import RetrievalResult, Retrieved
from nflb.rag.store import StoredChunk


class FakeLLM(LLMProvider):
    """Devuelve, en orden, las respuestas programadas para cada esquema (por nombre)."""

    name = "fake"

    def __init__(self, scripted: dict[str, list] | None = None, text: str = "ok"):
        self.scripted = {k: list(v) for k, v in (scripted or {}).items()}
        self.text = text
        self.calls: list[tuple[str, list[dict]]] = []

    def complete(self, system, messages, *, max_tokens=1500, effort="low"):
        self.calls.append(("complete", messages))
        return self.text

    def structured(self, system, messages, schema, *, max_tokens=4000, effort="low"):
        self.calls.append((schema.__name__, messages))
        queue = self.scripted.get(schema.__name__)
        if not queue:
            raise LLMError(f"sin respuesta programada para {schema.__name__}")
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return schema.model_validate(item)


def chunk(cid: str, text: str = "texto", doc: str = "Ordenanza de Telde", sec: str = "Artículo 9"):
    return StoredChunk(cid, text, {"id": cid, "documento": doc, "seccion": sec, "url": "https://x"})


class FakeRetriever:
    def __init__(self, chunks: list[StoredChunk], sufficient: bool = True):
        self.chunks = chunks
        self.sufficient = sufficient
        self.queries: list[str] = []

    def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResult:
        self.queries.append(query)
        items = [Retrieved(c, 1.0 / (i + 1), 0.9, i, i) for i, c in enumerate(self.chunks)]
        return RetrievalResult(items, 0.9 if self.sufficient else 0.5, self.sufficient)
