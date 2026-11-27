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
from nflb.core.texts import CIERRE
from nflb.i18n import t

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
    # Inglés (modo demostración, BOT_LANGUAGE=en)
    r"\b(?:hits?|beats?|hurts?|threatens?)\s+(?:me|us|my\s+(?:kids|children))\b",
    r"\b(?:domestic\s+)?(?:violence|abused?|abusing)\b",
    r"\b(?:kill\s+myself|end\s+my\s+life|don'?t\s+want\s+to\s+live|want\s+to\s+die)\b",
    r"\b(?:sleep|sleeping)\s+(?:on|in)\s+the\s+streets?\b",
    r"\b(?:homeless|nowhere\s+to\s+sleep)\s+(?:tonight|today)\b",
    r"\bevict(?:ed|ing|ion)\b.{0,20}\b(?:today|tonight|tomorrow)\b",
    r"\b(?:kids|children)\s+(?:haven'?t|have\s+not)\s+eaten\b",
    r"\bno\s+food\s+(?:today|tonight)\b",
    r"\b(?:afraid|scared)\s+of\s+my\s+(?:partner|husband|wife|boyfriend|girlfriend|ex)\b",
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
    lines = [t("🆘 *Lo que cuentas es importante y no tienes que resolverlo sola ni solo.*",
               "🆘 *What you're telling me is important, and you don't have to face it alone.*"),
             ""]  # fmt: skip
    for c in verified_contacts():
        if c["telefono"] == "112":
            lines.append(t(f"📞 *112* — {c['nombre']}. {c['cuando']}.",
                           "📞 *112* — Emergencies. If there is danger right now."))  # fmt: skip
        else:
            lines.append(f"📞 *{c['telefono']}* — {c['nombre']}. {c['cuando']}.")
    if not any(c["telefono"] == "112" for c in verified_contacts()):
        lines.append(t("📞 *112* — Emergencias. Si hay peligro ahora mismo.",
                       "📞 *112* — Emergencies. If there is danger right now."))  # fmt: skip
    lines += [
        "",
        t("Contacta *hoy* con los Servicios Sociales del Ayuntamiento de Telde y cuéntales "
          "lo que pasa.",
          "Contact Telde City Council's Social Services (Servicios Sociales) *today* and tell "
          "them what is happening."),
        "",
        t("Si quieres, después seguimos con los papeles. Lo primero es que estés a salvo.",
          "If you want, we can carry on with the paperwork afterwards. The first thing is "
          "that you are safe."),
    ]  # fmt: skip
    return "\n".join(lines)


OUT_OF_SCOPE = t(
    "Eso se me escapa: solo puedo orientarte sobre ayudas sociales y trámites relacionados "
    "en Telde. ¿Hay algo de eso en lo que te pueda ayudar?",
    "That's outside what I can do: I can only guide you on social benefits and related "
    "procedures in Telde. Is there anything like that I can help you with?",
)

EXPEDIENTE = t(
    "No tengo acceso a los expedientes ni puedo saber cómo va el tuyo. Para eso, pregunta "
    "directamente en tu Unidad de Trabajo Social o en el organismo que lo tramita.",
    "I don't have access to case files and can't know how yours is going. For that, ask "
    "your Social Work Unit (Unidad de Trabajo Social) or the office handling it directly.",
) + "\n\n" + CIERRE

SALUDO = t(
    "¡Hola! Cuéntame tu situación o pregúntame por una ayuda, y te digo qué podrías "
    "consultar. También puedo preparar un resumen para tu cita (/resumen) o ayudarte con "
    "una carta que te pida papeles (/requerimiento).",
    "Hi! Tell me about your situation or ask me about a benefit, and I'll tell you what you "
    "could ask about. I can also prepare a summary for your appointment (/summary) or help "
    "you with a letter asking you for documents (/letter).",
)

SAFE_GENERIC = t(
    "Perdona, ahora mismo no puedo darte una respuesta fiable sobre eso. Pregúntalo en tu "
    "Unidad de Trabajo Social, que es quien puede orientarte bien.",
    "Sorry, I can't give you a reliable answer about that right now. Please ask your Social "
    "Work Unit (Unidad de Trabajo Social), who can guide you properly.",
) + "\n\n" + CIERRE
