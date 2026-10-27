# Diseño de la CLI

La interfaz de OniriFix está pensada para trabajar en una terminal, sin conexión
y sin sorpresas: primero se mira, después se decide y solo al final se escribe.
Todos los mensajes y la ayuda están en español.

## Convenciones

- Las **opciones globales** van antes del subcomando:

  ```bash
  onirifix --obra oniriums analizar manuscrito.md
  onirifix --db data/otra.db --config config/reglas.yaml analizar manuscrito.md
  ```

- `--help`/`-h` funciona en cualquier nivel:

  ```bash
  onirifix --help
  onirifix corregir --help
  onirifix registro personajes --help
  ```

- `--version`/`-V` muestra la versión instalada.
- Los códigos de salida son `0` para éxito y distintos de `0` para errores de
  uso, lectura, configuración o `--estricto` con hallazgos L1/L2.
- Rich se usa para tablas y paneles; si la salida no es una terminal, el texto
  sigue siendo legible y sin dependencia de color.

## Opciones globales

| Opción | Efecto |
| :--- | :--- |
| `--db RUTA` | Base SQLite. Por defecto `data/onirifix.db`. |
| `--config RUTA` | YAML de reglas. Por defecto `config/reglas.yaml`. |
| `--obra`, `-o` | Slug de la obra activa. Por defecto `general`. |
| `--verbose`, `-v` | Aumenta el nivel de log (`-vv` para debug). |

Las mismas rutas se pueden fijar con `ONIRIFIX_DB`, `ONIRIFIX_CONFIG`,
`ONIRIFIX_OBRA`, etc. La precedencia es:

```text
defaults internos < config/reglas.yaml < variables de entorno < opciones CLI
```

## Comandos

### `init`

Crea los directorios, la configuración si falta, la base SQLite y la obra
activa. Es idempotente.

```bash
onirifix init
onirifix --obra mi-novela init
```

### `analizar`

Lee el manuscrito y genera informes sin modificarlo. Es la vista previa
completa.

```bash
onirifix --obra oniriums analizar examples/manuscrito_ejemplo.md
onirifix --obra oniriums analizar manuscrito.md --salida informes --formato md,csv,json
onirifix --obra oniriums analizar manuscrito.md --reglas TIP-001,TIP-005 --sin-l3
onirifix --obra oniriums analizar manuscrito.md --estricto
```

Opciones útiles:

| Opción | Efecto |
| :--- | :--- |
| `--salida`, `-s` | Directorio de informes. |
| `--formato`, `-f` | Lista separada por comas: `md`, `csv`, `json`, `diff`. |
| `--reglas`, `-r` | Ejecuta solo esos IDs. |
| `--sin-l3` | Oculta hallazgos de solo informe. |
| `--sin-informes` | No escribe archivos; solo terminal. |
| `--estricto` | Sale con código `1` si hay L1/L2. |

### `corregir`

Calcula los parches aplicables. Por defecto **no escribe** (dry-run).

```bash
# Ver qué se aplicaría
onirifix --obra oniriums corregir manuscrito.md

# Aplicar L1, con backup y auditoría
onirifix --obra oniriums corregir manuscrito.md --aplicar

# Aplicar también L2 por encima de 0.95
onirifix --obra oniriums corregir manuscrito.md --aplicar --aplicar-l2 --umbral 0.95

# Escribir en otro archivo
onirifix --obra oniriums corregir manuscrito.md --aplicar --destino limpio.md
```

| Opción | Efecto |
| :--- | :--- |
| `--aplicar` | Escribe los cambios (sin esta bandera, dry-run). |
| `--nivel` | `L1`, `L2` o `L1,L2`. Por defecto `L1`. |
| `--aplicar-l2` | Habilita parches L2. Sin esta bandera no se aplica L2. |
| `--umbral` | Confianza mínima L2 (`0.0`–`1.0`). |
| `--backup` / `--sin-backup` | Fuerza o desactiva la copia de seguridad. |
| `--destino` | Archivo de salida distinto del original. |
| `--salida`, `--formato`, `--sin-informes` | Igual que en `analizar`. |

Reglas de seguridad:

- L1 solo se aplica con `--aplicar`.
- L2 requiere `--aplicar-l2` **y** superar `--umbral`.
- L3 nunca se aplica.
- Si se sobrescribe el original, se crea backup antes de escribir.
- Si un parche no coincide con el texto actual, se omite y se informa del
  motivo.

### `revisar`

Revisión interactiva, hallazgo a hallazgo. Es útil para L2 ambiguo o para
decidir manualmente qué parches aceptar.

```bash
onirifix --obra oniriums revisar manuscrito.md
onirifix --obra oniriums revisar manuscrito.md --reglas DIA-002,TIL-001 --simular
```

En cada hallazgo se muestra el contexto y se pregunta:

```text
¿Aplicar? [s]í / [n]o / [e]ditar / [t]odos / [q]uitar
```

- `s`: aplica ese parche.
- `n`: lo omite.
- `e`: permite escribir un reemplazo manual.
- `t`: aplica el actual y todos los siguientes.
- `q`: termina la revisión sin aplicar el actual ni los restantes.

`--simular` recorre las decisiones pero no escribe. `--limite` acota cuántos
hallazgos se revisan. Si se indica `--salida`, se generan informes con el
resultado de la revisión.

### `frecuencia`

Informe L3 de repetición léxica.

```bash
onirifix --obra oniriums frecuencia manuscrito.md --top 30
onirifix --obra oniriums frecuencia manuscrito.md --sin-capitulos
```

Muestra línea, palabra y detalle (apariciones, densidad y capítulos). Nunca
modifica el archivo.

### `duplicados`

Informe L3 de párrafos duplicados exactos o difusos.

