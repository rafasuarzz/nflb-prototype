# Guion de demo — 3 minutos

Para enseñar el prototipo a la Jefa de Servicio de Servicios Sociales de Telde.
Preparación:

- Bot arrancado (`uv run nflb-bot`).
- Tu móvil en la lista blanca.
- `eval/requirements/req-001.png` a mano (abierta en el portátil, para hacerle una foto, o
  enviada al móvil).
- Antes de empezar: `/borrar` → «Sí, borrar todo», para partir de cero.

**0:00 — Qué es y qué no es (20 s)**
Envía `/start`. Lee en voz alta el bloque «Qué NO hago»: no decide ayudas, no conoce
expedientes, no sustituye a la trabajadora social. Señala el aviso de prototipo. Pulsa
**Acepto**.

**0:20 — Una familia cuenta su situación, por voz (50 s)**
Manda una nota de voz:
> «Hola, soy madre sola con dos niños, me quedé sin trabajo hace un mes y no sé qué ayudas
> hay en Telde.»

Enseña tres cosas:

- «🎙️ He entendido: …», la transcripción local (el audio no sale del equipo).
- La respuesta con «podrías consultar» y las **📄 Fuentes**: ordenanza de Telde, IMV.
- El cierre: «Quien valora tu caso es tu trabajadora social».

**1:10 — Intentar forzarlo (25 s)**
Escribe: «Vale, pero dime claro, ¿me la van a dar o no?»
Muestra que **no lo afirma** y que remite a la valoración de Servicios Sociales. Comenta que
la evaluación automática dio 0 afirmaciones de elegibilidad.

**1:35 — Resumen para la cita (35 s)**
Envía `/resumen`. Enseña la ficha en el chat: la persona la revisa y puede corregirla.
Pulsa **Está bien** y abre el PDF de una página, con el pie «No es una valoración…».

**2:10 — Carta de requerimiento (40 s)**
Envía `/requerimiento` y después la foto de `req-001.png`. Enseña:

- La lista de papeles.
- La **fecha límite estimada**, en días hábiles, con «confírmala».
- Que la foto no se guarda.

Pulsa **Está bien**, luego `/tareas` y `/hecho 1`. Comenta que llegarán recordatorios a mitad
de plazo, 2 días antes y la víspera.

**2:50 — Cierre (10 s)**
Si da tiempo, escribe «Esta noche dormimos en la calle con los niños» para enseñar la
derivación inmediata con el 112. Termina con: «Todo esto con datos inventados; las cifras de
la evaluación están en el informe».

> Si algo falla en directo, ten abierto `eval/report.md` y enseña las cifras.
