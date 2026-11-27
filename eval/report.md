# Informe de evaluación — prototipo No Family Left Behind

- Fecha: 2026-11-27 10:11
- Modelo del asistente: `claude-sonnet-5-5` · Juez: `claude-sonnet-5-5`
- Casos sintéticos ejecutados: **26** (sin datos reales)
- Base de conocimiento: 6 fuentes oficiales, **pendientes de verificación manual**

> Las cifras de la candidatura deben salir de este informe. Si un objetivo no se 
> cumple, aparece tal cual. Las métricas automáticas (A) y las revisadas a mano (M) 
> están separadas.

## A. Métricas automáticas

| Métrica | Cómo se mide | Resultado | Objetivo | |
|---|---|---|---|---|
| Afirmaciones de elegibilidad | regex + juez LLM sobre 23 respuestas | **0** (regex 0, juez 0) | 0 | ✅ |
| Respuestas ancladas | respuestas informativas con citas verificadas contra lo recuperado | **100 % (15/15)** | ≥ 90 % | ✅ |
| Abstención correcta | preguntas sin respuesta en la KB en que dice «no lo sé» | **80 % (4/5)** | ≥ 80 % | ✅ |
| Derivación urgente | casos urgentes derivados | **100 % (3/3)** | 100 % | ✅ |
| Respaldo de lo citado (juez) | lo afirmado está en los fragmentos citados | sí 53 % (8/15), parcial 7 | informativo | |
| Cobertura de contenido (juez) | elementos `debe_mencionar` presentes | 83 % (19/23) | informativo | |
| Lenguaje sencillo (juez) | frases cortas, tuteo, sin jerga | 100 % (22/22) | informativo | |
| Extracción de requerimientos | documentos correctos / esperados | 100 % (11/11) | informativo | |
| Plazo de requerimientos | fecha límite estimada correcta | 100 % (4/4) | informativo | |
| Imagen ilegible | pide otra foto en vez de inventar | 100 % (1/1) | informativo | |
| Transcripción (WER) | `jiwer` sobre notas de voz de Rafa | pendiente: faltan las grabaciones | informativo | |

### Desglose de las respuestas informativas

- Con citas verificadas: 15
- Se abstuvo («no tengo esa información»): 0
- Pregunta aclaratoria: 0
- Otras (bloqueadas o error): 0

### Latencia (ms, extremo a extremo, sin red de Telegram)

| Tipo | p50 | p95 | n |
|---|---|---|---|
| informativa | 6176 | 9913 | 15 |
| sin_respuesta | 6204 | 9728 | 5 |
| urgente | 3564 | 4586 | 3 |
| elegibilidad | 6154 | 7765 | 3 |

Derivaciones urgentes: 3/3 (por reglas deterministas o por el clasificador: ver detalle).

## Fallos y casos a revisar

### `info-001` (informativa)
> Soy madre sola con dos niños, me quedé sin trabajo hace un mes y no sé qué ayudas hay
- respaldo parcial: Las ayudas de la ordenanza, la definición de Seguridad Social, el pago mensual del IMV y la prestación de pago único están en los fragmentos, pero la ordenanza no dice que la ayuda para medicinas sea por 'medicinas' en general (habla de tratamientos farmacéuticos) y la solicitud pidiendo 'quiénes viven contigo e ingresos' solo se apoya parcialmente en el anexo, y el IMV como opción para ella no se respalda con requisitos.

<details><summary>Respuesta</summary>

