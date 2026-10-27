# Arquitectura de OniriFix

Este documento describe la implementación actual de OniriFix: sus capas, el
flujo de una corrección, las decisiones de diseño y los puntos de extensión.
La especificación original que sirvió de punto de partida se conserva en
[`project.md`](project.md).

## Principios

1. **El autor decide.** L1 corrige mecánica segura, L2 propone con umbral y L3
   solo informa. Ningún hallazgo L3 se convierte en parche.
2. **Dry-run por defecto.** `analizar` y `corregir` no escriben el manuscrito
   salvo que se use `--aplicar`. Antes de sobrescribir se crea una copia con
   marca de tiempo.
3. **Determinismo y offline.** El núcleo no llama a LLMs ni a servicios de red.
   spaCy o Hunspell son opcionales y solo enriquecen la detección; sin ellos el
   programa sigue funcionando.
4. **Trazabilidad.** Cada parche aplicado puede registrarse en SQLite con regla,
   nivel, posición, confianza y texto original/sugerido.
5. **Idempotencia.** Aplicar dos veces la misma corrección no cambia el
   resultado. Las reglas y los parches se diseñan para no generar ruido cuando
   el texto ya es correcto.

## Capas

```text
┌──────────────────────────────────────────────────────────────┐
│ Presentación        cli.py · informes/terminal.py            │
│                     Click, Rich, preguntas interactivas      │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│ Servicio            servicio.py                              │
│                     abrir_contexto, analizar, corregir,      │
│                     auditoría, selección de niveles          │
└───────┬──────────────────────┬──────────────────────┬────────┘
        │                      │                      │
┌───────▼────────┐   ┌─────────▼─────────┐   ┌────────▼───────┐
│ Dominio        │   │ Núcleo            │   │ Persistencia   │
│ modelo.py      │   │ motor.py          │   │ db/            │
│ Hallazgo       │   │ parches.py        │   │ SQLite + repos │
│ Parche, Regla  │   │ backups.py        │   │ importador     │
│ Obra, Glosario │   │ registro_reglas   │   │ auditoría      │
└───────┬────────┘   └─────────┬─────────┘   └────────────────┘
        │                      │
┌───────▼──────────────────────▼───────────────────────────────┐
│ Reglas              reglas/tipografia.py · dialogos.py ·      │
│                     tildes.py · homofonos.py · ortografia.py  │
│                     consistencia.py · repeticion.py           │
└──────────────────────────────────────────────────────────────┘

Infraestructura transversal: config.py · io/cargadores.py ·
informes/ (Markdown, CSV, JSON, diff) · linguistica.py · util.py
```

La dependencia apunta hacia el dominio y el núcleo. Las reglas no conocen
Click, SQLite ni la terminal. La CLI no contiene SQL ni lógica lingüística: solo
resuelve opciones, abre un contexto de servicio y presenta resultados.

## Módulos

| Ruta | Responsabilidad |
| :--- | :--- |
| `src/onirifix/cli.py` | Comandos, opciones globales, códigos de salida y presentación. |
| `src/onirifix/servicio.py` | Orquesta configuración, registro, motor, E/S y auditoría. |
| `src/onirifix/modelo.py` | Tipos inmutables del dominio: `Hallazgo`, `Parche`, `Documento`, `Glosario`, `Obra`… |
| `src/onirifix/config.py` | Defaults, fusión del YAML, variables de entorno y `Settings`. |
| `src/onirifix/nucleo/motor.py` | Activa reglas, captura errores, deduplica y ordena hallazgos. |
| `src/onirifix/nucleo/parches.py` | Selecciona por nivel/umbral y aplica parches verificando offsets. |
| `src/onirifix/nucleo/registro_reglas.py` | Registro global y descubrimiento automático de plugins. |
| `src/onirifix/nucleo/backups.py` | Copia `archivo.<timestamp>.bak` antes de escribir. |
| `src/onirifix/db/conexion.py` | Apertura de SQLite, PRAGMAs y validación del esquema. |
| `src/onirifix/db/esquema.py` | DDL versionado (`PRAGMA user_version = 1`). |
| `src/onirifix/db/repositorios.py` | Repositorios y fachada `Registro`. |
| `src/onirifix/db/importador.py` | Importación/exportación YAML idempotente. |
| `src/onirifix/reglas/` | Catálogo de reglas L1/L2/L3. |
| `src/onirifix/informes/` | Markdown, CSV, JSON, diff y tablas de terminal. |
| `src/onirifix/io/cargadores.py` | Lectura UTF-8/CP1252, BOM, saltos y detección de capítulos. |
| `src/onirifix/linguistica.py` | Adaptadores opcionales de spaCy y spylls. |

## Flujo de análisis

1. La CLI resuelve `Settings` (rutas, obra, umbral, backup y auditoría) con la
   precedencia `defaults < YAML < entorno < CLI`.
