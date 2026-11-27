"""Textos fijos del asistente (no generados por el modelo). Español; inglés solo para demos."""

from nflb.i18n import t

CIERRE = t(
    "Quien valora tu caso es tu trabajadora social.",
    "Your social worker is the one who assesses your case.",
)

BIENVENIDA = t(
    "👋 Hola. Soy un asistente de orientación del proyecto *No Family Left Behind* "
    "para familias de Telde.\n\n"
    "*Qué hago:*\n"
    "• Te cuento qué ayudas *podrías consultar*, con la fuente de cada dato.\n"
    "• Te ayudo a preparar un resumen de una página para tu cita con la trabajadora social.\n"
    "• Si te piden papeles (un requerimiento), convierto la carta en una lista de tareas "
    "con recordatorios.\n\n"
    "*Qué NO hago:*\n"
    "• No decido ni valoro si te dan una ayuda.\n"
    "• No conozco el estado de tu expediente.\n"
    "• No sustituyo a tu trabajadora social.\n\n"
    "⚠️ *Esto es una versión de prueba. No compartas datos reales.*\n\n"
    "Para funcionar necesito guardar lo que me cuentes durante un tiempo "
    "(se borra solo tras 30 días sin usarme, o cuando escribas /borrar). "
    "Tú decides si enseñas el resumen a alguien.\n\n"
    "¿Aceptas?",
    "👋 Hi. I'm a guidance assistant from the *No Family Left Behind* project "
    "for families in Telde.\n\n"
    "*What I do:*\n"
    "• I tell you which benefits you *could ask about*, with the source of each fact.\n"
    "• I help you prepare a one-page summary for your appointment with the social worker.\n"
    "• If you are asked for documents (a request letter), I turn the letter into a task list "
    "with reminders.\n\n"
    "*What I DON'T do:*\n"
    "• I don't decide or assess whether you get a benefit.\n"
    "• I can't see the status of your case file.\n"
    "• I don't replace your social worker.\n\n"
    "⚠️ *This is a test version. Don't share real data.*\n\n"
    "To work, I need to keep what you tell me for a while "
    "(it is deleted automatically after 30 days without use, or when you type /delete). "
    "You decide whether to show the summary to anyone.\n\n"
    "Do you accept?",
)

SIN_CONSENTIMIENTO = t(
    "De acuerdo. No he guardado nada. Si cambias de idea, escribe /start.",
    "OK. I haven't saved anything. If you change your mind, type /start.",
)

CONSENTIMIENTO_REQUERIDO = t(
    "Antes de seguir necesito que aceptes cómo uso tus datos. Escribe /start, por favor.",
    "Before we continue, please accept how I use your data. Type /start, please.",
)

AYUDA = t(
    "*Puedes escribirme o mandarme una nota de voz* contándome tu situación "
    "o preguntando por una ayuda.\n\n"
    "*Comandos:*\n"
    "/resumen — prepara un resumen para tu cita\n"
    "/requerimiento — cómo enviarme la foto de una carta que te pide papeles\n"
    "/tareas — los papeles que te faltan\n"
    "/hecho <n> — marca un papel como conseguido\n"
    "/borrar — borra todos tus datos\n"
    "/ayuda — este mensaje\n\n"
    "*Lo que no puedo hacer:* decidir si te dan una ayuda, ver tu expediente "
    "o sustituir a tu trabajadora social. " + CIERRE,
    "*You can write to me or send me a voice note* telling me about your situation "
    "or asking about a benefit.\n\n"
    "*Commands:*\n"
    "/summary — prepare a summary for your appointment\n"
    "/letter — how to send me a photo of a letter asking you for documents\n"
    "/tasks — the documents you still need\n"
    "/done <n> — mark a document as obtained\n"
    "/delete — delete all your data\n"
    "/help — this message\n\n"
    "*What I can't do:* decide whether you get a benefit, see your case file "
    "or replace your social worker. " + CIERRE,
)

CONSENTIMIENTO_OK = t("Gracias. ", "Thank you. ") + AYUDA

BORRAR_PREGUNTA = t(
    "¿Seguro que quieres borrar *todo* lo que tengo de ti "
    "(conversación, resúmenes, tareas y recordatorios)? No se puede deshacer.",
    "Are you sure you want to delete *everything* I have about you "
    "(conversation, summaries, tasks and reminders)? This cannot be undone.",
)
BORRADO_OK = t(
    "Hecho. He borrado todos tus datos. Si quieres volver, escribe /start.",
    "Done. I've deleted all your data. If you want to come back, type /start.",
)
BORRADO_CANCELADO = t("Vale, no he borrado nada.", "OK, I haven't deleted anything.")

NO_AUTORIZADO = t(
    "Este asistente está en pruebas y solo pueden usarlo personas invitadas.",
    "This assistant is in testing and only invited people can use it.",
)

PROXIMAMENTE = t(
    "Esta función todavía se está preparando. Prueba más tarde.",
    "This feature is still being prepared. Try again later.",
)

NO_SE = t(
    "No tengo esa información. Pregúntalo a tu trabajadora social. ",
    "I don't have that information. Please ask your social worker. ",
) + CIERRE
