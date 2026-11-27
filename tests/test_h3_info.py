"""H3: respuestas citadas, guardarraíles, derivación urgente y fuera de alcance."""

import pytest

from nflb.core import guardrails, safety, texts
from nflb.core.assistant import Assistant
from nflb.llm.base import LLMError
from tests.fakes import FakeLLM, FakeRetriever, chunk

INFO = "informativa"


def route(intent=INFO, q="ayudas emergencia"):
    return {"intencion": intent, "consulta_busqueda": q}


def info(resp, citas=(), sin=False, acl=False):
    return {"respuesta": resp, "citas": list(citas), "sin_informacion": sin,
            "es_pregunta_aclaratoria": acl}  # fmt: skip


def make(scripted, chunks=None, sufficient=True):
    chunks = chunks or [chunk("ord-telde-art9", sec="Artículo 9. Requisitos generales.")]
    return Assistant(FakeLLM(scripted), FakeRetriever(chunks, sufficient))


# ------------------------------------------------------------------ guardarraíles


@pytest.mark.parametrize(
    "text",
    [
        "Tienes derecho a la ayuda.",
        "No puedo decirte si cumples los requisitos.",  # bloqueada también en negativo
        "Seguro que te dan la renta.",
        "Te la van a conceder pronto.",
        "Te corresponde el ingreso mínimo vital.",
        "Podrías cobrar… no: puedes cobrar el IMV.",
        "Tendrías derecho a pedirla.",
        "TIENES DERECHO",
    ],
)
def test_forbidden_detected(text):
    assert guardrails.find_forbidden(text)


@pytest.mark.parametrize(
    "text",
    [
        "Podrías consultar la Renta Canaria de Ciudadanía.",
        "Podría interesarte preguntar por las ayudas de emergencia social.",
        "En la norma se pide estar empadronada en Telde.",
        "Quien valora tu caso es tu trabajadora social.",
    ],
)
def test_allowed_phrasing_passes(text):
    assert guardrails.find_forbidden(text) == []


def test_pii_masked_but_emergency_numbers_kept():
    out = guardrails.mask_pii("Mi DNI 12345678Z, NIE X1234567L, tel 612 345 678, llama al 112")
    assert "12345678Z" not in out and "X1234567L" not in out and "612 345 678" not in out
    assert "112" in out


def test_citation_verification():
    assert guardrails.invalid_citations("Dato [a-art1] y [zz-art9]", ["a-art1"], {"a-art1"}) == [
        "zz-art9"
    ]
    assert guardrails.strip_citations("Dato [a-art1].") == "Dato."


# ------------------------------------------------------------------ flujo informativo


def test_informative_answer_is_cited_rendered_and_closed():
    a = make({"_RouterOut": [route()], "InfoOut": [
        info("• Podrías consultar las prestaciones municipales [ord-telde-art9].",
             ["ord-telde-art9"])]})  # fmt: skip
    r = a.respond("Me quedé sin trabajo, ¿qué ayudas hay?")
    assert r.status == "ok" and r.citations == ["ord-telde-art9"]
    assert "[ord-telde-art9]" not in r.text
    assert "📄 Fuente: Ordenanza de Telde, Artículo 9. Requisitos generales" in r.text
    assert r.text.endswith(texts.CIERRE)


def test_forbidden_phrase_triggers_regeneration():
    a = make({"_RouterOut": [route()], "InfoOut": [
        info("Tienes derecho a la ayuda [ord-telde-art9].", ["ord-telde-art9"]),
        info("Podrías consultar la ayuda [ord-telde-art9].", ["ord-telde-art9"]),
    ]})  # fmt: skip
    r = a.respond("¿Me la dan?")
    assert r.status == "ok" and "derecho" not in r.text
    correction = a.llm.calls[-1][1][-1]["content"]
    assert "expresiones prohibidas" in correction


def test_persistent_forbidden_phrase_gives_safe_generic():
    bad = info("Cumples los requisitos [ord-telde-art9].", ["ord-telde-art9"])
    r = make({"_RouterOut": [route()], "InfoOut": [bad, bad]}).respond("¿Cumplo?")
    assert r.status == "bloqueada" and r.text == safety.SAFE_GENERIC
    assert not guardrails.find_forbidden(r.text)


def test_invented_citation_twice_gives_no_se():
    bad = info("Dato [inventado-art99].", ["inventado-art99"])
    r = make({"_RouterOut": [route()], "InfoOut": [bad, bad]}).respond("Pregunta")
    assert r.status == "bloqueada" and r.text == texts.NO_SE


