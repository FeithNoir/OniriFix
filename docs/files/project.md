## 1. Filosofía de diseño

Una herramienta de corrección de ficción tiene una regla de oro: **puede sugerirlo todo, pero solo decide el autor.** El objetivo no es "arreglar el libro": es eliminar el trabajo mecánico para que tu energía se gaste en las decisiones editoriales de verdad — la voz de Feith Noir, los residuos de IA, el ritmo de los capítulos finales. De ahí se derivan cinco principios no negociables:

1. **Tres niveles de confianza, nunca dos.** Lo mecánico se corrige solo; lo contextual se propone; lo estilístico jamás se toca.
2. **Dry-run por defecto.** Ningún archivo se modifica sin la bandera explícita `--aplicar`, y antes de tocar nada se crea copia de seguridad con marca de tiempo.
3. **Idempotencia.** `corregir(corregir(x)) == corregir(x)`. Los 39 casos de diálogo que ya están bien escritos deben sobrevivir intactos a cualquier pasada.
4. **Trazabilidad total.** Cada cambio queda registrado con línea, contexto, regla y confianza. Nada se corrige "en silencio".
5. **Offline-first y determinista.** El núcleo no llama a ningún LLM: mismas entradas, mismas salidas.

### Los tres niveles de seguridad

| Nivel | Nombre | Qué hace | Ejemplo real del manuscrito | ¿Modifica el archivo? |
|---|---|---|---|---|
| **L1** | Mecánico | Corrige solo patrones 100 % deterministas | «—Basta. **—Dijo** Mico» → «—dijo» | Sí, con `--aplicar` |
| **L2** | Asistido | Detecta y propone; corrige solo por encima de un umbral de confianza | **hacía** (verbo) vs **hacia** (preposición) · `mirá` → `mirará` | Con `--aplicar-l2 --umbral 0.9` |
| **L3** | Solo informe | Señala; jamás corrige | `soltó` ×330 · párrafos duplicados · residuo de IA | Nunca |

---

## 2. Mapa problema → automatización

Mapeo directo con los hallazgos del informe editorial:

| # | Problema detectado | Volumen | Estrategia técnica | Nivel |
|---|---|---|---|---|
| 1 | Mayúscula tras raya en atribución («—Dijo…») | 1260 (vs 39 correctos) | 3 sub-patrones regex + verificación morfológica | L1/L2 |
| 2 | Tipografía mecánica (dobles espacios, comillas rectas, `...` → `…`, raya `–` vs `—`) | cientos | regex puro | L1 |
| 3 | Futuros truncados (`mirá`, `susurrá`) | ~25 | diccionario + candidato morfológico | L2 |
| 4 | Homófonos y tildes contextuales (`hacía/hacia` ×18, `barrió`, `halláis`) | ~23 | POS-tagging de spaCy + lista de homófonos | L2 |
| 5 | Variantes de nombres propios (Kaar'Tcha, M'dir…) | puntuales | glosario YAML + similitud difusa | L2 |
| 6 | Repetición léxica (`soltó` ×330, `dijo` ×348, `suspirar` ×201, «en seco» ×34) | — | frecuencias + densidad por capítulo | L3 |
| 7 | Párrafos/scenas duplicados y residuo de IA (Cap. 3 y 8) | ~15 bloques | hash exacto + similitud difusa | L3 |
| 8 | Puntuación RAE estricta («—X. —dijo» → «—X —dijo») | opcional | sub-regla configurable (opt-in) | L1 opt-in |

**Lo que NO se automatiza, por diseño:** la reescritura de repeticiones (decidir qué `soltó` muta a `espetó` es prosodia, no regex), el borrado de residuos de IA (solo se señalan) y cualquier cambio que afecte a la voz de los tres protagonistas.

---

## 3. Stack de librerías

