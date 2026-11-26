"""Ingesta de la base de conocimiento.

Lee kb/manifest.yaml, extrae y trocea cada fuente por estructura, calcula embeddings y carga
la BD. Es idempotente: volver a ejecutarlo no duplica nada (solo actualiza lo que cambie).
Genera un informe en kb/ingest_report.md.

Uso:  uv run python scripts/ingest.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import yaml

from nflb.config import ROOT_DIR
from nflb.db.session import init_db
from nflb.rag.chunker import chunk_source
from nflb.rag.store import SQLiteVectorStore, StoredChunk, get_store

KB_DIR = ROOT_DIR / "kb"


def run(
    manifest_path: Path = KB_DIR / "manifest.yaml",
    sources_dir: Path = KB_DIR / "sources",
    embed_fn=None,
    store=None,
    report_path: Path | None = KB_DIR / "ingest_report.md",
) -> dict:
    init_db()
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    store = store or get_store()
    if embed_fn is None:
        from nflb.rag.embeddings import get_embedder

        embed_fn = get_embedder().embed_passages

    rows, warnings = [], []
    ids = set()
    for src in manifest["fuentes"]:
        ids.add(src["id"])
        path = sources_dir / src["archivo"]
        if not path.exists():
            warnings.append(f"`{src['id']}`: falta el archivo {src['archivo']}; no se carga.")
            continue
        skipped: list[str] = []
        try:
            chunks = chunk_source(src, sources_dir, manifest.get("fecha_descarga"), skipped)
        except Exception as e:  # una fuente rota no debe tumbar la ingesta entera
            warnings.append(f"`{src['id']}`: error al procesar ({type(e).__name__}: {e}).")
            continue
        if not chunks:
            warnings.append(f"`{src['id']}`: no se ha extraído ningún fragmento.")
        if not src.get("verificada_por_rafa"):
            warnings.append(f"`{src['id']}`: fuente pendiente de verificación manual.")
        for s in skipped:
            warnings.append(f"`{src['id']}`: descartado {s} (principio P2).")
        res = store.upsert_source(
            src["id"], [StoredChunk(c.id, c.text, c.meta) for c in chunks], embed_fn
        )
        rows.append((src, len(chunks), res))

    removed = store.delete_sources_not_in(ids) if isinstance(store, SQLiteVectorStore) else 0

    total = store.count()
    report = _report(rows, warnings, removed, total)
    if report_path:
        report_path.write_text(report, encoding="utf-8")
    return {"documentos": len(rows), "fragmentos": total, "avisos": warnings, "filas": rows}


def _report(rows, warnings, removed, total) -> str:
    lines = [
        "# Informe de ingesta de la base de conocimiento",
        "",
        f"Fecha: {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"- Documentos procesados: **{len(rows)}**",
        f"- Fragmentos en la base: **{total}**",
        f"- Fragmentos de fuentes retiradas del manifiesto: {removed} eliminados",
        "",
        "| Fuente | Ámbito | Fragmentos | Nuevos | Actualizados | Sin cambios | Borrados |",
        "|---|---|---|---|---|---|---|",
    ]
    for src, n, r in rows:
        lines.append(
            f"| `{src['id']}` | {src['ambito']} | {n} | {r.inserted} | {r.updated} | "
            f"{r.unchanged} | {r.deleted} |"
        )
    lines += ["", "## Avisos", ""] + ([f"- {w}" for w in warnings] or ["- Ninguno"])
    return "\n".join(lines) + "\n"


def main() -> int:
    out = run()
    print(f"Documentos: {out['documentos']} · Fragmentos: {out['fragmentos']}")
    for w in out["avisos"]:
        print(f"AVISO: {w}")
    print("Informe: kb/ingest_report.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
