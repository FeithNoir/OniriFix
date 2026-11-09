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
    """DIA-001: «—Basta. —Dijo» → «—Basta. —dijo» (o «—Basta —dijo» en modo RAE estricto)."""

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
        estricto = bool(ctx.config.obtener("dialogos.rae_estricto", False))
        for match in self._patron.finditer(texto):
            if not _es_verbo(match.group("verbo"), verbos):
                continue
            # En modo RAE estricto el punto no se escribe antes del inciso
            # (—Basta —dijo); «!», «?» y «…» se conservan siempre.
            cierre = match.group("cierre")
            if cierre == "." and estricto:
                cierre = ""
            sugerencia = f"{cierre} —{minuscula_inicial(match.group('verbo'))}"
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=sugerencia,
                confianza=0.97,
                nota="Verbo de habla del inciso: va en minúscula.",
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
    por_defecto = False

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
            # Solo el punto desaparece: «—¿Vienes? —preguntó» y «—Eso… —dijo»
            # conservan su signo. Un punto que cierra «...» tampoco se toca.
            cierre = match.group("cierre")
            if cierre == "." and not texto.endswith(".", 0, match.start()):
                cierre = ""
            sugerencia = f"{cierre} —{minuscula_inicial(match.group('verbo'))}"
            if sugerencia == match.group(0):
                continue
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


def _rayas_previas_en_linea(texto: str, posicion: int) -> int:
    inicio_linea = texto.rfind("\n", 0, posicion) + 1
    return texto.count("—", inicio_linea, posicion)


def _es_linea_de_dialogo(texto: str, posicion: int) -> bool:
    inicio_linea = texto.rfind("\n", 0, posicion) + 1
    return texto[inicio_linea:posicion].lstrip(" \t").startswith("—")


_VERBOS_TAMBIEN_NARRATIVOS = {
    "soltó", "apuntó", "concluyó", "continuó", "siguió", "añadió", "decía", "agregó",
    "remató", "cortó", "señaló", "sentenció", "anunció", "observó", "admitió", "aclaró",
    "intervino", "terminó", "bufó", "rió", "rio", "sonrió", "suspiró",
}


@registrar
class AtribucionSinRaya:
    """DIA-006: «—¿En qué piensas? / Preguntó Feith» → «—¿En qué piensas? —preguntó Feith»."""

    id = "DIA-006"
    nivel = Nivel.L2
    descripcion = "Une el verbo de habla suelto al parlamento con raya y minúscula."
    prioridad = 9
    por_defecto = True

    # Caso A: el verbo quedó en la línea (o párrafo) siguiente.
    _salto = re.compile(
        r"(?P<cierre>[.,!?…]?)(?P<hueco>[ \t]*\n{1,2}[ \t]*)" + _VERBO_CAPITAL
    )
    # Caso B: el verbo sigue en la misma línea, pero sin raya.
    _misma_linea = re.compile(
        r"(?P<cierre>[.,!?…])(?P<hueco>[ \t]+)" + _VERBO_CAPITAL
    )

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        verbos = verbos_habla(ctx)
        for patron, caso in ((self._salto, "salto"), (self._misma_linea, "linea")):
            for match in patron.finditer(texto):
                if not _es_verbo(match.group("verbo"), verbos):
                    continue
                # La línea donde acaba el parlamento tiene que abrir con raya.
                if not _es_linea_de_dialogo(texto, match.start()):
                    continue
                # En la misma línea, el verbo debe caer dentro del parlamento
                # (número impar de rayas antes), no tras un inciso ya cerrado.
                if caso == "linea" and _rayas_previas_en_linea(texto, match.start()) % 2 == 0:
                    continue
                # «…dijo él—. Preguntó»: el punto cierra un inciso, no un parlamento.
                if texto.endswith("—", 0, match.start()):
                    continue
                cierre = match.group("cierre")
                # Con punto o coma, el signo se cae: «—Basta —dijo».
                conservado = cierre if cierre in {"!", "?", "…"} else ""
                sugerencia = f"{conservado} —{minuscula_inicial(match.group('verbo'))}"
                verbo = match.group("verbo").casefold()
                if caso == "salto":
                    # Un verbo que solo puede ser de habla («Preguntó»,
                    # «Murmuró») tras un parlamento es inequívoco. Los que
                    # también narran («Soltó el aire», «Apuntó al blanco») bajan.
                    confianza = 0.75 if verbo in _VERBOS_TAMBIEN_NARRATIVOS else 0.92
                else:
                    confianza = 0.88
                # Si la línea anterior ya acaba en narración (número par de
                # rayas: «—Hola —dijo Ana, sonriendo.»), no es atribución suelta.
                if caso == "salto" and _rayas_previas_en_linea(texto, match.start()) % 2 == 0:
                    continue
                hallazgo = crear_hallazgo(
                    texto,
                    regla=self.id,
                    nivel=self.nivel,
                    inicio=match.start(),
                    fin=match.end(),
                    sugerencia=sugerencia,
                    confianza=confianza,
                    nota=(
                        "El verbo de habla va unido al parlamento con raya y en minúscula; "
                        "si había punto, desaparece (—Basta —dijo)."
                    ),
                )
                if hallazgo:
                    yield hallazgo


