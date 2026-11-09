"""Capa que cubre el área de trabajo mientras corre un análisis o una escritura."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QProgressBar, QVBoxLayout, QWidget

from onirifix.gui.componentes.spinner import Spinner


class CapaOcupado(QFrame):
    """Oscurece el panel central, bloquea clics y explica qué está pasando."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("BusyOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.hide()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.addStretch(1)
        panel = QFrame()
        panel.setObjectName("BusyPanel")
        panel.setMaximumWidth(420)
        interior = QVBoxLayout(panel)
        interior.setContentsMargins(28, 28, 28, 28)
        interior.setSpacing(14)
        self.spinner = Spinner(52)
        self.titulo = QLabel("Trabajando…")
        self.titulo.setObjectName("BusyTitle")
        self.titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detalle = QLabel("")
        self.detalle.setObjectName("Muted")
        self.detalle.setWordWrap(True)
        self.detalle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progreso = QProgressBar()
        self.progreso.setTextVisible(False)
        self.progreso.setFixedHeight(8)
        self.pista = QLabel("Las demás acciones quedan en pausa hasta que termine.")
        self.pista.setObjectName("Muted")
        self.pista.setWordWrap(True)
        self.pista.setAlignment(Qt.AlignmentFlag.AlignCenter)
        interior.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignCenter)
        interior.addWidget(self.titulo)
        interior.addWidget(self.detalle)
        interior.addWidget(self.progreso)
        interior.addWidget(self.pista)
        layout.addWidget(panel, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)

    def mostrar(self, titulo: str, detalle: str = "") -> None:
        self.titulo.setText(titulo)
        self.detalle.setText(detalle)
        self.progreso.setRange(0, 0)
        self.spinner.iniciar()
        self.show()
        self.raise_()

    def progreso_en(self, actual: int, total: int, detalle: str | None = None) -> None:
        if total <= 0:
            self.progreso.setRange(0, 0)
        else:
            self.progreso.setRange(0, total)
            self.progreso.setValue(min(actual, total))
        if detalle is not None:
            self.detalle.setText(detalle)

    def ocultar(self) -> None:
        self.spinner.detener()
        self.hide()
