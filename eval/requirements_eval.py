"""Evaluación de la extracción de requerimientos sobre las imágenes sintéticas."""

from __future__ import annotations

from datetime import date

from rapidfuzz import fuzz

from nflb.config import ROOT_DIR
from nflb.core import deadlines, requirement

MATCH = 80  # similitud mínima (token_set_ratio) para dar un documento por correcto


def _match(expected: list[str], got: list[str]) -> int:
    used, ok = set(), 0
    for e in expected:
        best = max(((fuzz.token_set_ratio(e.lower(), g.lower()), i) for i, g in enumerate(got)
                    if i not in used), default=(0, None))  # fmt: skip
        if best[0] >= MATCH:
            ok += 1
            used.add(best[1])
    return ok


def run_requirements(llm, cases: list[dict]) -> dict:
    docs_ok = docs_total = plazo_ok = plazo_total = ileg_ok = ileg_total = 0
    detalle = []
    for c in cases:
        exp = c["esperado"]
        data = (ROOT_DIR / c["imagen"]).read_bytes()
        try:
            x = requirement.extract(llm, data, "image/png")
        except Exception as e:
            detalle.append(f"- `{c['id']}`: ERROR {type(e).__name__}")
            continue
        got = [d.documento for d in x.documentos_requeridos]
        if exp["ilegible"]:
            ileg_total += 1
            asked = requirement.needs_new_photo(x)
            ileg_ok += asked
            detalle.append(
                f"- `{c['id']}` (borroso): {'pide otra foto ✅' if asked else '❌ no pidió otra foto; extrajo: ' + '; '.join(got)}"
            )
            continue
        n = _match(exp["documentos"], got)
        docs_ok += n
        docs_total += len(exp["documentos"])
        extra = len(got) - n
        plazo_total += 1
        dl = requirement.compute_deadline(x)
        if exp["fecha_notificacion"] is None:
            good = dl is None and x.fecha_notificacion is None
            plazo_ok += good
            note = (
                "sin fecha en la carta: no inventa fecha ✅"
                if good
                else f"❌ inventó fecha {x.fecha_notificacion}"
            )
        else:
            want = deadlines.add_business_days(date.fromisoformat(exp["fecha_notificacion"]),
                                               exp["plazo_dias_habiles"])  # fmt: skip
            good = dl == want
            plazo_ok += good
            note = f"fecha límite {dl} ({'✅' if good else f'❌ esperada {want}'})"
        detalle.append(f"- `{c['id']}`: documentos {n}/{len(exp['documentos'])}"
                       f"{f' (+{extra} de más)' if extra > 0 else ''}; {note}")  # fmt: skip
    pct = lambda a, b: f"{100 * a / b:.0f} % ({a}/{b})" if b else "n/a"  # noqa: E731
    return {"docs": pct(docs_ok, docs_total), "plazo": pct(plazo_ok, plazo_total),
            "ilegible": pct(ileg_ok, ileg_total), "detalle": detalle}  # fmt: skip
