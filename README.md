# No Family Left Behind — prototipo

Asistente de IA (Telegram, texto y voz) que orienta a familias de Telde sobre ayudas sociales.
**Informa y prepara; nunca decide.** Prototipo con **datos sintéticos únicamente**.

> README en construcción: se completa en el hito H8 (instalación, arquitectura,
> limitaciones de privacidad, qué cambiaría en el piloto y guion de demo).

## Arranque rápido (provisional)

Requisitos: [uv](https://docs.astral.sh/uv/) (instala Python 3.12 solo para el proyecto).

```powershell
uv sync
copy .env.example .env   # y rellena los valores
uv run nflb-bot
```

Pruebas: `uv run pytest` · Calidad: `uv run ruff check src tests`

## Estado por hitos

- [x] H1 — Esqueleto, configuración, BD, `/start` con consentimiento, `/ayuda`, `/borrar`
- [ ] H2 — Ingesta de la KB + recuperación híbrida
- [ ] H3 — Consultas informativas con citas + guardarraíles
- [ ] H4 — Notas de voz
- [ ] H5 — Resumen previo a la cita
- [ ] H6 — Requerimientos
- [ ] H7 — Evaluación
- [ ] H8 — README y demo
