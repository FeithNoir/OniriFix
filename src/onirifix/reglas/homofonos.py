"""Homófonos con contexto suficiente para proponer un cambio (L2)."""

from __future__ import annotations

from collections.abc import Iterator

try:  # pragma: no cover
    import regex as re
except ImportError:  # pragma: no cover
    import re  # type: ignore[no-redef]

from onirifix.modelo import Contexto, Hallazgo, Nivel, crear_hallazgo
from onirifix.nucleo.registro_reglas import registrar
from onirifix.reglas._comun import preservar_caso


@registrar
class HaberSi:
    id = "HOM-001"
    nivel = Nivel.L2
    descripcion = "Corrige «haber si» por «a ver si»."
    prioridad = 42
    por_defecto = True

    _patron = re.compile(
        r"\b(?P<palabra>haber)\b(?=\s+(?:si|qué|cómo|cuándo|dónde|quién)\b)",
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
                sugerencia=preservar_caso(match.group("palabra"), "a ver"),
                confianza=0.93,
                nota="«A ver» introduce una comprobación; «haber» es el auxiliar.",
            )
            if hallazgo:
                yield hallazgo


@registrar
class AVerParticipio:
    id = "HOM-002"
    nivel = Nivel.L2
    descripcion = "Corrige «a ver + participio» por «haber + participio»."
    prioridad = 43
    por_defecto = True

    _patron = re.compile(
        r"\b(?P<palabra>a ver)\b(?=\s+(?:sido|tenido|hecho|dicho|visto|puesto|"
        r"escrito|roto|vuelto|abierto|cerrado|muerto|nacido|venido|ido)\b)",
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
                sugerencia=preservar_caso(match.group("palabra"), "haber"),
                confianza=0.9,
                nota="Delante de un participio corresponde el auxiliar «haber».",
            )
            if hallazgo:
                yield hallazgo
