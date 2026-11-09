# Cobertura del informe editorial

Este documento cruza las correcciones que pide el informe editorial de la
novela con las reglas de OniriFix. Sirve para saber **qué hace la herramienta
sola, qué propone para que tú decidas y qué queda en tus manos**.

> El informe y el manuscrito son privados y no están en el repositorio. Los
> ejemplos de esta página son frases inventadas que reproducen el *tipo* de
> error, nunca el texto de la obra.

## Cómo leer la tabla

| Estado | Significado |
| :--- | :--- |
| **Automático** | Regla L1: se aplica sin preguntar (en la GUI llega marcada como aceptada; en la CLI, con `--aplicar`). |
| **Asistido** | Regla L2: propone el cambio con su contexto y tú lo aceptas o rechazas. En la CLI, `--aplicar-l2` + umbral. |
| **Señalado** | Regla L3: aparece en el informe y en la GUI como «solo aviso». Nunca cambia el texto. |
| **Manual** | Requiere criterio narrativo o de lectura. Ninguna regla lo toca. |

## 1. Puntuación y atribución de diálogo

| Problema | Ejemplo inventado | Regla | Nivel | Estado |
| :--- | :--- | :--- | :--- | :--- |
| Verbo de habla en mayúscula tras el cierre | `—Basta. —Dijo Ana.` | `DIA-001` | L1 | Automático |
| Verbo de habla como oración suelta, sin raya (misma línea o siguiente) | `—¿Vienes? Preguntó Ana.` | `DIA-006` | L2 | Asistido |
| Inciso sin cerrar antes de una nueva pregunta o exclamación | `—Vale —dijo Ana. ¿Vienes?` | `DIA-007` | L2 | Asistido |
| Reanudación del parlamento en mayúscula | `—… —dijo Ana. —Las llaves…` | `DIA-002` | L2 | Asistido |
| Espacios que faltan junto a la raya | `Hola—dijo Ana.` | `DIA-004`, `DIA-005` | L1 | Automático |
| Diálogo que abre con guion simple | `-Ya voy.` | `TIP-007` | L1 | Automático |
| Saber quién habla en escenas de tres voces, reescribir incisos complejos | — | — | — | **Manual** |

## 2. «hacía/hacia», subjuntivos y tildes diacríticas

| Problema | Ejemplo inventado | Regla | Nivel | Estado |
| :--- | :--- | :--- | :--- | :--- |
| `hacía` usado como preposición de dirección | `Miró hacía el muelle.` | `TIL-001` | L2 | Asistido |
| `hacia` usado como verbo | `Hacia frío.` | `TIL-001` | L2 | Asistido |
| Futuro en lugar de subjuntivo tras `como si`, `antes de que`, `hasta que`, `dejó que`, `para que`, `sin que` | `como si ocultará algo` | `TIL-006` | L2 | Asistido |
| `cuando` con sentido de futuro en pasado | — | — | — | **Manual** |
| `Sé` (verbo), `Sí` (afirmación), `él` (pronombre) | `Se que no me crees.` | `TIL-005` | L2 | Asistido |
| `qué`/`cómo`/`dónde`/`cuánto` en interrogativa indirecta | `No sé que decir.` | `TIL-005` | L2 | Asistido |
| `Tu/Tú`, `Mas/Más`, `Aun/Aún` en general | — | — | — | **Manual** (depende del sentido) |
| `Por qué` / `Porque` / `Por que` | — | — | — | **Manual** |
| `aún así` → `aun así` | `Aún así, siguió.` | `ORT-001` | L2 | Asistido |

## 3. Pretéritos y sustantivos sin tilde (o con tilde de más)

| Problema | Ejemplo inventado | Regla | Nivel | Estado |
| :--- | :--- | :--- | :--- | :--- |
| Pretérito inequívoco sin tilde (`conto`, `respondio`…) | `Nadie conto nada.` | `TIL-003` | L1 (minúscula) / L2 | Automático / Asistido |
| Pretérito ambiguo (`señalo`, `miro`, `paso`, `cambio`, `río`…) con contexto claro | `Ana asintió y señalo la puerta.` | `TIL-003` | L2 | Asistido |
| Pretérito ambiguo **sin** contexto suficiente | `Yo miro el mar.` | — | — | **Manual** (la regla calla a propósito) |
| `rió` / `rio` | `Lina río a carcajadas.` | `TIL-003` (`tildes.forma_rio`) | L2 | Asistido |
| Sustantivo escrito como pretérito tras determinante (`un suspiró`, `un gestó`, `el silenció`) | `Hubo un suspiró.` | `TIL-004` | L2 | Asistido |
| Participio mal formado (`había corrió`), `saque/saco`, `término/terminó` | — | — | — | **Manual** |
| Concordancia de género o número (`aquellos ideas`) | — | — | — | **Manual** |

## 4. Ortotipografía