| Librería | Rol | Por qué esta y no otra |
|---|---|---|
| `regex` | Motor de patrones | Sustituto directo de `re` con Unicode real (`\p{Lu}`, `\p{L}`): imprescindible para ÁÉÍÓÚÜÑ |
| `spacy` + `es_core_news_sm/lg` | POS, NER, lemas | Lo único que distingue de forma fiable `hacia` (ADP) de `hacía` (VERB), y un nombre propio de un verbo de habla |
| `spylls` (o `hunspell`) | Corrector ortográfico | Diccionario español + diccionario personalizado con el glosario de Oniriums; detecta `mirá`/`susurrá`/`halláis` |
| `rapidfuzz` | Similitud de cadenas | Duplicados difusos (el residuo de IA rara vez es copia exacta) |
| `click` | CLI | Comandos limpios, ayuda autogenerada |
| `rich` | Terminal e informes | Tablas, diffs coloreados y progreso para 223 000 palabras |
| `PyYAML` | Configuración | El glosario del universo se edita sin tocar código |
| `pytest` | Tests | Golden tests con fragmentos reales del manuscrito |
| `python-docx` (fase futura) | E/S de Word | Para parchear directamente el .docx preservando estilos |

```bash
pip install regex spacy rapidfuzz click rich pyyaml pytest
python -m spacy download es_core_news_sm     # rápido; `lg` si quieres máxima precisión
pip install spylls                            # hunspell en Python puro, sin Java
```

---

## 4. Arquitectura

```
                    ┌─────────────────────────────────────────┐
                    │                 CLI (click)             │
                    │   analizar · corregir · revisar · ...   │
                    └───────────────────┬─────────────────────┘
                                        │
        ┌───────────────┐   ┌───────────▼───────────┐   ┌──────────────────┐
        │  E/S (io/)    │──▶│   MOTOR (nucleo/)     │──▶│  INFORMES        │
        │ txt·md·docx   │   │ pipeline de reglas    │   │ md·csv·json·diff │
        │ + backups     │   │ registry · parches    │   │ terminal (rich)  │
        └───────────────┘   └───────────┬───────────┘   └──────────────────┘
                                        │
        ┌───────────────┬───────────────▼──────────────┬───────────────────┐
        │  reglas/L1    │        reglas/L2             │   reglas/L3       │
        │ tipografía    │  diálogo-B · tildes POS      │  frecuencia       │
        │ diálogo-A     │  ortografía+diccionario      │  duplicados       │
        │               │  consistencia onomástica     │  residuo IA       │
        └───────────────┴──────────────▲───────────────┴───────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │  CONFIG (YAML, editable sin código) │
                    │  mundo_oniriums.yaml · reglas.yaml  │
                    └─────────────────────────────────────┘
```

### Estructura del proyecto

```
onirifix/
├── pyproject.toml
├── config/
│   ├── reglas.yaml               # toggles y umbrales por regla
│   └── mundo_oniriums.yaml       # glosario del universo (lo editas tú)
├── src/onirifix/
│   ├── cli.py                    # comandos click
│   ├── modelo.py                 # Hallazgo, Regla, Contexto, Parche
│   ├── nucleo/
│   │   ├── motor.py              # ejecuta reglas, deduplica, ordena
│   │   ├── parches.py            # aplica L1/L2 verificando idempotencia
│   │   └── backups.py            # copia con timestamp antes de tocar nada
│   ├── reglas/
│   │   ├── dialogos.py           # DIA-001/002/003 (la regla estrella)
│   │   ├── tildes.py             # TIL-001 hacía/hacia · TIL-002 truncados
│   │   ├── ortografia.py         # ORT-001 diccionario + glosario
│   │   ├── tipografia.py         # TIP-00x mecánicas (L1)
│   │   ├── consistencia.py       # CON-001 variantes de nombres
│   │   └── repeticion.py         # REP-001/002 (solo informe)
│   ├── informes/                 # markdown, csv, json, diff, terminal
│   └── io/                       # cargadores txt/md/docx
└── tests/
    ├── golden/                   # fragmentos reales → salida esperada
    ├── test_idempotencia.py
    └── test_reglas.py
```

