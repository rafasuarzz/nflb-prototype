"""Guardarraíles de post-procesado (sección 7.3).

- Frases prohibidas de elegibilidad (P1/P2). Se bloquean INCLUSO EN NEGATIVO
  ("no puedo decirte si cumples los requisitos" también se bloquea): el prompt prohíbe esas
  expresiones en cualquier forma, así la métrica "0 afirmaciones" no tiene falsos positivos.
- Verificación de citas: todo [id] citado debe estar entre los fragmentos recuperados.
- Enmascarado de datos sensibles en la salida (DNI/NIE, IBAN, teléfono, correo).
- Cierre obligatorio (P4).
"""

from __future__ import annotations

import re

from nflb.core.texts import CIERRE

FORBIDDEN_PATTERNS = [
    r"\btienes?\s+derecho\b",
    r"\btend(?:rás|ras|ría|ria)s?\s+derecho\b",
    r"\bcumples?\s+(?:con\s+)?(?:todos\s+)?(?:los\s+)?requisitos\b",
    r"\bcumplir(?:ías|ias|ás|as)\s+(?:con\s+)?(?:los\s+)?requisitos\b",
    r"\bte\s+(?:la\s+|lo\s+|las\s+|los\s+)?(?:van\s+a\s+)?conceder(?:án|an|ían|ian)?\b",
    r"\bte\s+(?:la\s+|lo\s+)?conceden\b",
    r"\bte\s+corresponde(?:n|rá|ra|ría|ria)?\b",
    r"\bseguro\s+que\s+te\s+(?:la\s+|lo\s+)?(?:dan|darán|daran|conceden)\b",
    r"\bte\s+(?:la\s+|lo\s+)?(?:van\s+a\s+)?dar(?:án|an)?\s+(?:la\s+|esa\s+)?(?:ayuda|prestación|prestacion|renta)\b",
    r"\beres\s+(?:una?\s+)?(?:persona\s+)?beneficiari[oa]\b",
    r"\b(?:sí|si)\s+(?:que\s+)?(?:puedes|podrías|podrias)\s+cobrar\b",
    r"\bpuedes\s+cobrar\b",
    r"\bcobrarás\b|\bcobraras\b",
    r"\bte\s+(?:la\s+)?aprobar(?:án|an)\b",
    r"\bcalific(?:as|arías|arias)\s+para\b",
    r"\beres\s+elegible\b",
    # Inglés (modo demostración, BOT_LANGUAGE=en). También en negativo.
    r"\byou(?:'re|\s+are|'d\s+be|\s+would\s+be)\s+(?:not\s+)?(?:entitled|eligible)\b",
    r"\byou\s+(?:do\s+not\s+|don'?t\s+|would\s+|will\s+)?qualify\b",
    r"\byou\s+(?:do\s+not\s+|don'?t\s+)?meet\s+(?:all\s+)?(?:the\s+)?(?:requirements|criteria)\b",
    r"\byou\s+(?:have|'ve\s+got)\s+(?:the\s+|a\s+)?right\s+to\s+(?:receive|get|claim|the)\b",
    r"\byou(?:'ll|\s+will)\s+(?:be\s+granted|be\s+awarded|be\s+approved)\b",
    r"\byou(?:'ll|\s+will)\s+(?:get|receive)\s+(?:it|the\s+(?:benefit|aid|help|payment|allowance|income))\b",
    r"\b(?:they|it)(?:'ll|\s+will)\s+(?:grant|give|award|approve)\s+(?:you|it)\b",
    r"\byou\s+can\s+(?:collect|receive)\s+(?:it|the\s+(?:benefit|aid|payment|allowance|income|money))\b",
    r"\byou(?:'re|\s+are)\s+(?:a\s+)?beneficiary\b",
]
_FORBIDDEN = [re.compile(p, re.I) for p in FORBIDDEN_PATTERNS]


def find_forbidden(text: str) -> list[str]:
    return [m.group(0) for p in _FORBIDDEN for m in [p.search(text)] if m]


# --- datos sensibles ---------------------------------------------------------

_PII = [
    (re.compile(r"\b[XYZ]\s?-?\d{7}\s?-?[A-Z]\b", re.I), "[NIE oculto]"),
    (re.compile(r"\b\d{8}\s?-?[A-Z]\b", re.I), "[DNI oculto]"),
    (re.compile(r"\bES\d{2}(?:[ ]?\d{4}){5}\b", re.I), "[IBAN oculto]"),
    (
        re.compile(r"(?<!\d)(?:\+34[ ]?)?[6789]\d{2}[ ]?\d{3}[ ]?\d{3}(?!\d)"),
        "[teléfono oculto]",
    ),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"), "[correo oculto]"),
]

# Teléfonos públicos que sí pueden aparecer (bloque de urgencias)
_ALLOWED_NUMBERS = {"112", "016", "024", "060", "020"}


def mask_pii(text: str) -> str:
    for rx, repl in _PII:
        text = rx.sub(lambda m, r=repl: m.group(0) if m.group(0) in _ALLOWED_NUMBERS else r, text)
    return text


# --- citas -------------------------------------------------------------------

# Cualquier token entre corchetes con aspecto de id (incluye letras con tilde, para que un
# id mal formado también se detecte y se valide en lugar de colarse en la respuesta).
CITE_RX = re.compile(r"\[([^\W_][\w-]{2,119})\]")


def cited_ids(text: str) -> list[str]:
    return list(dict.fromkeys(CITE_RX.findall(text)))


def invalid_citations(text: str, declared: list[str], allowed: set[str]) -> list[str]:
    ids = set(cited_ids(text)) | set(declared)
    return sorted(i for i in ids if i not in allowed)


def strip_citations(text: str) -> str:
    text = CITE_RX.sub("", text)
    text = re.sub(r"[ \t]+([.,;:])", r"\1", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def ensure_closing(text: str) -> str:
    return text if CIERRE.lower() in text.lower() else f"{text.rstrip()}\n\n{CIERRE}"
