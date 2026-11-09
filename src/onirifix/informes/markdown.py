"""Informe Markdown legible sin CSS."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from onirifix import __version__
from onirifix.modelo import Hallazgo, Nivel, ResultadoAnalisis, ResultadoCorreccion
from onirifix.util import escapar_markdown, truncar


def _celda(texto: str | None, maximo: int = 80) -> str:
    if texto is None:
        return "—"
    limpio = " ".join(texto.split()) if texto.strip() else repr(texto)
    return escapar_markdown(truncar(limpio, maximo))


def renderizar_markdown(
    resultado: ResultadoAnalisis,
    *,
    correccion: ResultadoCorreccion | None = None,
    max_por_regla: int = 300,
) -> str:
    doc = resultado.documento
    lineas: list[str] = [
        "# Informe de OniriFix",
        "",
        f"- Archivo: `{doc.ruta.name}`",
        f"- Palabras: {doc.palabras} · Capítulos: {len(doc.capitulos)}",
        f"- Reglas ejecutadas: {len(resultado.reglas_ejecutadas)}",
        f"- Generado: {datetime.now():%Y-%m-%d %H:%M} · OniriFix {__version__}",
        "",
    ]

    if not resultado.hallazgos:
        lineas += [
            "## Sin hallazgos",
            "",
            "Ninguna regla encontró nada que señalar. Recuerda que las reglas son "
            "mecánicas: L3 nunca decide por ti y la lectura en voz alta sigue siendo "
            "insustituible.",
            "",
        ]
    else:
        lineas += [
            "## Resumen",
            "",
            "| Nivel | Significado | Hallazgos |",
            "|---|---|---|",
        ]
        for nivel in Nivel:
            lineas.append(
                f"| {nivel.value} | {nivel.etiqueta} | {len(resultado.por_nivel(nivel))} |"
            )
        lineas += [
            "",
            "> L1 son cambios mecánicos; L2 requieren revisión o umbral; "
            "L3 son avisos para la lectura humana: L3 nunca decide por ti y "
            "no se aplican automáticamente.",
            "",
        ]

    if correccion is not None:
        lineas += [
            "## Corrección",
            "",
            f"- Parches aplicados: **{len(correccion.aplicados)}**",
            f"- Parches omitidos: {len(correccion.omitidos)}",
        ]
        if correccion.backup:
            lineas.append(f"- Copia de seguridad: `{correccion.backup}`")
        if correccion.escrito and correccion.destino:
            lineas.append(f"- Archivo escrito: `{correccion.destino}`")
        lineas.append("")

    if resultado.errores:
        lineas += ["## Errores de reglas", ""]
        lineas += [f"- {error}" for error in resultado.errores]
        lineas.append("")

    if resultado.hallazgos:
        por_regla: dict[str, list[Hallazgo]] = defaultdict(list)
        for hallazgo in resultado.hallazgos:
            por_regla[hallazgo.regla].append(hallazgo)
        lineas += ["## Hallazgos por regla", ""]
        for regla_id in resultado.conteo_por_regla():
            grupo = por_regla[regla_id]
            descripcion = resultado.descripciones.get(regla_id, "")
            lineas += [
                f"### `{regla_id}` · {grupo[0].nivel.value} · {len(grupo)}",
                "",
            ]
            if descripcion:
                lineas += [descripcion, ""]
            lineas += [
                "| Línea | Original | Sugerencia | Confianza | Nota |",
                "|---|---|---|---|---|",
            ]
            for hallazgo in grupo[:max_por_regla]:
                lineas.append(
                    f"| {hallazgo.linea} | {_celda(hallazgo.original)} | "
                    f"{_celda(hallazgo.sugerencia)} | {hallazgo.confianza:.2f} | "
                    f"{_celda(hallazgo.nota, 120)} |"
                )
            restantes = len(grupo) - max_por_regla
            if restantes > 0:
                lineas.append("")
                lineas.append(
                    f"_… y {restantes} hallazgo(s) más (consulta el CSV o el JSON)._"
                )
            lineas.append("")

    return "\n".join(lineas).rstrip() + "\n"