2. `abrir_contexto()` valida o crea la obra, abre SQLite y construye un
   `Glosario` agregado con personajes, alias, lugares, términos, variantes y
   verbos de habla.
3. `cargar_documento()` lee el archivo, normaliza saltos de línea y detecta
   capítulos por encabezados Markdown o líneas canónicas.
4. `Motor.analizar()` recorre las reglas activas. Cada regla recibe el texto
   completo y un `Contexto` con configuración, glosario y documento.
5. El motor captura excepciones por regla: un fallo en una regla no cancela el
   resto y queda en `ResultadoAnalisis.errores`.
6. `deduplicar()` elimina solapamientos. Ante dos hallazgos sobre el mismo
   tramo, gana el de menor `prioridad`, luego L1/L2/L3 y finalmente el de mayor
   confianza.
7. El resultado se presenta en terminal y, si se pide, se escribe en Markdown,
   CSV y JSON.

## Flujo de corrección

1. Se analiza el documento con todas las reglas para conservar también el
   contexto editorial (L3 aparece en los informes).
2. `seleccionar_parches()` convierte hallazgos en parches:
   - L1 se selecciona si el nivel está permitido;
   - L2 solo con `--aplicar-l2` y confianza `>= umbral_l2`;
   - L3 nunca.
3. `aplicar_parches()` ordena por offset, comprueba que `original` siga en la
   posición esperada y aplica de izquierda a derecha. Los parches solapados o
   desfasados se omiten con un motivo explícito.
4. Si `--aplicar` está activo y hay cambios:
   - se crea un backup si se sobrescribe el archivo original;
   - se escribe el destino con la codificación de entrada (UTF-8 para `.docx`);
   - se registran los parches aplicados en `correcciones` si la auditoría está
     activa.
5. Los informes incluyen el diff (`parches.diff`) solo cuando hay cambios.

## Reglas como plugins

Una regla es una clase con `id`, `nivel`, `descripcion`, `prioridad`,
`por_defecto` y un método `aplicar(texto, ctx)` que devuelve un iterable de
`Hallazgo`. El decorador `@registrar` instancia y registra la clase:

```python
from onirifix.modelo import Contexto, Hallazgo, Nivel, crear_hallazgo
from onirifix.nucleo.registro_reglas import registrar


@registrar
class MiRegla:
    id = "MIA-001"
    nivel = Nivel.L1
    descripcion = "Ejemplo de regla."
    prioridad = 50
    por_defecto = True

    def aplicar(self, texto: str, ctx: Contexto):
        for coincidencia in ...:
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=coincidencia.start(),
                fin=coincidencia.end(),
                sugerencia="...",
                confianza=0.95,
            )
            if hallazgo is not None:
                yield hallazgo
```

`descubrir_reglas()` importa todos los módulos de `onirifix.reglas` y devuelve
las instancias ordenadas por prioridad. Para añadir una regla basta con crear
un archivo en ese paquete; no hay que editar el motor.

## Configuración y determinismo

- `Configuracion` fusiona los defaults con el YAML de forma recursiva. Un mapa
  vacío (`correcciones: {}`) vacía deliberadamente el default correspondiente.
- Las reglas consultan la configuración a través de `Contexto.config`, nunca de
  variables globales.
- Las dependencias opcionales se encapsulan en `linguistica.py`. Si no están
  instaladas, las reglas que las necesitan simplemente no aportan hallazgos.
- Los informes JSON incluyen `generado_en`; el análisis en sí es determinista.

## Errores y códigos de salida

- `manejar_errores` convierte `ValueError`, `OSError`, `UnicodeError` y
  `ErrorLectura` en `click.ClickException` legibles.
- `analizar --estricto` devuelve código `1` si hay hallazgos L1/L2.
- Los errores de una regla se aíslan y se muestran en el informe; no abortan la
  ejecución.
- Un esquema SQLite más nuevo o más antiguo lanza `ErrorEsquema` con
  instrucciones de migración.

## Decisiones deliberadas

- **No hay ORM.** SQLite estándar y repositorios explícitos mantienen el
  empaquetado ligero y el SQL visible.
- **El glosario manda sobre el diccionario.** Los nombres del universo y sus
  variantes se consultan antes que cualquier corrección general.
- **L3 es inmutable.** Frecuencia, duplicados, residuo de IA y frases largas solo
  producen material de revisión.
- **La auditoría es opcional.** Se puede desactivar con
  `ONIRIFIX_AUDITORIA=false` o `auditoria: false` para auditar el rendimiento
  sin escribir en la base.
- **La CLI no hace magia.** Las opciones globales (`--db`, `--config`, `--obra`)
  van antes del subcomando, como en `onirifix --obra oniriums analizar ...`.

## Siguientes pasos técnicos

- Escritura de `.docx` preservando estilos (hoy solo se lee).
- Reglas adicionales de estilo y ritmo, siempre en L3.
- Exportación de parches revisables en formato editorial.
- Migraciones automáticas cuando cambie `VERSION_ESQUEMA`.
