"""Tildes diacríticas, interrogativas indirectas y subjuntivos (L2).

Cubre la «Pasada 2 — Gramática fina» del informe editorial con patrones
cerrados: «Se lo que…» → «Sé lo que…», «Si, eso…» → «Sí, eso…», «el ya
intuía» → «él ya intuía», «sabes que hacer» → «sabes qué hacer» y el futuro
usado en lugar del subjuntivo tras «como si», «antes de que»…
"""

from __future__ import annotations

from collections.abc import Iterator

try:  # pragma: no cover
    import regex as re
except ImportError:  # pragma: no cover
    import re  # type: ignore[no-redef]

from onirifix.modelo import Contexto, Hallazgo, Nivel, crear_hallazgo
from onirifix.nucleo.registro_reglas import registrar
from onirifix.reglas._comun import es_palabra_glosario, preservar_caso

_INICIO = r"(?:(?<=^)|(?<=[\n—¿¡«\"“])|(?<=[.!?…][ \t]))"

_FORMAS_SABER = (
    "sé|sabes|sabe|sabemos|sabéis|saben|sabía|sabías|sabíamos|sabían|supe|supo|"
    "supieron|saber|sabiendo|preguntó|preguntaba|preguntaron|pregunto|preguntarse|"
    "preguntándose|decidir|imaginaba|imagino|entendía|entiendo|explicó|recordaba|recuerdo"
)
_INTERROGATIVOS = {
    "que": "qué",
    "como": "cómo",
    "donde": "dónde",
    "cuando": "cuándo",
    "cuanto": "cuánto",
    "cuanta": "cuánta",
    "cuantos": "cuántos",
    "cuantas": "cuántas",
    "quien": "quién",
    "quienes": "quiénes",
    "cual": "cuál",
}