def test_uncited_answer_is_regenerated_then_abstains():
    bad = info("Hay muchas ayudas, pregunta.")
    r = make({"_RouterOut": [route()], "InfoOut": [bad, bad]}).respond("Pregunta")
    assert r.text == texts.NO_SE


def test_model_says_no_info():
    r = make({"_RouterOut": [route()], "InfoOut": [info("", sin=True)]}).respond("¿Beca comedor?")
    assert r.status == "sin_info" and r.text == texts.NO_SE


def test_low_relevance_abstains_without_calling_generator():
    a = make({"_RouterOut": [route()]}, sufficient=False)
    r = a.respond("¿Cómo saco el carnet de conducir?")
    assert r.text == texts.NO_SE
    assert [c[0] for c in a.llm.calls] == ["_RouterOut"]


def test_clarifying_question_has_no_sources_block():
    a = make({"_RouterOut": [route()], "InfoOut": [
        info("¿Estás empadronada en Telde?", acl=True)]})  # fmt: skip
    r = a.respond("Necesito ayuda")
    assert r.status == "aclaratoria" and "Fuente" not in r.text


def test_clarifying_with_cited_info_keeps_sources_and_closing():
    a = make({"_RouterOut": [route()], "InfoOut": [
        info("Podrías consultar [ord-telde-art9]. ¿Estás empadronada?", ["ord-telde-art9"], acl=True)]})  # fmt: skip
    r = a.respond("Necesito ayuda")
    assert r.status == "ok" and "📄 Fuente" in r.text and r.text.endswith(texts.CIERRE)


def test_llm_failure_in_generation_is_safe():
    r = make({"_RouterOut": [route()], "InfoOut": [LLMError("caída")]}).respond("Pregunta")
    assert r.status == "error" and r.text == safety.SAFE_GENERIC


# ------------------------------------------------------------------ otras intenciones


@pytest.mark.parametrize(
    "msg",
    [
        "Mi pareja me pega y tengo miedo",
        "Esta noche dormimos en la calle con los niños",
        "Ya no quiero vivir, quiero acabar con todo",
    ],
)
def test_urgent_by_rules_without_llm(msg):
    a = make({})  # sin respuestas programadas: si se llamara al LLM fallaría
    r = a.respond(msg)
    assert r.intent == "urgente" and "112" in r.text
    assert a.llm.calls == []


def test_urgent_by_classifier():
    r = make({"_RouterOut": [route("urgente")]}).respond("Mi hijo está fatal y no sé qué hacer")
    assert r.intent == "urgente" and r.text == safety.urgent_block()


def test_urgent_block_shows_only_verified_numbers():
    block = safety.urgent_block()
    assert "112" in block
    for c in safety.verified_contacts():
        assert c["verificado"] is True


@pytest.mark.parametrize(
    "intent,expected",
    [
        ("fuera_de_alcance", safety.OUT_OF_SCOPE),
        ("estado_expediente", safety.EXPEDIENTE),
        ("saludo", safety.SALUDO),
    ],
)
def test_fixed_intents(intent, expected):
    assert make({"_RouterOut": [route(intent)]}).respond("x").text == expected


def test_router_failure_falls_back_to_grounded_info():
    a = make({"_RouterOut": [LLMError("caída")], "InfoOut": [
        info("Podrías consultar [ord-telde-art9].", ["ord-telde-art9"])]})  # fmt: skip
    assert a.respond("¿Ayudas?").status == "ok"


def test_handle_text_persists_history():
    from nflb.core import users

    uid = users.hash_user_id(111)
    users.give_consent(uid, 1)
    a = make({"_RouterOut": [route("saludo")]})
    a.handle_text(uid, "hola")
    assert [h["role"] for h in users.get_history(uid)] == ["user", "assistant"]


def test_accented_or_malformed_ids_are_caught():
    assert guardrails.cited_ids("Dato [ley-imv-daduodécima-p1].") == ["ley-imv-daduodécima-p1"]
    assert guardrails.strip_citations("Dato [ley-imv-daduodécima-p1].") == "Dato."
    assert guardrails.cited_ids("[importe omitido]") == []


def test_section_key_is_ascii_for_unknown_ordinals():
    from nflb.rag.chunker import section_key

    assert section_key("Disposición adicional duodécima. Transición") == "daduodecima"
