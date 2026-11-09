"""Diálogos: registro de la sesión y confirmación de escritura."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


class DialogoRegistro(QDialog):
    """Mensajes de la sesión: análisis, escrituras, copias y errores."""

    def __init__(self, lineas: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Registro de la sesión")
        self.resize(720, 420)
        layout = QVBoxLayout(self)
        titulo = QLabel("Registro de la sesión")
        titulo.setObjectName("EmptyTitle")
        texto = QPlainTextEdit()
        texto.setReadOnly(True)
        texto.setPlainText("\n".join(lineas) if lineas else "Todavía no hay mensajes.")
        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        botones.rejected.connect(self.reject)
        botones.accepted.connect(self.accept)
        layout.addWidget(titulo)
        layout.addWidget(texto, 1)
        layout.addWidget(botones)
