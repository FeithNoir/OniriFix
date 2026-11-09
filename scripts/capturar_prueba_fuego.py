"""Capturas de la prueba de fuego: la interfaz real sobre un manuscrito real.

El manuscrito NO está en el repositorio. Se trabaja sobre una copia en una
carpeta temporal (el original no se toca) y solo se guardan las capturas:

    python scripts/capturar_prueba_fuego.py --manuscrito /ruta/al/libro.pdf \\
        [--config reglas.yaml] [--inicio 16]

Genera ``docs/screenshots/NN-prueba-fuego-*.png``.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
DESTINO = RAIZ / "docs" / "screenshots"


def _bombear(app, segundos: float = 0.2) -> None:  # type: ignore[no-untyped-def]
    fin = time.monotonic() + segundos
    while time.monotonic() < fin:
        app.processEvents()
        time.sleep(0.01)


def _esperar(ventana, app, limite: float = 300.0) -> None:  # type: ignore[no-untyped-def]
    inicio = time.monotonic()
    while ventana.esta_ocupado() or ventana._reanalizar_al_terminar:
        if time.monotonic() - inicio > limite:
            raise TimeoutError("La ventana sigue ocupada")
        app.processEvents()
        time.sleep(0.01)
    _bombear(app)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscrito", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--inicio", type=int, default=16)
    args = parser.parse_args()

    from PySide6.QtWidgets import QApplication

    from onirifix.config import cargar_settings
    from onirifix.gui.tema import aplicar_tema
    from onirifix.gui.ventana import VentanaPrincipal

    DESTINO.mkdir(parents=True, exist_ok=True)
    numero = [args.inicio]

    def guardar(ventana, nombre: str) -> Path:  # type: ignore[no-untyped-def]
        _bombear(app)
        ruta = DESTINO / f"{numero[0]:02d}-prueba-fuego-{nombre}.png"
        ventana.grab().save(str(ruta), "PNG")
        numero[0] += 1
        print(f"  {ruta.relative_to(RAIZ)}")
        return ruta

    with tempfile.TemporaryDirectory(prefix="onirifix-fuego-") as tmp:
        carpeta = Path(tmp)
        os.environ["ONIRIFIX_HOME"] = str(carpeta / "home")
        for variable in ("ONIRIFIX_DB", "ONIRIFIX_SALIDA", "ONIRIFIX_BACKUPS"):
            os.environ.pop(variable, None)
        if args.config:
            os.environ["ONIRIFIX_CONFIG"] = str(args.config.resolve())
        (carpeta / "manuscritos").mkdir()
        copia = carpeta / "manuscritos" / args.manuscrito.name
        shutil.copy2(args.manuscrito, copia)

        app = QApplication.instance() or QApplication([sys.argv[0]])
        aplicar_tema(app)  # type: ignore[arg-type]
        ventana = VentanaPrincipal(cargar_settings(), restaurar=False)
        ventana._modo_silencioso = True
        ventana.resize(1600, 980)
        ventana.show()
        print("Capturas en docs/screenshots:")

        # 1. Abrir: el manuscrito elegido, aún sin analizar.
        ventana.abrir_manuscrito(copia, analizar=False)
        ventana._estado("Manuscrito listo. Pulsa Analizar para revisarlo.")
        guardar(ventana, "abrir")

        # 2. Analizando: la captura se toma a mitad del análisis real.
        capturado = {"hecho": False}

        def al_avanzar(hechas: int, total: int, _detalle: str) -> None:
            if not capturado["hecho"] and total and hechas >= total // 2:
                capturado["hecho"] = True
                ventana.capa.progreso_en(hechas, total, _detalle)
                guardar(ventana, "analizando")

        ventana.analizar()
        ventana._trabajador.avance.connect(al_avanzar)  # type: ignore[union-attr]
        _esperar(ventana, app)

        # 3. Resultado del análisis.
        ventana.tabla.selectRow(0)
        guardar(ventana, "analisis")

        # 4. Detalle de un hallazgo (verbo de habla suelto, DIA-006).
        sesion = ventana.sesion
        assert sesion is not None
        objetivo = next(
            (i for i, h in enumerate(sesion.hallazgos) if h.regla == "DIA-006" and h.confianza >= 0.9),
            0,
        )
        ventana.filtros.fijar(regla="DIA-006")
        _bombear(app)
        ventana.tabla.selectRow(max(ventana.tabla.modelo.fila_de(objetivo), 0))
        guardar(ventana, "hallazgo")

        # 5. Texto completo con el hallazgo resaltado.
        ventana.ver_en_texto()
        guardar(ventana, "texto-completo")
        ventana.pestanas.setCurrentIndex(0)

        # 6. Estadísticas de lo pendiente en L2.
        ventana.filtros.limpiar()
        ventana.filtros.fijar(nivel="L2")
        ventana._secciones["reglas"].abrir(False)
        ventana._secciones["filtros"].abrir(False)
        ventana._secciones["estadisticas"].abrir(True)
        ventana.tabla.selectRow(0)
        guardar(ventana, "estadisticas")
        ventana._secciones["filtros"].abrir(True)

        # 7. Aceptar las L2 seguras.
        ventana.filtros.limpiar()
        ventana.aceptar_l2_seguras()
        ventana.tabla.selectRow(0)
        guardar(ventana, "l2-seguras")

        # 8. Aplicar: el PDF original no se toca; se escribe un .corregido.md.
        ventana.aplicar_cambios(confirmar=False)
        _esperar(ventana, app)
        ventana._secciones["estadisticas"].abrir(False)
        ventana._secciones["reglas"].abrir(True)
        ventana.tabla.selectRow(0)
        guardar(ventana, "aplicado")

        # 9. Exportar el informe y el manuscrito corregido en PDF.
        ventana.exportar_informe(carpeta / "informe")
        _esperar(ventana, app)
        guardar(ventana, "exportado")
        informe = ventana.ultimos_informes.get("pdf")
        if informe and shutil.which("pdftoppm"):
            base = DESTINO / f"{numero[0]:02d}-prueba-fuego-informe-pdf"
            subprocess.run(
                ["pdftoppm", "-png", "-r", "80", "-f", "1", "-l", "1", "-singlefile",
                 str(informe), str(base)],
                check=True,
            )
            print(f"  {base.with_suffix('.png').relative_to(RAIZ)}")
        ventana.close()
        app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