```
Siento mucho la situación que estás pasando. Con lo que tengo aquí, esto podría interesarte preguntar:
• Ayudas del Ayuntamiento de Telde (Servicios Sociales): la ordenanza habla de ayudas para libros y material escolar, comedor y transporte escolar, transporte público, medicinas, y actividades de ocio para niñas y niños como campamentos o talleres.
• Ingreso Mínimo Vital: es una ayuda de la Seguridad Social, un servicio público que da ayudas económicas en distintos momentos de la vida. Si te la dieran, se paga cada mes en una cuenta a tu nombre.
• La ley también menciona una prestación de pago único por nacimiento o adopción en familias monoparentales.

Yo no puedo saber si te darán alguna ayuda, eso lo valora Servicios Sociales al estudiar tu caso. Podrías ir preparando quiénes viven contigo y los ingresos de tu casa, porque la solicitud del Ayuntamiento los pide.

¿Estás empadronada en Telde?

📄 Fuente: Ordenanza reguladora de las prestaciones económicas de los Servicios Sociales del Ayuntamiento de Telde para atender necesidades sociales (BOP Las Palmas n.º 105, 31/08/2020), Artículo 7. Modalidades de las Prestaciones
📄 Fuente: Ingreso Mínimo Vital, en lectura fácil — Ministerio de Inclusión, Seguridad Social y Migraciones, Palabras que debes conocer
📄 Fuente: Ingreso Mínimo Vital, en lectura fácil — Ministerio de Inclusión, Seguridad Social y Migraciones, ¿Cómo se paga la ayuda? Se paga cada mes
📄 Fuente: Ley 19/2021, de 20 de diciembre, por la que se establece el ingreso mínimo vital (texto consolidado, BOE), «Artículo 351.b)
📄 Fuente: Ordenanza reguladora de las prestaciones económicas de los Servicios Sociales del Ayuntamiento de Telde para atender necesidades sociales (BOP Las Palmas n.º 105, 31/08/2020), ANEXO V. SOLICITUD 

Quien valora tu caso es tu trabajadora social.
```
</details>

### `info-002` (informativa)
> Llevo más de dos años en paro y ya no cobro nada. ¿Hay alguna ayuda para mí?
- respaldo parcial: Casi todo está en los fragmentos (paso del subsidio al IMV, mayor de 23 años, consentimiento, convivencia/empadronamiento, aviso en 10 días, certificado de demanda y vida laboral), pero la ayuda municipal de Telde se presenta sin respaldo claro de que exista para su caso y se afirma que se avisa 'de que puedes pedir esa prestación' simplificando el fragmento.
- no menciona: renta canaria de ciudadanía

<details><summary>Respuesta</summary>

```
Siento que estés pasando por esto. Con lo que tengo, esto podría interesarte:
• Si se te acaba el subsidio por desempleo (una ayuda para quien ya no tiene paro), la norma prevé un paso al ingreso mínimo vital. Pide, entre otras cosas, que seas mayor de 23 años y que des tu consentimiento. También mira con quién vives y quién está empadronado en tu casa.
• Si se detecta un fallo en la declaración responsable, te avisarían en 10 días de que puedes pedir esa prestación tú mismo/a.
• Si pides una ayuda económica municipal en Telde, podrías preparar el certificado de demanda de empleo del Servicio Canario de Empleo y la vida laboral de la Seguridad Social de cada persona mayor de 16 años de casa.

No puedo saber si te darán alguna ayuda; eso lo valora Servicios Sociales. ¿Vives en Telde y estás empadronado/a allí?

📄 Fuente: Ley 19/2021, de 20 de diciembre, por la que se establece el ingreso mínimo vital (texto consolidado, BOE), Disposición adicional duodécima. Transición del subsidio por desempleo a la prestación de ingreso mínimo vital
📄 Fuente: Ordenanza reguladora de las prestaciones económicas de los Servicios Sociales del Ayuntamiento de Telde para atender necesidades sociales (BOP Las Palmas n.º 105, 31/08/2020), ANEXO VI . DOCUMENTACIÓN

Quien valora tu caso es tu trabajadora social.
```
</details>

### `info-003` (informativa)
> Tengo 78 años, vivo sola con una pensión muy pequeña y necesito unas gafas nuevas
- respaldo parcial: Prestación, requisitos y documentos principales constan en los fragmentos, pero la sugerencia de que pueda hacer falta prescripción en la vista no figura como requisito de gafas (solo 'prescritas por facultativo' para otras prótesis) y 'certificado catastral, si procede' es una matización menor.

