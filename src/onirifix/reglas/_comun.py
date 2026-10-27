"""Piezas compartidas por las reglas lingüísticas."""

from __future__ import annotations

import importlib
from collections.abc import Iterable
from types import ModuleType

try:  # pragma: no cover - depende del entorno
    re: ModuleType = importlib.import_module("regex")
except ImportError:  # pragma: no cover
    re = importlib.import_module("re")

from onirifix.modelo import Contexto, Glosario
from onirifix.util import clave, contar_palabras, unir_or

VERBOS_HABLA_DEFECTO: frozenset[str] = frozenset(
    ["dijo", "decía", "preguntó", "preguntaba", "respondió", "respondía", "susurró", "susurraba", "murmuró", "murmuraba", "gruñó", "gruñía", "bramó", "bramaba", "exclamó", "exclamaba", "añadió", "añadía", "observó", "observaba", "soltó", "soltaba", "espetó", "espetaba", "replicó", "replicaba", "insistió", "insistía", "concluyó", "concluía", "vociferó", "vociferaba", "gritó", "gritaba", "contestó", "contestaba", "comentó", "comentaba", "declaró", "declaraba", "explicó", "explicaba", "apuntó", "apuntaba", "repuso", "reponía", "inquirió", "inquiría", "terció", "terciaba", "musitó", "musitaba", "balbuceó", "balbuceaba", "tartamudeó", "tartamudeaba"]
)

# Palabras que, tras una atribución, suelen indicar que el mismo hablante
# continúa (o que la frase es una reanudación, no una nueva intervención).
PALABRAS_REANUDACION: frozenset[str] = frozenset(
    ["el", "la", "los", "las", "lo", "un", "una", "unos", "unas", "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas", "aquel", "aquella", "aquellos", "aquellas", "mi", "mis", "tu", "tus", "su", "sus", "nuestro", "nuestra", "nuestros", "nuestras", "pero", "y", "o", "ni", "que", "porque", "aunque", "cuando", "mientras", "no", "sí", "si", "ya", "aún", "aun", "también", "solo", "sólo", "claro", "bueno", "me", "te", "se", "nos", "le", "les", "lo", "los", "la", "las", "esto", "eso", "aquello", "nada", "algo", "nadie", "alguien", "todo", "todos", "toda", "todas", "vamos", "ven", "espera", "mira", "oye", "escucha", "dime", "donde", "como", "quien", "cual", "cuanto", "tanto", "tan", "muy", "más", "menos"]
)

TERMINALES_ORACION = ".!?…"


def verbos_habla(ctx: Contexto) -> frozenset[str]:
    extra = ctx.config.obtener("dialogos.verbos_extra", []) or []
    return frozenset(
        {v.casefold() for v in (*VERBOS_HABLA_DEFECTO, *ctx.glosario.verbos_habla, *extra)}
    )


def es_verbo_habla(palabra: str, verbos: Iterable[str]) -> bool:
    return palabra.casefold() in {v.casefold() for v in verbos}


def oracion_alrededor(
    texto: str, inicio: int, fin: int, *, maximo: int = 400
) -> tuple[str, int, int]:
    """Devuelve la oración que contiene ``[inicio:fin]`` y sus offsets."""

    inicio_oracion = 0
    for terminal in TERMINALES_ORACION + "\n":
        posicion = texto.rfind(terminal, 0, inicio)
        if posicion > inicio_oracion:
            inicio_oracion = posicion + 1
    # No arrastrar espacios ni una raya de diálogo inicial.
    while inicio_oracion < inicio and texto[inicio_oracion] in " \t—":
        inicio_oracion += 1

    fin_oracion = len(texto)
    for terminal in TERMINALES_ORACION + "\n":
        posicion = texto.find(terminal, fin)
        if posicion != -1:
            fin_oracion = min(fin_oracion, posicion + 1)

    if fin_oracion - inicio_oracion > maximo:
        inicio_oracion = max(inicio_oracion, inicio - maximo // 2)
        fin_oracion = min(fin_oracion, inicio + maximo // 2)
    return texto[inicio_oracion:fin_oracion], inicio_oracion, fin_oracion


def palabra_glosario(palabra: str, glosario: Glosario) -> bool:
    return clave(palabra) in {
        clave(p)
        for p in (
            *glosario.nombres,
            *glosario.alias,
            *glosario.toponimos,
            *glosario.terminos,
            *glosario.variantes,
        )
    }


def es_palabra_glosario(palabra: str, glosario: Glosario) -> bool:
    return clave(palabra) in {
        clave(p)
        for p in glosario.nombres
        | glosario.alias
        | glosario.toponimos
        | glosario.terminos
        | frozenset(glosario.variantes)
    }


def preservar_caso(original: str, reemplazo: str) -> str:
    if original.isupper():
        return reemplazo.upper()
    if original[:1].isupper():
        return reemplazo[:1].upper() + reemplazo[1:]
    return reemplazo


def minuscula_inicial(texto: str) -> str:
    if not texto:
        return texto
    return texto[0].lower() + texto[1:]


def patron_de(palabras: Iterable[str]) -> str:
    return unir_or(re.escape(p) for p in palabras)


def dividir_oraciones(texto: str) -> list[tuple[str, int, int]]:
    resultado: list[tuple[str, int, int]] = []
    patron = re.compile(r"[^.!?…\n]+(?:[.!?…]+|$)", re.MULTILINE)
    for match in patron.finditer(texto):
        contenido = match.group(0)
        if contenido.strip():
            inicio = match.start() + len(contenido) - len(contenido.lstrip())
            fin = match.end() - (len(contenido) - len(contenido.rstrip()))
            resultado.append((texto[inicio:fin], inicio, fin))
    return resultado


def contar_palabras_texto(texto: str) -> int:
    return contar_palabras(texto)
