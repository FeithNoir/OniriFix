"""Genera las capturas de la interfaz de escritorio en docs/screenshots.

Usa un relato inventado en una carpeta temporal (nunca texto de un manuscrito
real) y la plataforma ``offscreen`` de Qt, así que funciona sin pantalla:

    python scripts/capture_gui_screenshots.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
DESTINO = RAIZ / "docs" / "screenshots"

RELATO = """# Capítulo 1: El faro apagado

—No pienso volver. —Dijo Lina mientras cerraba la puerta.

Tomás miró hacía el muelle. La lluvia caía sobre las redes y el viento  empujaba las barcas...

Lina se acercó al ventanal y señalo la torre del faro. Tomás se rio sin ganas.

—Se que no me crees —murmuró ella—. Pero esa luz se apagó sola.

Hubo un suspiró largo entre los dos. Nadie respondio.

# Capítulo 2: La subasta

La la plaza estaba llena antes del amanecer. Mateo contó las monedas como si fuera la última vez.

Vienes conmigo a la subasta?

—¡Silencio¡ —gritó el subastador, y la sala obedeció.

—Él lo sabía todo  —dijo Ana— y nunca dijo nada.

TODO: revisar el nombre del barco.
"""


def _esperar(ventana, app, limite: float = 30.0) -> None:  # type: ignore[no-untyped-def]
    inicio = time.monotonic()
    while ventana.esta_ocupado() or ventana._reanalizar_al_terminar:
        if time.monotonic() - inicio > limite:
            raise TimeoutError("La ventana sigue ocupada")
        app.processEvents()
        time.sleep(0.02)
    for _ in range(10):
        app.processEvents()
        time.sleep(0.01)


def _guardar(ventana, app, nombre: str) -> Path:  # type: ignore[no-untyped-def]
    for _ in range(20):
        app.processEvents()
        time.sleep(0.01)
    ruta = DESTINO / nombre
    ventana.grab().save(str(ruta), "PNG")
    print(f"  {ruta.relative_to(RAIZ)}")
    return ruta


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from onirifix.config import cargar_settings
    from onirifix.gui.revision import Estado
    from onirifix.gui.tema import aplicar_tema
    from onirifix.gui.ventana import VentanaPrincipal

    DESTINO.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="onirifix-capturas-") as tmp:
        carpeta = Path(tmp)
        os.environ["ONIRIFIX_HOME"] = str(carpeta)
        for variable in ("ONIRIFIX_DB", "ONIRIFIX_CONFIG", "ONIRIFIX_SALIDA", "ONIRIFIX_BACKUPS"):
            os.environ.pop(variable, None)
        manuscrito = carpeta / "el-faro-apagado.md"
        manuscrito.write_text(RELATO, encoding="utf-8")

        app = QApplication.instance() or QApplication([sys.argv[0]])
        aplicar_tema(app)  # type: ignore[arg-type]
        ventana = VentanaPrincipal(cargar_settings(), restaurar=False)
        ventana._modo_silencioso = True
        ventana.resize(1440, 900)
        ventana.show()
        print("Capturas en docs/screenshots:")

        _guardar(ventana, app, "09-gui-inicio.png")

        # El análisis del relato de ejemplo tarda milisegundos: se muestra la
        # capa de ocupado tal como la pinta la ventana mientras trabaja.
        ventana.abrir_manuscrito(manuscrito, analizar=False)
        ventana._fijar_ocupado(
            True,
            "Analizando manuscrito…",
            f"{manuscrito.name} · 40 reglas. No se modifica nada.",
        )
        _guardar(ventana, app, "10-gui-analizando.png")
        ventana._fijar_ocupado(False)
        ventana.analizar()
        _esperar(ventana, app)
        ventana.tabla.selectRow(0)
        _guardar(ventana, app, "11-gui-analisis.png")

        ventana.filtros.fijar(nivel="L2")
        _esperar(ventana, app)
        ventana.tabla.selectRow(0)
        _guardar(ventana, app, "12-gui-filtro-l2.png")

        ventana.filtros.limpiar()
        _esperar(ventana, app)
        sesion = ventana.sesion
        assert sesion is not None
        objetivo = next(
            (i for i, h in enumerate(sesion.hallazgos) if h.regla == "TIL-003"),
            0,
        )
        ventana.tabla.selectRow(ventana.tabla.modelo.fila_de(objetivo))
        ventana.decidir_seleccion(Estado.ACEPTADO)
        _guardar(ventana, app, "13-gui-inspector.png")

        ventana._secciones["reglas"].abrir(False)
        ventana._secciones["filtros"].abrir(False)
        ventana._secciones["estadisticas"].abrir(True)
        _guardar(ventana, app, "14-gui-estadisticas.png")

        ventana.filtros.fijar(nivel="L2")
        ventana.decidir_visibles(Estado.ACEPTADO)
        ventana.filtros.limpiar()
        ventana.aplicar_cambios(confirmar=False)
        _esperar(ventana, app)
        ventana._secciones["reglas"].abrir(True)
        _guardar(ventana, app, "15-gui-aplicado.png")

        ventana.close()
        app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
