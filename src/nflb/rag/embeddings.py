"""Embeddings locales multilingües (E5). Respeta los prefijos `query:` / `passage:`."""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

import numpy as np

from nflb.config import get_settings


class Embedder(Protocol):
    dim: int

    def embed_passages(self, texts: list[str]) -> np.ndarray: ...
    def embed_query(self, text: str) -> np.ndarray: ...


class E5Embedder:
    def __init__(self, model_name: str | None = None):
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name or get_settings().embedding_model
        self.model = SentenceTransformer(self.model_name, device="cpu")
        self.dim = self.model.get_embedding_dimension()

    def _encode(self, texts: list[str]) -> np.ndarray:
        vecs = self.model.encode(
            texts, batch_size=16, normalize_embeddings=True, show_progress_bar=False
        )
        return np.asarray(vecs, dtype=np.float32)

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        return self._encode([f"passage: {t}" for t in texts])

    def embed_query(self, text: str) -> np.ndarray:
        return self._encode([f"query: {text}"])[0]


@lru_cache
def get_embedder() -> E5Embedder:
    return E5Embedder()