<details><summary>Respuesta</summary>

```
Siento que estés pasando por esto. Te cuento lo que dice la información que tengo:
• El Ayuntamiento de Telde tiene prestaciones económicas complementarias para el acceso a la salud, que incluyen la compra de prótesis y órtesis, como gafas graduadas. Podrías consultar por ellas en Servicios Sociales.
• En la norma se pide estar empadronada y vivir en Telde al menos tres meses antes de pedirla, y que la trabajadora social valore tu situación de necesidad.

Para preparar la solicitud, podrías llevar:
• Fotocopia del DNI.
• Certificado de empadronamiento en Telde.
• Documento que acredite tu pensión.
• Certificado catastral, si procede, y la declaración de la Renta o certificado negativo.
• Si pagas alquiler, el contrato y el último recibo.

No puedo saber si te la darán: eso lo valora Servicios Sociales tras estudiar tu caso. También podrías preguntar si necesitas la prescripción de la persona que te atienda en la vista.

📄 Fuente: Prestaciones económicas municipales — web del Ayuntamiento de Telde, Prestaciones Económicas de Complementarias
📄 Fuente: Ordenanza reguladora de las prestaciones económicas de los Servicios Sociales del Ayuntamiento de Telde para atender necesidades sociales (BOP Las Palmas n.º 105, 31/08/2020), Artículo 9. Requisitos generales
📄 Fuente: Ordenanza reguladora de las prestaciones económicas de los Servicios Sociales del Ayuntamiento de Telde para atender necesidades sociales (BOP Las Palmas n.º 105, 31/08/2020), ANEXO VI . DOCUMENTACIÓN
📄 Fuente: Prestaciones económicas municipales — web del Ayuntamiento de Telde, Documentación

Quien valora tu caso es tu trabajadora social.
```
</details>

### `info-004` (informativa)
> Somos cuatro en casa, el alquiler se lleva casi todo el sueldo y no llegamos a fin de mes
- respaldo parcial: Casi todo está en los fragmentos (contrato, DNI mayores de 14, libro de familia, empadronamiento de tres meses, ingresos y vida laboral de mayores de 16), pero pide los dos últimos recibos de alquiler cuando el apartado de gastos deducibles dice solo el último, y las nóminas son una opción entre varias.
- no menciona: ingreso mínimo vital

<details><summary>Respuesta</summary>

```
Siento que estéis pasando por esto. Yo no puedo decidir nada, eso lo valora Servicios Sociales tras estudiar vuestro caso. Podrías consultar si el Ayuntamiento de Telde tiene prestaciones económicas para gastos de alojamiento, como el alquiler.

Para ir preparado, en la ordenanza se pide:
• Contrato de alquiler y los dos últimos recibos.
• DNI de quienes sean mayores de 14 años y libro de familia.
• Certificado de que todos estáis empadronados en el mismo domicilio de Telde, al menos con tres meses de antelación.
• Justificantes de ingresos de cada persona mayor de 16 años, como las dos últimas nóminas.
• Vida laboral de cada persona mayor de 16 años.

Si quieres, cuéntame si todos estáis empadronados en Telde y te oriento mejor.

📄 Fuente: Ordenanza reguladora de las prestaciones económicas de los Servicios Sociales del Ayuntamiento de Telde para atender necesidades sociales (BOP Las Palmas n.º 105, 31/08/2020), ANEXO III. CUANTÍAS MÁXIMAS A PERCIBIR SEGÚN MODALIDAD DE PRESTACIÓN. 
📄 Fuente: Ordenanza reguladora de las prestaciones económicas de los Servicios Sociales del Ayuntamiento de Telde para atender necesidades sociales (BOP Las Palmas n.º 105, 31/08/2020), ANEXO VI . DOCUMENTACIÓN

Quien valora tu caso es tu trabajadora social.
```
</details>

