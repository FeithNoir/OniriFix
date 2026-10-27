"""Tildes contextuales y futuros truncados (L2)."""

from __future__ import annotations

from collections.abc import Iterator

try:  # pragma: no cover
    import regex as re
except ImportError:  # pragma: no cover
    import re  # type: ignore[no-redef]

from onirifix.modelo import Contexto, Hallazgo, Nivel, crear_hallazgo
from onirifix.nucleo.registro_reglas import registrar
from onirifix.reglas._comun import oracion_alrededor, preservar_caso
from onirifix.util import clave

# ---------------------------------------------------------------------------
# TIL-001 · hacia / hacía
# ---------------------------------------------------------------------------

_DETERMINANTES = {
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    "del",
    "al",
    "su",
    "sus",
    "mi",
    "mis",
    "tu",
    "tus",
    "nuestro",
    "nuestra",
    "nuestros",
    "nuestras",
    "este",
    "esta",
    "estos",
    "estas",
    "ese",
    "esa",
    "esos",
    "esas",
    "aquel",
    "aquella",
    "aquellos",
    "aquellas",
    "donde",
    "arriba",
    "abajo",
    "dentro",
    "fuera",
    "allí",
    "allá",
    "aquí",
    "acá",
    "el norte",
    "el sur",
    "el este",
    "el oeste",
}

_SUSTANTIVOS_DE_HACER = {
    "frío",
    "calor",
    "tiempo",
    "años",
    "días",
    "meses",
    "semanas",
    "horas",
    "mucho",
    "poco",
    "tarde",
    "noche",
    "sol",
    "viento",
    "falta",
    "daño",
    "gracia",
    "ilusión",
    "miedo",
    "rabia",
    "pena",
    "sueño",
}

_PRONOMBRES_DE_HACER = {
    "se",
    "me",
    "te",
    "le",
    "nos",
    "os",
    "les",
    "ya",
    "no",
    "lo",
    "la",
    "los",
    "las",
}

_VERBOS_DE_MOVIMIENTO = {
    "iba",
    "iban",
    "fue",
    "fueron",
    "caminaba",
    "caminaban",
    "corría",
    "corrían",
    "volvió",
    "volvieron",
    "miró",
    "miraron",
    "se dirigió",
    "se dirigieron",
    "llegó",
    "llegaron",
    "salió",
    "salieron",
    "entró",
    "entraron",
    "avanzó",
    "avanzaron",
}


def _palabra_antes(texto: str, posicion: int) -> str:
    coincidencia = re.search(r"([^\W\d_]+)\s*$", texto[:posicion], re.UNICODE)
    return coincidencia.group(1).casefold() if coincidencia else ""


def _palabra_despues(texto: str, posicion: int) -> str:
    coincidencia = re.match(r"\s*([^\W\d_]+)", texto[posicion:], re.UNICODE)
    return coincidencia.group(1).casefold() if coincidencia else ""


@registrar
class HaciaHacia:
    id = "TIL-001"
    nivel = Nivel.L2
    descripcion = "Distingue la preposición «hacia» del imperfecto «hacía»."
    prioridad = 40
    por_defecto = True

    _patron = re.compile(
        r"\bhacia\b", flags=re.IGNORECASE | re.UNICODE
    )

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        if not bool(ctx.config.obtener("tildes.hacia", True)):
            return
        for match in self._patron.finditer(texto):
            oracion, _, _ = oracion_alrededor(texto, match.start(), match.end())
            anterior = _palabra_antes(texto, match.start())
            siguiente = _palabra_despues(texto, match.end())

            confianza = 0.0
            motivo = ""
            if ctx.analizador is not None and ctx.analizador.disponible:
                pos = ctx.analizador.pos_de("hacia", oracion)
                if pos in {"VERB", "AUX"}:
                    confianza = 0.96
                    motivo = "El etiquetador lo analiza como verbo."
                elif pos in {"ADP", "ADV"}:
                    continue

            if confianza == 0.0:
                if siguiente in _SUSTANTIVOS_DE_HACER:
                    confianza = 0.84
                    motivo = "Contexto de imperfecto: hacía frío/tiempo/años…"
                elif anterior in _PRONOMBRES_DE_HACER:
                    confianza = 0.8
                    motivo = "Pronombre átono o negación ante el verbo hacer."
                elif anterior in _VERBOS_DE_MOVIMIENTO or siguiente in _DETERMINANTES:
                    continue

            if confianza == 0.0:
                continue

            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=preservar_caso(match.group(0), "hacía"),
                confianza=confianza,
                nota=motivo,
            )
            if hallazgo:
                yield hallazgo