```bash
onirifix --obra oniriums duplicados manuscrito.md
onirifix --obra oniriums duplicados manuscrito.md --similitud 95 --minimo-palabras 12
```

### `reglas`

Lista el catálogo, el nivel, si está activa y su descripción.

```bash
onirifix reglas
```

Es la forma rápida de comprobar el efecto de `config/reglas.yaml` y de
`dialogos.rae_estricto`.

### `doctor`

Diagnóstico de dependencias, rutas, configuración, base de datos y reglas.

```bash
onirifix doctor
```

Comprueba Click, Rich, PyYAML, `regex`, `rapidfuzz` y las dependencias
opcionales (spaCy, spylls, python-docx). También avisa de configuraciones
sospechosas, como comillas que no tienen dos caracteres.

## Registro

El árbol `registro` gestiona el canon de la obra. Todos los comandos usan la
obra activa salvo `obras crear`, `obras listar`, `obras ver` y
`obras eliminar`, que reciben un slug o listan todas.

```bash
# Obras
onirifix registro obras listar
onirifix registro obras crear mi-novela --titulo "Mi novela" --autor "Autora"
onirifix registro obras ver mi-novela
onirifix registro obras eliminar mi-novela --si

# Personajes
onirifix --obra mi-novela registro personajes agregar "Feith Noir" --alias Feith
onirifix --obra mi-novela registro personajes listar
onirifix --obra mi-novela registro personajes eliminar "Feith Noir" --si

# Lugares
onirifix --obra mi-novela registro lugares agregar "Villa Gris" --tipo ciudad
onirifix --obra mi-novela registro lugares listar

# Términos y variantes
onirifix --obra mi-novela registro terminos agregar Oniriums --sensible
onirifix --obra mi-novela registro terminos variante Oniriums Onirium
onirifix --obra mi-novela registro terminos variantes Oniriums
onirifix --obra mi-novela registro terminos listar --tipo glosario

# Verbos de habla
onirifix --obra mi-novela registro verbos agregar trinó
onirifix --obra mi-novela registro verbos listar

# Intercambio y auditoría
onirifix registro importar examples/obra.ejemplo.yaml
onirifix --obra mi-novela registro exportar mi-novela.yaml
onirifix --obra mi-novela registro historial --limite 20
```

`registro importar` no cambia la obra activa: después hay que usar
`--obra <slug>` o definir `ONIRIFIX_OBRA`.

## Informes

`analizar`, `corregir` y `revisar` pueden escribir en `--salida`:

| Formato | Archivo | Contenido |
| :--- | :--- | :--- |
| `md` | `informe.md` | Informe legible agrupado por nivel y regla. |
| `csv` | `hallazgos.csv` | Una fila por hallazgo, UTF-8 con BOM para Excel. |
| `json` | `hallazgos.json` | Datos estructurados, resumen y corrección. |
| `diff` | `parches.diff` | Diff unificado de los cambios aplicados. |

El Markdown limita los hallazgos mostrados por regla con
`informes.max_por_regla` (300 por defecto). El CSV y el JSON conservan todo.
El diff solo se genera cuando hay cambios aplicados.

## Flujo recomendado

```bash
# 1. Preparar el proyecto y el canon
onirifix init
onirifix registro importar examples/obra.ejemplo.yaml

# 2. Ver el estado sin tocar nada
onirifix --obra oniriums analizar manuscrito.md

# 3. Aplicar la mecánica segura
onirifix --obra oniriums corregir manuscrito.md --aplicar

# 4. Revisar lo contextual
onirifix --obra oniriums revisar manuscrito.md --reglas DIA-002,TIL-001,TIL-002

# 5. Trabajar el material L3 a mano
onirifix --obra oniriums frecuencia manuscrito.md --top 50
onirifix --obra oniriums duplicados manuscrito.md
```

## Variables de entorno

| Variable | Efecto |
| :--- | :--- |
| `ONIRIFIX_HOME` | Raíz del proyecto. |
| `ONIRIFIX_DB` | Base SQLite. |
| `ONIRIFIX_CONFIG` | YAML de reglas. |
| `ONIRIFIX_SALIDA` | Directorio de informes. |
| `ONIRIFIX_BACKUPS` | Directorio de copias de seguridad. |
| `ONIRIFIX_OBRA` | Obra activa. |
| `ONIRIFIX_UMBRAL_L2` | Umbral L2 por defecto. |
| `ONIRIFIX_BACKUP` | `true`/`false`: copia antes de escribir. |
| `ONIRIFIX_AUDITORIA` | `true`/`false`: registra cambios en SQLite. |
| `ONIRIFIX_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`… |

El archivo `.env` del directorio de trabajo se carga automáticamente sin
sobrescribir variables ya definidas en el shell.

## Errores frecuentes

| Mensaje | Causa y solución |
| :--- | :--- |
| `No existe la obra 'x'` | La obra no está en la base. Créala o importa un YAML. |
| `No existe el archivo: …` | Revisa la ruta del manuscrito. |
| `Formato no soportado` | Usa `.txt`, `.md` o `.docx`. |
| `La escritura .docx no está implementada` | Usa `--destino archivo.md`. |
| `Para aplicar L2 añade --aplicar-l2` | Añade la bandera y revisa el umbral. |
| `reglas desconocidas` | Consulta `onirifix reglas` y revisa `--reglas`. |

## Accesibilidad y estilo

- La ayuda y los mensajes usan español neutro.
- Los paneles no dependen solo del color: incluyen etiquetas y texto.
- Los informes Markdown usan tablas y bloques de cita legibles sin CSS.
- Los errores de la CLI se muestran por stderr con el prefijo `Error:` de
  Click; el código de salida permite usarla en CI.
