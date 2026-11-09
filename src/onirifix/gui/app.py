"""Punto de entrada de la interfaz de escritorio."""

from __future__ import annotations

import sys
from pathlib import Path

from onirifix.config import Settings, cargar_settings


def main(
    argv: list[str] | None = None,
    *,
    settings: Settings | None = None,
    archivo: Path | None = None,
) -> int:
    """Abre la ventana. Devuelve el código de salida de Qt."""

    from PySide6.QtWidgets import QApplication

    from onirifix.gui.tema import aplicar_tema
    from onirifix.gui.ventana import VentanaPrincipal

    argumentos = list(sys.argv if argv is None else argv)
    if archivo is None and len(argumentos) > 1 and not argumentos[1].startswith("-"):
        archivo = Path(argumentos[1])
    app = QApplication.instance() or QApplication(argumentos)
    app.setApplicationName("OniriFix")
    app.setOrganizationName("OniriFix")
    aplicar_tema(app)  # type: ignore[arg-type]
    ventana = VentanaPrincipal(settings or cargar_settings())
    ventana.show()
    if archivo is not None:
        ventana.abrir_manuscrito(archivo)
    return int(app.exec())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
