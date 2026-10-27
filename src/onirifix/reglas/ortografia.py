"""Ortografía: abreviaturas, diccionario opcional y palabras repetidas."""

from __future__ import annotations

from collections.abc import Iterator

try:  # pragma: no cover
    import regex as re
except ImportError:  # pragma: no cover
    import re  # type: ignore[no-redef]

from onirifix.modelo import Contexto, Hallazgo, Nivel, crear_hallazgo
from onirifix.nucleo.registro_reglas import registrar
from onirifix.reglas._comun import preservar_caso
from onirifix.util import clave


@registrar
class CorreccionesExplicitas:
    id = "ORT-001"
    nivel = Nivel.L2
    descripcion = "Aplica el mapa de correcciones recurrentes de la configuración."
    prioridad = 35
    por_defecto = True

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        correcciones = ctx.config.obtener("ortografia.correcciones", {}) or {}
        if not isinstance(correcciones, dict) or not correcciones:
            return
        mapa = {
            str(clave_original).casefold(): str(valor)
            for clave_original, valor in correcciones.items()
            if str(clave_original).strip()
        }
        if not mapa:
            return
        patron = re.compile(
            r"\b(?:" + "|".join(re.escape(k) for k in sorted(mapa, key=len, reverse=True)) + r")\b",
            flags=re.IGNORECASE | re.UNICODE,
        )
        for match in patron.finditer(texto):
            original = match.group(0)
            reemplazo = mapa.get(original.casefold())
            if not reemplazo:
                continue
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=preservar_caso(original, reemplazo),
                confianza=0.82,
                nota="Corrección explícita del mapa de ortografía.",
            )
            if hallazgo:
                yield hallazgo


@registrar
class DiccionarioOrtografico:
    id = "ORT-002"
    nivel = Nivel.L2
    descripcion = "Consulta un diccionario Hunspell o una lista de palabras."
    prioridad = 44
    por_defecto = True

    _patron = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)?", re.UNICODE)

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        corrector = ctx.corrector
        if corrector is None or not corrector.disponible:
            return

        claves_glosario = {
            clave(p)
            for p in (
                *ctx.glosario.nombres,
                *ctx.glosario.alias,
                *ctx.glosario.toponimos,
                *ctx.glosario.terminos,
                *ctx.glosario.variantes,
            )
        }
        for match in self._patron.finditer(texto):
            palabra = match.group(0)
            if len(palabra) < 2:
                continue
            if palabra[:1].isupper():
                # Evitar señalar nombres propios y palabras al inicio de frase.
                continue
            if clave(palabra) in claves_glosario:
                continue
            if corrector.conocida(palabra):
                continue

            sugerencias = corrector.sugerencias(palabra)
            sugerencia = sugerencias[0] if sugerencias else None
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=sugerencia,
                confianza=0.66 if sugerencia else 0.4,
                nota=(
                    "Palabra desconocida para el diccionario."
                    if sugerencia
                    else "Palabra desconocida sin sugerencias claras."
                ),
            )
            if hallazgo:
                yield hallazgo


@registrar
class PalabraRepetida:
    id = "ORT-003"
    nivel = Nivel.L2
    descripcion = "Detecta palabras repetidas consecutivas («la la»)."
    prioridad = 3
    por_defecto = True

    _patron = re.compile(
        r"\b(?P<palabra>[^\W\d_]+)(?P<separador>[ \t]+)(?P=palabra)\b",
        flags=re.IGNORECASE | re.UNICODE,
    )

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        for match in self._patron.finditer(texto):
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=match.group("palabra"),
                confianza=0.87,
                nota="Palabra repetida consecutiva.",
            )
            if hallazgo:
                yield hallazgo
