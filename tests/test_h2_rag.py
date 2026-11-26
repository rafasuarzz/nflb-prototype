"""H2: troceado por estructura, almacén idempotente y recuperación híbrida."""

from pathlib import Path

import numpy as np
import pytest
import yaml

from nflb.rag import chunker
from nflb.rag.retriever import HybridRetriever, tokenize
from nflb.rag.store import SQLiteVectorStore, StoredChunk

ROOT = Path(__file__).resolve().parents[1]


# ----------------------------------------------------------- embedder falso (sin modelo)


class FakeEmbedder:
    """Bolsa de palabras con hashing: determinista y suficiente para probar la mecánica."""

    dim = 256

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float32)
        for t in tokenize(text):
            v[hash(t) % self.dim] += 1
        n = np.linalg.norm(v)
        return v / n if n else v

    def embed_passages(self, texts):
        return np.vstack([self._vec(t) for t in texts])

    def embed_query(self, text):
        return self._vec(text)


# ----------------------------------------------------------- troceado


@pytest.mark.parametrize(
    "title,key",
    [
        ("Artículo 9. Requisitos generales.", "art9"),
        ("Artículo 13 bis. Algo.", "art13bis"),
        ("Disposición adicional primera. Actualización", "da1"),
        ("Disposición derogatoria única. Derogación normativa.", "dd1"),
        ("ANEXO VI . DOCUMENTACIÓN", "anexo-vi"),
        ("¿Qué es la unidad de convivencia?", "que-es-la-unidad-de-convivenci"),
    ],
)
def test_section_key(title, key):
    assert chunker.section_key(title) == key


PDF_TEXT = """Boletín Oficial de la Provincia de Las Palmas. Número 105, lunes 31 de agosto 7940
ANUNCIO sin relación
ORDENANZA REGULADORA DE LAS
ÍNDICE:
Artículo 1. Objeto
Artículo 2. Requisitos
Artículo 1. Objeto.
1. La Ordenanza tiene por objeto regular las prestaciones
económicas de los Servicios Sociales para atender necesida-
des sociales de las familias empadronadas en el municipio.
Boletín Oficial de la Provincia de Las Palmas. Número 105, lunes 31 de agosto de 2020 7941
Artículo 2. Requisitos.
a) Estar empadronada en el municipio con una antigüedad mínima.
b) No disponer de recursos suficientes para atender la necesidad.
"""


def test_pdf_parse_by_article_skips_index_and_headers():
    secs = chunker.parse_pdf_text(PDF_TEXT, "ORDENANZA REGULADORA DE LAS")
    keys = [chunker.section_key(s.title) for s in secs]
    assert keys.count("art1") == 1 and keys.count("art2") == 1
    art1 = next(s for s in secs if chunker.section_key(s.title) == "art1")
    assert "necesidades sociales" in art1.text  # guion de fin de línea reparado
    assert "Boletín Oficial" not in art1.text  # cabecera del boletín eliminada
    assert "ANUNCIO sin relación" not in " ".join(s.text for s in secs)


def test_web_markdown_sections_and_dedup():
    md = (
        "# Prestaciones\nIntro breve de la página con contexto suficiente para no fusionarse "
        "con la siguiente sección porque supera el mínimo de caracteres establecido.\n"
        + "Texto adicional. " * 15
        + "\n**Requisitos:**\n- Estar empadronado en Telde.\n- Estar empadronado en Telde.\n"
        + "- Otra condición que hay que cumplir en el momento de pedirla. " * 6
    )
    secs = chunker.parse_web_markdown(md, "Doc")
    titles = [s.title for s in secs]
    assert "Prestaciones" in titles and "Requisitos" in titles
    req = next(s for s in secs if s.title == "Requisitos")
    assert req.text.count("Estar empadronado en Telde.") == 1


def test_split_long_keeps_title_and_limit():
    s = chunker.Section("Artículo 5. Largo.", "\n".join(["Frase de prueba bastante larga."] * 200))
    parts = chunker.split_long(s)
    assert len(parts) > 1
    assert all(len(p.text) <= chunker.MAX_CHARS for p in parts)
    assert parts[0].title == "Artículo 5. Largo. (parte 1)"


def test_amount_tables_are_detected():
    assert chunker.has_amount_table("1 adulto 658 euros; 2 adultos 855 euros; 3 adultos 1.052 €")
    assert not chunker.has_amount_table("La cuantía se actualiza con el SMI. Mínimo 100 euros.")


