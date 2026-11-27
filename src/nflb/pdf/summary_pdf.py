"""PDF de una página (A4, ≥ 11 pt) con el resumen previo a la cita."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Frame, KeepInFrame, Paragraph, Spacer

from nflb.core.summary import NO_INDICADO, Ficha

DISCLAIMER = (
    "Resumen orientativo preparado por la propia familia con ayuda de un asistente. "
    "No es una valoración. La valoración corresponde a los Servicios Sociales del "
    "Ayuntamiento de Telde."
)
MIN_FONT = 11

_INK = HexColor("#1f2933")
_ACCENT = HexColor("#2f5d8a")


def _styles(size: float):
    body = ParagraphStyle("b", fontName="Helvetica", fontSize=size, leading=size * 1.3,
                          textColor=_INK)  # fmt: skip
    head = ParagraphStyle("h", parent=body, fontName="Helvetica-Bold", textColor=_ACCENT,
                          spaceBefore=size * 0.6, spaceAfter=size * 0.15)  # fmt: skip
    title = ParagraphStyle("t", parent=body, fontName="Helvetica-Bold", fontSize=size + 6,
                           leading=(size + 6) * 1.2, spaceAfter=size * 0.3)  # fmt: skip
    return body, head, title


def _story(f: Ficha, size: float):
    body, head, title = _styles(size)
    story = [Paragraph("Resumen para mi cita con Servicios Sociales", title),
             Paragraph(f"Fecha: {escape(f.fecha_generacion)}", body), Spacer(1, size * 0.4)]  # fmt: skip

    def text(h: str, v: str):
        story.extend([Paragraph(escape(h), head), Paragraph(escape(v), body)])

    def items(h: str, v: list[str]):
        story.append(Paragraph(escape(h), head))
        for x in v or [NO_INDICADO]:
            story.append(Paragraph(("• " if v else "") + escape(x), body))

    text("Quién vive en casa", f.composicion_hogar)
    text("Situación actual", f.situacion_actual)
    text("Lo que más necesito", f.necesidad_principal)
    items("Ayudas por las que he preguntado", f.ayudas_consultadas)
    items("Papeles que ya tengo", f.documentos_disponibles)
    items("Papeles que me faltan", f.documentos_pendientes)
    items("Preguntas para la cita", f.preguntas_para_la_cita)
    return story


def render_pdf(f: Ficha, path: Path) -> Path:
    """Siempre 1 página: si el contenido no cabe, se reduce hasta 11 pt y luego se recorta."""
    from reportlab.pdfgen.canvas import Canvas

    path.parent.mkdir(parents=True, exist_ok=True)
    w, h = A4
    margin = 1.8 * cm
    footer_h = 2.2 * cm
    c = Canvas(str(path), pagesize=A4)
    c.setTitle("Resumen para la cita")
    frame = Frame(margin, margin + footer_h, w - 2 * margin, h - 2 * margin - footer_h,
                  showBoundary=0)  # fmt: skip
    for size in (13, 12, MIN_FONT):
        story = _story(f, size)
        fits = KeepInFrame(frame._aW, frame._aH, story, mode="error")
        try:
            fits.wrap(frame._aW, frame._aH)
            break
        except Exception:
            continue
    else:  # ni a 11 pt cabe: recortar (nunca bajar del mínimo legible)
        story = [KeepInFrame(frame._aW, frame._aH, _story(f, MIN_FONT), mode="truncate")]
    frame.addFromList(story, c)

    # pie con el aviso legal
    foot = ParagraphStyle("f", fontName="Helvetica-Oblique", fontSize=MIN_FONT,
                          leading=MIN_FONT * 1.25, textColor=_INK)  # fmt: skip
    c.setStrokeColor(_ACCENT)
    c.line(margin, margin + footer_h - 0.3 * cm, w - margin, margin + footer_h - 0.3 * cm)
    p = Paragraph(escape(DISCLAIMER), foot)
    p.wrapOn(c, w - 2 * margin, footer_h)
    p.drawOn(c, margin, margin)
    c.showPage()
    c.save()
    return path
