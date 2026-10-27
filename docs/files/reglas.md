# Catálogo de reglas

OniriFix trae **28 reglas** agrupadas por familia y nivel. El motor no conoce
sus identificadores: descubre los plugins de `onirifix.reglas` y ejecuta los que
estén activos. Este documento explica qué detecta cada regla, su nivel, su
confianza y cómo configurarla.

## Cómo leer los niveles

| Nivel | Uso | ¿Se aplica? |
| :--- | :--- | :--- |
| **L1** | Corrección mecánica y determinista. | Solo con `--aplicar`. |
| **L2** | Propuesta contextual. | Solo con `--aplicar-l2` y `--umbral`. |
| **L3** | Material de revisión editorial. | **Nunca**. |

La confianza es un valor entre `0.0` y `1.0`. En L2, el umbral por defecto es
`0.90`; un hallazgo por debajo no se aplica, pero sí aparece en el informe.
`--nivel` de `corregir` también puede limitar qué niveles se seleccionan, pero
L2 siempre exige `--aplicar-l2`.

## Tabla resumen

| ID | Nivel | Prioridad | Conf. | Activa por defecto | Qué hace |
| :--- | :--- | ---: | ---: | :--- | :--- |
| `TIP-001` | L1 | 60 | 0.99 | Sí | Colapsa espacios múltiples entre palabras. |
| `TIP-002` | L1 | 20 | 0.98 | Sí | Quita espacios antes de `, . ; : ! ? …`. |
| `TIP-003` | L1 | 30 | 0.96 | Sí | Añade espacio tras `, ; :` cuando falta. |
| `TIP-004` | L1 | 10 | 0.99 | Sí | Convierte `...` en `…`. |
| `TIP-005` | L1 | 40 | 0.97 | Sí | Convierte comillas rectas emparejadas al estilo configurado. |
| `TIP-006` | L1 | 70 | 0.95 | No* | Convierte apóstrofos rectos entre letras en `’`. |
| `TIP-007` | L1 | 50 | 0.95 | Sí | Normaliza `–`, `--` y guiones usados como raya. |
| `TIP-008` | L1 | 61 | 0.98 | Sí | Sustituye tabulaciones entre palabras por un espacio. |
| `TIP-009` | L1 | 5 | 0.96 | Sí | Colapsa `,,`, `;;`, `::`. |
| `TIP-010` | L3 | 1000 | 0.45 | No | Señala líneas con un número impar de comillas rectas. |
| `DIA-001` | L1 | 10 | 0.97 | Sí | Baja a minúscula el verbo de habla tras el cierre de un diálogo. |
| `DIA-002` | L2 | 80 | 0.62 | Sí | Propone minúscula en una reanudación de diálogo. |
| `DIA-003` | L1 | 4 | 0.92 | No† | Modo RAE estricto: elimina el punto antes de la atribución. |
| `DIA-004` | L1 | 15 | 0.94 | Sí | Añade el espacio que falta antes de una raya de atribución. |
| `DIA-005` | L1 | 16 | 0.90 | Sí | Añade el espacio que falta después de una raya de cierre. |
| `TIL-001` | L2 | 40 | 0.80–0.96 | Sí | Distingue `hacia` (preposición) de `hacía` (imperfecto). |
| `TIL-002` | L2 | 41 | 0.74–0.82 | Sí | Detecta futuros truncados (`mirá` → `mirará`). |
| `HOM-001` | L2 | 42 | 0.93 | Sí | Corrige `haber si` por `a ver si`. |
| `HOM-002` | L2 | 43 | 0.90 | Sí | Corrige `a ver + participio` por `haber + participio`. |
| `ORT-001` | L2 | 35 | 0.82 | Sí | Aplica el mapa de correcciones recurrentes del YAML. |
| `ORT-002` | L2 | 44 | 0.40–0.66 | Sí | Consulta un diccionario Hunspell o una lista de palabras. |
| `ORT-003` | L2 | 3 | 0.87 | Sí | Detecta palabras repetidas consecutivas (`la la`). |
| `CON-001` | L2 | 45 | 0.97 | Sí | Sustituye variantes registradas por su forma canónica. |
| `CON-002` | L2 | 46 | 0.84 | Sí | Restaura la capitalización de nombres y lugares canónicos. |
| `REP-001` | L3 | 90 | 1.00 | Sí | Frecuencia léxica con densidad y desglose por capítulo. |
| `REP-002` | L3 | 91 | 0.45–1.00 | Sí | Párrafos duplicados exactos o difusos. |
| `REP-003` | L3 | 92 | 0.50 | Sí | Frases típicas de residuo de IA. |
| `REP-004` | L3 | 93 | 0.60 | Sí | Frases que superan `repeticion.longitud_frase`. |