@registrar
class IncisoSinCerrar:
    """DIA-007: «—Hola —dijo Mico. ¿Vienes?» → «—Hola —dijo Mico—. ¿Vienes?»."""

    id = "DIA-007"
    nivel = Nivel.L2
    descripcion = "Cierra con raya el inciso del narrador cuando el parlamento continúa."
    prioridad = 11
    por_defecto = True

    _patron = re.compile(
        r"(?<=\S)[ \t]—" + _VERBO_ATRIBUCION + r"(?P<resto>[^—\n.;:!?…]*?)"
        r"(?P<signo>[.,])(?P<espacio>[ \t]+)(?=[¿¡])"
    )

    # «—Por aquí —respondió Bruno, señalando el muelle. —Sale al alba»: el
    # parlamento sigue con una raya nueva en vez de cerrar el inciso.
    _reanudacion = re.compile(
        r"(?P<signo>[.])[ \t]+—(?=[¿¡«\"“]?[A-ZÁÉÍÓÚÑ])", re.UNICODE
    )

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        verbos = verbos_habla(ctx)
        for match in self._patron.finditer(texto):
            if not _es_verbo(match.group("verbo"), verbos):
                continue
            if not _es_linea_de_dialogo(texto, match.start()):
                continue
            # La raya del inciso debe ser la segunda de su tramo (abre el inciso).
            if _rayas_previas_en_linea(texto, match.start()) % 2 == 0:
                continue
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start("signo"),
                fin=match.end("signo"),
                sugerencia=f"—{match.group('signo')}",
                confianza=0.84,
                nota="El parlamento continúa tras el inciso: la raya de cierre va antes del signo.",
            )
            if hallazgo:
                yield hallazgo
        for match in self._reanudacion.finditer(texto):
            if not _es_linea_de_dialogo(texto, match.start()):
                continue
            rayas = _rayas_previas_en_linea(texto, match.start())
            if rayas < 2 or rayas % 2 == 1:
                continue
            # El tramo de narración tiene que abrir con un verbo de habla.
            ultima_raya = texto.rfind("—", 0, match.start())
            inciso = _PALABRA_INICIAL.match(texto, ultima_raya + 1)
            if inciso is None or not _es_verbo(inciso.group(1), verbos):
                continue
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia="—. ",
                confianza=0.88,
                nota=(
                    "El parlamento continúa tras el inciso: se cierra el inciso con raya "
                    "y punto, sin abrir una raya nueva (—dijo Ana—. Seguimos)."
                ),
            )
            if hallazgo:
                yield hallazgo


_PALABRA_INICIAL = re.compile(r"([^\W\d_]+)", re.UNICODE)