# ---------------------------------------------------------------------------
# TIL-002 · futuros truncados
# ---------------------------------------------------------------------------

_VERBOS_BASE = ["mirar", "susurrar", "hablar", "caminar", "correr", "amar", "temer", "partir", "saltar", "gritar", "llorar", "reír", "sonreír", "escribir", "leer", "abrir", "cerrar", "pensar", "sentir", "dormir", "pedir", "seguir", "servir", "venir", "tener", "poner", "salir", "valer", "hacer", "decir", "querer", "poder", "saber", "ver", "dar", "estar", "ser", "ir", "oír", "traer", "caer", "romper", "volver", "resolver", "mover", "contar", "encontrar", "recordar", "mostrar", "probar", "costar", "jugar", "llegar", "pasar", "dejar", "llevar", "tomar"]

_RAICES_IRREGULARES = {
    "tener": "tendr",
    "poner": "pondr",
    "salir": "saldr",
    "valer": "valdr",
    "venir": "vendr",
    "hacer": "har",
    "decir": "dir",
    "querer": "querr",
    "poder": "podr",
    "saber": "sabr",
    "ver": "ver",
    "dar": "dar",
    "estar": "estar",
    "ser": "ser",
    "ir": "ir",
    "haber": "habr",
    "caber": "cabr",
    "oír": "oir",
    "traer": "traer",
    "caer": "caer",
    "roer": "roer",
}

_SUFIJOS_FUTURO = ("é", "ás", "á", "emos", "éis", "án")


def _construir_futuros() -> frozenset[str]:
    formas: set[str] = set()
    for verbo in _VERBOS_BASE:
        raiz = _RAICES_IRREGULARES.get(verbo, verbo)
        for sufijo in _SUFIJOS_FUTURO:
            formas.add(raiz + sufijo)
    return frozenset(formas)


_FORMAS_FUTURO = _construir_futuros()

# Orden de preferencia: 3.ª persona del singular primero, que es el caso más
# habitual en narrativa.
_SUFIJOS_CANDIDATOS = ("ará", "erá", "irá", "arás", "erás", "irás", "aráis", "eréis", "iréis")

_PALABRAS_VALIDAS = {
    # Se comparan sin acentos (``clave``), así que se guardan normalizadas.
    "esta",
    "aca",
    "alla",
    "quiza",
    "quizas",
    "mama",
    "papa",
    "sofa",
    "ca",
    "raja",
}

_VOSEO = {
    "mirá",
    "susurrá",
    "hablá",
    "decí",
    "vení",
    "tené",
    "poné",
    "salí",
    "hacé",
    "andá",
    "escuchá",
    "esperá",
    "callá",
    "tomá",
    "dejá",
    "cantá",
    "contá",
    "buscá",
}


@registrar
class FuturosTruncados:
    id = "TIL-002"
    nivel = Nivel.L2
    descripcion = "Detecta futuros a los que les falta una sílaba («mirá» → «mirará»)."
    prioridad = 41
    por_defecto = True

    _patron = re.compile(r"\b(?P<palabra>[^\W\d_]{2,}á)\b", re.UNICODE)

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        if not bool(ctx.config.obtener("tildes.futuros_truncados", True)):
            return
        permitir_voseo = bool(ctx.config.obtener("tildes.permitir_voseo", False))
        validas_extra = {
            clave(str(p)) for p in (ctx.config.obtener("tildes.palabras_validas_extra", []) or [])
        }
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
            palabra = match.group("palabra")
            normalizada = clave(palabra)
            if normalizada in _PALABRAS_VALIDAS or normalizada in validas_extra:
                continue
            if normalizada in claves_glosario:
                continue
            if permitir_voseo and palabra.casefold() in _VOSEO:
                continue

            base = palabra[:-1]
            candidatos = [base + sufijo for sufijo in _SUFIJOS_CANDIDATOS]
            encontrados = [c for c in candidatos if c.casefold() in _FORMAS_FUTURO]
            if not encontrados:
                continue

            candidato = encontrados[0]
            confianza = 0.82 if len(encontrados) == 1 else 0.74
            nota = "Futuro truncado probable."
            if len(encontrados) > 1:
                nota += " Alternativas: " + ", ".join(encontrados[:3]) + "."

            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=preservar_caso(palabra, candidato),
                confianza=confianza,
                nota=nota,
            )
            if hallazgo:
                yield hallazgo
