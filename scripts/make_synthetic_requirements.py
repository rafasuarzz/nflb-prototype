"""Genera 5 requerimientos SINTÉTICOS (imágenes) para la evaluación del H6.

Todo el contenido es inventado: organismos genéricos, sin nombres ni DNI reales.
Uno está borroso (debe pedir otra foto) y otro está incompleto (sin fecha: no debe inventarla).
Salida: eval/requirements/*.png + eval/cases/requerimientos.yaml (verdad de referencia).
"""

from __future__ import annotations

from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "requirements"

CASES = [
    {
        "id": "req-001",
        "organismo": "AYUNTAMIENTO DE TELDE — CONCEJALÍA DE SERVICIOS SOCIALES",
        "fecha": "16 de noviembre de 2026",
        "fecha_iso": "2026-11-16",
        "plazo": 10,
        "docs": [
            "Certificado de empadronamiento colectivo",
            "Libro de familia",
            "Últimas tres nóminas o certificado de prestaciones del SEPE",
        ],
        "via": "Registro General del Ayuntamiento o sede electrónica",
    },
    {
        "id": "req-002",
        "organismo": "SERVICIO DE GESTIÓN DE PENSIONES Y AYUDAS DE INTEGRACIÓN (GOBIERNO DE CANARIAS)",
        "fecha": "3 de noviembre de 2026",
        "fecha_iso": "2026-11-03",
        "plazo": 10,
        "docs": [
            "Certificado de inscripción como demandante de empleo",
            "Anexo II - Miembros de la unidad de convivencia firmado",
            "Certificado bancario de titularidad de la cuenta",
        ],
        "via": "Sede electrónica del Gobierno de Canarias u oficinas de registro",
    },
    {
        "id": "req-003",
        "organismo": "INSTITUTO NACIONAL DE LA SEGURIDAD SOCIAL",
        "fecha": "20 de noviembre de 2026",
        "fecha_iso": "2026-11-20",
        "plazo": 10,
        "docs": [
            "Certificado de empadronamiento histórico",
            "Sentencia de divorcio o convenio regulador",
            "Declaración de la renta del último ejercicio",
        ],
        "via": "Sede electrónica de la Seguridad Social o registro",
    },
    {  # borroso
        "id": "req-004",
        "organismo": "AYUNTAMIENTO DE TELDE — CONCEJALÍA DE SERVICIOS SOCIALES",
        "fecha": "18 de noviembre de 2026",
        "fecha_iso": "2026-11-18",
        "plazo": 10,
        "docs": ["Contrato de alquiler", "Recibos de alquiler de los tres últimos meses"],
        "via": "Registro General",
        "blur": True,
    },
    {  # incompleto: sin fecha visible
        "id": "req-005",
        "organismo": "AYUNTAMIENTO DE TELDE — CONCEJALÍA DE SERVICIOS SOCIALES",
        "fecha": None,
        "fecha_iso": None,
        "plazo": 10,
        "docs": ["Informe médico actualizado", "Dos presupuestos del gasto solicitado"],
        "via": "Registro General",
    },
]


def font(size: int, bold: bool = False):
    for name in ["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def wrap(draw, text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=f) > width:
            lines.append(cur)
            cur = w
        else:
            cur = test
    return lines + [cur]


def render(c: dict, path: Path) -> None:
    W, H, M = 1240, 1754, 110  # A4 a 150 ppp
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    fb, fr, fs = font(30, True), font(27), font(22)
    y = M
    for line in wrap(d, c["organismo"], fb, W - 2 * M):
        d.text((M, y), line, fill="black", font=fb)
        y += 40
    y += 30
    d.text((M, y), "Expediente: 2026/XXXX (ficticio)", fill="black", font=fs)
    y += 34
    if c["fecha"]:
        d.text((M, y), f"Telde, a {c['fecha']}", fill="black", font=fr)
    y += 70
    d.text((M, y), "ASUNTO: REQUERIMIENTO DE SUBSANACIÓN DE DOCUMENTACIÓN", fill="black", font=fb)
    y += 70
    body = (
        "Examinada su solicitud, se ha comprobado que no aporta la documentación necesaria. "
        "De conformidad con el artículo 68 de la Ley 39/2015, se le requiere para que, en el "
        f"plazo de {c['plazo']} días hábiles a contar desde el día siguiente a la recepción de "
        "esta notificación, aporte los siguientes documentos:"
    )
    for line in wrap(d, body, fr, W - 2 * M):
        d.text((M, y), line, fill="black", font=fr)
        y += 38
    y += 20
    for i, doc in enumerate(c["docs"], 1):
        for j, line in enumerate(wrap(d, f"{i}. {doc}", fr, W - 2 * M - 40)):
            d.text((M + (40 if j else 20), y), line, fill="black", font=fr)
            y += 38
    y += 30
    tail = (
        f"La documentación podrá presentarse en: {c['via']}. Si no lo hiciera, se le "
        "tendrá por desistido de su petición, previa resolución."
    )
    for line in wrap(d, tail, fr, W - 2 * M):
        d.text((M, y), line, fill="black", font=fr)
        y += 38
    y += 80
    d.text((M, y), "LA JEFA DE SERVICIO (documento ficticio para pruebas)", fill="black", font=fs)
    if c.get("blur"):
        img = img.resize((W // 4, H // 4)).filter(ImageFilter.GaussianBlur(3)).resize((W, H))
    else:
        img = img.rotate(1.2, fillcolor="#f4f1ea", expand=False)
    img.save(path)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cases = []
    for c in CASES:
        render(c, OUT / f"{c['id']}.png")
        cases.append(
            {
                "id": c["id"],
                "tipo": "requerimiento",
                "imagen": f"eval/requirements/{c['id']}.png",
                "esperado": {
                    "ilegible": bool(c.get("blur")),
                    "fecha_notificacion": None if c.get("blur") else c["fecha_iso"],
                    "plazo_dias_habiles": None if c.get("blur") else c["plazo"],
                    "documentos": [] if c.get("blur") else c["docs"],
                },
            }
        )
    (ROOT / "eval" / "cases" / "requerimientos.yaml").write_text(
        "# 5 requerimientos sintéticos (generados por scripts/make_synthetic_requirements.py)\n"
        + yaml.safe_dump(cases, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(f"{len(cases)} requerimientos en {OUT}")


if __name__ == "__main__":
    main()
