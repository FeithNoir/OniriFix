"""Pruebas del modelo de dominio."""

from __future__ import annotations

from pathlib import Path

import pytest

from onirifix.modelo import (
    Capitulo,
    Documento,
    Hallazgo,
    Nivel,
    Parche,
    crear_hallazgo,
)


def test_nivel_desde_acepta_mayusculas_y_enum() -> None:
    assert Nivel.desde("l1") is Nivel.L1
    assert Nivel.desde(Nivel.L2) is Nivel.L2
    with pytest.raises(ValueError, match="Nivel desconocido"):
        Nivel.desde("L4")


def test_crear_hallazgo_calcula_linea_columna_y_contexto() -> None:
    texto = "Primera línea\nSegunda línea con error\nTercera"
    hallazgo = crear_hallazgo(
        texto,
        regla="TEST-001",
        nivel=Nivel.L1,
        inicio=texto.index("error"),
        fin=texto.index("error") + len("error"),
        sugerencia="acierto",
        confianza=0.95555,
        radio_contexto=5,
    )
    assert hallazgo is not None
    assert hallazgo.linea == 2
    assert hallazgo.columna == texto.index("error") - texto.index("\n")
    assert hallazgo.confianza == 0.9556
    assert hallazgo.original == "error"
    assert "error" in hallazgo.contexto


def test_crear_hallazgo_columna_primera_linea_es_uno_based() -> None:
    hallazgo = crear_hallazgo(
        "hola mundo",
        regla="TEST",
        nivel=Nivel.L1,
        inicio=0,
        fin=4,
        sugerencia="adiós",
        confianza=1,
    )
    assert hallazgo is not None
    assert hallazgo.linea == 1
    assert hallazgo.columna == 1


def test_crear_hallazgo_ignora_reemplazo_identico() -> None:
    assert (
        crear_hallazgo(
            "hola",
            regla="TEST",
            nivel=Nivel.L1,
            inicio=0,
            fin=4,
            sugerencia="hola",
            confianza=1,
        )
        is None
    )


def test_crear_hallazgo_valida_span() -> None:
    with pytest.raises(ValueError, match="Span inválido"):
        crear_hallazgo(
            "hola",
            regla="TEST",
            nivel=Nivel.L1,
            inicio=2,
            fin=8,
            sugerencia=None,
            confianza=1,
        )


def test_hallazgo_aplicable_solo_l1_l2_con_sugerencia() -> None:
    base = dict(
        regla="TEST",
        inicio=0,
        fin=4,
        original="hola",
        confianza=1,
        linea=1,
        columna=1,
        contexto="hola",
    )
    assert Hallazgo(**base, nivel=Nivel.L1, sugerencia="x").aplicable
    assert not Hallazgo(**base, nivel=Nivel.L1, sugerencia=None).aplicable
    assert not Hallazgo(**base, nivel=Nivel.L3, sugerencia="x").aplicable


def test_hallazgos_se_solapan() -> None:
    uno = Hallazgo("A", Nivel.L1, 0, 5, "a", None, 1, 1, 1, "")
    dos = Hallazgo("B", Nivel.L1, 4, 8, "b", None, 1, 1, 1, "")
    tres = Hallazgo("C", Nivel.L1, 5, 9, "c", None, 1, 1, 1, "")
    assert uno.se_solapa(dos)
    assert not uno.se_solapa(tres)


def test_parche_desde_hallazgo() -> None:
    hallazgo = Hallazgo("A", Nivel.L2, 1, 3, "ab", "cd", 0.9, 1, 2, "")
    parche = Parche.desde_hallazgo(hallazgo)
    assert parche is not None
    assert (parche.inicio, parche.fin, parche.reemplazo) == (1, 3, "cd")
    assert Parche.desde_hallazgo(
        Hallazgo("A", Nivel.L3, 0, 1, "a", None, 1, 1, 1, "")
    ) is None


def test_documento_capitulo_de() -> None:
    documento = Documento(
        ruta=Path("prueba.md"),
        texto="# Uno\na\n# Dos\nb",
        capitulos=(),
    )
    assert documento.palabras == 6
    documento = Documento(
        ruta=Path("prueba.md"),
        texto="# Uno\na\n# Dos\nb",
        capitulos=(Capitulo("Uno", 0, 7, 1),),
    )
    assert documento.capitulo_de(2).titulo == "Uno"  # type: ignore[union-attr]
    assert documento.capitulo_de(50) is None
