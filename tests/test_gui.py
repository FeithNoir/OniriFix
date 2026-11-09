"""Pruebas de la ventana en modo ``offscreen``.

Recorrido guionizado completo: abrir → analizar → revisar → aplicar →
exportar. Se omiten si PySide6 no está instalado. Texto inventado.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from onirifix.config import cargar_settings
from onirifix.gui.revision import Estado

pytestmark = pytest.mark.gui

TEXTO = (
    "# Capítulo 1\n\n"
    "—Basta. —Dijo Lina.\n\n"
    "Tomás dio dos pasos hacía adelante...\n\n"
    "# Capítulo 2\n\n"
    "Vienes mañana?\n\n"
    "La la tarde caía sobre el puerto.\n"
)


# ---------------------------------------------------------------------------
# Ventana (Qt offscreen)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def app():  # type: ignore[no-untyped-def]
    from PySide6.QtWidgets import QApplication

    from onirifix.gui.tema import aplicar_tema

    instancia = QApplication.instance() or QApplication([])
    aplicar_tema(instancia)  # type: ignore[arg-type]
    return instancia


def _esperar(ventana, limite: float = 20.0) -> None:  # type: ignore[no-untyped-def]
    from PySide6.QtTest import QTest

    inicio = time.monotonic()
    QTest.qWait(10)
    while ventana.esta_ocupado() or ventana._reanalizar_al_terminar:
        if time.monotonic() - inicio > limite:
            raise TimeoutError("La ventana sigue ocupada.")
        QTest.qWait(20)


@pytest.fixture
def ventana(app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    from onirifix.gui.ventana import VentanaPrincipal

    monkeypatch.setenv("ONIRIFIX_HOME", str(tmp_path))
    for variable in ("ONIRIFIX_DB", "ONIRIFIX_CONFIG", "ONIRIFIX_SALIDA", "ONIRIFIX_BACKUPS"):
        monkeypatch.delenv(variable, raising=False)
    ventana = VentanaPrincipal(cargar_settings(), restaurar=False)
    ventana._modo_silencioso = True
    ventana.show()
    yield ventana
    _esperar(ventana)
    ventana.close()


def test_flujo_completo_analizar_revisar_aplicar(ventana, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    manuscrito = tmp_path / "relato.md"
    manuscrito.write_text(TEXTO, encoding="utf-8")
    errores: list[str] = []
    ventana.error_mostrado.connect(errores.append)

    # 1. Analizar: no toca el archivo.
    ventana.abrir_manuscrito(manuscrito)
    assert ventana.esta_ocupado()
    _esperar(ventana)
    assert errores == []
    sesion = ventana.sesion
    assert sesion is not None and len(sesion) >= 4
    assert manuscrito.read_text(encoding="utf-8") == TEXTO

    # 2. Revisar: rechazar una corrección L1 y aceptar la L2 de «hacía».
    ventana.filtros.fijar(regla="TIP-004")
    rechazar = list(ventana.tabla.modelo.indices)
    assert rechazar
    ventana.decidir_visibles(Estado.RECHAZADO)
    ventana.filtros.fijar(regla="TIL-001")
    assert ventana.decidir_visibles(Estado.ACEPTADO) == 1
    ventana.filtros.fijar(regla="")
    avisos = [i for i, e in enumerate(sesion.estados) if e == Estado.AVISO]
    assert avisos  # L3: se muestran pero no se aplican

    # 3. Aplicar con copia de seguridad; la ventana vuelve a analizar.
    ventana.aplicar_cambios(confirmar=False)
    _esperar(ventana)
    assert errores == []
    corregido = manuscrito.read_text(encoding="utf-8")
    assert "hacia adelante" in corregido
    assert "—dijo Lina" in corregido
    assert "La tarde caía" in corregido or "La la tarde" in corregido
    assert "adelante..." in corregido  # rechazado: la elipsis queda igual
    assert "Vienes mañana?" in corregido  # L3 nunca se aplica
    copias = list((tmp_path / ".onirifix" / "backups").glob("relato.md.*.bak"))
    assert len(copias) == 1
    assert copias[0].read_text(encoding="utf-8") == TEXTO
    assert ventana.ultima_correccion is not None
    assert ventana.sesion is not None and ventana.sesion is not sesion

    # 4. Exportar el informe, con el diff de lo aplicado.
    carpeta = tmp_path / "informe"
    rutas: list[dict[str, Path]] = []
    ventana.informe_exportado.connect(rutas.append)
    ventana.exportar_informe(carpeta)
    _esperar(ventana)
    assert rutas and {"md", "csv", "json", "diff"} <= set(rutas[0])
    diff = (carpeta / "parches.diff").read_text(encoding="utf-8")
    assert "+Tomás dio dos pasos hacia adelante..." in diff


def test_capa_ocupado_bloquea_acciones_concurrentes(ventana, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    manuscrito = tmp_path / "breve.md"
    manuscrito.write_text("Miró hacía allí.\n", encoding="utf-8")
    ventana.abrir_manuscrito(manuscrito)
    assert ventana.esta_ocupado()
    trabajador = ventana._trabajador
    ventana.analizar()  # ignorado mientras trabaja
    assert ventana._trabajador is trabajador
    _esperar(ventana)
    assert not ventana.esta_ocupado()


def test_inspector_muestra_antes_y_despues(ventana, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    from onirifix.gui.componentes.inspector import vista_previa

    manuscrito = tmp_path / "breve.md"
    manuscrito.write_text("Miró hacía allí.\n", encoding="utf-8")
    ventana.abrir_manuscrito(manuscrito)
    _esperar(ventana)
    hallazgo = ventana.sesion.hallazgos[0]
    antes, despues = vista_previa(ventana.resultado.documento.texto, hallazgo)
    assert "hacía" in antes and "hacia" in despues


def test_comando_gui_registrado() -> None:
    from click.testing import CliRunner

    from onirifix.cli import cli

    resultado = CliRunner().invoke(cli, ["gui", "--help"])
    assert resultado.exit_code == 0
    assert "interfaz de escritorio" in resultado.output