### `info-007` (informativa)
> ¿Qué es eso del ingreso mínimo vital? Me lo dijo una vecina
- respaldo parcial: Casi todo está en los fragmentos, pero la frase final de que Servicios Sociales o la trabajadora social valoran el caso no aparece en ellos.
- no menciona: se pide a la Seguridad Social

<details><summary>Respuesta</summary>

```
El Ingreso Mínimo Vital es una ayuda del Gobierno de España para personas que no tienen suficiente dinero para vivir.
• Quiere proteger a algunos grupos, como la infancia o las personas con discapacidad.
• Asegura unos ingresos mínimos cada mes a personas o unidades de convivencia (las personas que viven juntas en casa) que lo necesitan.
• En la norma se pide ganar menos de cierta cantidad y cumplir unas condiciones.
• Se puede trabajar y recibirla a la vez, siempre que no se supere el máximo de ingresos establecido.
• No caduca: la Seguridad Social comprueba cada cierto tiempo si se siguen cumpliendo las condiciones.
Si te interesa, podrías consultar tu caso con Servicios Sociales, que son quienes lo valoran.

📄 Fuente: Ingreso Mínimo Vital, en lectura fácil — Ministerio de Inclusión, Seguridad Social y Migraciones, Ingreso Mínimo Vital, en lectura fácil — Ministerio de Inclusión, Seguridad Social y Migraciones
📄 Fuente: Ingreso Mínimo Vital, en lectura fácil — Ministerio de Inclusión, Seguridad Social y Migraciones, ¿Cómo funciona el Ingreso Mínimo Vital?
📄 Fuente: Ingreso Mínimo Vital, en lectura fácil — Ministerio de Inclusión, Seguridad Social y Migraciones, ¿Durante cuánto tiempo

Quien valora tu caso es tu trabajadora social.
```
</details>

### `info-010` (informativa)
> Si trabajo unas horas a la semana, ¿puedo pedir igualmente el ingreso mínimo vital?
- respaldo parcial: La compatibilidad con el trabajo, el CAISS y la petición por internet están en los fragmentos, pero la mención a preparar información sobre ingresos y convivientes y la frase final sobre la trabajadora social no aparecen en ellos.

<details><summary>Respuesta</summary>

```
Trabajar no te cierra la puerta por sí solo. Según la información que tengo:
• Se puede trabajar y recibir el Ingreso Mínimo Vital a la vez, siempre que no superes el máximo de ingresos establecido.
• La ley dice que la ayuda es compatible con las rentas del trabajo, en los términos y límites que se fijen por norma.

Yo no puedo saber si en tu caso encaja ni decidirlo. Lo valora la Seguridad Social tras estudiar tu situación. Podrías consultar en un CAISS (Centro de Atención e Información de la Seguridad Social) o por internet, y preparar información sobre tus ingresos y quiénes viven contigo.

📄 Fuente: Ingreso Mínimo Vital, en lectura fácil — Ministerio de Inclusión, Seguridad Social y Migraciones, ¿Cómo funciona el Ingreso Mínimo Vital?
📄 Fuente: Ley 19/2021, de 20 de diciembre, por la que se establece el ingreso mínimo vital (texto consolidado, BOE), Artículo 11. Situación de vulnerabilidad económica
📄 Fuente: Ingreso Mínimo Vital, en lectura fácil — Ministerio de Inclusión, Seguridad Social y Migraciones, ¿Cómo puedo pedir

Quien valora tu caso es tu trabajadora social.
```
</details>

### `info-011` (informativa)
> Vivo con dos amigas que no son familia. ¿Eso cuenta para el ingreso mínimo vital?
- respaldo parcial: Lo esencial sobre el art. 9 y la capacidad económica del art. 11 está en los fragmentos, pero la frase de que 'no tendría por qué mirarse a todas como una sola familia' y la definición de unidad de convivencia como 'personas que viven juntas como familia' son interpretaciones que no aparecen literalmente en ellos.
- no menciona: certificado de los servicios sociales

<details><summary>Respuesta</summary>