def test_chunk_source_metadata(tmp_path):
    (tmp_path / "doc.pdf.txt").write_text(PDF_TEXT, encoding="utf-8")
    src = {
        "id": "ord-x", "documento": "Ordenanza X", "ambito": "municipal", "url": "https://x",
        "archivo": "doc.pdf.txt", "formato": "pdf", "desde": "ORDENANZA REGULADORA DE LAS",
        "fecha_documento": "2020-08-31", "excluir": ["^Artículo 2"],
    }  # fmt: skip
    chunker.pdf_to_text = lambda p: Path(p).read_text(encoding="utf-8")  # sin PDF real
    chunks = chunker.chunk_source(src, tmp_path, "2026-11-26")
    assert [c.id for c in chunks] == ["ord-x-art1"]  # art2 excluido por el manifiesto
    meta = chunks[0].meta
    for k in ("id", "documento", "seccion", "ambito", "url", "fecha_documento",
              "fecha_descarga", "validado_por_servicios_sociales"):  # fmt: skip
        assert k in meta
    assert meta["validado_por_servicios_sociales"] is False


# ----------------------------------------------------------- almacén


def _chunks():
    mk = lambda i, t, s: StoredChunk(i, t, {"id": i, "seccion": s, "documento": "D"})  # noqa: E731
    return [
        mk("d-art1", "El certificado de empadronamiento se pide en el ayuntamiento.", "Art 1"),
        mk(
            "d-art2", "La renta de ciudadanía exige inscripción como demandante de empleo.", "Art 2"
        ),
        mk("d-art3", "Las ayudas de emergencia social cubren alimentación e higiene.", "Art 3"),
    ]


def test_store_upsert_is_idempotent():
    store, emb = SQLiteVectorStore(), FakeEmbedder()
    r1 = store.upsert_source("d", _chunks(), emb.embed_passages)
    assert (r1.inserted, store.count()) == (3, 3)
    r2 = store.upsert_source("d", _chunks(), emb.embed_passages)
    assert (r2.inserted, r2.unchanged, store.count()) == (0, 3, 3)
    changed = _chunks()[:2]
    changed[0].text += " Cambio."
    r3 = store.upsert_source("d", changed, emb.embed_passages)
    assert (r3.updated, r3.deleted, store.count()) == (1, 1, 2)


def test_hybrid_retrieval_returns_relevant_with_metadata():
    store, emb = SQLiteVectorStore(), FakeEmbedder()
    store.upsert_source("d", _chunks(), emb.embed_passages)
    r = HybridRetriever(store, emb, top_k=2, min_score=0.1)
    res = r.retrieve("¿Dónde pido el certificado de empadronamiento?")
    assert res.items[0].id == "d-art1"
    assert res.items[0].meta["documento"] == "D"
    assert res.sufficient


def test_threshold_marks_insufficient():
    store, emb = SQLiteVectorStore(), FakeEmbedder()
    store.upsert_source("d", _chunks(), emb.embed_passages)
    res = HybridRetriever(store, emb, min_score=0.99).retrieve("carnet de conducir")
    assert not res.sufficient


def test_empty_store():
    res = HybridRetriever(SQLiteVectorStore(), FakeEmbedder()).retrieve("hola")
    assert res.items == [] and not res.sufficient


# ----------------------------------------------------------- KB real (integración)


@pytest.mark.integration
def test_real_kb_query_returns_relevant_fragments():
    """Ingesta real de una fuente con el modelo E5 y consulta de prueba (criterio de H2)."""
    from nflb.rag.embeddings import get_embedder

    manifest = yaml.safe_load((ROOT / "kb/manifest.yaml").read_text(encoding="utf-8"))
    src = next(s for s in manifest["fuentes"] if s["id"] == "rcc-sede")
    chunks = chunker.chunk_source(src, ROOT / "kb/sources", manifest["fecha_descarga"])
    store, emb = SQLiteVectorStore(), get_embedder()
    store.upsert_source(src["id"], [StoredChunk(c.id, c.text, c.meta) for c in chunks],
                        emb.embed_passages)  # fmt: skip
    res = HybridRetriever(store, emb, top_k=3).retrieve(
        "¿Qué documentos necesito para pedir la renta canaria de ciudadanía?"
    )
    assert res.sufficient
    text = " ".join(i.chunk.text for i in res.items).lower()
    assert "empadronamiento" in text or "dni" in text
    assert all(i.meta["url"].startswith("https://sede.gobiernodecanarias.org") for i in res.items)
