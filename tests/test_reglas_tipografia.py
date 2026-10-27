"""Pruebas de las reglas de tipografía mecánica."""

from __future__ import annotations

import pytest
from tests.conftest import aplicar_hallazgos, ejecutar_regla

from onirifix.config import Configuracion
from onirifix.modelo import Nivel


def test_tip_001_colapsa_espacios() -> None:
    hallazgos = ejecutar_regla("TIP-001", "Hola   mundo")
    assert len(hallazgos) == 1
    assert hallazgos[0].sugerencia == " "
    assert aplicar_hallazgos(hallazgos, "Hola   mundo") == "Hola mundo"


def test_tip_001_no_toca_sangria() -> None:
    assert ejecutar_regla("TIP-001", "    Hola mundo") == []


def test_tip_002_quita_espacio_antes_de_puntuacion() -> None:
    hallazgos = ejecutar_regla("TIP-002", "Hola , mundo.")
    assert [h.sugerencia for h in hallazgos] == [","]


def test_tip_003_anade_espacio_despues_de_puntuacion() -> None:
    hallazgos = ejecutar_regla("TIP-003", "Hola,mundo;bien:hecho")
    assert len(hallazgos) == 3
    assert aplicar_hallazgos(hallazgos, "Hola,mundo;bien:hecho") == "Hola, mundo; bien: hecho"


def test_tip_003_no_toca_numeros() -> None:
    assert ejecutar_regla("TIP-003", "3,14 y 2:30") == []


def test_tip_004_puntos_suspensivos() -> None:
    hallazgos = ejecutar_regla("TIP-004", "No...")
    assert len(hallazgos) == 1
    assert hallazgos[0].sugerencia == "…"
    assert aplicar_hallazgos(hallazgos, "No...") == "No…"


def test_tip_005_comillas_rectas() -> None:
    texto = 'Dijo "hola" y se fue.'
    hallazgos = ejecutar_regla("TIP-005", texto)
    assert len(hallazgos) == 1
    assert hallazgos[0].sugerencia == "«hola»"
    assert aplicar_hallazgos(hallazgos, texto) == "Dijo «hola» y se fue."


def test_tip_005_respeta_configuracion() -> None:
    config = Configuracion(
        {"tipografia": {"comillas": "“”", "convertir_comillas": True}}
    )
    hallazgos = ejecutar_regla("TIP-005", 'Dijo "hola".', config=config)
    assert hallazgos[0].sugerencia == "“hola”"


def test_tip_005_desactivada_por_configuracion() -> None:
    config = Configuracion({"tipografia": {"convertir_comillas": False}})
    assert ejecutar_regla("TIP-005", 'Dijo "hola".', config=config) == []


def test_tip_006_apostrofos() -> None:
    hallazgos = ejecutar_regla("TIP-006", "l'aire")
    assert [h.sugerencia for h in hallazgos] == ["’"]


def test_tip_006_se_puede_desactivar() -> None:
    config = Configuracion({"tipografia": {"convertir_apostrofos": False}})
    assert ejecutar_regla("TIP-006", "l'aire", config=config) == []


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("–Hola", "—Hola"),
        ("--Hola", "—Hola"),
        ("Hola –dijo", "Hola —dijo"),
        ("Hola -- dijo", "Hola — dijo"),
    ],
)
def test_tip_007_rayas(texto: str, esperado: str) -> None:
    hallazgos = ejecutar_regla("TIP-007", texto)
    assert aplicar_hallazgos(hallazgos, texto) == esperado


def test_tip_008_tabulaciones() -> None:
    hallazgos = ejecutar_regla("TIP-008", "Hola\tmundo")
    assert aplicar_hallazgos(hallazgos, "Hola\tmundo") == "Hola mundo"


def test_tip_009_puntuacion_duplicada() -> None:
    hallazgos = ejecutar_regla("TIP-009", "Hola,, mundo")
    assert aplicar_hallazgos(hallazgos, "Hola,, mundo") == "Hola, mundo"


def test_tip_010_comillas_desbalanceadas_es_l3() -> None:
    hallazgos = ejecutar_regla("TIP-010", 'Dijo "hola\n')
    assert len(hallazgos) == 1
    assert hallazgos[0].nivel is Nivel.L3
    assert hallazgos[0].sugerencia is None