**Decisión clave:** cada regla es un *plugin* auto-contenido que registra su `id`, su nivel y su función `aplicar()`. El motor no sabe nada de diálogos ni tildes: solo ejecuta reglas, deduplica hallazgos solapados y los ordena por línea. Añadir una regla nueva = añadir un archivo de ~40 líneas.

---

## 5. Las reglas, en detalle

### 5.1 La regla estrella: mayúsculas en diálogos (1260 casos)

Es el error sistemático mayor del manuscrito (1260 incorrectos frente a 39 correctos). Se descompone en tres sub-patrones:

- **DIA-001 (L1) — Verbo de habla tras cierre de frase.** «—Basta. **—Dijo** Mico.» La mayúscula es siempre errónea. Determinista al 100 %.
- **DIA-002 (L2) — Reanudación de diálogo.** «—… —dijo Mico. **—Las** llaves están…» Si el mismo personaje continúa, minúscula; si cambia de hablante o es frase nominal, puede ser correcta. Heurística de hablante + verificación de nombre propio.
- **DIA-003 (L1, opt-in) — Modo RAE estricto.** «—Basta. —dijo Mico.» → «—Basta —dijo Mico.» (elimina el punto interior cuando sigue el verbo de atribución).

```python
# src/onirifix/reglas/dialogos.py
import regex as re  # mejor soporte Unicode que `re`

VERBOS = ["dijo", "preguntó", "respondió", "susurró", "murmuró", "gruñó",
          "bramó", "exclamó", "añadió", "observó", "soltó", "espetó",
          "replicó", "insistió", "concluyó", "vociferó"]
CAPS = "|".join(v.capitalize() for v in VERBOS)

# DIA-001: cierre de frase + raya + verbo de habla en mayúscula
RE_DIA1 = re.compile(rf"([.!?…]) —({CAPS})\b")

def aplicar(texto, ctx):
    for m in RE_DIA1.finditer(texto):
        original, verbo = m.group(0), m.group(2)
        fijado = f"{m.group(1)} —{verbo[0].lower()}{verbo[1:]}"
        yield Hallazgo(
            regla="DIA-001", nivel="L1",
            linea=texto[:m.start()].count("\n") + 1,
            contexto=texto[max(0, m.start() - 60): m.end() + 60],
            original=original, sugerencia=fijado,
            confianza=0.97,
            nota="Verbo de habla en mayúscula tras cierre de diálogo.",
        )
```

Para **DIA-002**, la heurística es: *si la palabra tras la raya está en el glosario de nombres (Feith, Mico, Vespera…), no se toca; si el lematizador la identifica como verbo o sustantivo común sobre la frase completa, se propone minúscula con confianza ~0.80; si es ambigua, revisión interactiva.* Los 39 casos correctos quedan protegidos por construcción: la regla solo baja mayúsculas que hoy están altas, nunca al revés.

### 5.2 Tildes contextuales con POS-tagging (hacía/hacia)

Un diccionario no puede decidir entre `hacia` y `hacía`; un etiquetador morfológico sí:

```python
# src/onirifix/reglas/tildes.py
def revisar_hacia(frase, ctx):
    for tok in ctx.nlp(frase):
        if tok.text.lower() == "hacia":
            if tok.lemma_ == "hacer" and tok.pos_ in ("VERB", "AUX"):
                return "hacía"      # «hacia frío» → «hacía frío» (conf. 0.95)
            if tok.pos_ in ("ADP", "ADV"):
                return None         # «caminaba hacia el norte»: correcta
            return "REVISAR"        # ambigua → L2 con confianza baja
```

La misma estructura sirve para los homófonos vigilados (`barrió`, `halláis`, `sino/si no`, `haber/a ver`…): detección por diccionario + contexto, propuesta y confirmación.

### 5.3 Futuros truncados (`mirá`, `susurrá`)

El patrón del manuscrito es un futuro al que le falta una sílaba. Un candidato morfológico simple lo caza:

