"""Fixtures compartidas por las pruebas de OniriFix."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from onirifix.config import Configuracion
from onirifix.db.repositorios import Registro
from onirifix.io.cargadores import detectar_capitulos
from onirifix.modelo import Contexto, Documento, Glosario, Hallazgo, Nivel
from onirifix.nucleo.registro_reglas import descubrir_reglas


@pytest.fixture
def config() -> Configuracion:
    return Configuracion()


@pytest.fixture
def registro(tmp_path: Path) -> Registro:
    base = Registro(tmp_path / "onirifix.db")
    try:
        yield base
    finally:
        base.cerrar()


def ejecutar_regla(
    regla_id: str,
    texto: str,
    *,
    config: Configuracion | None = None,
    glosario: Glosario | None = None,
    ruta: Path | None = None,
    documento: Documento | None = None,
) -> list[Hallazgo]:
    """Ejecuta una sola regla con un contexto mínimo y determinista."""

    config = config or Configuracion()
    glosario = glosario or Glosario()
    documento = documento or Documento(
        ruta=ruta or Path("prueba.md"),
        texto=texto,
        capitulos=detectar_capitulos(texto),
    )
    contexto = Contexto(
        config=config,
        glosario=glosario,
        documento=documento,
        ruta=documento.ruta,
    )
    reglas = {regla.id: regla for regla in descubrir_reglas()}
    return list(reglas[regla_id].aplicar(texto, contexto))


def aplicar_hallazgos(hallazgos: list[Hallazgo], texto: str) -> str:
    """Aplica hallazgos de izquierda a derecha (utilidad de aserción)."""

    resultado = texto
    for hallazgo in sorted(hallazgos, key=lambda h: h.inicio, reverse=True):
        if hallazgo.sugerencia is not None:
            resultado = (
                resultado[: hallazgo.inicio]
                + hallazgo.sugerencia
                + resultado[hallazgo.fin :]
            )
    return resultado


@dataclass(slots=True)
class EntornoCLI:
    raiz: Path
    db: Path
    config: Path
    salida: Path
    backups: Path


@pytest.fixture
def entorno_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> EntornoCLI:
    monkeypatch.chdir(tmp_path)
    config = tmp_path / "config" / "reglas.yaml"
    Configuracion().guardar_plantilla(config)
    return EntornoCLI(
        raiz=tmp_path,
        db=tmp_path / "data" / "onirifix.db",
        config=config,
        salida=tmp_path / "informes",
        backups=tmp_path / "backups",
    )


@pytest.fixture
def texto_con_errores() -> str:
    return (
        "# Capítulo 1\n\n"
        "—Basta. —Dijo Mico.\n\n"
        'Dijo "hola" y se fue...\n\n'
        "La la ciudad , estaba llena.\n"
    )


@pytest.fixture
def nivel_l1() -> Nivel:
    return Nivel.L1
