"""Reglas de diálogo, la parte más delicada de la ortotipografía española."""

from __future__ import annotations

from collections.abc import Iterator

try:  # pragma: no cover
    import regex as re
except ImportError:  # pragma: no cover
    import re  # type: ignore[no-redef]

from onirifix.modelo import Contexto, Hallazgo, Nivel, crear_hallazgo
from onirifix.nucleo.registro_reglas import registrar
from onirifix.reglas._comun import (
    PALABRAS_REANUDACION,
    es_palabra_glosario,
    minuscula_inicial,
    patron_de,
    verbos_habla,
)

_VERBO_CAPITAL = r"(?P<verbo>[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)\b"
_VERBO_ATRIBUCION = r"(?P<verbo>[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)\b"


def _es_verbo(palabra: str, verbos: frozenset[str]) -> bool:
    return palabra.casefold() in verbos


@registrar
class VerboTrasCierre:
    """DIA-001: «—Basta. —Dijo» → «—Basta. —dijo»."""

    id = "DIA-001"
    nivel = Nivel.L1
    descripcion = "Baja a minúscula el verbo de habla tras el cierre de un diálogo."
    prioridad = 10
    por_defecto = True

    _patron = re.compile(
        r"(?P<cierre>[.!?…])(?P<espacio>[ \t]+)—(?P<espacio2>[ \t]*)" + _VERBO_CAPITAL
    )

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        verbos = verbos_habla(ctx)
        for match in self._patron.finditer(texto):
            if not _es_verbo(match.group("verbo"), verbos):
                continue
            sugerencia = (
                f"{match.group('cierre')}{match.group('espacio')}—"
                f"{minuscula_inicial(match.group('verbo'))}"
            )
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=sugerencia,
                confianza=0.97,
                nota="Verbo de habla en mayúscula tras cierre de diálogo.",
            )
            if hallazgo:
                yield hallazgo


@registrar
class ReanudacionDialogo:
    """DIA-002: propone minúscula cuando el mismo hablante reanuda."""

    id = "DIA-002"
    nivel = Nivel.L2
    descripcion = "Propone minúscula en una reanudación de diálogo tras atribución."
    prioridad = 80
    por_defecto = True

    _patron = re.compile(
        r"(?P<cierre>[.!?…])(?P<espacio>[ \t]*)—"
        r"(?P<palabra>[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)\b"
    )

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        verbos = verbos_habla(ctx)
        patron_verbos = re.compile(r"\b(?:" + patron_de(verbos) + r")\b", re.IGNORECASE)
        for match in self._patron.finditer(texto):
            palabra = match.group("palabra")
            if palabra.casefold() not in PALABRAS_REANUDACION:
                continue
            if es_palabra_glosario(palabra, ctx.glosario):
                continue
            previo = texto[max(0, match.start() - 140) : match.start()]
            if not patron_verbos.search(previo):
                continue
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start("palabra"),
                fin=match.end("palabra"),
                sugerencia=minuscula_inicial(palabra),
                confianza=0.62,
                nota=(
                    "Posible reanudación del mismo hablante. La mayúscula también "
                    "puede ser correcta si empieza una intervención nueva."
                ),
            )
            if hallazgo:
                yield hallazgo


@registrar
class ModoRaeEstricto:
    """DIA-003: «—Basta. —dijo» → «—Basta —dijo»."""

    id = "DIA-003"
    nivel = Nivel.L1
    descripcion = "Modo RAE estricto: elimina el punto interior antes de la atribución."
    prioridad = 4
    por_defecto = False

    _patron = re.compile(
        r"(?P<cierre>[.!?…])(?P<espacio>[ \t]*)—(?P<espacio2>[ \t]*)"
        + _VERBO_ATRIBUCION
    )

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        if not bool(ctx.config.obtener("dialogos.rae_estricto", False)):
            return
        verbos = verbos_habla(ctx)
        for match in self._patron.finditer(texto):
            if not _es_verbo(match.group("verbo"), verbos):
                continue
            sugerencia = f" —{minuscula_inicial(match.group('verbo'))}"
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=sugerencia,
                confianza=0.92,
                nota="Puntuación de diálogo en modo RAE estricto (opt-in).",
            )
            if hallazgo:
                yield hallazgo


@registrar
class EspacioAntesDeRaya:
    """DIA-004: «Hola—dijo» → «Hola —dijo»."""

    id = "DIA-004"
    nivel = Nivel.L1
    descripcion = "Añade el espacio que falta antes de una raya de atribución."
    prioridad = 15
    por_defecto = True

    _patron = re.compile(r"(?<=[a-záéíóúüñ])—(?P<verbo>[a-záéíóúüñ]+)\b")

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        verbos = verbos_habla(ctx)
        for match in self._patron.finditer(texto):
            if not _es_verbo(match.group("verbo"), verbos):
                continue
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=f" —{match.group('verbo')}",
                confianza=0.94,
                nota="Falta un espacio antes de la raya de atribución.",
            )
            if hallazgo:
                yield hallazgo


@registrar
class EspacioDespuesDeRaya:
    """DIA-005: «Mico—Las» → «Mico— Las»."""

    id = "DIA-005"
    nivel = Nivel.L1
    descripcion = "Añade el espacio que falta después de una raya de cierre."
    prioridad = 16
    por_defecto = True

    _patron = re.compile(r"(?<=[a-záéíóúüñ])—(?=[A-ZÁÉÍÓÚÜÑ])")

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        for match in self._patron.finditer(texto):
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia="— ",
                confianza=0.9,
                nota="Falta un espacio después de la raya de cierre.",
            )
            if hallazgo:
                yield hallazgo