| Problema | Ejemplo inventado | Regla | Nivel | Estado |
| :--- | :--- | :--- | :--- | :--- |
| Elipsis corruptas tras punto | `Y.…`, `Bueno….` | `TIP-011` | L1 | Automático |
| Tres puntos en lugar de `…` | `Bueno...` | `TIP-004` | L1 | Automático |
| Comillas rectas | `"hola"` | `TIP-005` | L1 | Automático |
| Comillas inglesas `“…”` | `“hola”` | `TIP-014` | L2 | Asistido (confianza baja: muchas obras las reservan para pensamientos) |
| Comillas mezcladas o anidadas en una misma frase | — | — | — | **Manual** (decidir el sistema de la obra) |
| Signo de apertura usado como cierre | `¡Ya voy ¡` | `TIP-012` | L1 | Automático |
| Falta el signo de apertura `¿`/`¡` | `Vienes mañana?` | `TIP-013` | L3 | Señalado (dónde empieza la pregunta es lectura) |
| Espacio dentro de `¿ ¡ « »` | `¿ Vienes ?` | `TIP-015` | L1 | Automático |
| Espacios dobles, antes de coma, puntuación repetida | `hola ,  adiós,,` | `TIP-001`–`TIP-003`, `TIP-009` | L1 | Automático |
| Minúscula tras punto y seguido | `Iba lento. casi parado.` | `ORT-004` | L2 | Asistido |
| Mayúscula tras `?`/`!` cuando la frase continúa (vocativos) | — | — | — | **Manual** |
| Gritos en MAYÚSCULAS sostenidas | — | — | — | **Manual** (decisión de estilo) |

## 5. Punto de vista (head-hopping)

Saltos de cabeza dentro de una escena, anclas de POV, transiciones entre
escenas: **manual**. No hay forma determinista de saber de quién es una
interioridad.

## 6. Duplicaciones y repeticiones

| Problema | Regla | Nivel | Estado |
| :--- | :--- | :--- | :--- |
| Párrafo u oración repetido literalmente justo a continuación | `REP-005` | L2 | Asistido (propone borrar la copia) |
| Párrafos idénticos o casi idénticos separados por otros | `REP-002` | L3 | Señalado |
| Palabra repetida consecutiva (`la la`) | `ORT-003` | L2 | Asistido (las enfáticas `muy muy` bajan de umbral) |
| Frases-firma y muletillas (`media sonrisa`, adverbios en -mente…) | `REP-001`, `REP-003` | L3 | Señalado (con densidad por capítulo) |
| Acciones duplicadas con sinónimos, escenas contadas dos veces, capítulos con dos finales | — | — | **Manual** (elegir qué versión queda) |

## 7. Residuos editoriales y anacronismos

| Problema | Regla | Nivel | Estado |
| :--- | :--- | :--- | :--- |
| Comentarios de asistente (`Aquí tienes…`, `¿Quieres que continúe?`) | `REP-006` | L3 | Señalado (borrar es manual) |
| Marcadores de plantilla (`(Contexto anterior…)`, `Escena ampliada`, `[TODO]`, `TODO:`) | `REP-006` | L3 | Señalado |
| Términos vetados / anacronismos | `REP-006` con `residuos_borrador.vetados` | L3 | Señalado (la política de préstamos es tuya) |
| Frases en otro idioma sin traducir | `REP-006` si se añaden a `vetados` o `patrones` | L3 | Señalado / Manual |

## 8. Continuidad, nombres y lógica interna

| Problema | Regla | Nivel | Estado |
| :--- | :--- | :--- | :--- |
| Variantes de un nombre ya registradas en el glosario | `CON-001` | L2 | Asistido |
| Capitalización de nombres y lugares canónicos | `CON-002` | L2 | Asistido |
| Contradicciones de cifras, objetos, ojos, toponimia; quién sabe qué y cuándo | — | — | **Manual** (biblia de continuidad) |

## 9. Errores léxicos puntuales

| Problema | Regla | Nivel | Estado |
| :--- | :--- | :--- | :--- |
| Erratas de una letra que no son palabra | `ORT-002` (con diccionario `[ortografia]`) | L2 | Asistido |
| Erratas recurrentes que tú identifiques | `ORT-001` (`ortografia.correcciones` del YAML) | L2 | Asistido |
| Palabra real pero equivocada (`tubo`/`tuvo`, `halla`/`haya`) | — | — | **Manual** (o añadirla a `ortografia.correcciones` si en tu obra siempre es error) |
| Palabras omitidas, oraciones rotas, refranes mal citados, mezcla de `vos`/`vosotros` | — | — | **Manual** |

## Resumen

- **Automático (L1):** `DIA-001`, `DIA-004`, `DIA-005`, `TIP-001`–`TIP-005`,
  `TIP-007`–`TIP-009`, `TIP-011`, `TIP-012`, `TIP-015` y los pretéritos
  inequívocos de `TIL-003`.
- **Asistido (L2):** `DIA-002`, `DIA-006`, `DIA-007`, `TIL-001`, `TIL-003`
  (ambiguos), `TIL-004`, `TIL-005`, `TIL-006`, `TIP-014`, `ORT-001`–`ORT-004`,
  `REP-005`, `CON-001`, `CON-002`.
- **Señalado (L3):** `TIP-013`, `REP-001`–`REP-004`, `REP-006`.
- **Manual:** punto de vista, continuidad, `Por qué/Porque`, `Tu/Tú` y demás
  diacríticas dependientes del sentido, concordancias, participios mal
  formados, palabras omitidas, elegir entre versiones duplicadas, poda de
  muletillas, política de anacronismos y gritos en mayúsculas.
