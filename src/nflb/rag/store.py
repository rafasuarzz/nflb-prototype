"""Interfaz VectorStore y su implementación sobre SQLite.

La especificación pide PostgreSQL + pgvector. Docker no está arrancado en la máquina de
desarrollo, así que la implementación activa es SQLite (los vectores se cargan en memoria
y se compara con numpy: con unos cientos de fragmentos es instantáneo). La interfaz es la
misma, de modo que un `PgVectorStore` puede sustituirla sin tocar el resto del código.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.engine import Engine

from nflb.db.models import KBChunk
from nflb.db.session import session_scope


@dataclass
class StoredChunk:
    id: str
    text: str
    meta: dict


@dataclass
class UpsertResult:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    deleted: int = 0


def content_hash(text: str, meta: dict) -> str:
    key = text + "|" + "|".join(f"{k}={meta[k]}" for k in sorted(meta))
    return hashlib.sha256(key.encode()).hexdigest()


class VectorStore(Protocol):
    def upsert_source(
        self, source_id: str, chunks: list[StoredChunk], embed_fn
    ) -> UpsertResult: ...
    def all_chunks(self) -> list[StoredChunk]: ...
    def vector_search(self, query_vec: np.ndarray, k: int) -> list[tuple[StoredChunk, float]]: ...
    def count(self) -> int: ...


class SQLiteVectorStore:
    def __init__(self, engine: Engine | None = None):
        self.engine = engine
        self._cache: tuple[list[StoredChunk], np.ndarray] | None = None

    # -- escritura (idempotente) --
    def upsert_source(self, source_id: str, chunks: list[StoredChunk], embed_fn) -> UpsertResult:
        """Carga los fragmentos de una fuente. Solo recalcula embeddings de lo que ha cambiado
        y elimina los fragmentos de la fuente que ya no existen. Volver a ejecutar no duplica."""
        res = UpsertResult()
        with session_scope(self.engine) as s:
            existing = {
                c.id: c for c in s.scalars(select(KBChunk).where(KBChunk.source_id == source_id))
            }
            to_embed: list[tuple[StoredChunk, str]] = []
            for ch in chunks:
                h = content_hash(ch.text, ch.meta)
                old = existing.get(ch.id)
                if old is not None and old.content_hash == h:
                    res.unchanged += 1
                else:
                    to_embed.append((ch, h))
            if to_embed:
                vecs = embed_fn([f"{c.meta.get('seccion', '')}\n{c.text}" for c, _ in to_embed])
                for (ch, h), vec in zip(to_embed, vecs, strict=True):
                    row = existing.get(ch.id)
                    blob = np.asarray(vec, dtype=np.float32).tobytes()
                    if row is None:
                        s.add(
                            KBChunk(
                                id=ch.id,
                                source_id=source_id,
                                text=ch.text,
                                meta=ch.meta,
                                content_hash=h,
                                embedding=blob,
                            )
                        )
                        res.inserted += 1
                    else:
                        row.text, row.meta, row.content_hash, row.embedding = (
                            ch.text,
                            ch.meta,
                            h,
                            blob,
                        )
                        res.updated += 1
            stale = set(existing) - {c.id for c in chunks}
            if stale:
                s.execute(delete(KBChunk).where(KBChunk.id.in_(stale)))
                res.deleted = len(stale)
        self._cache = None
        return res

    def delete_sources_not_in(self, source_ids: set[str]) -> int:
        with session_scope(self.engine) as s:
            r = s.execute(delete(KBChunk).where(KBChunk.source_id.not_in(source_ids)))
            n = r.rowcount or 0
        self._cache = None
        return n

    # -- lectura --
    def _load(self) -> tuple[list[StoredChunk], np.ndarray]:
        if self._cache is None:
            with session_scope(self.engine) as s:
                rows = s.scalars(select(KBChunk).order_by(KBChunk.id)).all()
                chunks = [StoredChunk(r.id, r.text, r.meta) for r in rows]
                mat = (
                    np.vstack([np.frombuffer(r.embedding, dtype=np.float32) for r in rows])
                    if rows
                    else np.zeros((0, 1), dtype=np.float32)
                )
            self._cache = (chunks, mat)
        return self._cache

    def all_chunks(self) -> list[StoredChunk]:
        return list(self._load()[0])

    def count(self) -> int:
        return len(self._load()[0])

    def vector_search(self, query_vec: np.ndarray, k: int) -> list[tuple[StoredChunk, float]]:
        chunks, mat = self._load()
        if not chunks:
            return []
        sims = mat @ np.asarray(query_vec, dtype=np.float32)
        idx = np.argsort(-sims)[:k]
        return [(chunks[i], float(sims[i])) for i in idx]


def get_store(engine: Engine | None = None) -> VectorStore:
    from nflb.config import get_settings

    backend = get_settings().vector_backend
    if backend == "sqlite":
        return SQLiteVectorStore(engine)
    raise NotImplementedError(
        f"VECTOR_BACKEND={backend!r} no está implementado en el prototipo (usa 'sqlite')."
    )
