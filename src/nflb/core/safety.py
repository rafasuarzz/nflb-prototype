"""Derivación urgente (sección 7.4) y respuestas fijas fuera de alcance (7.5).

La detección de urgencias tiene DOS capas:
1. Reglas deterministas (regex) que se evalúan antes que nada: si saltan, se deriva siempre,
   aunque el clasificador LLM falle o la API no responda.
2. La categoría `urgente` del clasificador de intención, para lo que las reglas no capten.

El bloque de urgencias es un texto fijo (no generado). Los teléfonos salen de
data/contactos.yaml y solo se muestran los verificados; el 112 siempre.
"""

from __future__ import annotations

import re
from functools import lru_cache

import yaml

from nflb.config import ROOT_DIR

_URGENT_PATTERNS = [
    r"\bme\s+(?:pega|pegan|pegó|pego|maltrata|amenaza|amenazan)\b",
    r"\b(?:violencia|maltrato|agresión|agresion|abus(?:o|a|an)\b)",
    r"\b(?:quitarme|quitar\s*me)\s+la\s+vida\b",
    r"\bsuicid",
    r"\b(?:matarme|morirme|no\s+quiero\s+vivir|acabar\s+con\s+todo)\b",
    r"\b(?:dormir|duermo|dormimos)\s+en\s+la\s+calle\b",
    r"\b(?:sin|no\s+tengo|no\s+tenemos)\s+(?:techo|dónde|donde)\s+dormir\b",
    r"\bnos\s+(?:echan|desahucian|han\s+echado)\s+(?:hoy|esta\s+noche|mañana)\b",
    r"\bdesahucio\s+(?:hoy|mañana|esta\s+semana)\b",
    r"\b(?:los|mis)\s+(?:niños|hijos|niñas|hijas)\s+(?:no\s+han\s+comido|están\s+en\s+peligro|solos)\b",
    r"\bno\s+(?:tenemos|tengo)\s+(?:nada\s+)?(?:para\s+)?comer\s+(?:hoy|esta\s+noche)\b",
    r"\b(?:tengo|tiene)\s+miedo\s+(?:de|a)\s+(?:mi|su)\s+(?:pareja|marido|mujer|novio|ex)\b",
]
_URGENT = [re.compile(p, re.I) for p in _URGENT_PATTERNS]


def is_urgent_by_rules(text: str) -> bool:
    return any(p.search(text) for p in _URGENT)


@lru_cache
def verified_contacts() -> list[dict]:
    path = ROOT_DIR / "data" / "contactos.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [c for c in data["contactos"] if c.get("verificado") and c.get("telefono")]


def urgent_block() -> str:
    lines = ["🆘 *Lo que cuentas es importante y no tienes que resolverlo sola ni solo.*", ""]
    for c in verified_contacts():
        lines.append(f"📞 *{c['telefono']}* — {c['nombre']}. {c['cuando']}.")
    if not any(c["telefono"] == "112" for c in verified_contacts()):
        lines.append("📞 *112* — Emergencias. Si hay peligro ahora mismo.")
    lines += [
        "",
        "Contacta *hoy* con los Servicios Sociales del Ayuntamiento de Telde y cuéntales "
        "lo que pasa.",
        "",
        "Si quieres, después seguimos con los papeles. Lo primero es que estés a salvo.",
    ]
    return "\n".join(lines)


OUT_OF_SCOPE = (
    "Eso se me escapa: solo puedo orientarte sobre ayudas sociales y trámites relacionados "
    "en Telde. ¿Hay algo de eso en lo que te pueda ayudar?"
)

EXPEDIENTE = (
    "No tengo acceso a los expedientes ni puedo saber cómo va el tuyo. Para eso, pregunta "
    "directamente en tu Unidad de Trabajo Social o en el organismo que lo tramita.\n\n"
    "Quien valora tu caso es tu trabajadora social."
)

SALUDO = (
    "¡Hola! Cuéntame tu situación o pregúntame por una ayuda, y te digo qué podrías "
    "consultar. También puedo preparar un resumen para tu cita (/resumen) o ayudarte con "
    "una carta que te pida papeles (/requerimiento)."
)

SAFE_GENERIC = (
    "Perdona, ahora mismo no puedo darte una respuesta fiable sobre eso. Pregúntalo en tu "
    "Unidad de Trabajo Social, que es quien puede orientarte bien.\n\n"
    "Quien valora tu caso es tu trabajadora social."
)
