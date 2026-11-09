"""Secciones del panel lateral que se pueden plegar y desplegar."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class SeccionPlegable(QFrame):
    """Tarjeta con cabecera clicable. Emite ``cambiada`` al plegarse o desplegarse."""

    cambiada = Signal(str, bool)

    def __init__(
        self,
        clave: str,
        titulo: str,
        contenido: QWidget,
        *,
        abierta: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.clave = clave
        self._abierta = abierta
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)
        cabecera = QFrame()
        cabecera.setObjectName("CollapseHeader")
        cabecera.setCursor(Qt.CursorShape.PointingHandCursor)
        fila = QHBoxLayout(cabecera)
        fila.setContentsMargins(0, 2, 0, 2)
        fila.setSpacing(8)
        self.chevron = QLabel("▾")
        self.chevron.setObjectName("CollapseChevron")
        self.chevron.setFixedWidth(14)
        rotulo = QLabel(titulo.upper())
        rotulo.setObjectName("Section")
        fila.addWidget(self.chevron)
        fila.addWidget(rotulo, 1)
        self.cuerpo = QWidget()
        cuerpo = QVBoxLayout(self.cuerpo)
        cuerpo.setContentsMargins(0, 0, 0, 0)
        cuerpo.setSpacing(0)
        cuerpo.addWidget(contenido)
        layout.addWidget(cabecera)
        layout.addWidget(self.cuerpo)
        self._cabecera = cabecera
        cabecera.mousePressEvent = self._pulsada  # type: ignore[method-assign]
        self.abrir(abierta, emitir=False)

    def _pulsada(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.LeftButton:
            self.alternar()
            event.accept()
            return
        QFrame.mousePressEvent(self._cabecera, event)

    def esta_abierta(self) -> bool:
        return self._abierta

    def alternar(self) -> None:
        self.abrir(not self._abierta)

    def abrir(self, abierta: bool, *, emitir: bool = True) -> None:
        self._abierta = abierta
        self.cuerpo.setVisible(abierta)
        self.chevron.setText("▾" if abierta else "▸")
        self.setProperty("collapsed", not abierta)
        self.style().unpolish(self)
        self.style().polish(self)
        if emitir:
            self.cambiada.emit(self.clave, abierta)