\* `TIP-006` está apagada en los defaults internos, pero el `config/reglas.yaml`
de ejemplo la activa.  
† `DIA-003` se activa con `dialogos.rae_estricto: true` aunque su interruptor
general esté en `false`.

## Tipografía (TIP)

Las reglas TIP son mecánicas y no dependen de NLP. Todas respetan el texto
original y solo generan hallazgos cuando la sustitución cambia algo.

### TIP-001 · espacios múltiples

```text
Hola   mundo  →  Hola mundo
```

No toca la sangría inicial ni los espacios antes de puntuación (eso lo hace
TIP-002). Confianza `0.99`.

### TIP-002 · espacio antes de puntuación

```text
Hola , mundo.  →  Hola, mundo.
```

### TIP-003 · espacio después de puntuación

```text
Hola,mundo;bien:hecho  →  Hola, mundo; bien: hecho
```

No actúa sobre números (`3,14`, `2:30`).

### TIP-004 · puntos suspensivos

```text
No...  →  No…
```

### TIP-005 · comillas rectas

Convierte parejas `"texto"` al par configurado en `tipografia.comillas`. El
default es `«»`; para estilo anglosajón se puede usar `“”`. Se desactiva con
`tipografia.convertir_comillas: false`.

### TIP-006 · apóstrofos

```text
l'aire  →  l’aire
```

Solo entre letras, para no tocar comillas sueltas. Se controla con
`tipografia.convertir_apostrofos`.

### TIP-007 · rayas de diálogo

Normaliza:

- `–Hola` o `--Hola` al inicio de línea → `—Hola`;
- `Hola –dijo` → `Hola —dijo`;
- `Hola -- dijo` → `Hola — dijo`.

### TIP-008 · tabulaciones

```text
Hola\tmundo  →  Hola mundo
```

### TIP-009 · puntuación duplicada

```text
Hola,, mundo  →  Hola, mundo
```

### TIP-010 · comillas desbalanceadas (L3)

Cuenta comillas rectas por línea. Es L3 porque una línea puede tener una sola
comilla legítimamente (por ejemplo, un apóstrofo o un diálogo partido).

## Diálogos (DIA)

El diálogo español es la parte más delicada. OniriFix separa lo determinista de
lo interpretativo.

### DIA-001 · verbo de habla en mayúscula

```text
—Basta. —Dijo Mico.  →  —Basta. —dijo Mico.
```

Solo actúa si la palabra está en el catálogo de verbos de habla (incluye los
verbos del registro y `dialogos.verbos_extra`). Si el verbo no se reconoce, no
se toca.

### DIA-002 · reanudación de diálogo (L2)

```text
—Vete —dijo él. —La puerta está abierta.
```

Propone `la` con confianza `0.62` porque también podría ser una intervención
nueva. No actúa si la palabra es un nombre del glosario o si no hay una
atribución previa cercana.

### DIA-003 · modo RAE estricto (opt-in)

```text
—Basta. —dijo Mico.  →  —Basta —dijo Mico.
```

Se activa con `dialogos.rae_estricto: true` (o `reglas.DIA-003: true`). Cambia
la puntuación de diálogo, por eso no es el comportamiento por defecto.

### DIA-004 · espacio antes de raya

```text
Hola—dijo Mico.  →  Hola —dijo Mico.
```

### DIA-005 · espacio después de raya

```text
Mico—Las llaves.  →  Mico— Las llaves.
```

## Tildes y homófonos

### TIL-001 · hacia / hacía (L2)

La preposición `hacia` no lleva tilde; el imperfecto de `hacer` sí. La regla
usa contexto y, si spaCy está disponible, la etiqueta POS. Sin spaCy aplica
heurísticas:

- `hacia frío`, `hacia tiempo`, `hacia años`… → `hacía`;
- pronombre o negación delante (`se hacia`, `no hacia`) → `hacía`;
- verbo de movimiento o determinante después (`caminaba hacia el norte`,
  `hacia la puerta`) → no toca.

Se controla con `tildes.hacia`.

### TIL-002 · futuros truncados (L2)

```text
Mirá el cielo.  →  Mirará el cielo.
```

Construye candidatos morfológicos a partir de una lista de verbos frecuentes y
sus raíces irregulares. Respeta:

- palabras válidas como `está`, `acá`, `allá`, `quizá`, `mamá`, `sofá`;
- el glosario de la obra;
- `tildes.palabras_validas_extra`;
- el voseo, si `tildes.permitir_voseo: true` (`mirá`, `susurrá`…).

### HOM-001 · haber si

```text
haber si vienes  →  a ver si vienes
```

Solo cuando `haber` va seguido de `si`, `qué`, `cómo`, `cuándo`, `dónde` o
`quién`.

### HOM-002 · a ver + participio

```text
a ver sido un error  →  haber sido un error
```

Trabaja con una lista conservadora de participios para no confundir `a ver` con
`haber` en otros contextos.

