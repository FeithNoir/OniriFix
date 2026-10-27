"""Utilidades pequeñas y sin dependencias del dominio."""

from __future__ import annotations

import re
import sys
import unicodedata
from bisect import bisect_right
from collections.abc import Iterable, Iterator


def configurar_salida_utf8() -> None:
    """Fuerza UTF-8 cuando la salida se redirige a un archivo o a una tubería.

    En una consola interactiva no se toca nada: Windows ya escribe Unicode a
    través de la API de consola. Al redirigir, Python usa la codificación
    ANSI del sistema y símbolos como ``→`` o ``…`` provocan
    ``UnicodeEncodeError``. Con ``errors="replace"`` nunca se pierde el
    informe entero por un carácter.
    """

    for flujo in (sys.stdout, sys.stderr):
        if flujo is None or flujo.isatty():
            continue
        codificacion = (getattr(flujo, "encoding", "") or "").lower().replace("-", "")
        if codificacion == "utf8":
            continue
        reconfigurar = getattr(flujo, "reconfigure", None)
        if reconfigurar is None:
            continue
        try:
            reconfigurar(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            continue


def slugify(texto: str) -> str:
    """Convierte un título en un slug estable para la CLI y las URLs."""

    normalizado = unicodedata.normalize("NFKD", texto)
    ascii_texto = normalizado.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_texto).strip("-")
    return slug or "obra"


def sin_acentos(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normalizado if not unicodedata.combining(c))


def clave(texto: str) -> str:
    """Clave de comparación: minúsculas, sin acentos y sin espacios extra."""

    return " ".join(sin_acentos(texto).casefold().split())


def unir_alias(alias: str | Iterable[str] | None) -> str | None:
    if alias is None:
        return None
    if isinstance(alias, str):
        partes = [p.strip() for p in alias.replace(";", ",").split(",")]
    else:
        partes = [str(p).strip() for p in alias]
    limpio = [p for p in partes if p]
    return ", ".join(dict.fromkeys(limpio)) or None


def separar_alias(alias: str | None) -> list[str]:
    if not alias:
        return []
    return [p.strip() for p in alias.replace(";", ",").split(",") if p.strip()]


def truncar(texto: str, maximo: int = 160) -> str:
    limpio = " ".join(texto.split())
    if len(limpio) <= maximo:
        return limpio
    return limpio[: max(0, maximo - 1)].rstrip() + "…"


def escapar_markdown(texto: str) -> str:
    """Escapa lo mínimo para que el contexto no rompa una tabla Markdown."""

    return texto.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def contar_palabras(texto: str) -> int:
    return len(re.findall(r"[^\W\d_]+(?:['’][^\W\d_]+)?", texto, flags=re.UNICODE))


def indices_de_linea(texto: str) -> list[int]:
    """Offsets donde empieza cada línea (incluida la línea 0)."""

    return [0, *(match.end() for match in re.finditer("\n", texto))]


def linea_en(indices: list[int], offset: int) -> int:
    """Número de línea 1-based para un offset, usando índices precalculados."""

    return bisect_right(indices, offset)


def parrafos_con_offset(texto: str) -> Iterator[tuple[str, int, int]]:
    """Itera párrafos separados por una o más líneas en blanco.

    Devuelve ``(contenido, inicio, fin)`` con offsets reales sobre el texto,
    para que las reglas de duplicados puedan señalar la posición exacta.
    """

    inicio = 0
    for separador in re.finditer(r"\n[ \t]*\n", texto):
        bloque = texto[inicio : separador.start()]
        if bloque.strip():
            yield bloque, inicio, separador.start()
        inicio = separador.end()
    bloque = texto[inicio:]
    if bloque.strip():
        yield bloque, inicio, len(texto)


def normalizar_espacios(texto: str) -> str:
    return " ".join(texto.split())


def capitalizar_es(texto: str) -> str:
    if not texto:
        return texto
    return texto[0].upper() + texto[1:]


def minuscular_es(texto: str) -> str:
    if not texto:
        return texto
    return texto[0].lower() + texto[1:]


def unir_or(partes: Iterable[str]) -> str:
    """Une alternativas ya escapadas para un patrón regex."""

    return "|".join(sorted(set(partes), key=len, reverse=True))


def escapar_regex(texto: str) -> str:
    return re.escape(texto)
