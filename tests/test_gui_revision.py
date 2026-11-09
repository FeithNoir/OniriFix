"""Pruebas de ``SesionRevision``: decisiones, filtros y estadísticas, sin Qt.

Todo el texto es inventado para la prueba.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from onirifix.config import Configuracion
from onirifix.gui.revision import Estado, Filtro, SesionRevision
from onirifix.io.cargadores import detectar_capitulos
from onirifix.modelo import Documento, Glosario, Nivel
from onirifix.nucleo.motor import Motor

TEXTO = (
    "# Capítulo 1\n\n"
    "—Basta. —Dijo Lina.\n\n"
    "Tomás dio dos pasos hacía adelante...\n\n"
    "# Capítulo 2\n\n"
    "Vienes mañana?\n\n"
    "La la tarde caía sobre el puerto.\n"
)


def _resultado(texto: str = TEXTO):  # type: ignore[no-untyped-def]
    documento = Documento(ruta=Path("prueba.md"), texto=texto, capitulos=detectar_capitulos(texto))
    return Motor(Configuracion(), Glosario()).analizar(documento)


# ---------------------------------------------------------------------------
# Sesión de revisión (sin Qt)
# ---------------------------------------------------------------------------


def test_estados_iniciales_por_nivel() -> None:
    sesion = SesionRevision(_resultado())
    assert len(sesion) > 0
    for hallazgo, estado in zip(sesion.hallazgos, sesion.estados, strict=True):
        if not hallazgo.aplicable:
            assert estado == Estado.AVISO
        elif hallazgo.nivel == Nivel.L1:
            assert estado == Estado.ACEPTADO
        else:
            assert estado == Estado.PENDIENTE
    assert Estado.AVISO in sesion.estados  # «Vienes mañana?» es L3


def test_l3_es_solo_lectura() -> None:
    sesion = SesionRevision(_resultado())
    avisos = [i for i, e in enumerate(sesion.estados) if e == Estado.AVISO]
    assert sesion.decidir(avisos, Estado.ACEPTADO) == 0
    assert all(sesion.estados[i] == Estado.AVISO for i in avisos)
    with pytest.raises(ValueError):
        sesion.decidir(0, Estado.AVISO)


def test_filtros_por_nivel_regla_y_capitulo() -> None:
    sesion = SesionRevision(_resultado())
    assert sesion.capitulos() == ["Capítulo 1", "Capítulo 2"]
    l2 = sesion.filtrar(Filtro(nivel="L2"))
    assert l2 and all(sesion.hallazgos[i].nivel == Nivel.L2 for i in l2)
    til = sesion.filtrar(Filtro(regla="TIL-001"))
    assert [sesion.hallazgos[i].original for i in til] == ["hacía"]
    cap2 = sesion.filtrar(Filtro(capitulo="Capítulo 2"))
    assert cap2 and all(sesion.capitulo(i) == "Capítulo 2" for i in cap2)
    assert sesion.filtrar(Filtro(texto="hacia")) == til


def test_parches_solo_de_aceptados() -> None:
    sesion = SesionRevision(_resultado())
    todos = list(range(len(sesion)))
    sesion.decidir(todos, Estado.RECHAZADO)
    assert sesion.parches_aceptados() == []
    til = sesion.filtrar(Filtro(regla="TIL-001"))
    sesion.decidir(til, Estado.ACEPTADO)
    parches = sesion.parches_aceptados()
    assert [p.reemplazo for p in parches] == ["hacia"]
    resumen = sesion.resumen()
    assert resumen.total == len(sesion)
    assert resumen.por_estado["aceptado"] == 1
