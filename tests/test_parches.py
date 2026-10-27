"""Pruebas de selección y aplicación de parches."""

from __future__ import annotations

import pytest

from onirifix.modelo import Hallazgo, Nivel, Parche
from onirifix.nucleo.parches import aplicar_parches, crear_diff, seleccionar_parches


def _hallazgo(
    original: str,
    sugerencia: str | None,
    *,
    inicio: int,
    nivel: Nivel = Nivel.L1,
    confianza: float = 1.0,
    regla: str = "TEST",
) -> Hallazgo:
    return Hallazgo(
        regla=regla,
        nivel=nivel,
        inicio=inicio,
        fin=inicio + len(original),
        original=original,
        sugerencia=sugerencia,
        confianza=confianza,
        linea=1,
        columna=inicio + 1,
        contexto=original,
    )


def test_seleccionar_l1_sin_pedir_l2() -> None:
    hallazgos = [
        _hallazgo("ab", "cd", inicio=0),
        _hallazgo("ef", "gh", inicio=3, nivel=Nivel.L2, confianza=0.99),
        _hallazgo("ij", None, inicio=6, nivel=Nivel.L3),
    ]
    parches = seleccionar_parches(hallazgos)
    assert [p.regla for p in parches] == ["TEST"]
    assert len(parches) == 1


def test_seleccionar_l2_respeta_umbral() -> None:
    hallazgos = [
        _hallazgo("ab", "cd", inicio=0, nivel=Nivel.L2, confianza=0.90),
        _hallazgo("ef", "gh", inicio=3, nivel=Nivel.L2, confianza=0.89),
    ]
    assert len(seleccionar_parches(hallazgos, aplicar_l2=True, umbral_l2=0.9)) == 1


def test_seleccionar_l2_sin_flag_no_aplica() -> None:
    hallazgos = [
        _hallazgo("ab", "cd", inicio=0, nivel=Nivel.L2, confianza=0.99)
    ]
    assert seleccionar_parches(hallazgos) == []
    assert len(seleccionar_parches(hallazgos, aplicar_l2=True)) == 1


def test_aplicar_parches_en_orden() -> None:
    texto = "uno dos tres"
    parches = [
        Parche(8, 12, "tres", "TRES", "A", Nivel.L1, 1.0),
        Parche(0, 3, "uno", "UNO", "B", Nivel.L1, 1.0),
    ]
    corregido, aplicados, omitidos = aplicar_parches(texto, parches)
    assert corregido == "UNO dos TRES"
    assert [p.regla for p in aplicados] == ["B", "A"]
    assert omitidos == []


def test_aplicar_parches_omite_solapados() -> None:
    texto = "abcdef"
    parches = [
        Parche(0, 4, "abcd", "X", "A", Nivel.L1, 1.0),
        Parche(2, 5, "cde", "Y", "B", Nivel.L1, 1.0),
    ]
    corregido, aplicados, omitidos = aplicar_parches(texto, parches)
    assert corregido == "Xef"
    assert [p.regla for p in aplicados] == ["A"]
    assert len(omitidos) == 1
    assert "solapa" in omitidos[0][1]


def test_aplicar_parches_omite_texto_cambiado() -> None:
    texto = "abcdef"
    parche = Parche(0, 3, "xyz", "123", "A", Nivel.L1, 1.0)
    corregido, aplicados, omitidos = aplicar_parches(texto, [parche])
    assert corregido == texto
    assert aplicados == []
    assert "El texto cambió" in omitidos[0][1]


def test_aplicar_parches_omite_fuera_de_rango() -> None:
    parche = Parche(0, 99, "abc", "x", "A", Nivel.L1, 1.0)
    _, aplicados, omitidos = aplicar_parches("abc", [parche])
    assert aplicados == []
    assert "fuera del texto" in omitidos[0][1]


def test_crear_diff() -> None:
    diff = crear_diff("hola\n", "adiós\n", "prueba.md")
    assert "--- prueba.md.original" in diff
    assert "+++ prueba.md.corregido" in diff
    assert "-hola" in diff
    assert "+adiós" in diff


@pytest.mark.parametrize("texto", ["", "sin cambios"])
def test_crear_diff_sin_cambios(texto: str) -> None:
    assert crear_diff(texto, texto, "x") == ""
