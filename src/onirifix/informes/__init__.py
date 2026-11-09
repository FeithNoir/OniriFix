"""Informes de OniriFix: Markdown, CSV, JSON y diff.

Las funciones de este paquete son puras respecto al motor: reciben un
``ResultadoAnalisis`` (y opcionalmente un ``ResultadoCorreccion``) y escriben
archivos. Las comparten la CLI y la interfaz de escritorio.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from onirifix.informes.datos import escribir_csv, escribir_json
from onirifix.informes.markdown import renderizar_markdown
from onirifix.modelo import ResultadoAnalisis, ResultadoCorreccion
from onirifix.nucleo.parches import crear_diff

FORMATOS_CONOCIDOS: tuple[str, ...] = ("md", "csv", "json", "diff")
FORMATOS_DEFECTO: frozenset[str] = frozenset({"md", "csv", "json"})

NOMBRES: dict[str, str] = {
    "md": "informe.md",
    "csv": "hallazgos.csv",
    "json": "hallazgos.json",
    "diff": "parches.diff",
}


def normalizar_formatos(formatos: str | Iterable[str] | None) -> set[str]:
    """Convierte ``"md, csv;json"`` o una lista en un conjunto en minúsculas."""

    if formatos is None:
        return set(FORMATOS_DEFECTO)
    if isinstance(formatos, str):
        partes: Iterable[str] = formatos.replace(";", ",").split(",")
    else:
        partes = formatos
    return {parte.strip().lower() for parte in partes if parte and parte.strip()}


def escribir_informes(
    resultado: ResultadoAnalisis,
    salida: Path,
    *,
    formatos: str | Iterable[str] | None = None,
    correccion: ResultadoCorreccion | None = None,
    max_por_regla: int = 300,
) -> dict[str, Path]:
    """Escribe los informes pedidos y devuelve ``{formato: ruta}``.

    Los formatos desconocidos se ignoran. El diff solo se escribe si hay una
    corrección con cambios.
    """

    pedidos = [f for f in FORMATOS_CONOCIDOS if f in normalizar_formatos(formatos)]
    if not pedidos:
        return {}
    salida = Path(salida).expanduser()
    rutas: dict[str, Path] = {}

    for formato in pedidos:
        if formato == "diff" and (correccion is None or not correccion.aplicados):
            continue
        salida.mkdir(parents=True, exist_ok=True)
        ruta = salida / NOMBRES[formato]
        if formato == "md":
            ruta.write_text(
                renderizar_markdown(
                    resultado, correccion=correccion, max_por_regla=max_por_regla
                ),
                encoding="utf-8",
            )
        elif formato == "csv":
            escribir_csv(resultado, ruta)
        elif formato == "json":
            escribir_json(resultado, ruta, correccion=correccion)
        elif formato == "diff" and correccion is not None:
            ruta.write_text(
                crear_diff(
                    resultado.documento.texto,
                    correccion.texto_corregido,
                    resultado.documento.ruta.name,
                ),
                encoding="utf-8",
            )
        rutas[formato] = ruta
    return rutas


__all__ = [
    "FORMATOS_CONOCIDOS",
    "escribir_informes",
    "normalizar_formatos",
    "renderizar_markdown",
]
