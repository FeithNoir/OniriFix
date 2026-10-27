"""Reglas de tipografía mecánica (L1)."""

from __future__ import annotations

from collections.abc import Iterator

try:  # pragma: no cover
    import regex as re
except ImportError:  # pragma: no cover
    import re  # type: ignore[no-redef]

from onirifix.modelo import Contexto, Hallazgo, Nivel, crear_hallazgo
from onirifix.nucleo.registro_reglas import registrar


@registrar
class EspaciosMultiples:
    id = "TIP-001"
    nivel = Nivel.L1
    descripcion = "Colapsa espacios múltiples entre palabras."
    prioridad = 60
    por_defecto = True

    _patron = re.compile(r"(?<=[^\s.,;:!?…])[ \t]{2,}(?=[^\s.,;:!?…])")

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        for match in self._patron.finditer(texto):
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=" ",
                confianza=0.99,
                nota="Espacios múltiples entre palabras.",
            )
            if hallazgo:
                yield hallazgo


@registrar
class EspaciosAntesDePuntuacion:
    id = "TIP-002"
    nivel = Nivel.L1
    descripcion = "Elimina espacios antes de comas, puntos y signos de cierre."
    prioridad = 20
    por_defecto = True

    _patron = re.compile(r"[ \t]+(?P<punct>[,.;:!?…])(?![,.;:!?…])")

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        for match in self._patron.finditer(texto):
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=match.group("punct"),
                confianza=0.98,
                nota="Espacio antes de signo de puntuación.",
            )
            if hallazgo:
                yield hallazgo


@registrar
class EspacioDespuesDePuntuacion:
    id = "TIP-003"
    nivel = Nivel.L1
    descripcion = "Añade espacio después de coma, punto y coma o dos puntos."
    prioridad = 30
    por_defecto = True

    _patron = re.compile(r"(?P<punct>[,;:])(?=[^\W\d_])", re.UNICODE)

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        for match in self._patron.finditer(texto):
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=match.group("punct") + " ",
                confianza=0.96,
                nota="Falta un espacio después de la puntuación.",
            )
            if hallazgo:
                yield hallazgo


@registrar
class PuntosSuspensivos:
    id = "TIP-004"
    nivel = Nivel.L1
    descripcion = "Convierte tres o más puntos en puntos suspensivos (…)."
    prioridad = 10
    por_defecto = True

    _patron = re.compile(r"[ \t]*\.{3,}")

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        for match in self._patron.finditer(texto):
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia="…",
                confianza=0.99,
                nota="Puntos suspensivos tipográficos.",
            )
            if hallazgo:
                yield hallazgo


@registrar
class ComillasRectas:
    id = "TIP-005"
    nivel = Nivel.L1
    descripcion = "Convierte comillas rectas emparejadas al estilo configurado."
    prioridad = 40
    por_defecto = True

    _patron = re.compile(r'"(?P<interior>[^"\n]{1,2000})"')

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        if not bool(ctx.config.obtener("tipografia.convertir_comillas", True)):
            return
        comillas = ctx.config.comillas
        apertura, cierre = comillas[0], comillas[1]
        for match in self._patron.finditer(texto):
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=f"{apertura}{match.group('interior')}{cierre}",
                confianza=0.97,
                nota="Comillas rectas emparejadas.",
            )
            if hallazgo:
                yield hallazgo


@registrar
class Apostrofos:
    id = "TIP-006"
    nivel = Nivel.L1
    descripcion = "Convierte apóstrofos rectos entre letras en apóstrofos tipográficos."
    prioridad = 70
    por_defecto = False

    _patron = re.compile(r"(?<=[^\W\d_])['’](?=[^\W\d_])", re.UNICODE)

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        if not bool(ctx.config.obtener("tipografia.convertir_apostrofos", False)):
            return
        for match in self._patron.finditer(texto):
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia="’",
                confianza=0.95,
                nota="Apóstrofo tipográfico.",
            )
            if hallazgo:
                yield hallazgo


@registrar
class RayasDeDialogo:
    id = "TIP-007"
    nivel = Nivel.L1
    descripcion = "Normaliza guiones y en dashes usados como raya de diálogo."
    prioridad = 50
    por_defecto = True

    _inicio_en_dash = re.compile(r"(?m)^(?P<indent>[ \t]*)–[ \t]*(?=\S)")
    _inicio_doble_guion = re.compile(r"(?m)^(?P<indent>[ \t]*)--[ \t]*(?!-)(?=\S)")
    _inciso_en_dash = re.compile(r"(?<=\S)[ \t]–[ \t]*(?=\S)")
    _inciso_doble_guion = re.compile(r"(?<=\s)--(?=\s)")

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        if not bool(ctx.config.obtener("tipografia.rayas", True)):
            return
        for patron, constructor in (
            (self._inicio_en_dash, lambda m: f"{m.group('indent')}—"),
            (self._inicio_doble_guion, lambda m: f"{m.group('indent')}—"),
            (self._inciso_en_dash, lambda m: " —"),
            (self._inciso_doble_guion, lambda m: "—"),
        ):
            for match in patron.finditer(texto):
                hallazgo = crear_hallazgo(
                    texto,
                    regla=self.id,
                    nivel=self.nivel,
                    inicio=match.start(),
                    fin=match.end(),
                    sugerencia=constructor(match),
                    confianza=0.95,
                    nota="Raya de diálogo normalizada.",
                )
                if hallazgo:
                    yield hallazgo


@registrar
class Tabulaciones:
    id = "TIP-008"
    nivel = Nivel.L1
    descripcion = "Sustituye tabulaciones entre palabras por un espacio."
    prioridad = 61
    por_defecto = True

    _patron = re.compile(r"(?<=[^\s.,;:!?…])\t+(?=[^\s.,;:!?…])")

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        for match in self._patron.finditer(texto):
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=" ",
                confianza=0.98,
                nota="Tabulación entre palabras.",
            )
            if hallazgo:
                yield hallazgo


@registrar
class PuntuacionDuplicada:
    id = "TIP-009"
    nivel = Nivel.L1
    descripcion = "Colapsa comas, puntos y coma o dos puntos repetidos."
    prioridad = 5
    por_defecto = True

    _patron = re.compile(r"[ \t]*(?P<punct>[,;:])(?P=punct)+")

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        for match in self._patron.finditer(texto):
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=match.group("punct"),
                confianza=0.96,
                nota="Signo de puntuación duplicado.",
            )
            if hallazgo:
                yield hallazgo


@registrar
class ComillasDesbalanceadas:
    id = "TIP-010"
    nivel = Nivel.L3
    descripcion = "Señala líneas con un número impar de comillas rectas."
    prioridad = 1000
    por_defecto = False

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        posicion = 0
        for linea in texto.splitlines(keepends=True):
            if linea.count('"') % 2 == 1:
                contenido = linea.rstrip("\n")
                hallazgo = crear_hallazgo(
                    texto,
                    regla=self.id,
                    nivel=self.nivel,
                    inicio=posicion,
                    fin=posicion + max(1, len(contenido)),
                    sugerencia=None,
                    confianza=0.45,
                    nota="Número impar de comillas rectas en la línea.",
                )
                if hallazgo:
                    yield hallazgo
            posicion += len(linea)