```python
RE_TRUNCO = re.compile(r"\b\p{L}+á\b")     # palabra terminada en á tónica

def candidato(tok: str, dicc) -> str | None:
    base = tok[:-1]                         # «mirá» → «mir»
    for sufijo in ("ará", "aráis", "arás"):
        if (propuesta := base + sufijo) in dicc:
            return propuesta                # «mir» + «ará» = «mirará» ✓
    return None
```

Nivel L2 con confirmación: si algún día un personaje hablara en voseo («mirá esto»), la regla se desactiva por personaje/registro desde `reglas.yaml`.

### 5.4 Consistencia onomástica

El universo tiene su propio diccionario, editable por ti y siempre por encima del diccionario general:

```yaml
# config/mundo_oniriums.yaml
nombres: [Feith, Noir, Mico, Ralex, Elara, Vespera, "Kaar'Tcha", Miguel, Carlos, Cocoa]
glosario: [Oniriums, onirio, jerinca, Mochi, azotador, "Placas Maestras", Velo]
toponimos: ["Villa Gris", "Campos Dorados", "M'dir", "Bosque de Ceniza"]
variantes:
  "Kaar'Tcha": ["KaarTcha", "Kaar Tcha", "Kaar-tcha"]
  "Cocoa de M'dir": ["Cocoa de Mdir", "Cocoa de M' dir"]
verbos_habla_extra: [trinó, silbó]
```

CON-001 busca variantes (exactas y difusas) y propone reemplazo global confirmado — vital para la secuela, donde **Mochi** y **jerinca** deben sembrarse con ortografía idéntica desde el primer capítulo.

### 5.5 Repetición y duplicados (solo informe)

```python
import hashlib
from rapidfuzz import fuzz

def duplicados(parrafos, min_palabras=8):
    exactos, previos = {}, []
    for i, p in enumerate(parrafos):
        huella = " ".join(p.lower().split())
        if len(huella.split()) < min_palabras:
            continue
        k = hashlib.md5(huella.encode()).hexdigest()
        if k in exactos:
            yield ("EXACTO", exactos[k], i)
        else:
            for j, h in previos:
                if fuzz.ratio(huella, h) >= 92:      # residuo de IA reformulado
                    yield ("DIFUSO", j, i)
        exactos.setdefault(k, i)
        previos.append((i, huella))
```

REP-001 produce el informe de frecuencias (top-N con densidad por capítulo, filtrando el glosario) y REP-002 los duplicados exactos y difusos. Ambos alimentan la decisión editorial sobre los residuos de IA de los Cap. 3 y 8, pero **jamás borran nada**.

---

## 6. Modelo de datos y pipeline

```python
# src/onirifix/modelo.py
from dataclasses import dataclass
from typing import Iterator, Literal, Protocol

Nivel = Literal["L1", "L2", "L3"]

@dataclass(frozen=True)
class Hallazgo:
    regla: str            # "DIA-001"
    nivel: Nivel
    linea: int
    contexto: str         # ±60 caracteres alrededor
    original: str
    sugerencia: str | None
    confianza: float      # 0.0 – 1.0
    nota: str = ""

@dataclass
class Contexto:
    glosario: dict        # cargado de mundo_oniriums.yaml
    nlp: object           # pipeline spaCy compartido (se crea una vez)
    config: dict

class Regla(Protocol):
    id: str
    nivel: Nivel
    descripcion: str
    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]: ...
```

**Pipeline de ejecución:**

1. **Cargar** el texto canónico (UTF-8, numeración de líneas estable) y las configs YAML.
2. **Inicializar** spaCy una sola vez y procesar párrafos con `nlp.pipe()`.
3. **Ejecutar** todas las reglas activadas, recolectando hallazgos.
4. **Deduplicar** hallazgos solapados (una posición no recibe dos parches).
5. **Clasificar**: L1 → cola de parches; L2 → filtrada por `--umbral`; L3 → solo informe.
6. **Backup** con timestamp si hay `--aplicar`.
7. **Aplicar** parches de derecha a izquierda verificando que `original` sigue presente en la posición esperada.
8. **Emitir** informes: `informe.md`, `hallazgos.csv`, `parches.diff` y resumen en terminal.

