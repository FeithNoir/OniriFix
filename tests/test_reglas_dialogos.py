"""Pruebas de las reglas de diálogo."""

from __future__ import annotations

from tests.conftest import aplicar_hallazgos, ejecutar_regla

from onirifix.config import Configuracion
from onirifix.modelo import Nivel


def test_dia_001_baja_verbo_tras_cierre() -> None:
    texto = "—Basta. —Dijo Mico."
    hallazgos = ejecutar_regla("DIA-001", texto)
    assert len(hallazgos) == 1
    assert hallazgos[0].sugerencia == ". —dijo"
    assert aplicar_hallazgos(hallazgos, texto) == "—Basta. —dijo Mico."


def test_dia_001_no_toca_verbo_desconocido() -> None:
    assert ejecutar_regla("DIA-001", "—Basta. —Corrió Mico.") == []


def test_dia_001_respeta_verbos_del_registro() -> None:
    from onirifix.modelo import Glosario

    glosario = Glosario(verbos_habla=frozenset({"trinó"}))
    hallazgos = ejecutar_regla(
        "DIA-001", "—Basta. —Trinó el pájaro.", glosario=glosario
    )
    assert len(hallazgos) == 1
    assert hallazgos[0].sugerencia == ". —trinó"


def test_dia_002_reanudacion() -> None:
    texto = "—Vete —dijo él. —La puerta está abierta."
    hallazgos = ejecutar_regla("DIA-002", texto)
    assert len(hallazgos) == 1
    assert hallazgos[0].nivel is Nivel.L2
    assert hallazgos[0].sugerencia == "la"
    assert hallazgos[0].confianza < 0.7


def test_dia_002_no_confunde_nombre_del_glosario() -> None:
    from onirifix.modelo import Glosario

    glosario = Glosario(nombres=frozenset({"La"}))
    assert (
        ejecutar_regla(
            "DIA-002",
            "—Vete —dijo él. —La puerta está abierta.",
            glosario=glosario,
        )
        == []
    )


def test_dia_003_opt_in_explicito() -> None:
    config = Configuracion({"dialogos": {"rae_estricto": True}})
    texto = "—Basta. —dijo Mico."
    hallazgos = ejecutar_regla("DIA-003", texto, config=config)
    assert len(hallazgos) == 1
    assert aplicar_hallazgos(hallazgos, texto) == "—Basta —dijo Mico."


def test_dia_003_apagado_por_configuracion() -> None:
    config = Configuracion({"dialogos": {"rae_estricto": False}})
    assert (
        ejecutar_regla("DIA-003", "—Basta. —dijo Mico.", config=config) == []
    )


def test_dia_004_espacio_antes_de_raya() -> None:
    texto = "Hola—dijo Mico."
    hallazgos = ejecutar_regla("DIA-004", texto)
    assert len(hallazgos) == 1
    assert aplicar_hallazgos(hallazgos, texto) == "Hola —dijo Mico."


def test_dia_005_espacio_despues_de_raya() -> None:
    texto = "Mico—Las llaves."
    hallazgos = ejecutar_regla("DIA-005", texto)
    assert len(hallazgos) == 1
    assert aplicar_hallazgos(hallazgos, texto) == "Mico— Las llaves."
