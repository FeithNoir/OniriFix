"""Indicador de actividad dibujado a mano, sin depender de GIFs."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from onirifix.gui.tema import COLORES


class Spinner(QWidget):
    """Arco que gira mientras una tarea larga está en curso."""

    def __init__(self, tamano: int = 56, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._angulo = 0
        self.setFixedSize(tamano, tamano)
        self._timer = QTimer(self)
        self._timer.setInterval(28)
        self._timer.timeout.connect(self._avanzar)

    def iniciar(self) -> None:
        if not self._timer.isActive():
            self._timer.start()
        self.show()

    def detener(self) -> None:
        self._timer.stop()

    def _avanzar(self) -> None:
        self._angulo = (self._angulo + 10) % 360
        self.update()

    def paintEvent(self, _event) -> None:  # type: ignore[no-untyped-def]
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        margen = 5
        rect = self.rect().adjusted(margen, margen, -margen, -margen)
        pista = QPen(QColor(COLORES["borde"]), 4)
        pista.setCapStyle(Qt.PenCapStyle.RoundCap)
        pintor.setPen(pista)
        pintor.drawArc(rect, 0, 360 * 16)
        arco = QPen(QColor(COLORES["acento"]), 4)
        arco.setCapStyle(Qt.PenCapStyle.RoundCap)
        pintor.setPen(arco)
        pintor.drawArc(rect, -self._angulo * 16, 110 * 16)
