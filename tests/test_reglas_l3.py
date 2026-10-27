"""Pruebas de repetición, duplicados y residuo de IA (L3)."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import ejecutar_regla

from onirifix.config import Configuracion
from onirifix.modelo import Documento, Glosario, Nivel
from onirifix.reglas.repeticion import calcular_frecuencias


def test_rep_001_frecuencia_lexica() -> None:
    texto = "dragón " * 8 + "La espada brillaba."
    hallazgos = ejecutar_regla("REP-001", texto)
    assert len(hallazgos) == 1
    assert hallazgos[0].nivel is Nivel.L3
    assert hallazgos[0].sugerencia is None
    assert "8 apariciones" in hallazgos[0].nota


def test_rep_001_umbral_configurable() -> None:
    config = Configuracion({"repeticion": {"minimo_palabras": 3}})
    hallazgos = ejecutar_regla("REP-001", "dragón dragón dragón", config=config)
    assert len(hallazgos) == 1


def test_rep_001_top_limita() -> None:
    texto = ("dragón " * 8) + ("espada " * 8) + ("castillo " * 8)
    config = Configuracion({"repeticion": {"top": 1}})
    assert len(ejecutar_regla("REP-001", texto, config=config)) == 1


def test_rep_001_desglose_por_capitulo() -> None:
    texto = "# Uno\n" + ("dragón " * 5) + "\n# Dos\n" + ("dragón " * 5)
    documento = Documento(
        ruta=Path("x.md"),
        texto=texto,
        capitulos=(
            # Los offsets reales no importan para esta prueba de frecuencias.
            __import__("onirifix.modelo", fromlist=["Capitulo"]).Capitulo(
                "Uno", 0, texto.index("# Dos"), 1
            ),
            __import__("onirifix.modelo", fromlist=["Capitulo"]).Capitulo(
                "Dos", texto.index("# Dos"), len(texto), 6
            ),
        ),
    )
    config = Configuracion({"repeticion": {"minimo_palabras": 5}})
    frecuencias = calcular_frecuencias(texto, Glosario(), config, documento)
    dragon = next(f for f in frecuencias if f.palabra == "dragón")
    assert dragon.por_capitulo == {"Uno": 5, "Dos": 5}


def test_rep_001_desactivar_capitulos_en_nota() -> None:
    texto = "# Uno\ndragón dragón dragón dragón dragón dragón dragón dragón"
    config = Configuracion(
        {"repeticion": {"minimo_palabras": 5, "por_capitulo": False}}
    )
    hallazgos = ejecutar_regla("REP-001", texto, config=config)
    assert len(hallazgos) == 1
    assert "Capítulos:" not in hallazgos[0].nota


def test_rep_002_duplicado_exacto() -> None:
    parrafo = "Esta es una frase larga con muchas palabras para duplicar."
    texto = f"{parrafo}\n\n{parrafo}"
    hallazgos = ejecutar_regla("REP-002", texto)
    assert len(hallazgos) == 1
    assert hallazgos[0].nivel is Nivel.L3
    assert "Duplicado exacto" in hallazgos[0].nota


def test_rep_002_duplicado_difuso() -> None:
    texto = (
        "Esta es una frase larga con muchas palabras para duplicar.\n\n"
        "Esta es una frase larga con muchas palabras para duplicar!"
    )
    hallazgos = ejecutar_regla("REP-002", texto)
    assert len(hallazgos) == 1
    assert "difuso" in hallazgos[0].nota


def test_rep_003_residuo_ia() -> None:
    hallazgos = ejecutar_regla(
        "REP-003", "En el vasto tapiz de la noche, todo era calma."
    )
    assert len(hallazgos) == 1
    assert hallazgos[0].sugerencia is None
    assert "residuo de IA" in hallazgos[0].nota


def test_rep_004_frase_larga() -> None:
    texto = "palabra " * 61 + "."
    hallazgos = ejecutar_regla("REP-004", texto)
    assert len(hallazgos) == 1
    assert "61 palabras" in hallazgos[0].nota


def test_rep_004_no_marca_frase_corta() -> None:
    assert ejecutar_regla("REP-004", "Una frase corta.") == []
