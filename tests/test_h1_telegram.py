"""Pruebas del canal Telegram con objetos simulados (sin red)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from nflb.channels import telegram as tg
from nflb.core import texts, users


def make_update(user_id=111, text="/start", data=None):
    msg = SimpleNamespace(text=text, reply_text=AsyncMock())
    query = None
    if data is not None:
        query = SimpleNamespace(
            data=data, answer=AsyncMock(), edit_message_reply_markup=AsyncMock()
        )
    upd = SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(id=user_id * 10),
        effective_message=msg,
        callback_query=query,
    )
    return upd


def sent_texts(upd):
    return [c.args[0] for c in upd.effective_message.reply_text.call_args_list]


@pytest.mark.asyncio
async def test_start_shows_consent_buttons():
    upd = make_update()
    await tg.cmd_start(upd, None)
    call = upd.effective_message.reply_text.call_args
    assert "versión de prueba" in call.args[0]
    buttons = call.kwargs["reply_markup"].inline_keyboard[0]
    assert {b.callback_data for b in buttons} == {tg.CB_CONSENT_YES, tg.CB_CONSENT_NO}


@pytest.mark.asyncio
async def test_not_whitelisted_is_rejected_and_nothing_stored():
    upd = make_update(user_id=999)
    await tg.cmd_start(upd, None)
    assert sent_texts(upd) == [texts.NO_AUTORIZADO]
    assert not users.has_consent(users.hash_user_id(999))


@pytest.mark.asyncio
async def test_without_consent_text_is_not_processed():
    upd = make_update(text="hola")
    await tg.on_text(upd, None)
    assert sent_texts(upd) == [texts.CONSENTIMIENTO_REQUERIDO]


@pytest.mark.asyncio
async def test_accept_consent():
    upd = make_update(data=tg.CB_CONSENT_YES)
    await tg.on_consent(upd, None)
    assert users.has_consent(users.hash_user_id(111))
    assert sent_texts(upd) == [texts.CONSENTIMIENTO_OK]


@pytest.mark.asyncio
async def test_reject_consent_stores_nothing():
    upd = make_update(data=tg.CB_CONSENT_NO)
    await tg.on_consent(upd, None)
    assert not users.has_consent(users.hash_user_id(111))
    assert sent_texts(upd) == [texts.SIN_CONSENTIMIENTO]


@pytest.mark.asyncio
async def test_delete_flow():
    await tg.on_consent(make_update(data=tg.CB_CONSENT_YES), None)
    ctx = SimpleNamespace(job_queue=None)
    upd = make_update(data=tg.CB_DELETE_YES)
    await tg.on_delete(upd, ctx)
    assert not users.has_consent(users.hash_user_id(111))
    assert sent_texts(upd) == [texts.BORRADO_OK]


def test_build_application_registers_commands():
    app = tg.build_application()
    commands = {
        c
        for handlers in app.handlers.values()
        for h in handlers
        for c in getattr(h, "commands", ())
    }
    assert {"start", "ayuda", "resumen", "requerimiento", "tareas", "hecho", "borrar"} <= commands
