# Registro SQLite

El registro es la memoria de la obra: obras, personajes, lugares, términos,
variantes y verbos de habla. La CLI y las reglas lo consultan a través de
repositorios; nadie fuera de `onirifix.db` habla SQL directamente.

## Ubicación y versionado

- Ruta por defecto: `data/onirifix.db` (relativa a `ONIRIFIX_HOME` o al
  directorio actual).
- Se puede cambiar con `--db`, `ONIRIFIX_DB` o editando la configuración de
  entorno.
- El esquema se versiona con `PRAGMA user_version`. La versión actual es **1**.
- Si la base no existe, se crea y se aplica el DDL. Si la versión es distinta,
  `ErrorEsquema` explica cómo exportar y reimportar.
- La conexión activa `foreign_keys = ON`, `journal_mode = WAL`,
  `synchronous = NORMAL` y un `busy_timeout` de 5 segundos.

## Tablas

### `obras`

Identifica cada proyecto editorial.

| Columna | Tipo | Notas |
| :--- | :--- | :--- |
| `id` | INTEGER | PK autoincremental. |
| `slug` | TEXT | Único; se normaliza con `slugify`. |
| `titulo` | TEXT | Obligatorio. |
| `autor`, `genero`, `descripcion` | TEXT | Opcionales. |
| `idioma` | TEXT | `es` por defecto. |
| `creada_en`, `actualizada_en` | TEXT | UTC ISO-8601. |

### `personajes`

| Columna | Tipo | Notas |
| :--- | :--- | :--- |
| `id` | INTEGER | PK. |
| `obra_id` | INTEGER | FK con `ON DELETE CASCADE`. |
| `nombre` | TEXT | Único por obra. |
| `rol`, `descripcion`, `notas` | TEXT | Opcionales. |
| `alias` | TEXT | Lista separada por comas. |
| `activo` | INTEGER | `1`/`0`. Los inactivos no entran en el glosario. |

### `lugares`

`nombre` único por obra; `tipo`, `alias`, `descripcion` y `notas` son
opcionales. Los lugares alimentan los topónimos del glosario.

### `terminos`

| Columna | Tipo | Notas |
| :--- | :--- | :--- |
| `termino` | TEXT | Único por `(obra, termino, tipo)`. |
| `tipo` | TEXT | `nombre`, `glosario`, `toponimo`, `expresion` u `otro`. |
| `definicion`, `notas` | TEXT | Opcionales. |
| `sensible` | INTEGER | Marca términos delicados para el editor. |

Los términos de tipo `toponimo` se suman a `Glosario.toponimos`; el resto va a
`Glosario.terminos`. Los de tipo `nombre` también participan en CON-002.

### `variantes`

| Columna | Tipo | Notas |
| :--- | :--- | :--- |
| `termino_id` | INTEGER | FK con `ON DELETE CASCADE`. |
| `variante` | TEXT | Única por término. |
| `es_error` | INTEGER | `1` = CON-001 la corrige; `0` = forma legítima. |
| `notas` | TEXT | Opcional. |

Solo las variantes con `es_error = 1` entran en `Glosario.variantes` como mapa
`variante → término canónico`.

### `verbos_habla`

| Columna | Tipo | Notas |
| :--- | :--- | :--- |
| `obra_id` | INTEGER | `NULL` = verbo global; si no, verbo de la obra. |
| `verbo` | TEXT | Único por `(obra_id, verbo)`. Se guarda en minúsculas. |

`Glosario.verbos_habla` mezcla los verbos globales y los de la obra. Se usan en
DIA-001, DIA-002, DIA-003 y DIA-004.

### `correcciones`

Auditoría de parches aplicados.

| Columna | Tipo | Notas |
| :--- | :--- | :--- |
| `obra_id` | INTEGER | FK con `ON DELETE SET NULL`. |
| `archivo` | TEXT | Ruta del manuscrito. |
| `regla` | TEXT | ID de la regla. |
| `nivel` | TEXT | `L1`, `L2` o `L3`. |
| `linea`, `columna` | INTEGER | Posición 1-based. |
| `original`, `sugerencia` | TEXT | Texto antes/después. |
| `confianza` | REAL | Confianza del hallazgo. |
| `aplicado` | INTEGER | `1` si se escribió. |
| `creada_en` | TEXT | UTC ISO-8601. |

La auditoría solo se escribe cuando `corregir --aplicar` o `revisar` aplican
parches y `auditoria` está activa. `analizar` nunca escribe en esta tabla.

## Repositorios

`Registro` es la fachada que agrupa:

| Repositorio | Operaciones principales |
| :--- | :--- |
| `obras` | `crear`, `obtener`, `por_id`, `listar`, `actualizar`, `eliminar`, `asegurar`. |
| `personajes` | `agregar`, `obtener`, `listar`, `actualizar`, `eliminar`. |
| `lugares` | `agregar`, `obtener`, `listar`, `actualizar`, `eliminar`. |
| `terminos` | `agregar`, `obtener`, `buscar`, `listar`, `actualizar`, `eliminar`, `agregar_variante`, `variantes`, `eliminar_variante`. |
| `verbos` | `agregar`, `listar`, `listar_propios`, `eliminar`. |
| `correcciones` | `registrar`, `listar`. |