@registrar
class TildesDiacriticas:
    id = "TIL-005"
    nivel = Nivel.L2
    descripcion = "Tildes diacríticas e interrogativas indirectas (Sé, Sí, él, qué hacer)."
    prioridad = 37
    por_defecto = True

    _se_saber = re.compile(
        _INICIO + r"(?P<palabra>Se)(?=[ \t]+(?:lo[ \t]+que|que|qu[eé][ \t]|c[oó]mo|d[oó]nde|"
        r"cu[aá]ndo|qui[eé]n|cu[aá]nto|perfectamente|bien)\b)",
        re.UNICODE,
    )
    _no_se = re.compile(
        r"\b(?P<antes>[Nn]o|[Yy]o|[Yy]a|[Tt]ampoco|[Ll]o)[ \t]+(?P<palabra>se)"
        r"(?=[ \t]+(?:que|qu[eé][ \t]|c[oó]mo|d[oó]nde|cu[aá]ndo|qui[eé]n|cu[aá]nto|"
        r"nada|mucho|bien)\b|[.!?…,])",
        re.UNICODE,
    )
    _si_afirmativo = re.compile(_INICIO + r"(?P<palabra>[Ss]i)(?=[ \t]*[,.!…]|[ \t]+—)", re.UNICODE)
    _el_pronombre = re.compile(
        r"(?<![^\W\d_])(?P<palabra>[Ee]l)(?=[ \t]+(?:ya|también|tampoco|nunca|siempre|no|"
        r"solo|sí|mismo[ \t]+se)\b|[ \t]*[,.;:!?…](?![\w])|[ \t]+(?:para|y|con|sin|por)[ \t]+"
        r"(?:[a-záéíóúñ]+(?:ar|er|ir|ír)(?:lo|la|le|los|las|les|se)?|que)\b)",
        re.UNICODE,
    )
    _que_infinitivo = re.compile(
        r"\b(?:" + _FORMAS_SABER + r")[ \t]+(?P<palabra>que|donde|como|cuando|quien|cual)"
        r"[ \t]+(?P<siguiente>[a-záéíóúñ]+(?:ar|er|ir|ír)(?:lo|la|le|los|las|les|se|me|te|nos)?)\b",
        re.IGNORECASE | re.UNICODE,
    )
    _indirecta = re.compile(
        r"\b(?:no[ \t]+sé|no[ \t]+sabía|no[ \t]+sabe|no[ \t]+saben|no[ \t]+sabes|"
        r"se[ \t]+preguntó|se[ \t]+preguntaba|preguntó|preguntaba|sin[ \t]+saber)[ \t]+"
        r"(?P<palabra>cuanto|cuanta|cuantos|cuantas|donde|como|cuando|quien|quienes|cual)\b",
        re.IGNORECASE | re.UNICODE,
    )

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        if not bool(ctx.config.obtener("tildes.diacriticas", True)):
            return
        casos: list[tuple[int, int, str, float, str]] = []
        for match in self._se_saber.finditer(texto):
            casos.append(
                (match.start("palabra"), match.end("palabra"), "Sé", 0.88,
                 "«Sé» del verbo saber lleva tilde diacrítica.")
            )
        for match in self._no_se.finditer(texto):
            casos.append(
                (match.start("palabra"), match.end("palabra"), "sé", 0.86,
                 f"Tras «{match.group('antes')}» es el verbo saber: «sé».")
            )
        for match in self._si_afirmativo.finditer(texto):
            casos.append(
                (match.start("palabra"), match.end("palabra"),
                 preservar_caso(match.group("palabra"), "sí"), 0.8,
                 "«Sí» afirmativo lleva tilde. Revisa si es un «si» condicional con inciso.")
            )
        for match in self._el_pronombre.finditer(texto):
            casos.append(
                (match.start("palabra"), match.end("palabra"),
                 preservar_caso(match.group("palabra"), "él"), 0.82,
                 "El artículo no puede ir solo aquí: es el pronombre «él».")
            )
        for match in self._que_infinitivo.finditer(texto):
            palabra = match.group("palabra")
            casos.append(
                (match.start("palabra"), match.end("palabra"),
                 preservar_caso(palabra, _INTERROGATIVOS[palabra.casefold()]), 0.86,
                 "Interrogativa indirecta ante infinitivo: lleva tilde.")
            )
        for match in self._indirecta.finditer(texto):
            palabra = match.group("palabra")
            casos.append(
                (match.start("palabra"), match.end("palabra"),
                 preservar_caso(palabra, _INTERROGATIVOS[palabra.casefold()]), 0.8,
                 "Interrogativa indirecta: el interrogativo lleva tilde.")
            )

        vistos: set[int] = set()
        for inicio, fin, sugerencia, confianza, nota in sorted(casos):
            if inicio in vistos:
                continue
            vistos.add(inicio)
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=inicio,
                fin=fin,
                sugerencia=sugerencia,
                confianza=confianza,
                nota=nota,
            )
            if hallazgo:
                yield hallazgo


# ---------------------------------------------------------------------------
# TIL-006 · futuro en lugar de subjuntivo
# ---------------------------------------------------------------------------

_DISPARADORES = (
    r"como[ \t]+si|antes[ \t]+de[ \t]+que|sin[ \t]+que|para[ \t]+que|a[ \t]+fin[ \t]+de[ \t]+que|"
    r"hasta[ \t]+que|dejó[ \t]+que|dejaba[ \t]+que|pidió[ \t]+que|pedía[ \t]+que|"
    r"quería[ \t]+que|esperaba[ \t]+que|ordenó[ \t]+que|permitió[ \t]+que|evitar[ \t]+que|"
    r"evitó[ \t]+que|deseaba[ \t]+que|rogó[ \t]+que|exigió[ \t]+que|ojalá"
)
_PUENTE = r"(?:(?:no|se|le|lo|la|les|los|las|me|te|nos|[A-ZÁÉÍÓÚÑ][\w'’]+)[ \t]+){0,2}"

