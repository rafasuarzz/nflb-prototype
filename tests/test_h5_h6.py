"""H5 (resumen + PDF) y H6 (requerimientos, plazos y recordatorios que sobreviven a un reinicio)."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

from pypdf import PdfReader

from nflb.core import deadlines, records, requirement, summary, users
from nflb.pdf.summary_pdf import DISCLAIMER, render_pdf
from tests.fakes import FakeLLM, FakeRetriever, chunk

NO_HOL = frozenset()

# ------------------------------------------------------------------ días hábiles


def test_business_days_skip_weekends_and_holidays():
    # Viernes 2026-12-04 + 3 hábiles: lun 7, (mar 8 festivo), mié 9, jue 10
    assert deadlines.add_business_days(date(2026, 12, 4), 3) == date(2026, 12, 10)
    assert deadlines.add_business_days(date(2026, 12, 4), 3, NO_HOL) == date(2026, 12, 9)


def test_ten_business_days_from_notification():
    # Notificada el lunes 2026-11-16: cuenta desde el martes 17 → 10 hábiles = lunes 30
    assert deadlines.add_business_days(date(2026, 11, 16), 10, NO_HOL) == date(2026, 11, 30)


def test_reminder_dates():
    d = deadlines.reminder_dates(date(2026, 11, 16), date(2026, 11, 30), today=date(2026, 11, 16))
    assert d["vispera"] == date(2026, 11, 27) and d["dos_dias"] == date(2026, 11, 26)
    assert date(2026, 11, 17) <= d["mitad"] < d["dos_dias"]


# ------------------------------------------------------------------ resumen + PDF

FICHA = {
    "composicion_hogar": "Vivo con mis dos hijos de 5 y 8 años",
    "situacion_actual": "Me quedé sin trabajo hace un mes. Cobro 300 euros de una pensión.",
    "necesidad_principal": "Pagar el alquiler y la comida",
    "ayudas_consultadas": ["Ingreso Mínimo Vital", "Tienes derecho a la ayuda municipal"],
    "documentos_disponibles": ["DNI"],
    "documentos_pendientes": [],
    "preguntas_para_la_cita": ["¿Qué papeles tengo que llevar?"],
    "fecha_generacion": "",
}


def test_ficha_sanitized_no_amounts_no_eligibility_and_no_indicado():
    f = summary.build_ficha(FakeLLM({"Ficha": [FICHA]}), [{"role": "user", "content": "x"}])
    assert "300 euros" not in f.situacion_actual and "[importe omitido]" in f.situacion_actual
    assert f.ayudas_consultadas == ["Ingreso Mínimo Vital"]
    text = summary.ficha_as_text(f)
    assert "No indicado" in text  # documentos_pendientes vacío
    assert f.fecha_generacion == date.today().isoformat()


def test_pdf_is_one_a4_page_with_disclaimer(tmp_path):
    f = summary.sanitize(summary.Ficha(**FICHA))
    p = render_pdf(f, tmp_path / "r.pdf")
    reader = PdfReader(str(p))
    assert len(reader.pages) == 1
    text = " ".join(reader.pages[0].extract_text().split())
    assert "No es una valoración" in text and "Servicios Sociales" in text
    assert DISCLAIMER.split(".")[0] in text


def test_pdf_long_content_still_one_page(tmp_path):
    long = dict(FICHA, preguntas_para_la_cita=["Pregunta larga " * 12] * 25)
    p = render_pdf(summary.sanitize(summary.Ficha(**long)), tmp_path / "r.pdf")
    assert len(PdfReader(str(p)).pages) == 1


# ------------------------------------------------------------------ requerimientos

EXTR = {
    "organismo_emisor": "Ayuntamiento de Telde - Servicios Sociales",
    "fecha_notificacion": "2026-11-16",
    "plazo_dias_habiles": 10,
    "fecha_limite_estimada": "2026-12-31",  # el modelo se equivoca: lo recalcula el sistema
    "documentos_requeridos": [
        {"documento": "Certificado de empadronamiento", "detalle": None, "confianza": "alta"},
        {"documento": "Vida laboral", "detalle": "actualizada", "confianza": "baja"},
    ],
    "via_de_entrega": "Registro municipal",
    "texto_no_legible": False,
}


def test_extraction_and_deadline_computed_by_system():
    x = requirement.extract(FakeLLM({"Extraccion": [EXTR]}), b"img", "image/jpeg")
    assert not requirement.needs_new_photo(x)
    dl = requirement.compute_deadline(x)
    assert dl == deadlines.add_business_days(date(2026, 11, 16), 10)
    text = requirement.confirmation_text(
        x,
        requirement.tasks_from(x, [{"instrucciones": requirement.ASK_UTS, "fuente": None}] * 2),
        dl,
    )
    assert "Fecha límite estimada" in text and "Confírmala" in text
    assert "no se lee bien" in text  # confianza baja señalada


def test_illegible_or_empty_asks_new_photo():
    x = requirement.Extraccion(texto_no_legible=True)
    assert requirement.needs_new_photo(x)
    x2 = requirement.Extraccion(texto_no_legible=False, documentos_requeridos=[])
    assert requirement.needs_new_photo(x2)


def test_missing_date_no_deadline_invented():
    x = requirement.Extraccion.model_validate(dict(EXTR, fecha_notificacion=None))
    assert requirement.compute_deadline(x) is None
    assert "no puedo estimar" in requirement.deadline_text(x, None)


def test_instructions_only_from_kb_with_valid_citation():
    retr = FakeRetriever(
        [chunk("telde-web-como-acceder", "Se pide en el registro", sec="Cómo acceder")]
    )
    llm = FakeLLM({"_HelpOut": [{"documentos": [
        {"numero": 1, "instrucciones": "Se pide en el registro municipal [telde-web-como-acceder]", "cita": "telde-web-como-acceder"},
        {"numero": 2, "instrucciones": "En la web de la Seguridad Social", "cita": "inventado"},
    ]}]})  # fmt: skip
    out = requirement.instructions_for(llm, retr, ["Empadronamiento", "Vida laboral"])
    assert out[0]["fuente"] and "registro" in out[0]["instrucciones"]
    assert out[1] == {"instrucciones": requirement.ASK_UTS, "fuente": None}


def test_tasks_done_and_reminders_survive_restart():
    from nflb.channels.telegram import restore_reminders

    uid = users.hash_user_id(111)
    users.give_consent(uid, 999)
    x = requirement.Extraccion.model_validate(EXTR)
    tasks = requirement.tasks_from(x, [{"instrucciones": "a", "fuente": None}] * 2)
    today = date.today()
    notified = today - timedelta(days=1)
    deadline = deadlines.add_business_days(notified, 10)
    req_id = records.save_requirement(uid, x.model_dump(), tasks, deadline)
    rows = records.plan_reminders(uid, req_id, notified, deadline, today)
    assert len(rows) >= 2

    ok, tasks2 = records.mark_done(uid, 1)
    assert ok and tasks2[0]["hecho"] and not tasks2[1]["hecho"]
    assert records.latest_requirement(uid).tasks[0]["hecho"]  # persistido

    # "Reinicio": un JobQueue nuevo recupera los recordatorios desde la BD
    scheduled = []
    jq = SimpleNamespace(run_once=lambda cb, when, data, name: scheduled.append((data, when, name)))
    assert restore_reminders(jq) == len(rows)
    assert {d for d, _, _ in scheduled} == {r.id for r in rows}
    assert all(w > datetime.now(UTC) for _, w, _ in scheduled)

    records.mark_sent(rows[0].id)
    scheduled.clear()
    assert restore_reminders(jq) == len(rows) - 1

    users.delete_user(uid)  # /borrar se lleva también requerimientos y recordatorios
    assert records.pending_reminders() == []


def test_reminder_message_lists_pending_only():
    tasks = [{"documento": "A", "hecho": True}, {"documento": "B", "hecho": False}]
    msg = requirement.reminder_message("vispera", tasks, date(2026, 11, 30), date(2026, 11, 27))
    assert "• B" in msg and "• A" not in msg
    assert requirement.reminder_message("vispera", [{"documento": "A", "hecho": True}],
                                        date(2026, 11, 30), date(2026, 11, 27)) == ""  # fmt: skip
