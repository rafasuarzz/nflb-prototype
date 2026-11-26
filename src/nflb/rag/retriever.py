"""Recuperación híbrida: similitud vectorial (E5) + BM25, fusionadas con Reciprocal Rank Fusion.

BM25 captura mejor el vocabulario exacto de la normativa (nombres de ayudas y documentos);
los vectores capturan las paráfrasis ("me quedé sin trabajo" ~ "situación de desempleo").

Umbral de relevancia: si el fragmento más parecido (similitud coseno E5) no supera
`RAG_MIN_SCORE`, se considera que la base de conocimiento no cubre la pregunta.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from nflb.config import get_settings
from nflb.rag.store import StoredChunk, VectorStore

RRF_K = 60
CANDIDATES = 30

_STOP = set(
    """a al algo como con de del el ella ellos en entre era es esta este esto estos ha hay la
    las le les lo los mas me mi mis muy no nos o para pero por que se sea ser si sin sobre
    su sus te tengo ti tu tus un una uno unos y ya yo""".split()
)


def tokenize(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    tokens = re.findall(r"[a-z0-9]+", text)
    return [_stem(t) for t in tokens if t not in _STOP and len(t) > 1]


def _stem(t: str) -> str:
    """Stemming mínimo para plurales y género (ayudas→ayuda, requisitos→requisito)."""
    for suf in ("iones", "es", "s"):
        if len(t) > 5 and t.endswith(suf):
            return t[: -len(suf)] + ("ion" if suf == "iones" else "")
    return t


@dataclass
class Retrieved:
    chunk: StoredChunk
    score: float  # puntuación RRF
    cosine: float | None  # similitud vectorial, si entró por esa vía
    bm25_rank: int | None
    vec_rank: int | None

    @property
    def id(self) -> str:
        return self.chunk.id

    @property
    def meta(self) -> dict:
        return self.chunk.meta


@dataclass
class RetrievalResult:
    items: list[Retrieved]
    best_cosine: float
    sufficient: bool


class HybridRetriever:
    def __init__(
        self, store: VectorStore, embedder, top_k: int | None = None, min_score: float | None = None
    ):
        settings = get_settings()
        self.store = store
        self.embedder = embedder
        self.top_k = top_k or settings.rag_top_k
        self.min_score = settings.rag_min_score if min_score is None else min_score
        self._chunks = store.all_chunks()
        self._bm25 = (
            BM25Okapi([tokenize(f"{c.meta.get('seccion', '')} {c.text}") for c in self._chunks])
            if self._chunks
            else None
        )

    def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResult:
        top_k = top_k or self.top_k
        if not self._chunks:
            return RetrievalResult([], 0.0, False)

        vec_hits = self.store.vector_search(self.embedder.embed_query(query), CANDIDATES)
        vec_rank = {c.id: (r, sim) for r, (c, sim) in enumerate(vec_hits)}

        scores = self._bm25.get_scores(tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: -scores[i])[:CANDIDATES]
        bm_rank = {self._chunks[i].id: r for r, i in enumerate(order) if scores[i] > 0}

        by_id = {c.id: c for c in self._chunks}
        fused: dict[str, float] = {}
        for cid, (r, _) in vec_rank.items():
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (RRF_K + r + 1)
        for cid, r in bm_rank.items():
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (RRF_K + r + 1)

        ranked = sorted(fused, key=lambda c: -fused[c])[:top_k]
        items = [
            Retrieved(
                chunk=by_id[cid],
                score=fused[cid],
                cosine=vec_rank[cid][1] if cid in vec_rank else None,
                bm25_rank=bm_rank.get(cid),
                vec_rank=vec_rank[cid][0] if cid in vec_rank else None,
            )
            for cid in ranked
        ]
        best = vec_hits[0][1] if vec_hits else 0.0
        return RetrievalResult(items=items, best_cosine=best, sufficient=best >= self.min_score)
