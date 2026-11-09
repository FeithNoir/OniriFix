"""Texto completo del manuscrito con salto y resaltado del hallazgo activo."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor, QTextOption
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from onirifix.gui.tema import COLORES
from onirifix.modelo import Documento, Hallazgo


def _corto(texto: str, maximo: int = 50) -> str:
    limpio = " ".join(texto.replace("\n", " ⏎ ").split())
    return limpio if len(limpio) <= maximo else limpio[: maximo - 1] + "…"


class _Utf16:
    """Convierte offsets de Python (puntos de código) a offsets de Qt (UTF-16)."""

    def __init__(self, texto: str) -> None:
        self._astrales = [i for i, c in enumerate(texto) if ord(c) > 0xFFFF]

    def __call__(self, indice: int) -> int:
        if not self._astrales:
            return indice
        from bisect import bisect_left

        return indice + bisect_left(self._astrales, indice)


class VistaTexto(QWidget):
    """Lector de solo lectura. El texto se carga perezosamente al mostrarse."""

    capitulo_elegido = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        fila = QHBoxLayout()
        self.etiqueta = QLabel("Selecciona un hallazgo para verlo en su sitio.")
        self.etiqueta.setObjectName("Muted")
        self.capitulos = QComboBox()
        self.capitulos.setMinimumWidth(220)
        self.capitulos.setToolTip("Saltar al inicio de un capítulo")
        self.capitulos.activated.connect(self._ir_a_capitulo)
        fila.addWidget(self.etiqueta, 1)
        fila.addWidget(QLabel("Ir a"))
        fila.addWidget(self.capitulos)
        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.editor.setObjectName("VistaTexto")
        layout.addLayout(fila)
        layout.addWidget(self.editor, 1)
        self._documento: Documento | None = None
        self._cargado: Documento | None = None
        self._utf16 = _Utf16("")
        self._pendiente: Hallazgo | None = None

    # -- datos ------------------------------------------------------------

    def fijar_documento(self, documento: Documento | None) -> None:
        """Recuerda el documento; el texto se vuelca solo cuando hace falta."""

        self._documento = documento
        self.capitulos.clear()
        if documento is not None:
            for capitulo in documento.capitulos:
                self.capitulos.addItem(capitulo.titulo, capitulo.inicio)
        if self.isVisible():
            self._asegurar_texto()

    def _asegurar_texto(self) -> None:
        if self._documento is None or self._cargado is self._documento:
            return
        self.editor.setPlainText(self._documento.texto)
        self._utf16 = _Utf16(self._documento.texto)
        self._cargado = self._documento

    def showEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().showEvent(event)
        self._asegurar_texto()
        if self._pendiente is not None:
            self.resaltar(self._pendiente)

    # -- navegación -------------------------------------------------------

    def resaltar(self, hallazgo: Hallazgo | None, *, titulo: str = "") -> None:
        self._pendiente = hallazgo
        if hallazgo is None or not self.isVisible():
            return
        self._asegurar_texto()
        inicio, fin = self._utf16(hallazgo.inicio), self._utf16(hallazgo.fin)
        cursor = QTextCursor(self.editor.document())
        cursor.setPosition(inicio)
        cursor.setPosition(max(fin, inicio + 1), QTextCursor.MoveMode.KeepAnchor)
        seleccion = QTextEdit.ExtraSelection()
        formato = QTextCharFormat()
        formato.setBackground(QColor(COLORES.get("acento", "#f2b84b")))
        formato.setForeground(QColor("#1b1626"))
        seleccion.format = formato
        seleccion.cursor = cursor
        self.editor.setExtraSelections([seleccion])
        # Centra la línea: primero al final del bloque y luego al hallazgo.
        destino = QTextCursor(self.editor.document())
        destino.setPosition(inicio)
        self.editor.setTextCursor(destino)
        self.editor.centerCursor()
        sugerencia = "" if hallazgo.sugerencia is None else f" → «{_corto(hallazgo.sugerencia)}»"
        self.etiqueta.setText(
            f"{hallazgo.regla} · línea {hallazgo.linea}"
            + (f" · {titulo}" if titulo else "")
            + f" · «{_corto(hallazgo.original)}»{sugerencia}"
        )

    def _ir_a_capitulo(self, fila: int) -> None:
        inicio = self.capitulos.itemData(fila)
        if inicio is None:
            return
        self._asegurar_texto()
        cursor = QTextCursor(self.editor.document())
        cursor.setPosition(self._utf16(int(inicio)))
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()
        # Lleva el capítulo arriba del todo.
        barra = self.editor.verticalScrollBar()
        barra.setValue(barra.maximum())
        self.editor.ensureCursorVisible()
        self.capitulo_elegido.emit(self.capitulos.itemText(fila))