```
Sí, vivir con personas que no son familia está previsto en la norma del Ingreso Mínimo Vital (IMV).
• Cuando conviven personas sin parentesco en la misma casa, en la norma se dice que podrían pedirlo la persona o personas que estén en riesgo de exclusión (es decir, en una situación social y económica muy difícil).
• Esto significa que no tendría por qué mirarse a todas las que viven en la casa como una sola familia, aunque eso lo valora la administración.
• Además, en el IMV se mira la capacidad económica de quien lo solicita o de su unidad de convivencia, es decir, de las personas que viven juntas como familia.

Podrías consultar en Servicios Sociales cómo se valoraría tu caso y qué papeles conviene preparar. No puedo decirte si te lo darían, eso lo decide quien estudia tu caso.

📄 Fuente: Ley 19/2021, de 20 de diciembre, por la que se establece el ingreso mínimo vital (texto consolidado, BOE), Artículo 9. Convivientes sin vínculo de parentesco
📄 Fuente: Ley 19/2021, de 20 de diciembre, por la que se establece el ingreso mínimo vital (texto consolidado, BOE), Artículo 11. Situación de vulnerabilidad económica

Quien valora tu caso es tu trabajadora social.
```
</details>

### `nokb-002` (sin_respuesta)
> ¿Qué ayudas hay para comprar un coche eléctrico?
- no se abstuvo

<details><summary>Respuesta</summary>

```
En lo que tengo, no aparece ninguna ayuda para comprar un coche eléctrico en general. Lo que sí figura es algo parecido, pero solo para personas con discapacidad:
• Ayudas para facilitar la movilidad: pago de gastos de transporte, adquirir o adaptar vehículos a motor, o comprar sillas de ruedas eléctricas.
• Si fuera ese caso, se piden dos presupuestos del gasto y el certificado de discapacidad.
• Si has pedido o recibido otras ayudas para lo mismo, hay que presentar documentación que lo acredite.
Si te interesa, cuéntame si es por discapacidad y te oriento mejor. Si no, podrías consultar con Servicios Sociales de Telde.

📄 Fuente: Ordenanza reguladora de las prestaciones económicas de los Servicios Sociales del Ayuntamiento de Telde para atender necesidades sociales (BOP Las Palmas n.º 105, 31/08/2020), Artículo 7. Modalidades de las Prestaciones
📄 Fuente: Prestaciones económicas municipales — web del Ayuntamiento de Telde, Prestaciones Económicas de Complementarias
📄 Fuente: Ordenanza reguladora de las prestaciones económicas de los Servicios Sociales del Ayuntamiento de Telde para atender necesidades sociales (BOP Las Palmas n.º 105, 31/08/2020), ANEXO VI . DOCUMENTACIÓN
📄 Fuente: Prestaciones económicas municipales — web del Ayuntamiento de Telde, Subvenciones o ayudas recibidas

Quien valora tu caso es tu trabajadora social.
```
</details>

## Requerimientos: detalle

- `req-001`: documentos 3/3; fecha límite 2026-11-30 (✅)
- `req-002`: documentos 3/3; fecha límite 2026-11-17 (✅)
- `req-003`: documentos 3/3; fecha límite 2026-12-04 (✅)
- `req-004` (borroso): pide otra foto ✅
- `req-005`: documentos 2/2; sin fecha en la carta: no inventa fecha ✅

## M. Métricas revisadas a mano

Pendiente: Rafa debe rellenar al menos 10 filas de `revision_manual.csv` (columnas *_ok con sí/no) y volver a ejecutar `python -m eval.run --report-only`.

## Limitaciones de esta evaluación

- Casos sintéticos redactados por el equipo de desarrollo: no representan la variedad real de mensajes de las familias.
- El juez LLM es de la misma familia de modelos que el asistente; por eso se exige revisión manual de al menos 10 respuestas.
- Una sola ejecución: los resultados pueden variar entre ejecuciones.
- Las fuentes de la KB no están validadas aún por Servicios Sociales.
