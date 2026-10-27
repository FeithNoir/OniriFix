"""Pruebas del motor de reglas: activación, filtros y solapamientos."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest

from onirifix.config import Configuracion
from onirifix.modelo import (
    Contexto,
    Documento,
    Glosario,
    Hallazgo,
    Nivel,
    ResultadoAnalisis,
)
from onirifix.nucleo.motor import Motor


class ReglaFalsa:
    """Regla mínima para probar el motor sin depender del catálogo real."""

    por_defecto = True

    def __init__(
        self,
        regla_id: str,
        hallazgos: Iterable[Hallazgo] = (),
        *,
        nivel: Nivel = Nivel.L1,
        prioridad: int = 100,
        error: Exception | None = None,
    ) -> None:
        self.id = regla_id
        self.nivel = nivel
        self.descripcion = f"Regla de prueba {regla_id}."
        self.prioridad = prioridad
        self._hallazgos = list(hallazgos)
        self._error = error

    def aplicar(self, texto: str, ctx: Contexto) -> Iterable[Hallazgo]:
        if self._error is not None:
            raise self._error
        yield from self._hallazgos


def _hallazgo(
    regla: str,
    *,
    inicio: int = 0,
    fin: int = 4,
    original: str = "hola",
    nivel: Nivel = Nivel.L1,
) -> Hallazgo:
    return Hallazgo(
        regla=regla,
        nivel=nivel,
        inicio=inicio,
        fin=fin,
        original=original,
        sugerencia="adiós",
        confianza=0.9,
        linea=1,
        columna=inicio + 1,
        contexto=original,
    )


def _documento(texto: str = "hola mundo") -> Documento:
    return Documento(ruta=Path("prueba.md"), texto=texto)


def test_motor_respeta_reglas_desactivadas() -> None:
    config = Configuracion({"reglas": {"A": False, "B": True}})
    motor = Motor(
        config,
        Glosario(),
        reglas=[
            ReglaFalsa("A", [_hallazgo("A")]),
            ReglaFalsa("B", [_hallazgo("B", inicio=5, fin=10, original="mundo")]),
        ],
    )

    resultado = motor.analizar(_documento())

    assert resultado.reglas_ejecutadas == ["B"]
    assert [h.regla for h in resultado.hallazgos] == ["B"]


def test_motor_solo_reglas_explicitas() -> None:
    motor = Motor(
        Configuracion(),
        Glosario(),
        reglas=[ReglaFalsa("A", [_hallazgo("A")]), ReglaFalsa("B")],
    )

    resultado = motor.analizar(_documento(), solo_reglas=["b"])

    assert resultado.reglas_ejecutadas == ["B"]
    assert resultado.hallazgos == []


def test_motor_rechaza_regla_desconocida() -> None:
    motor = Motor(Configuracion(), Glosario(), reglas=[ReglaFalsa("A")])

    with pytest.raises(ValueError, match="Reglas desconocidas: NOPE"):
        motor.analizar(_documento(), solo_reglas=["NOPE"])


def test_motor_oculta_l3_si_se_pide() -> None:
    motor = Motor(
        Configuracion(),
        Glosario(),
        reglas=[
            ReglaFalsa("L1", [_hallazgo("L1")]),
            ReglaFalsa(
                "L3",
                [_hallazgo("L3", inicio=5, fin=10, original="mundo", nivel=Nivel.L3)],
            ),
        ],
    )

    con_l3 = motor.analizar(_documento())
    sin_l3 = motor.analizar(_documento(), incluir_l3=False)

    assert {h.nivel for h in con_l3.hallazgos} == {Nivel.L1, Nivel.L3}
    assert {h.nivel for h in sin_l3.hallazgos} == {Nivel.L1}


def test_motor_deduplica_solapamientos_por_prioridad() -> None:
    motor = Motor(
        Configuracion(),
        Glosario(),
        reglas=[
            ReglaFalsa("TARDE", [_hallazgo("TARDE")], prioridad=80),
            ReglaFalsa("PRONTO", [_hallazgo("PRONTO")], prioridad=10),
        ],
    )

    resultado = motor.analizar(_documento())

    assert [h.regla for h in resultado.hallazgos] == ["PRONTO"]


def test_motor_conserva_hallazgos_que_no_se_solapan() -> None:
    motor = Motor(
        Configuracion(),
        Glosario(),
        reglas=[
            ReglaFalsa(
                "A",
                [
                    _hallazgo("A", inicio=0, fin=4, original="hola"),
                    _hallazgo("A", inicio=5, fin=10, original="mundo"),
                ],
            )
        ],
    )

    resultado = motor.analizar(_documento())

    assert [h.original for h in resultado.hallazgos] == ["hola", "mundo"]


def test_motor_registra_error_de_una_regla_y_sigue() -> None:
    motor = Motor(
        Configuracion(),
        Glosario(),
        reglas=[
            ReglaFalsa("ROTA", error=RuntimeError("boom")),
            ReglaFalsa("SANA", [_hallazgo("SANA")]),
        ],
    )

    resultado = motor.analizar(_documento())

    assert resultado.errores == ["ROTA: RuntimeError: boom"]
    assert [h.regla for h in resultado.hallazgos] == ["SANA"]


def test_motor_pasa_configuracion_y_documento_al_contexto() -> None:
    visto: dict[str, object] = {}

    class ReglaCuriosa(ReglaFalsa):
        def aplicar(self, texto: str, ctx: Contexto) -> Iterable[Hallazgo]:
            visto["texto"] = texto
            visto["ruta"] = ctx.documento.ruta if ctx.documento else None
            visto["idioma"] = ctx.idioma
            return iter(())

    motor = Motor(Configuracion({"idioma": "es"}), Glosario(), reglas=[ReglaCuriosa("X")])
    documento = _documento("texto de prueba")

    resultado = motor.analizar(documento)

    assert isinstance(resultado, ResultadoAnalisis)
    assert visto == {
        "texto": "texto de prueba",
        "ruta": documento.ruta,
        "idioma": "es",
    }


def test_motor_activa_dia_003_con_rae_estricto() -> None:
    config = Configuracion({"reglas": {"DIA-003": False}, "dialogos": {"rae_estricto": True}})
    motor = Motor(config, Glosario())

    activas = {regla.id for regla in motor.reglas_activas()}

    assert "DIA-003" in activas
