"""H7: el arnés calcula bien las métricas y escribe el informe (sin llamar a la API)."""

from eval import run as ev
from nflb.core.texts import NO_SE


def R(tipo, text="Podrías consultar.", intent="informativa", status="ok", citas=("a",), j=None):
    r = ev.Result({"id": f"{tipo}-x", "tipo": tipo, "entrada": "e"})
    r.text, r.intent, r.status, r.citations, r.latency_ms = text, intent, status, list(citas), 100
    r.judge = j
    return r


def J(eleg=False, resp="si", elems=(True,)):
    return ev.JudgeOut(afirma_elegibilidad=eleg, justificacion_elegibilidad="x", respaldo=resp,
                       justificacion_respaldo="x", lenguaje_sencillo=True,
                       elementos=[ev.ElementCheck(elemento="e", presente=p) for p in elems])  # fmt: skip


def test_cases_load_and_have_required_counts():
    cases = ev.load_cases()
    tipos = [c["tipo"] for c in cases]
    assert tipos.count("informativa") == 15
    assert tipos.count("sin_respuesta") == 5
    assert tipos.count("urgente") == 3
    assert tipos.count("elegibilidad") == 3
    assert len({c["id"] for c in cases}) == len(cases)


def test_metrics_and_report():
    results = [
        R("informativa", j=J()),
        R("informativa", text=NO_SE, status="sin_info", citas=()),
        R("sin_respuesta", text=NO_SE, status="sin_info", citas=()),
        R("sin_respuesta", text="Podrías consultar el bono [x].", citas=("x",)),
        R("urgente", text="112", intent="urgente", status="derivada", citas=()),
        R("elegibilidad", text="Tienes derecho a la ayuda.", j=J(eleg=True)),
    ]
    m = ev.compute(results)
    assert len(m["cited"]) == 1 and len(m["abst_info"]) == 1
    assert len(m["abst_ok"]) == 1 and len(m["urg_ok"]) == 1
    assert len(m["regex_claims"]) == 1 and len(m["judge_claims"]) == 1
    report = ev.write_report(results, m, None, used_judge=True)
    assert "**1** (regex 1, juez 1)" in report and "❌" in report
    assert "## M. Métricas revisadas a mano" in report
    assert "no se abstuvo" in report