Métodos de la fachada:

- `glosario(slug)`: construye el `Glosario` de una obra existente.
- `glosario_para_id(obra_id)`: variante que ya tiene el ID.
- `resumen(slug)`: conteos de personajes, lugares, términos y verbos.
- `cerrar()`: cierra la conexión. También funciona como context manager.

Ejemplo:

```python
from pathlib import Path
from onirifix.db.repositorios import Registro

with Registro(Path("data/onirifix.db")) as registro:
    obra = registro.obras.asegurar("mi-novela", titulo="Mi novela")
    registro.personajes.agregar(obra.id, "Feith Noir", alias=["Feith"])
    glosario = registro.glosario("mi-novela")
    print(glosario.nombres)
```

## Cómo se construye el glosario

Para una obra:

1. **Personajes activos** → `nombres`; sus alias → `alias`.
2. **Lugares** → `toponimos`; sus alias → `alias`.
3. **Términos**:
   - tipo `toponimo` → `toponimos`;
   - cualquier otro tipo → `terminos`.
4. **Variantes** con `es_error = 1` → mapa `variante.casefold() → término`.
5. **Verbos** globales y de la obra → `verbos_habla`.

Las reglas consultan este objeto, no SQLite. Así el motor sigue siendo
independiente de la persistencia y se puede probar con un `Glosario` en memoria.

## Importación YAML

El YAML es un formato de intercambio, no la fuente de verdad. La importación es
idempotente: se puede repetir el mismo archivo sin duplicar entidades.

```yaml
obra:
  slug: oniriums
  titulo: Oniriums
  autor: Feith Noir
  idioma: es
  genero: fantasía

personajes:
  - nombre: Feith Noir
    rol: protagonista
    alias: [Feith]
    descripcion: Portadora del Velo.

lugares:
  - nombre: Villa Gris
    tipo: ciudad
    alias: [Villa]

terminos:
  - termino: Oniriums
    tipo: glosario
    definicion: Mundo onírico.
    sensible: true
    variantes: [Onirium, "Oniriums'"]
  - termino: Kaar'Tcha
    tipo: nombre
    variantes: [KaarTcha]

verbos_habla:
  - trinó
  - silbó
```

Reglas de importación:

- Si no hay `slug`, se usa el título o el nombre del archivo, normalizado con
  `slugify`.
- Si la obra ya existe, solo se actualizan los campos presentes y no nulos. Un
  `personaje` sin `alias` no borra el alias anterior.
- Los personajes, lugares y términos se buscan por nombre (y tipo, en el caso de
  términos). Si existen, se actualizan.
- Las variantes duplicadas y los verbos repetidos se cuentan en `omitidos`, no
  provocan error.
- Un elemento sin nombre se omite y genera un aviso.
- También existe un atajo `variantes:` en la raíz:

```yaml
variantes:
  Oniriums:
    - Onirium
    - Oniriums'
```

Las claves deben apuntar a un término ya existente en la obra.

`registro importar` informa de creados, actualizados y omitidos por tipo. La
obra importada queda disponible, pero la obra activa no cambia: usa
`--obra <slug>` o `ONIRIFIX_OBRA`.

## Exportación

`registro exportar [ruta]` serializa la obra activa con la misma forma que la
importación:

- `obra` con sus metadatos;
- `personajes` con alias separados en lista;
- `lugares`;
- `terminos` con sus variantes de error;
- `verbos_habla` propios de la obra.

La exportación no incluye los verbos globales ni la auditoría. Es un formato
pensado para versionar el canon de la obra en un repositorio.

## Auditoría e historial

Tras una corrección aplicada:

```bash
onirifix --obra mi-novela corregir manuscrito.md --aplicar
onirifix --obra mi-novela registro historial
```

Cada fila muestra fecha, regla, nivel, línea, original y sugerencia. Para
desactivar la escritura de auditoría:

```bash
onirifix --obra mi-novela corregir manuscrito.md --aplicar --sin-backup
# o en el entorno:
ONIRIFIX_AUDITORIA=false
```

La copia de seguridad y la auditoría son independientes: `--sin-backup` no
desactiva la auditoría.

## Integridad y borrado

- Borrar una obra elimina en cascada personajes, lugares, términos, variantes y
  verbos propios.
- Borrar un término elimina sus variantes.
- Las correcciones históricas quedan con `obra_id = NULL` si se borra la obra
  (no se pierde el registro de auditoría).
- Los nombres duplicados dentro de una obra lanzan `ValueError` con un mensaje
  legible; la CLI lo convierte en error de usuario.

## Copias de seguridad

Los backups se guardan en `.onirifix/backups` por defecto, con el nombre
`archivo.<AAAAMMDD-HHMMSS>.bak`. Si ya existe ese nombre en el mismo segundo, se
añade un contador. Se crean antes de sobrescribir el archivo original; si se
escribe en `--destino`, no se genera backup del origen.

## Pruebas del registro

`tests/test_registro.py` cubre:

- versión de esquema y tablas;
- CRUD de obras, personajes, lugares y términos;
- alias y variantes;
- glosario agregado y verbos globales/propios;
- borrado en cascada;
- auditoría;
- importación idempotente y conservación de campos ausentes;
- round-trip YAML;
- errores de formato y elementos sin nombre.