---

## 7. CLI

```text
onirifix analizar manuscrito.txt --salida informes/        # ver todo, no tocar nada
onirifix corregir manuscrito.txt --nivel L1 --backup       # lo mecánico, con backup
onirifix corregir manuscrito.txt --nivel L2 --umbral 0.9   # lo asistido, por confianza
onirifix revisar manuscrito.txt --reglas DIA-002,TIL-001   # interactivo: sí/no/editar
onirifix frecuencia manuscrito.txt --top 50 --por-capitulo # informe L3
onirifix duplicados manuscrito.txt --similitud 92          # informe L3
```

---

## 8. Informes de salida

| Archivo | Contenido | Uso |
|---|---|---|
| `informe.md` | Hallazgos agrupados por regla, con cita en contexto | Lectura humana |
| `hallazgos.csv` | Una fila por hallazgo (regla, línea, confianza, sugerencia) | Filtrable en Excel |
| `parches.diff` | Diff unificado de lo aplicado | Auditoría reversible |
| Terminal (rich) | Conteos por regla y % de avance | Marcador de la campaña |

---

## 9. Estrategia de tests

- **Golden tests:** ~60 casos reales de los 1260 + los de tildes, con su salida esperada exacta.
- **Idempotencia (propiedad):** aplicar dos veces = aplicar una. Garantía formal de que los 39 correctos sobreviven.
- **Test de no-daño:** sobre un texto de control limpio (un capítulo de una novela publicada), 0 hallazgos L1.
- **Corpus de regresión:** tras cada cambio, correr el manuscrito completo; el conteo debe decrecer de forma monótona (1260 → 900 → 300 → 0).

---

## 10. Hoja de ruta

| Fase | Contenido | Entregable visible | Estimación |
|---|---|---|---|
| 0 | Esqueleto + carga + `frecuencia` | Primer informe REP-001 | 1 sesión |
| 1 | Tipografía L1 + DIA-001 | ~75 % de los 1260 resueltos | 1 sesión |
| 2 | spaCy: DIA-002, TIL-001, TIL-002 | Nivel L2 con umbral | 2–3 sesiones |
| 3 | Diccionario + glosario + CON-001 | Ortografía con diccionario propio | 1–2 sesiones |
| 4 | REP-002 duplicados + informes | Detección de residuo de IA | 1 sesión |
| 5 | Modo interactivo + golden tests | v1.0 lista para la campaña | 1–2 sesiones |

---

## 11. Riesgos conocidos y mitigación

1. **Falso positivo por voseo.** «Mirá esto» es válido en voseo → desactivación por personaje/registro.
2. **Nombres que son palabras.** «Mico» significa «mono»: el glosario del universo manda siempre sobre el diccionario general.
3. **Sobre-corrección en DIA-002.** La reanudación de diálogo es lo más ambiguo de la ortotipografía española; por eso A es L1 y B es L2.
4. **Rendimiento.** 223 000 palabras: `nlp.pipe()` por párrafos y caché; las reglas regex son instantáneas.
5. **Homogeneidad estilística.** Si algún día entra un LLM para L3, nunca reescribe en cadena: la variación de repeticiones es decisión tuya.

## 12. Flujo de trabajo recomendado

1. `onirifix analizar` → leer `informe.md` completo (estimación del daño).
2. `corregir --nivel L1 --backup` → el grueso mecánico en segundos.
3. `revisar --reglas DIA-002,TIL-001,TIL-002` → media hora de decisiones 1-clic.
4. `frecuencia` + `duplicados` → con el informe L3 delante, decides a mano qué `soltó` sobrevive y qué bloque del Cap. 3/8 se elimina.
5. Repetir tras cada sesión de reescritura: el conteo de hallazgos es tu métrica objetiva de progreso.

---