"""Selección y aplicación de parches con verificación de posición."""

from __future__ import annotations

import difflib
from collections.abc import Iterable

from onirifix.modelo import Hallazgo, Nivel, Parche


def seleccionar_parches(
    hallazgos: Iterable[Hallazgo],
    *,
    niveles: set[Nivel] | None = None,
    aplicar_l2: bool = False,
    umbral_l2: float = 0.90,
) -> list[Parche]:
    """Convierte hallazgos aplicables en parches, respetando los tres niveles."""

    seleccionados: list[Parche] = []
    niveles = niveles or {Nivel.L1, Nivel.L2}
    for hallazgo in hallazgos:
        if hallazgo.sugerencia is None:
            continue
        if hallazgo.nivel not in niveles:
            continue
        if hallazgo.nivel == Nivel.L1:
            pass
        elif hallazgo.nivel == Nivel.L2:
            if not aplicar_l2 or hallazgo.confianza < umbral_l2:
                continue
        else:
            continue
        parche = Parche.desde_hallazgo(hallazgo)
        if parche is not None:
            seleccionados.append(parche)
    return sorted(seleccionados, key=lambda p: (p.inicio, p.fin))


def aplicar_parches(
    texto: str, parches: Iterable[Parche]
) -> tuple[str, list[Parche], list[tuple[Parche, str]]]:
    """Aplica parches de izquierda a derecha sobre offsets del texto original.

    Devuelve el texto nuevo, los parches aplicados y los omitidos con el motivo.
    Un parche se omite si su ``original`` ya no coincide en la posición esperada
    o si se solapa con otro ya aplicado.
    """

    ordenados = sorted(parches, key=lambda p: (p.inicio, p.fin))
    piezas: list[str] = []
    aplicados: list[Parche] = []
    omitidos: list[tuple[Parche, str]] = []
    cursor = 0

    for parche in ordenados:
        if parche.inicio < cursor:
            omitidos.append((parche, "Se solapa con un parche anterior."))
            continue
        if parche.inicio < 0 or parche.fin > len(texto):
            omitidos.append((parche, "Span fuera del texto."))
            continue
        actual = texto[parche.inicio : parche.fin]
        if actual != parche.original:
            omitidos.append(
                (
                    parche,
                    f"El texto cambió: se esperaba {parche.original!r} y hay {actual!r}.",
                )
            )
            continue
        piezas.append(texto[cursor : parche.inicio])
        piezas.append(parche.reemplazo)
        cursor = parche.fin
        aplicados.append(parche)

    piezas.append(texto[cursor:])
    return "".join(piezas), aplicados, omitidos


def crear_diff(original: str, corregido: str, nombre: str = "manuscrito") -> str:
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            corregido.splitlines(keepends=True),
            fromfile=f"{nombre}.original",
            tofile=f"{nombre}.corregido",
            lineterm="\n",
        )
    )
