"""Canal Telegram (long polling).

Todo lo específico de Telegram vive aquí. El núcleo (`nflb.core`) no importa nada de
este módulo, para poder cambiar de servicio de mensajería sin tocarlo.
"""

from __future__ import annotations

import asyncio
import tempfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

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
from nflb.core import records, requirement, summary, texts, users
from nflb.core.assistant import Assistant
from nflb.db.session import init_db
from nflb.i18n import t
from nflb.llm.base import LLMError
from nflb.logging_setup import get_logger, setup_logging
from nflb.pdf.summary_pdf import render_pdf

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
                InlineKeyboardButton(t("✅ Acepto", "✅ I accept"), callback_data=CB_CONSENT_YES),
                InlineKeyboardButton(t("❌ No acepto", "❌ I don't accept"), callback_data=CB_CONSENT_NO),
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
                InlineKeyboardButton(t("🗑️ Sí, borrar todo", "🗑️ Yes, delete everything"),
                                     callback_data=CB_DELETE_YES),
                InlineKeyboardButton(t("Cancelar", "Cancel"), callback_data=CB_DELETE_NO),
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


def _kb(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t, callback_data=d) for t, d in row] for row in rows]
    )


# --- /resumen (H5) ---

CB_SUM_OK = "sum:ok"
CB_SUM_FIX = "sum:fix"
SUM_BUTTONS = (
    [(t("✅ Está bien, hazme el PDF", "✅ That's right, make the PDF"), CB_SUM_OK)],
    [(t("✏️ Quiero corregir algo", "✏️ I want to correct something"), CB_SUM_FIX)],
)


