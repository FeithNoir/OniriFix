"""Exportación tabular (CSV) y estructurada (JSON) de los hallazgos."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from onirifix import __version__
from onirifix.modelo import Hallazgo, Nivel, ResultadoAnalisis, ResultadoCorreccion

COLUMNAS = (
    "archivo",
    "capitulo",
    "linea",
    "columna",
    "regla",
    "nivel",
    "confianza",
    "original",
    "sugerencia",
    "nota",
    "contexto",
)


def _capitulo(resultado: ResultadoAnalisis, hallazgo: Hallazgo) -> str:
    capitulo = resultado.documento.capitulo_de(hallazgo.inicio)
    return capitulo.titulo if capitulo else ""


def fila_hallazgo(resultado: ResultadoAnalisis, hallazgo: Hallazgo) -> dict[str, Any]:
    return {
        "archivo": resultado.documento.ruta.name,
        "capitulo": _capitulo(resultado, hallazgo),
        "linea": hallazgo.linea,
        "columna": hallazgo.columna,
        "regla": hallazgo.regla,
        "nivel": hallazgo.nivel.value,
        "confianza": f"{hallazgo.confianza:.2f}",
        "original": hallazgo.original,
        "sugerencia": "" if hallazgo.sugerencia is None else hallazgo.sugerencia,
        "nota": hallazgo.nota,
        "contexto": " ".join(hallazgo.contexto.split()),
    }


def escribir_csv(resultado: ResultadoAnalisis, ruta: Path) -> Path:
    # utf-8-sig para que Excel en Windows abra las tildes sin pelear.
    with ruta.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)
        escritor.writeheader()
        for hallazgo in resultado.hallazgos:
            escritor.writerow(fila_hallazgo(resultado, hallazgo))
    return ruta


def resumen_por_nivel(resultado: ResultadoAnalisis) -> dict[str, int]:
    return {nivel.value: len(resultado.por_nivel(nivel)) for nivel in Nivel}


def datos_json(
    resultado: ResultadoAnalisis, correccion: ResultadoCorreccion | None = None
) -> dict[str, Any]:
    datos: dict[str, Any] = {
        "onirifix": __version__,
        "generado_en": datetime.now().isoformat(timespec="seconds"),
        "archivo": str(resultado.documento.ruta),
        "palabras": resultado.documento.palabras,
        "capitulos": len(resultado.documento.capitulos),
        "reglas_ejecutadas": list(resultado.reglas_ejecutadas),
        "errores": list(resultado.errores),
        "resumen": resumen_por_nivel(resultado),
        "por_regla": resultado.conteo_por_regla(),
        "hallazgos": [
            {
                **fila_hallazgo(resultado, h),
                "confianza": h.confianza,
                "sugerencia": h.sugerencia,
                "inicio": h.inicio,
                "fin": h.fin,
                "contexto": h.contexto,
            }
            for h in resultado.hallazgos
        ],
    }
    if correccion is not None:
        datos["correccion"] = {
            "aplicados": len(correccion.aplicados),
            "omitidos": [
                {"regla": p.regla, "inicio": p.inicio, "motivo": motivo}
                for p, motivo in correccion.omitidos
            ],
            "escrito": correccion.escrito,
            "destino": str(correccion.destino) if correccion.destino else None,
            "backup": str(correccion.backup) if correccion.backup else None,
        }
    return datos


def escribir_json(
    resultado: ResultadoAnalisis,
    ruta: Path,
    *,
    correccion: ResultadoCorreccion | None = None,
) -> Path:
    ruta.write_text(
        json.dumps(datos_json(resultado, correccion), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return ruta
