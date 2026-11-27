"""Extracción de texto y troceado POR ESTRUCTURA (artículo / sección), no por caracteres.

Cada formato tiene su propio troceador:
- boe_html: textos consolidados del BOE (un fragmento por artículo o disposición).
- pdf:      boletines oficiales en PDF (cortes en "Artículo N.", "Disposición…", "ANEXO…").
- web_html: páginas web oficiales (cortes en encabezados y títulos en negrita).

Las secciones demasiado largas se parten en párrafos, conservando el título de la sección.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

MAX_CHARS = 1800  # ~450 tokens: cabe en la ventana de 512 de E5
MIN_CHARS = 80  # descarta entradas de índice y restos

# Fragmentos con 3 o más importes en euros = tablas de cuantías o de umbrales de ingresos.
# No se cargan: el asistente no calcula importes ni compara ingresos con umbrales (P2).
_EURO = re.compile(r"\d[\d.,]*\s*(?:€|euros?\b)", re.I)
MAX_EURO_AMOUNTS = 2


def has_amount_table(text: str) -> bool:
    return len(_EURO.findall(text)) > MAX_EURO_AMOUNTS


@dataclass
class Section:
    title: str
    text: str
    path: list[str] = field(default_factory=list)  # títulos/capítulos que la contienen


@dataclass
class Chunk:
    id: str
    source_id: str
    seccion: str
    text: str
    meta: dict


# ---------------------------------------------------------------- utilidades


def slugify(text: str, max_len: int = 40) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text[:max_len].strip("-") or "seccion"


_ORDINALS = {
    "primera": 1, "segunda": 2, "tercera": 3, "cuarta": 4, "quinta": 5, "sexta": 6,
    "septima": 7, "séptima": 7, "octava": 8, "novena": 9, "decima": 10, "décima": 10,
    "unica": 1, "única": 1,
}  # fmt: skip


def section_key(title: str) -> str:
    """Identificador corto y estable para una sección: art9, da1, anexo-vi…"""
    t = title.strip()
    if m := re.match(r"art[íi]culo\s+(\d+)\s*(bis|ter)?", t, re.I):
        return f"art{m.group(1)}{m.group(2) or ''}".lower()
    if m := re.match(
        r"disposici[oó]n\s+(adicional|transitoria|final|derogatoria)\s*(\w+)?", t, re.I
    ):
        kind = {"adicional": "da", "transitoria": "dt", "final": "df", "derogatoria": "dd"}[
            m.group(1).lower()
        ]
        raw = (m.group(2) or "única").lower()
        n = _ORDINALS.get(raw, slugify(raw, 20))
        return f"{kind}{n}"
    if m := re.match(r"anexo\s+([IVXL]+)\b", t, re.I):
        return f"anexo-{m.group(1).lower()}"
    return slugify(t, 30)


def _clean(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def split_long(section: Section) -> list[Section]:
    """Parte una sección larga en trozos por párrafos/líneas, sin cortar frases."""
    if len(section.text) <= MAX_CHARS:
        return [section]
    units = [u for u in re.split(r"\n+", section.text) if u.strip()]
    parts, cur = [], ""
    for u in units:
        while len(u) > MAX_CHARS:  # línea gigantesca: cortar por frases
            cut = u.rfind(". ", 0, MAX_CHARS)
            cut = cut + 1 if cut > MAX_CHARS // 3 else MAX_CHARS
            if cur:
                parts.append(cur)
                cur = ""
            parts.append(u[:cut].strip())
            u = u[cut:].strip()
        if len(cur) + len(u) + 1 > MAX_CHARS and cur:
            parts.append(cur)
            cur = u
        else:
            cur = f"{cur}\n{u}" if cur else u
    if cur:
        parts.append(cur)
    return [
        Section(title=f"{section.title} (parte {i})", text=p, path=section.path)
        for i, p in enumerate(parts, 1)
    ]


# ---------------------------------------------------------------- BOE (HTML)


def parse_boe_html(html: str) -> list[Section]:
    from lxml import html as lh

    root = lh.fromstring(html)
    body = root.xpath('//div[@id="textoxslt"]') or [root]
    sections: list[Section] = []
    path: dict[str, str] = {}
    current: Section | None = None
    for el in body[0].iter("h3", "h4", "h5", "p", "blockquote"):
        cls = el.get("class") or ""
        txt = _clean(el.text_content())
        if not txt:
            continue
        if el.tag == "h4" and cls.endswith("_num"):
            level = cls.split("_")[0]
            path[level] = txt
            if level == "titulo":
                path.pop("capitulo", None)
            continue
        if el.tag == "h4" and cls.endswith("_tit"):
            level = cls.split("_")[0]
            path[level] = f"{path.get(level, '')} {txt}".strip()
            continue
        if (
            el.tag in ("h4", "h5")
            and cls in ("articulo", "seccion", "preambulo")
            or (el.tag == "h4" and txt.lower().startswith(("preámbulo", "disposición")))
        ):
            current = Section(title=txt, text="", path=list(path.values()))
            sections.append(current)
            continue
        if el.tag == "p" and current is not None and "nota_pie" not in cls:
            if cls in ("fuera", "linkSubir") or txt.startswith("[Bloque"):
                continue
            current.text += txt + "\n"
    return [s for s in sections if s.text.strip()]


# ---------------------------------------------------------------- PDF (boletín)

_BOP_HEADER = re.compile(r"^\s*(\d+\s+)?Bolet[íi]n Oficial de la Provincia.*$", re.M)
_PDF_SPLIT = re.compile(
    r"^(?P<t>(?:Art[íi]culo\s+\d+\.?\s*[^\n]{0,120})"
    r"|(?:Disposici[oó]n\s+(?:adicional|transitoria|final|derogatoria)[^\n]{0,120})"
    r"|(?:ANEXO\s+[IVXL]+\b[^\n]{0,160})"
    r"|(?:CAP[ÍI]TULO\s+[\dIVXL]+\.?[^\n]{0,100})"
    r"|(?:PRE[ÁA]MBULO|ÍNDICE:?))\s*$",
    re.M,
)


def pdf_to_text(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _reflow(text: str) -> str:
    """Une las líneas cortadas por las columnas del boletín en párrafos."""
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # palabras partidas con guion
    out: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        starts_new = bool(re.match(r"^([-•·]|\d+[\.\)º]|[a-zñ]\.?\d*\)|[A-ZÁÉÍÓÚ]\.\s)", line))
        if out and not starts_new and not out[-1].endswith((".", ":", ";")):
            out[-1] += " " + line
        else:
            out.append(line)
    return "\n".join(out)


def parse_pdf_text(text: str, start_marker: str | None = None) -> list[Section]:
    if start_marker and start_marker in text:
        text = text[text.index(start_marker) :]
    text = _BOP_HEADER.sub("", text)
    text = re.sub(r"^\s*\d{1,3}\.\d{3}\s*$", "", text, flags=re.M)  # n.º de anuncio
    matches = list(_PDF_SPLIT.finditer(text))
    sections: list[Section] = []
    capitulo = ""
    for i, m in enumerate(matches):
        title = re.sub(r"\s+", " ", m.group("t")).strip()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = _reflow(text[m.end() : end])
        if title.upper().startswith("CAP"):
            capitulo = title
            continue
        # títulos de anexo que siguen en la línea siguiente (mayúsculas)
        if title.upper().startswith("ANEXO"):
            extra = re.match(r"^([A-ZÁÉÍÓÚÑ ,.()/-]{8,})\n", body)
            if extra:
                title = f"{title} {extra.group(1).strip()}"
                body = body[extra.end() :]
        sections.append(
            Section(title=title, text=_clean(body), path=[capitulo] if capitulo else [])
        )
    return _keep_longest_duplicates(sections)


def _keep_longest_duplicates(sections: list[Section]) -> list[Section]:
    """El índice repite los títulos de los artículos: nos quedamos con la versión con texto."""
    best: dict[str, Section] = {}
    order: list[str] = []
    for s in sections:
        k = section_key(s.title)
        if k not in best:
            order.append(k)
            best[k] = s
        elif len(s.text) > len(best[k].text):
            best[k] = s
    return [best[k] for k in order]


# ---------------------------------------------------------------- web (HTML)

_WEB_HEADING = re.compile(
    r"^(?:#{1,6}\s+(?P<h>.+?)\s*$"
    r"|(?:-|\d+\.)?\s*#{1,6}\s+(?P<h2>.+?)\s*$"
    r"|\*\*(?P<b>[^*]{3,120}?)\*\*\s*:?\s*(?P<rest>.*)$"
    r"|-\s+(?P<k>[A-ZÁÉÍÓÚ][^:\n]{2,60}):\s*$)",
    re.M,
)


def html_to_markdown(html: str) -> str:
    import trafilatura

    md = trafilatura.extract(html, favor_recall=True, include_tables=True, output_format="markdown")
    return md or ""


def parse_web_markdown(md: str, default_title: str) -> list[Section]:
    sections: list[Section] = []
    current = Section(title=default_title, text="")
    seen_lines: set[str] = set()
    for line in md.split("\n"):
        m = _WEB_HEADING.match(line.strip())
        if m:
            title = (m.group("h") or m.group("h2") or m.group("b") or m.group("k")).strip(" .:*")
            if current.text.strip():
                sections.append(current)
            current = Section(title=title, text="")
            rest = (m.group("rest") or "").strip()
            if rest:
                current.text += rest.replace("**", "") + "\n"
            continue
        clean = line.replace("**", "").strip()
        if not clean or clean in seen_lines and len(clean) > 15:
            continue  # las sedes repiten listas enteras
        seen_lines.add(clean)
        current.text += clean + "\n"
    if current.text.strip():
        sections.append(current)
    return _merge_small(sections)


def _merge_small(sections: list[Section]) -> list[Section]:
    """Une secciones muy cortas con la siguiente para que tengan contexto suficiente."""
    out: list[Section] = []
    carry: Section | None = None
    for s in sections:
        if carry is not None:
            s = Section(title=carry.title, text=f"{carry.text}\n{s.title}: {s.text}", path=s.path)
            carry = None
        if len(s.text) < MIN_CHARS * 3:
            carry = s
            continue
        out.append(s)
    if carry is not None:
        if out:
            out[-1].text += f"\n{carry.title}: {carry.text}"
        else:
            out.append(carry)
    return out


# ---------------------------------------------------------------- orquestación


def sections_for_source(src: dict, sources_dir: Path) -> list[Section]:
    path = sources_dir / src["archivo"]
    fmt = src["formato"]
    if fmt == "pdf":
        sections = parse_pdf_text(pdf_to_text(path), src.get("desde"))
    elif fmt == "boe_html":
        sections = parse_boe_html(path.read_text(encoding="utf-8", errors="ignore"))
    elif fmt == "web_html":
        md = html_to_markdown(path.read_text(encoding="utf-8", errors="ignore"))
        sections = parse_web_markdown(md, src["documento"])
    else:
        raise ValueError(f"Formato desconocido: {fmt}")
    excl = [re.compile(p, re.I) for p in src.get("excluir", [])]
    return [s for s in sections if not any(p.search(s.title) for p in excl)]


def chunk_source(
    src: dict,
    sources_dir: Path,
    fecha_descarga: str | None = None,
    skipped: list[str] | None = None,
) -> list[Chunk]:
    """Trocea una fuente. Si se pasa `skipped`, se le añaden los fragmentos descartados."""
    chunks: list[Chunk] = []
    used: dict[str, int] = {}
    for section in sections_for_source(src, sources_dir):
        if len(section.text) < MIN_CHARS:
            continue
        base = f"{src['id']}-{section_key(section.title)}"
        parts = split_long(section)
        for i, part in enumerate(parts, 1):
            cid = base if len(parts) == 1 else f"{base}-p{i}"
            if has_amount_table(part.text):
                if skipped is not None:
                    skipped.append(f"{cid} (tabla de importes)")
                continue
            if cid in used:
                used[cid] += 1
                cid = f"{cid}-{used[cid]}"
            else:
                used[cid] = 1
            chunks.append(
                Chunk(
                    id=cid,
                    source_id=src["id"],
                    seccion=part.title,
                    text=part.text.strip(),
                    meta={
                        "id": cid,
                        "documento": src["documento"],
                        "seccion": part.title,
                        "contexto": " › ".join(p for p in part.path if p),
                        "ambito": src["ambito"],
                        "url": src["url"],
                        "fecha_documento": src.get("fecha_documento"),
                        "fecha_descarga": fecha_descarga,
                        "validado_por_servicios_sociales": bool(
                            src.get("validado_por_servicios_sociales", False)
                        ),
                    },
                )
            )
    return chunks
