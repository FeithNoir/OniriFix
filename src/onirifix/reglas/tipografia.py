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
    descripcion = "Normaliza guiones (simple, doble o en dash) usados como raya de diálogo."
    prioridad = 50
    por_defecto = True

    _inicio_en_dash = re.compile(r"(?m)^(?P<indent>[ \t]*)–[ \t]*(?=\S)")
    _inicio_doble_guion = re.compile(r"(?m)^(?P<indent>[ \t]*)--[ \t]*(?!-)(?=\S)")
    _inciso_en_dash = re.compile(r"(?<=\S)[ \t]–[ \t]*(?=\S)")
    _inciso_doble_guion = re.compile(r"(?<=\s)--(?=\s)")
    # «-Serán cinco puntos»: guion simple pegado al parlamento. Con espacio
    # detrás («- item») es una lista Markdown y no se toca.
    _inicio_guion_simple = re.compile(
        r"(?m)^(?P<indent>[ \t]*)-(?=[¿¡A-ZÁÉÍÓÚÜÑa-záéíóúüñ])"
    )

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        if not bool(ctx.config.obtener("tipografia.rayas", True)):
            return
        for patron, constructor in (
            (self._inicio_en_dash, lambda m: f"{m.group('indent')}—"),
            (self._inicio_doble_guion, lambda m: f"{m.group('indent')}—"),
            (self._inciso_en_dash, lambda m: " —"),
            (self._inciso_doble_guion, lambda m: "—"),
            (self._inicio_guion_simple, lambda m: f"{m.group('indent')}—"),
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


@registrar
class ElipsisCorrupta:
    id = "TIP-011"
    nivel = Nivel.L1
    descripcion = "Limpia puntos pegados a los puntos suspensivos («.…», «….» → «…»)."
    prioridad = 9
    por_defecto = True

    _patron = re.compile(r"\.+…+\.*|…+\.+|…{2,}")

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        if not bool(ctx.config.obtener("tipografia.puntos_suspensivos", True)):
            return
        for match in self._patron.finditer(texto):
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia="…",
                confianza=0.96,
                nota="Tras los puntos suspensivos no se añade punto (ni antes).",
            )
            if hallazgo:
                yield hallazgo


@registrar
class SignoDeCierreInvertido:
    id = "TIP-012"
    nivel = Nivel.L1
    descripcion = "Corrige un signo de apertura usado como cierre («¡Lo siento ¡» → «¡Lo siento!»)."
    prioridad = 8
    por_defecto = True

    _patron = re.compile(
        r"(?P<abre>[¡¿])(?P<interior>[^¡!¿?\n]{1,300}?)(?P<esp>[ \t]*)(?P<cierre>[¡¿])(?=[ \t]*(?:$|[\n»”\"—)]))",
        re.MULTILINE,
    )

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        for match in self._patron.finditer(texto):
            correcto = "!" if match.group("abre") == "¡" else "?"
            if match.group("cierre") != match.group("abre"):
                continue
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start("esp"),
                fin=match.end("cierre"),
                sugerencia=correcto,
                confianza=0.94,
                nota="El signo de cierre está invertido.",
            )
            if hallazgo:
                yield hallazgo


@registrar
class SignoDeAperturaFaltante:
    id = "TIP-013"
    nivel = Nivel.L3
    descripcion = "Avisa de preguntas o exclamaciones sin signo de apertura (¿ ¡)."
    prioridad = 94
    por_defecto = True

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        inicio_linea = 0
        for linea in texto.split("\n"):
            abiertos = {"?": 0, "!": 0}
            posicion = 0
            while posicion < len(linea):
                caracter = linea[posicion]
                if caracter == "¿":
                    abiertos["?"] += 1
                elif caracter == "¡":
                    abiertos["!"] += 1
                elif caracter in "?!":
                    fin = posicion
                    while fin < len(linea) and linea[fin] in "?!":
                        fin += 1
                    racha = linea[posicion:fin]
                    if abiertos["?"] > 0 and "?" in racha:
                        abiertos["?"] -= 1
                    elif abiertos["!"] > 0 and "!" in racha:
                        abiertos["!"] -= 1
                    else:
                        apertura = "¿" if racha[0] == "?" else "¡"
                        hallazgo = crear_hallazgo(
                            texto,
                            regla=self.id,
                            nivel=self.nivel,
                            inicio=inicio_linea + posicion,
                            fin=inicio_linea + fin,
                            sugerencia=None,
                            confianza=0.7,
                            nota=f"Falta el signo de apertura «{apertura}»: colócalo donde empieza la pregunta o exclamación.",
                        )
                        if hallazgo:
                            yield hallazgo
                    posicion = fin
                    continue
                posicion += 1
            inicio_linea += len(linea) + 1


@registrar
class ComillasInglesas:
    id = "TIP-014"
    nivel = Nivel.L2
    descripcion = "Propone unificar comillas inglesas “…” al estilo configurado («…»)."
    prioridad = 41
    por_defecto = True

    _patron = re.compile(r"“(?P<interior>[^“”\n]{1,2000})”")

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        if not bool(ctx.config.obtener("tipografia.convertir_comillas", True)):
            return
        apertura, cierre = ctx.config.comillas[0], ctx.config.comillas[1]
        if apertura == "“":
            return
        for match in self._patron.finditer(texto):
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=f"{apertura}{match.group('interior')}{cierre}",
                confianza=0.6,
                nota=(
                    "Comillas inglesas. Si el texto es un pensamiento y la obra reserva “…” "
                    "para pensamientos, rechaza el cambio."
                ),
            )
            if hallazgo:
                yield hallazgo


@registrar
class EspacioTrasApertura:
    id = "TIP-015"
    nivel = Nivel.L1
    descripcion = "Elimina el espacio tras ¿ ¡ « y antes de » («¿ Vienes ?» → «¿Vienes?»)."
    prioridad = 21
    por_defecto = True

    # Un «¡» pegado al final de una palabra no abre nada: es un cierre mal
    # escrito (lo trata TIP-012 o queda para revisión), así que no se toca.
    _patron = re.compile(r"(?<!\w)(?P<signo>[¿¡«])[ \t]+(?=\S)|(?<=\S)[ \t]+(?P<cierre>»)")

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        if not bool(ctx.config.obtener("tipografia.espacios", True)):
            return
        for match in self._patron.finditer(texto):
            sugerencia = match.group("signo") or match.group("cierre")
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=sugerencia,
                confianza=0.97,
                nota="Los signos dobles van pegados a la palabra que encierran.",
            )
            if hallazgo:
                yield hallazgo
