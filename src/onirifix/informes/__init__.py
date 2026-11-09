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

FORMATOS_CONOCIDOS: tuple[str, ...] = ("md", "csv", "json", "diff", "pdf")
FORMATOS_DEFECTO: frozenset[str] = frozenset({"md", "csv", "json"})

NOMBRES: dict[str, str] = {
    "md": "informe.md",
    "csv": "hallazgos.csv",
    "json": "hallazgos.json",
    "diff": "parches.diff",
    "pdf": "informe.pdf",
}
NOMBRE_MANUSCRITO_PDF = "manuscrito-corregido.pdf"


def _titulo(documento) -> str:  # type: ignore[no-untyped-def]
    """Primer párrafo corto antes del primer capítulo (el título de la obra) o el nombre."""

    inicios = [c.inicio for c in documento.capitulos if c.inicio > 0]
    primero = inicios[0] if inicios else len(documento.texto)
    for parrafo in documento.texto[:primero].split("\n\n"):
        parrafo = parrafo.strip()
        if parrafo.startswith("#"):
            break
        if parrafo:
            return parrafo if len(parrafo) <= 100 and "\n" not in parrafo else documento.ruta.stem
    return documento.ruta.stem


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
    segundos: float | None = None,
) -> dict[str, Path]:
    """Escribe los informes pedidos y devuelve ``{formato: ruta}``.

    Los formatos desconocidos se ignoran. El diff solo se escribe si hay una
    corrección con cambios. Con ``pdf`` y una corrección con cambios también
    se maqueta el manuscrito corregido (clave ``manuscrito_pdf``).
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
                # El diff parte del texto que se corrigió, que puede no ser el
                # del análisis actual (la GUI vuelve a analizar tras aplicar).
                crear_diff(
                    correccion.analisis.documento.texto,
                    correccion.texto_corregido,
                    correccion.analisis.documento.ruta.name,
                ),
                encoding="utf-8",
            )
        elif formato == "pdf":
            from onirifix.informes.pdf import escribir_informe_pdf, escribir_manuscrito_pdf

            escribir_informe_pdf(
                resultado, ruta, correccion=correccion, max_por_regla=max_por_regla,
                segundos=segundos,
            )
            if correccion is not None and correccion.aplicados:
                rutas["manuscrito_pdf"] = escribir_manuscrito_pdf(
                    correccion.texto_corregido,
                    salida / NOMBRE_MANUSCRITO_PDF,
                    titulo=_titulo(correccion.analisis.documento),
                    subtitulo=f"Texto corregido con OniriFix · {len(correccion.aplicados)} cambios",
                )
        rutas[formato] = ruta
    return rutas


__all__ = [
    "FORMATOS_CONOCIDOS",
    "NOMBRE_MANUSCRITO_PDF",
    "escribir_informes",
    "normalizar_formatos",
    "renderizar_markdown",
]
