"""Textos fijos del asistente (no generados por el modelo)."""

CIERRE = "Quien valora tu caso es tu trabajadora social."

BIENVENIDA = (
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
    "¿Aceptas?"
)

SIN_CONSENTIMIENTO = "De acuerdo. No he guardado nada. Si cambias de idea, escribe /start."

CONSENTIMIENTO_REQUERIDO = (
    "Antes de seguir necesito que aceptes cómo uso tus datos. Escribe /start, por favor."
)

AYUDA = (
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
    "o sustituir a tu trabajadora social. " + CIERRE
)

CONSENTIMIENTO_OK = "Gracias. " + AYUDA

BORRAR_PREGUNTA = (
    "¿Seguro que quieres borrar *todo* lo que tengo de ti "
    "(conversación, resúmenes, tareas y recordatorios)? No se puede deshacer."
)
BORRADO_OK = "Hecho. He borrado todos tus datos. Si quieres volver, escribe /start."
BORRADO_CANCELADO = "Vale, no he borrado nada."

NO_AUTORIZADO = "Este asistente está en pruebas y solo pueden usarlo personas invitadas."

PROXIMAMENTE = "Esta función todavía se está preparando. Prueba más tarde."

NO_SE = "No tengo esa información. Pregúntalo a tu trabajadora social. " + CIERRE