## Ortografía (ORT)

### ORT-001 · correcciones explícitas

Usa el mapa `ortografia.correcciones` del YAML:

```yaml
ortografia:
  correcciones:
    q: que
    xq: porque
    tmb: también
```

Respeta mayúsculas/minúsculas (`Q` → `Que`). Un mapa vacío (`correcciones: {}`)
desactiva esta regla sin tocar el resto de la configuración.

### ORT-002 · diccionario

Necesita `ortografia.diccionario` (Hunspell/spylls) o
`ortografia.lista_palabras` (una palabra por línea). Si no hay corrector
disponible, no produce hallazgos. Ignora nombres propios, el glosario y palabras
de menos de dos letras.

### ORT-003 · palabras repetidas

```text
La la ciudad  →  La ciudad
```

Solo palabras consecutivas separadas por espacios o tabulaciones.

## Consistencia onomástica (CON)

El glosario del registro manda sobre el diccionario general y sobre las reglas
de estilo.

### CON-001 · variantes registradas

Cada variante marcada como error en el registro se sustituye por su término
canónico:

```text
Onirium  →  Oniriums
KaarTcha →  Kaar'Tcha
```

La búsqueda es exacta (sin fuzzy) y respeta mayúsculas del original en la
medida de lo posible. Confianza `0.97`.

### CON-002 · capitalización canónica

```text
feith noir llegó  →  Feith Noir llegó
```

Solo considera nombres con una señal interna de nombre propio: varias palabras,
mayúscula interna, apóstrofo o comilla tipográfica. Así `Mico` (que también es
un animal) no se corrige a ciegas. Se puede limitar con
`consistencia.incluir_personajes`, `incluir_lugares` e `incluir_terminos`.

## Repetición y residuo (REP, L3)

Estas reglas **nunca** generan parches. Su salida es material para el editor.

### REP-001 · frecuencia léxica

Cuenta palabras de contenido (más de `repeticion.min_longitud`, fuera de
`stopwords` y, por defecto, fuera del glosario). Informa de:

- número de apariciones;
- densidad por 1000 palabras;
- desglose por capítulo si `repeticion.por_capitulo: true`.

`repeticion.top` limita cuántas palabras se listan.

### REP-002 · párrafos duplicados

Detecta duplicados exactos mediante hash y duplicados difusos con
`rapidfuzz`. Solo compara párrafos de al menos `duplicados.minimo_palabras` y
usa `duplicados.similitud` (porcentaje) como umbral. `maximo_parrafos` protege
el rendimiento en manuscritos enormes.

### REP-003 · residuo de IA

Busca frases declaradas en `residuo_ia.frases` (`en el vasto tapiz`,
`un testimonio de`, `una sinfonía de`…). Solo informa: no reescribe.

### REP-004 · frases largas

Señala oraciones con más de `repeticion.longitud_frase` palabras (60 por
defecto). Es una señal de ritmo, no un error gramatical.

## Configuración de las reglas

Cada regla se puede apagar en `config/reglas.yaml`:

```yaml
reglas:
  TIP-001: true
  DIA-003: false
  TIP-010: false
```

Los valores ausentes se toman de los defaults internos. Para desactivar un
mapa completo, usa un mapa vacío:

```yaml
ortografia:
  correcciones: {}
```

La precedencia es `defaults < YAML < entorno < CLI`. `onirifix reglas` muestra
el catálogo y si cada regla está activa con la configuración actual.

## Solapamientos y prioridad

El motor puede recibir dos hallazgos sobre el mismo tramo. `deduplicar()`
ordena por posición, prioridad, nivel, longitud y confianza, y conserva el
primero. Por eso una regla específica (prioridad baja) gana a una genérica
(prioridad alta) cuando ambas detectan el mismo error.

Si dos hallazgos no se solapan, se conservan ambos. La aplicación de parches
vuelve a comprobar los offsets y omite los que se hayan desplazado.

## Idempotencia

Aplicar L1 dos veces debe dar el mismo texto que aplicar una vez. Las pruebas de
`tests/test_servicio.py` y `tests/test_cli.py` cubren este contrato, además de
la verificación de que un texto ya corregido no vuelve a generar L1.

## Añadir una regla

1. Crea un archivo en `src/onirifix/reglas/`.
2. Declara una clase con `id`, `nivel`, `descripcion`, `prioridad`,
   `por_defecto` y `aplicar(texto, ctx)`.
3. Decora la clase con `@registrar`.
4. Añade el interruptor a `DEFAULTS` en `config.py` y a `config/reglas.yaml`.
5. Escribe pruebas de caso positivo, caso negativo e idempotencia.
6. Documenta la regla en este archivo y ejecuta `pytest`, `ruff` y `mypy`.

No hace falta editar el motor: `descubrir_reglas()` importa el módulo nuevo en
la siguiente ejecución.
