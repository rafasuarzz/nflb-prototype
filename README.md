# No Family Left Behind — prototipo

Asistente de IA por **Telegram** (texto, notas de voz y fotos) que orienta a familias de Telde
sobre ayudas sociales municipales, autonómicas y estatales.

**Informa y prepara; nunca decide.** No evalúa la elegibilidad, no accede a expedientes y no
sustituye a la trabajadora social. Prototipo para la candidatura a Cities Deliver:
**solo datos sintéticos**.

| Qué hace | Cómo |
|---|---|
| Informa de qué ayudas *podrías consultar* | Respuestas ancladas a 6 fuentes oficiales, con la fuente citada |
| Prepara un resumen de 1 página para la cita | `/resumen` → ficha → confirmación → PDF |
| Convierte la foto de un requerimiento en tareas | Foto → lista de papeles → fecha límite estimada → recordatorios |

Resultados de la evaluación: [`eval/report.md`](eval/report.md).

---

## 1. Instalación

Requisitos: Windows, macOS o Linux con [uv](https://docs.astral.sh/uv/). `uv` instala él solo
Python 3.12 para el proyecto (no sirve 3.13+: `faster-whisper` y `torch` aún no tienen versión).

```powershell
uv sync                                   # dependencias (torch en versión CPU)
copy .env.example .env                    # y rellénalo (ver abajo)
uv run python scripts/ingest.py           # carga la base de conocimiento (1.ª vez: descarga E5)
uv run nflb-bot                           # arranca el bot
```

**`.env`** (nunca se sube al repositorio):

| Variable | De dónde sale |
|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |
| `TELEGRAM_BOT_TOKEN` | En Telegram, @BotFather → `/newbot` |
| `ALLOWED_USER_IDS` | Ids numéricos de las personas de prueba (pídelos a @userinfobot), separados por comas. **Lista blanca:** nadie más puede usar el bot |
| `USER_ID_SALT` | Cadena aleatoria larga. No cambiarla una vez en uso |

Otras: `ANTHROPIC_MODEL` (por defecto `claude-sonnet-5-5`), `JUDGE_MODEL`, `WHISPER_MODEL`
(`small`), `RETENTION_DAYS` (30), `DEBUG_LOG_CONTENT` (`false`).

**Pruebas y evaluación**

```powershell
uv run pytest -m "not integration"        # 78 pruebas unitarias, sin red
uv run pytest                             # + integración con el modelo E5 real
uv run python -m eval.run                 # evaluación completa → eval/report.md (~5 min, usa la API)
uv run python -m eval.wer                 # WER sobre las notas de voz de eval/audio/
uv run ruff check src tests eval scripts
```

## 2. Comandos del bot

`/start` (presentación y consentimiento) · `/ayuda` · `/resumen` · `/requerimiento` ·
`/tareas` · `/hecho <n>` · `/borrar` (borra todo, con confirmación).

## 3. Arquitectura

```
Telegram (texto / voz / foto)
   │  channels/telegram.py  ← único módulo que conoce Telegram (cambiable)
   │        └─(voz)→ stt/whisper.py (faster-whisper local) → "He entendido: …"
   ▼
core/assistant.py (fachada)
   ├─ core/safety.py   reglas deterministas de urgencia → bloque fijo con 112
   ├─ core/router.py   intención con salida estructurada (urgente, informativa, expediente…)
   ├─ core/info.py     rag/retriever.py (E5 + BM25 + RRF) → LLM → verificación de citas
   ├─ core/summary.py  ficha → confirmación → pdf/summary_pdf.py
   └─ core/requirement.py  visión → tareas → core/deadlines.py → recordatorios (JobQueue + BD)
   ▼
core/guardrails.py  frases prohibidas (también en negativo), citas válidas, datos sensibles, cierre
```

- **LLM desacoplado:** interfaz `LLMProvider` (`llm/base.py`) con `AnthropicProvider` y un
  esqueleto `OpenAIProvider`. El núcleo no importa ningún SDK.
- **Base de conocimiento:** `kb/manifest.yaml` → `scripts/ingest.py` trocea **por artículo o
  sección** (383 fragmentos), calcula embeddings locales y carga la BD. Es idempotente.
- **Almacenamiento:** SQLite (`var/nflb.db`). La especificación pide PostgreSQL + pgvector;
  Docker no estaba disponible, así que se implementó la misma interfaz `VectorStore` sobre
  SQLite. `docker-compose.yml` queda preparado para el piloto.

### Decisiones que conviene conocer

1. **Sin `temperature`.** `claude-sonnet-5-5` rechaza valores distintos del de por defecto. La
   estabilidad se consigue con salidas estructuradas (JSON Schema) y esfuerzo bajo.
2. **Frases de elegibilidad bloqueadas incluso en negativo** ("no puedo decirte si cumples los
   requisitos" también se bloquea). El prompt pide no usarlas nunca, y así la métrica de
   "0 afirmaciones" no tiene falsos positivos.
3. **Se excluyen de la KB las tablas de importes y umbrales de ingresos** (Anexo I de la
   ordenanza, cuantías del IMV y de la RCC). El asistente no compara ingresos con umbrales
   (P2), y no tenerlos en el contexto lo hace más difícil.
4. **El umbral de relevancia apenas filtra.** E5 comprime las similitudes (0,79–0,91) y no
   separa bien lo que está en la KB de lo que no. La abstención real la hacen el prompt
   ("solo con el contexto") y la verificación de citas. La tasa de abstención de la
   evaluación es la medida que importa.
5. **La urgencia se detecta en dos capas:** primero reglas fijas (derivan aunque la API
   falle), después el clasificador. El bloque de urgencias es texto fijo. Solo muestra los
   teléfonos con `verificado: true` en `data/contactos.yaml` (hoy, solo el 112).
6. **El plazo lo calcula el sistema, no el modelo:** días hábiles desde el día siguiente a la
   notificación (Ley 39/2015, art. 30), sin sábados, domingos ni festivos
   (`data/festivos.yaml`). Siempre se presenta como **fecha límite estimada**.

## 4. Fuentes y flujo de validación

`kb/manifest.yaml` recoge las 6 fuentes oficiales con su URL y su fecha:

- Ordenanza de prestaciones económicas de Telde (BOP Las Palmas n.º 105, 31/08/2020).
- Web de prestaciones municipales de Telde.
- Ley 19/2021 del IMV (consolidada).
- IMV en lectura fácil (Ministerio de Inclusión).
- Ley 5/2022 de la Renta Canaria de Ciudadanía (consolidada).
- Trámite 7441 de la sede del Gobierno de Canarias.

Cada fragmento lleva `validado_por_servicios_sociales: false`. **Flujo para el piloto:**

1. Rafa revisa cada fuente y pone `verificada_por_rafa: true`.
2. Servicios Sociales revisa el contenido y cambia `validado_por_servicios_sociales` a `true`
   en el manifiesto.
3. Se vuelve a ejecutar `scripts/ingest.py`, que solo actualiza lo que ha cambiado.
4. Opcional en el piloto: usar solo los fragmentos validados.

Si un tema no está en la KB, el asistente responde "No tengo esa información; pregúntalo a tu
trabajadora social". **No usa el conocimiento general del modelo.**

Pendientes conocidos:

- Ficha oficial del certificado de empadronamiento en Telde (no encontrada).
- Fiestas locales de Telde y la insular de Gran Canaria (vacías).
- Verificación de los festivos nacionales y autonómicos.
- Verificación del 016, el 024 y el teléfono de Servicios Sociales de Telde.

## 5. Limitaciones de privacidad del prototipo

- **Telegram no cifra de extremo a extremo los chats con bots.** Aceptable con datos
  sintéticos; **no** para familias reales.
- **API externa:** el texto de los mensajes y las fotos de los requerimientos se envían a la
  API de Anthropic (EE. UU.) para generar las respuestas. El audio **no**: se transcribe en
  local.
- **Solo datos sintéticos.** Lista blanca de usuarios (`ALLOWED_USER_IDS`).
- Qué se guarda:
  - El id de Telegram con hash HMAC y sal.
  - El `chat_id`, que hace falta para enviar los recordatorios.
  - Los últimos 10 turnos de conversación.
  - Las fichas confirmadas y los PDF.
  - Las extracciones de requerimientos confirmadas.
- **Las fotos y los audios no se guardan:** la foto solo existe en memoria durante la
  extracción, y el audio en una carpeta temporal que se borra al transcribirlo.
- `/borrar` elimina al momento todo lo anterior, PDF incluidos. Borrado automático tras **30
  días** sin actividad.
- Los logs son JSON y **no registran el contenido** de mensajes ni transcripciones, salvo con
  `DEBUG_LOG_CONTENT=true`.

## 6. Qué cambiaría en el piloto

- **Residencia de datos en la UE:** despliegue en la nube europea y un proveedor de LLM con
  procesamiento en la UE, o el modelo que figure en la candidatura, gracias a `LLMProvider`.
- **Contrato de encargo de tratamiento** con cada proveedor y **evaluación de impacto de
  protección de datos (EIPD)**.
- **Canal definitivo:** otro servicio de mensajería, cambiando solo `channels/`.
- Fuentes validadas por Servicios Sociales y teléfonos y festivos verificados.
- PostgreSQL + pgvector (`docker-compose.yml`) en lugar de SQLite.
- Evaluación con casos reales anonimizados y revisada por trabajadoras sociales.
- Respuestas por voz y otros idiomas (Fase 2).

## 7. Guion de demo (3 minutos)

Ver [`DEMO.md`](DEMO.md).
