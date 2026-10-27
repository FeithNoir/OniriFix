# Contribuir a OniriFix

Gracias por interesarte. OniriFix es una herramienta editorial: la prioridad no
es "corregir mucho", sino **no romper la voz del autor**. Cualquier cambio debe
respetar los tres niveles de confianza y el dry-run por defecto.

## Entorno de desarrollo

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -e ".[dev]"
pytest
```

Para trabajar con las dependencias opcionales:

```bash
pip install -e ".[dev,nlp,ortografia,docx]"
python -m spacy download es_core_news_sm
```

## Reglas de oro

1. **L1 solo con patrones deterministas.** Si dudas, baja a L2.
2. **L2 propone, no impone.** Umbral por defecto 0.90 y confianza explícita.
3. **L3 nunca modifica.** Solo informa.
4. **Toda regla debe ser idempotente.** Añade su caso a
   `tests/test_idempotencia.py`.
5. **No añadas un LLM al núcleo.** El núcleo es offline y determinista.
6. **No inventes datos de una obra.** El registro SQLite es la fuente de verdad.

## Añadir una regla

1. Crea `src/onirifix/reglas/mi_regla.py`.
2. Decora la clase con `@registrar`.
3. Declara `id`, `nivel`, `descripcion`, `prioridad` y `por_defecto`.
4. Implementa `aplicar(texto, ctx)` devolviendo `Hallazgo` mediante
   `crear_hallazgo`.
5. Añade el toggle en `config/reglas.yaml` y documenta la regla en
   `docs/files/reglas.md`.
6. Escribe pruebas unitarias y de idempotencia.

```python
from onirifix.modelo import Nivel, crear_hallazgo
from onirifix.nucleo.registro_reglas import registrar


@registrar
class MiRegla:
    id = "MIA-001"
    nivel = Nivel.L2
    descripcion = "Ejemplo de regla."
    prioridad = 50
    por_defecto = True

    def aplicar(self, texto, ctx):
        for match in PATRON.finditer(texto):
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia="...",
                confianza=0.85,
            )
            if hallazgo:
                yield hallazgo
```

## Estilo

- Python 3.11+, tipado moderno y `from __future__ import annotations`.
- Nombres de dominio en español (`Hallazgo`, `Parche`, `Obra`); APIs de
  librerías, en su idioma original.
- `ruff` y `mypy` deben pasar.
- Comentarios solo cuando explican una decisión, no lo que ya dice el código.

## Documentación

- `README.md`: propósito, instalación, uso.
- `docs/files/arquitectura.md`: capas, módulos, decisiones.
- `docs/files/reglas.md`: catálogo de reglas y límites.
- `docs/files/registro.md`: esquema SQLite y CLI del registro.
- `docs/files/diseno_cli.md`: criterios de experiencia en terminal.

No crees documentos redundantes. Si una regla nueva cambia el contrato público,
actualiza el README y el catálogo.
