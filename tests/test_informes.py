"""Pruebas de los informes Markdown, CSV, JSON y diff."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from onirifix.informes import escribir_informes, normalizar_formatos
from onirifix.informes.markdown import renderizar_markdown
from onirifix.modelo import (
    Documento,
    Hallazgo,
    Nivel,
    Parche,
    ResultadoAnalisis,
    ResultadoCorreccion,
)
from onirifix.nucleo.parches import crear_diff


def _resultado(tmp_path: Path) -> ResultadoAnalisis:
    texto = "# Capítulo 1\n\nHola , mundo.\n\nNo...\n"
    documento = Documento(
        ruta=tmp_path / "manuscrito.md",
        texto=texto,
        encoding="utf-8",
    )
    hallazgos = [
        Hallazgo(
            regla="TIP-002",
            nivel=Nivel.L1,
            inicio=texto.index(" ,"),
            fin=texto.index(" ,") + 2,
            original=" ,",
            sugerencia=",",
            confianza=0.99,
            linea=3,
            columna=5,
            contexto="Hola , mundo.",
            nota="Espacio antes de la coma.",
        ),
        Hallazgo(
            regla="TIP-002",
            nivel=Nivel.L1,
            inicio=texto.index("."),
            fin=texto.index(".") + 1,
            original=".",
            sugerencia=",",
            confianza=0.95,
            linea=3,
            columna=14,
            contexto="mundo.",
            nota="Segundo hallazgo de la misma regla.",
        ),
        Hallazgo(
            regla="REP-003",
            nivel=Nivel.L3,
            inicio=texto.index("No..."),
            fin=texto.index("No...") + 5,
            original="No...",
            sugerencia=None,
            confianza=0.7,
            linea=5,
            columna=1,
            contexto="No...",
            nota="Residuo de IA.",
        ),
    ]
    return ResultadoAnalisis(
        documento=documento,
        hallazgos=hallazgos,
        reglas_ejecutadas=["TIP-002", "REP-003"],
        descripciones={"TIP-002": "Espacio antes de puntuación.", "REP-003": "Residuo de IA."},
    )


def test_normalizar_formatos() -> None:
    assert normalizar_formatos(None) == {"md", "csv", "json"}
    assert normalizar_formatos("MD; CSV,json") == {"md", "csv", "json"}
    assert normalizar_formatos(["md", " diff "]) == {"md", "diff"}
    assert normalizar_formatos(",,, ") == set()


def test_escribir_todos_los_formatos(tmp_path: Path) -> None:
    resultado = _resultado(tmp_path)
    salida = tmp_path / "informes"

    rutas = escribir_informes(
        resultado,
        salida,
        formatos="md,csv,json",
        max_por_regla=1,
    )

    assert set(rutas) == {"md", "csv", "json"}
    assert rutas["md"].name == "informe.md"
    assert rutas["csv"].name == "hallazgos.csv"
    assert rutas["json"].name == "hallazgos.json"

    markdown = rutas["md"].read_text(encoding="utf-8")
    assert "# Informe de OniriFix" in markdown
    assert "## Resumen" in markdown
    assert "### `TIP-002`" in markdown
    assert "y 1 hallazgo(s) más" in markdown
    assert "No se aplican automáticamente" not in markdown or "L3" in markdown

    with rutas["csv"].open(encoding="utf-8-sig", newline="") as archivo:
        filas = list(csv.DictReader(archivo))
    assert len(filas) == 3
    assert filas[0]["archivo"] == "manuscrito.md"
    assert filas[0]["nivel"] == "L1"
    assert filas[0]["confianza"] == "0.99"

    datos = json.loads(rutas["json"].read_text(encoding="utf-8"))
    assert datos["archivo"] == str(resultado.documento.ruta)
    assert datos["resumen"] == {"L1": 2, "L2": 0, "L3": 1}
    assert len(datos["hallazgos"]) == 3
    assert "correccion" not in datos


def test_escribir_informes_sin_formatos_conocidos(tmp_path: Path) -> None:
    assert escribir_informes(_resultado(tmp_path), tmp_path / "x", formatos="pdf") == {}


def test_diff_solo_con_cambios(tmp_path: Path) -> None:
    resultado = _resultado(tmp_path)
    parche = Parche.desde_hallazgo(resultado.hallazgos[0])
    assert parche is not None
    correccion = ResultadoCorreccion(
        analisis=resultado,
        texto_corregido=resultado.documento.texto.replace(" ,", ","),
        parches_seleccionados=[parche],
        aplicados=[parche],
    )

    sin_correccion = escribir_informes(
        resultado, tmp_path / "sin", formatos="diff"
    )
    assert "diff" not in sin_correccion

    con_correccion = escribir_informes(
        resultado, tmp_path / "con-correccion", formatos="diff,md", correccion=correccion
    )
    assert "diff" in con_correccion
    diff = con_correccion["diff"].read_text(encoding="utf-8")
    assert "--- manuscrito.md.original" in diff
    assert "+++ manuscrito.md.corregido" in diff
    assert "-Hola , mundo." in diff
    assert "+Hola, mundo." in diff
    assert "Parches aplicados: **1**" in con_correccion["md"].read_text(encoding="utf-8")


def test_markdown_sin_hallazgos(tmp_path: Path) -> None:
    resultado = ResultadoAnalisis(
        documento=Documento(ruta=tmp_path / "vacio.md", texto=""),
        hallazgos=[],
    )

    markdown = renderizar_markdown(resultado)

    assert "## Sin hallazgos" in markdown
    assert "L3 nunca decide por ti" in markdown


def test_crear_diff_es_unificado() -> None:
    diff = crear_diff("uno\n", "dos\n", "x.md")
    assert diff.startswith("--- x.md.original")
    assert "+++ x.md.corregido" in diff
    assert "-uno" in diff
    assert "+dos" in diff
