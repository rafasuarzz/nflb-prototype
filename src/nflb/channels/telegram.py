"""Canal Telegram (long polling).

Todo lo específico de Telegram vive aquí. El núcleo (`nflb.core`) no importa nada de
este módulo, para poder cambiar de servicio de mensajería sin tocarlo.
"""

from __future__ import annotations

import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from nflb.config import get_settings
from nflb.core import texts, users
from nflb.core.assistant import Assistant
from nflb.db.session import init_db
from nflb.logging_setup import get_logger, setup_logging

log = get_logger("nflb.telegram")

CB_CONSENT_YES = "consent:yes"
CB_CONSENT_NO = "consent:no"
CB_DELETE_YES = "delete:yes"
CB_DELETE_NO = "delete:no"

_assistant: Assistant | None = None


def get_assistant() -> Assistant:
    global _assistant
    if _assistant is None:
        _assistant = Assistant()
    return _assistant


def _uid(update: Update) -> str:
    return users.hash_user_id(update.effective_user.id)


def _allowed(update: Update) -> bool:
    allowed = get_settings().allowed_user_ids
    return bool(update.effective_user) and update.effective_user.id in allowed


async def _reply(update: Update, text: str, markup=None) -> None:
    msg = update.effective_message
    try:
        await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
    except Exception:  # si el Markdown falla, mejor texto plano que nada
        await msg.reply_text(text, reply_markup=markup)


async def _guard(update: Update, need_consent: bool = True) -> str | None:
    """Comprueba lista blanca y consentimiento. Devuelve el hash o None si no puede seguir."""
    if not _allowed(update):
        log.info("acceso_denegado")
        await _reply(update, texts.NO_AUTORIZADO)
        return None
    uid = _uid(update)
    if need_consent and not users.has_consent(uid):
        await _reply(update, texts.CONSENTIMIENTO_REQUERIDO)
        return None
    if need_consent:
        users.touch(uid, chat_id=update.effective_chat.id)
    return uid


# --- Comandos ---


async def cmd_start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if await _guard(update, need_consent=False) is None:
        return
    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Acepto", callback_data=CB_CONSENT_YES),
                InlineKeyboardButton("❌ No acepto", callback_data=CB_CONSENT_NO),
            ]
        ]
    )
    await _reply(update, texts.BIENVENIDA, markup)


async def on_consent(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not _allowed(update):
        return
    if query.data == CB_CONSENT_YES:
        users.give_consent(_uid(update), update.effective_chat.id)
        log.info("consentimiento_aceptado")
        await query.edit_message_reply_markup(None)
        await _reply(update, texts.CONSENTIMIENTO_OK)
    else:
        log.info("consentimiento_rechazado")
        await query.edit_message_reply_markup(None)
        await _reply(update, texts.SIN_CONSENTIMIENTO)


async def cmd_ayuda(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if await _guard(update, need_consent=False) is None:
        return
    await _reply(update, texts.AYUDA)


async def cmd_borrar(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if await _guard(update, need_consent=False) is None:
        return
    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🗑️ Sí, borrar todo", callback_data=CB_DELETE_YES),
                InlineKeyboardButton("Cancelar", callback_data=CB_DELETE_NO),
            ]
        ]
    )
    await _reply(update, texts.BORRAR_PREGUNTA, markup)


async def on_delete(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not _allowed(update):
        return
    await query.edit_message_reply_markup(None)
    if query.data == CB_DELETE_YES:
        uid = _uid(update)
        _cancel_user_jobs(ctx, uid)
        users.delete_user(uid)
        log.info("datos_borrados")
        await _reply(update, texts.BORRADO_OK)
    else:
        await _reply(update, texts.BORRADO_CANCELADO)


def _cancel_user_jobs(ctx: ContextTypes.DEFAULT_TYPE, uid: str) -> None:
    if ctx.job_queue is None:
        return
    for job in ctx.job_queue.jobs():
        if job.name and job.name.startswith(f"rem:{uid}:"):
            job.schedule_removal()


async def cmd_pending(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if await _guard(update) is None:
        return
    await _reply(update, texts.PROXIMAMENTE)


async def answer_text(update: Update, ctx, uid: str, text: str) -> None:
    """Pasa el texto al núcleo (en un hilo: las llamadas al LLM son bloqueantes)."""
    if ctx is not None and getattr(ctx, "bot", None):
        await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    reply = await asyncio.to_thread(get_assistant().handle_text, uid, text)
    await _reply(update, reply.text)


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    uid = await _guard(update)
    if uid is None:
        return
    log.info("mensaje_texto", text=update.effective_message.text)
    await answer_text(update, ctx, uid, update.effective_message.text)


async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("error_no_controlado", error=type(ctx.error).__name__)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "Perdona, algo ha fallado. Inténtalo de nuevo en un momento."
        )


# --- Arranque ---


async def _purge_job(_ctx: ContextTypes.DEFAULT_TYPE) -> None:
    n = users.purge_inactive()
    if n:
        log.info("retencion_borrado", usuarios=n)


def build_application() -> Application:
    settings = get_settings()
    if settings.telegram_bot_token is None:
        raise SystemExit("Falta TELEGRAM_BOT_TOKEN en .env")
    app = ApplicationBuilder().token(settings.telegram_bot_token.get_secret_value()).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ayuda", cmd_ayuda))
    app.add_handler(CommandHandler("help", cmd_ayuda))
    app.add_handler(CommandHandler("borrar", cmd_borrar))
    for name in ("resumen", "requerimiento", "tareas", "hecho"):
        app.add_handler(CommandHandler(name, cmd_pending))
    app.add_handler(CallbackQueryHandler(on_consent, pattern=r"^consent:"))
    app.add_handler(CallbackQueryHandler(on_delete, pattern=r"^delete:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)

    app.job_queue.run_repeating(_purge_job, interval=6 * 3600, first=10, name="purge")
    return app


def main() -> None:
    setup_logging()
    init_db()
    settings = get_settings()
    if not settings.allowed_user_ids:
        log.warning("lista_blanca_vacia", aviso="Rellena ALLOWED_USER_IDS en .env")
    log.info("bot_arrancando", modelo=settings.anthropic_model)
    build_application().run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