_IRREGULARES_SUBJUNTIVO = {
    "hará": "hiciera",
    "harán": "hicieran",
    "será": "fuera",
    "serán": "fueran",
    "estará": "estuviera",
    "estarán": "estuvieran",
    "dará": "diera",
    "darán": "dieran",
    "verá": "viera",
    "verán": "vieran",
    "tendrá": "tuviera",
    "tendrán": "tuvieran",
    "podrá": "pudiera",
    "podrán": "pudieran",
    "sabrá": "supiera",
    "sabrán": "supieran",
    "querrá": "quisiera",
    "querrán": "quisieran",
    "pondrá": "pusiera",
    "pondrán": "pusieran",
    "saldrá": "saliera",
    "saldrán": "salieran",
    "vendrá": "viniera",
    "vendrán": "vinieran",
    "dirá": "dijera",
    "dirán": "dijeran",
    "habrá": "hubiera",
    "habrán": "hubieran",
    "irá": "fuera",
    "irán": "fueran",
    "cabrá": "cupiera",
    "valdrá": "valiera",
    "traerá": "trajera",
    "traerán": "trajeran",
    "leerá": "leyera",
    "creerá": "creyera",
    "caerá": "cayera",
    "oirá": "oyera",
    "sentirá": "sintiera",
    "pedirá": "pidiera",
    "seguirá": "siguiera",
    "servirá": "sirviera",
    "repetirá": "repitiera",
    "mentirá": "mintiera",
    "preferirá": "prefiriera",
    "sugerirá": "sugiriera",
    "vestirá": "vistiera",
    "elegirá": "eligiera",
    "corregirá": "corrigiera",
    "morirá": "muriera",
    "dormirá": "durmiera",
    "reirá": "riera",
    "sonreirá": "sonriera",
    "construirá": "construyera",
    "huirá": "huyera",
    "destruirá": "destruyera",
    "conducirá": "condujera",
    "producirá": "produjera",
}


def subjuntivo_desde_futuro(palabra: str) -> str | None:
    """«esperará» → «esperara», «temerá» → «temiera». ``None`` si no aplica."""

    minuscula = palabra.casefold()
    if minuscula in _IRREGULARES_SUBJUNTIVO:
        return _IRREGULARES_SUBJUNTIVO[minuscula]
    for futuro, subjuntivo in (("arán", "aran"), ("erán", "ieran"), ("irán", "ieran"),
                               ("ará", "ara"), ("erá", "iera"), ("irá", "iera")):
        if minuscula.endswith(futuro) and len(minuscula) > len(futuro) + 1:
            raiz = minuscula[: -len(futuro)]
            # «-drá», «-rrá» y similares son futuros irregulares no listados.
            if raiz.endswith(("d", "rr", "br")):
                return None
            return raiz + subjuntivo
    return None


@registrar
class FuturoPorSubjuntivo:
    id = "TIL-006"
    nivel = Nivel.L2
    descripcion = "Futuro usado en lugar de subjuntivo («como si esperará» → «como si esperara»)."
    prioridad = 36
    por_defecto = True

    _patron = re.compile(
        r"\b(?P<disparador>" + _DISPARADORES + r")[ \t]+" + _PUENTE
        + r"(?P<palabra>[^\W\d_]+(?:rá|rán))\b",
        re.IGNORECASE | re.UNICODE,
    )

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        if not bool(ctx.config.obtener("tildes.subjuntivos", True)):
            return
        for match in self._patron.finditer(texto):
            palabra = match.group("palabra")
            if es_palabra_glosario(palabra, ctx.glosario):
                continue
            subjuntivo = subjuntivo_desde_futuro(palabra)
            if subjuntivo is None:
                continue
            disparador = " ".join(match.group("disparador").split()).casefold()
            confianza = 0.9 if disparador == "como si" else 0.84
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start("palabra"),
                fin=match.end("palabra"),
                sugerencia=preservar_caso(palabra, subjuntivo),
                confianza=confianza,
                nota=(
                    f"Tras «{disparador}» va subjuntivo, no futuro. Se propone el "
                    "imperfecto (narración en pasado); en presente sería el subjuntivo presente."
                ),
            )
            if hallazgo:
                yield hallazgo