async def cmd_resumen(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    uid = await _guard(update)
    if uid is None:
        return
    history = users.get_history(uid)
    if not any(h["role"] == "user" for h in history):
        await _reply(update, t("Primero cuéntame un poco tu situación y luego preparo el resumen.",
                             "First tell me a bit about your situation, then I'll prepare the summary."))
        return
    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        ficha = await asyncio.to_thread(summary.build_ficha, get_assistant().llm, history)
    except LLMError:
        await _reply(update, t("Ahora no puedo preparar el resumen. Inténtalo en un rato.",
                             "I can't prepare the summary right now. Try again shortly."))
        return
    if summary.is_empty(ficha):
        await _reply(
            update,
            t("Todavía no sé lo suficiente para el resumen. Cuéntame quién vive en casa "
              "y qué necesitas.",
              "I don't know enough for the summary yet. Tell me who lives at home "
              "and what you need."),
        )
        return
    ctx.user_data["ficha"] = ficha.model_dump()
    ctx.user_data.pop("fixing_summary", None)
    await _reply(update, summary.ficha_as_text(ficha), _kb(*SUM_BUTTONS))


async def on_summary(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not _allowed(update) or "ficha" not in ctx.user_data:
        return
    uid = _uid(update)
    await query.edit_message_reply_markup(None)
    if query.data == CB_SUM_FIX:
        ctx.user_data["fixing_summary"] = True
        await _reply(update, t("Dime qué quieres cambiar (por ejemplo: «somos 3 en casa, no 4»).",
                               "Tell me what you want to change (for example: \"there are 3 of us at home, not 4\")."))
        return
    ficha = summary.Ficha.model_validate(ctx.user_data.pop("ficha"))
    path = users.user_files_dir(uid) / f"{t('resumen', 'summary')}-{ficha.fecha_generacion}.pdf"
    await asyncio.to_thread(render_pdf, ficha, path)
    records.save_summary(uid, ficha.model_dump(), True, str(path))
    with path.open("rb") as f:
        await update.effective_message.reply_document(
            f,
            filename=path.name,
            caption=t("Aquí tienes tu resumen. Tú decides si lo enseñas en la cita.",
                      "Here is your summary. You decide whether to show it at the appointment."),
        )


async def _fix_summary(update: Update, ctx, text: str) -> None:
    ficha = summary.Ficha.model_validate(ctx.user_data["ficha"])
    try:
        ficha = await asyncio.to_thread(summary.apply_corrections, get_assistant().llm, ficha, text)
    except LLMError:
        await _reply(update, t("No he podido aplicar el cambio. Prueba otra vez.",
                             "I couldn't apply the change. Please try again."))
        return
    ctx.user_data["ficha"] = ficha.model_dump()
    ctx.user_data.pop("fixing_summary", None)
    await _reply(update, summary.ficha_as_text(ficha), _kb(*SUM_BUTTONS))


# --- Requerimientos (H6) ---

CB_REQ_OK = "req:ok"
CB_REQ_NO = "req:no"


async def cmd_requerimiento(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if await _guard(update) is None:
        return
    await _reply(update, requirement.HOW_TO)


async def on_file(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    uid = await _guard(update)
    if uid is None:
        return
    msg = update.effective_message
    if msg.photo:
        tg_file, mime = await msg.photo[-1].get_file(), "image/jpeg"
    elif msg.document and msg.document.mime_type in ("application/pdf", "image/jpeg", "image/png"):
        tg_file, mime = await msg.document.get_file(), msg.document.mime_type
    else:
        await _reply(update, t("Ese tipo de archivo no lo puedo leer. Mándame una foto o un PDF.",
                             "I can't read that type of file. Send me a photo or a PDF."))
        return
    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    # La imagen solo vive en memoria durante la extracción: no se guarda en disco.
    data = bytes(await tg_file.download_as_bytearray())
    llm = get_assistant().llm
    try:
        x = await asyncio.to_thread(requirement.extract, llm, data, mime)
    except LLMError:
        await _reply(update, t("Ahora no puedo leer la carta. Inténtalo en un rato.",
                             "I can't read the letter right now. Try again shortly."))
        return
    finally:
        del data
    log.info("requerimiento_extraido", docs=len(x.documentos_requeridos),
             ilegible=x.texto_no_legible)  # fmt: skip
    if requirement.needs_new_photo(x):
        await _reply(update, requirement.NEW_PHOTO)
        return
    docs = [d.documento for d in x.documentos_requeridos]
    helps = await asyncio.to_thread(
        requirement.instructions_for, llm, get_assistant().retriever, docs
    )
    tasks = requirement.tasks_from(x, helps)
    deadline = requirement.compute_deadline(x)
    ctx.user_data["req"] = {
        "x": x.model_dump(),
        "tasks": tasks,
        "deadline": deadline.isoformat() if deadline else None,
    }
    await _reply(
        update,
        requirement.confirmation_text(x, tasks, deadline),
        _kb([(t("✅ Está bien", "✅ That's right"), CB_REQ_OK),
             (t("❌ No coincide", "❌ It doesn't match"), CB_REQ_NO)]),
    )


async def on_requirement(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not _allowed(update) or "req" not in ctx.user_data:
        return
    await query.edit_message_reply_markup(None)
    pending = ctx.user_data.pop("req")
    if query.data == CB_REQ_NO:
        await _reply(update, t("Vale, no guardo nada. Mándame otra foto más clara de la carta.",
                             "OK, I won't save anything. Send me a clearer photo of the letter."))
        return
    uid = _uid(update)
    deadline = date.fromisoformat(pending["deadline"]) if pending["deadline"] else None
    req_id = records.save_requirement(uid, pending["x"], pending["tasks"], deadline)
    msg = t("Guardado. Escribe /tareas para ver la lista y /hecho <número> al conseguir "
            "cada papel.",
            "Saved. Type /tasks to see the list and /done <number> when you get each "
            "document.")
    notified = pending["x"].get("fecha_notificacion")
    if deadline and notified:
        rows = records.plan_reminders(uid, req_id, date.fromisoformat(notified), deadline)
        for r in rows:
            schedule_reminder(ctx.job_queue, r.id, uid, r.when)
        if rows:
            msg += t(f"\n\n⏰ Te avisaré {len(rows)} veces antes del {deadline:%d/%m/%Y}.",
                     f"\n\n⏰ I'll remind you {len(rows)} times before {deadline:%d/%m/%Y}.")
    await _reply(update, msg)


async def cmd_tareas(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    uid = await _guard(update)
    if uid is None:
        return
    req = records.latest_requirement(uid)
    if req is None:
        await _reply(update, t("No tengo ninguna lista todavía.", "I don't have any list yet.") + "\n\n"
                     + requirement.HOW_TO)
        return
    dl = (f"\n\n📅 {t('Fecha límite estimada', 'Estimated deadline')}: {req.deadline:%d/%m/%Y}"
          if req.deadline else "")
    await _reply(update, t("*Tus papeles:*", "*Your documents:*") + "\n" + requirement.tasks_text(req.tasks) + dl)


async def cmd_hecho(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    uid = await _guard(update)
    if uid is None:
        return
    try:
        n = int(ctx.args[0])
    except (IndexError, ValueError, TypeError):
        await _reply(update, t("Escribe /hecho y el número del papel, por ejemplo: /hecho 2",
                             "Type /done and the document number, for example: /done 2"))
        return
    ok, tasks = records.mark_done(uid, n)
    if not ok:
        await _reply(update, t("No encuentro ese número. Mira la lista con /tareas.",
                             "I can't find that number. Check the list with /tasks."))
        return
    left = sum(not t["hecho"] for t in tasks)
    extra = (
        t("¡Ya lo tienes todo! Entrégalo antes de la fecha límite.",
          "You have everything! Hand it in before the deadline.")
        if left == 0
        else t(f"Te quedan {left}.", f"{left} left.")
    )
    await _reply(update, f"✅ {t('Marcado', 'Marked')}: {tasks[n - 1]['documento']}. {extra}")


def schedule_reminder(job_queue, reminder_id: int, uid: str, when) -> None:
    if job_queue is None:
        return
    job_queue.run_once(_send_reminder, when=when, data=reminder_id, name=f"rem:{uid}:{reminder_id}")


async def _send_reminder(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    found = records.reminder_context(ctx.job.data)
    if not found:
        return
    r, req, chat_id = found
    text = requirement.reminder_message(r.kind, req.tasks, req.deadline, date.today())
    if text and chat_id:
        await ctx.bot.send_message(chat_id, text)
    records.mark_sent(r.id)


def restore_reminders(job_queue) -> int:
    """Al arrancar, vuelve a programar los recordatorios guardados en la BD."""
    n = 0
    now = datetime.now(UTC)
    for r, _req, _chat in records.pending_reminders():
        when = r.when if r.when.tzinfo else r.when.replace(tzinfo=UTC)
        if when < now - timedelta(hours=12):  # demasiado antiguo: se descarta
            records.mark_sent(r.id)
            continue
        schedule_reminder(job_queue, r.id, r.user_id, max(when, now + timedelta(seconds=5)))
        n += 1
    return n


# --- Notas de voz (H4) ---


async def on_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    uid = await _guard(update)
    if uid is None:
        return
    from nflb.stt.whisper import transcribe

    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    voice = update.effective_message.voice or update.effective_message.audio
    tg_file = await voice.get_file()
    with tempfile.TemporaryDirectory() as tmp:  # el audio se borra al salir del bloque
        path = Path(tmp) / "nota.ogg"
        await tg_file.download_to_drive(path)
        text = await asyncio.to_thread(transcribe, path)
    log.info("voz_transcrita", transcript=text, chars=len(text))
    if not text:
        await _reply(update, t("No he entendido la nota de voz. ¿Me la repites o me lo escribes?",
                             "I didn't understand the voice note. Could you repeat it or write it?"))
        return
    await _reply(update, t(f"🎙️ He entendido: «{text}»\n_Si no es eso, escríbemelo y lo corrijo._",
                             f"🎙️ I understood: \"{text}\"\n_If that's not right, write it to me and I'll correct it._"))
    await answer_text(update, ctx, uid, text)


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
    if ctx is not None and ctx.user_data.get("fixing_summary"):
        await _fix_summary(update, ctx, update.effective_message.text)
        return
    await answer_text(update, ctx, uid, update.effective_message.text)


async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("error_no_controlado", error=type(ctx.error).__name__)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            t("Perdona, algo ha fallado. Inténtalo de nuevo en un momento.",
              "Sorry, something went wrong. Please try again in a moment.")
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
    app.add_handler(CommandHandler("resumen", cmd_resumen))
    app.add_handler(CommandHandler("requerimiento", cmd_requerimiento))
    app.add_handler(CommandHandler("tareas", cmd_tareas))
    app.add_handler(CommandHandler("hecho", cmd_hecho))
    # Alias en inglés (modo demostración)
    app.add_handler(CommandHandler("delete", cmd_borrar))
    app.add_handler(CommandHandler("summary", cmd_resumen))
    app.add_handler(CommandHandler(["letter", "requirement"], cmd_requerimiento))
    app.add_handler(CommandHandler("tasks", cmd_tareas))
    app.add_handler(CommandHandler("done", cmd_hecho))
    app.add_handler(CallbackQueryHandler(on_consent, pattern=r"^consent:"))
    app.add_handler(CallbackQueryHandler(on_delete, pattern=r"^delete:"))
    app.add_handler(CallbackQueryHandler(on_summary, pattern=r"^sum:"))
    app.add_handler(CallbackQueryHandler(on_requirement, pattern=r"^req:"))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, on_file))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, on_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)

    app.job_queue.run_repeating(_purge_job, interval=6 * 3600, first=10, name="purge")
    log.info("recordatorios_restaurados", n=restore_reminders(app.job_queue))
    return app


def main() -> None:
    setup_logging()
    init_db()
    settings = get_settings()
    if not settings.allowed_user_ids:
        log.warning("lista_blanca_vacia", aviso="Rellena ALLOWED_USER_IDS en .env")
    log.info("bot_arrancando", modelo=settings.anthropic_model, idioma=settings.bot_language)
    get_assistant().warm_up()  # carga E5 y la KB ahora, no en el primer mensaje
    build_application().run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
