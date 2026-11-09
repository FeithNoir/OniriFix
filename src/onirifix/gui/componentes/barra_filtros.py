"""Filtros de la lista de hallazgos: nivel, regla, capítulo, estado y texto."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QComboBox, QLabel, QLineEdit, QVBoxLayout, QWidget

from onirifix.gui.revision import TODOS, Estado, Filtro
from onirifix.modelo import Nivel


class BarraFiltros(QWidget):
    """Controles apilados al estilo de TagFlow. Emite ``cambiado``."""

    cambiado = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.texto = QLineEdit()
        self.texto.setPlaceholderText("Buscar en original, sugerencia o nota")
        self.texto.setClearButtonEnabled(True)
        self.nivel = QComboBox()
        self.nivel.addItem("Todos los niveles", TODOS)
        for nivel in Nivel:
            self.nivel.addItem(f"{nivel.value} · {nivel.etiqueta}", nivel.value)
        self.estado = QComboBox()
        self.estado.addItem("Cualquier estado", TODOS)
        for estado in Estado:
            self.estado.addItem(estado.etiqueta, estado.value)
        self.regla = QComboBox()
        self.capitulo = QComboBox()
        self.cargar_opciones([], [])
        for rotulo, control in (
            ("Buscar", self.texto),
            ("Nivel", self.nivel),
            ("Estado", self.estado),
            ("Regla", self.regla),
            ("Capítulo", self.capitulo),
        ):
            etiqueta = QLabel(rotulo)
            layout.addWidget(etiqueta)
            layout.addWidget(control)
        # La búsqueda espera a que se deje de escribir para no filtrar por tecla.
        self._retraso = QTimer(self)
        self._retraso.setSingleShot(True)
        self._retraso.setInterval(220)
        self._retraso.timeout.connect(self.cambiado.emit)
        self.texto.textChanged.connect(lambda _t: self._retraso.start())
        for combo in (self.nivel, self.estado, self.regla, self.capitulo):
            combo.currentIndexChanged.connect(lambda _i: self.cambiado.emit())

    def cargar_opciones(self, reglas: list[str], capitulos: list[str]) -> None:
        for combo, todos, valores in (
            (self.regla, "Todas las reglas", reglas),
            (self.capitulo, "Todos los capítulos", capitulos),
        ):
            actual = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(todos, TODOS)
            for valor in valores:
                combo.addItem(valor, valor)
            indice = combo.findData(actual)
            combo.setCurrentIndex(indice if indice >= 0 else 0)
            combo.blockSignals(False)

    def filtro(self) -> Filtro:
        return Filtro(
            nivel=self.nivel.currentData() or TODOS,
            regla=self.regla.currentData() or TODOS,
            capitulo=self.capitulo.currentData() or TODOS,
            estado=self.estado.currentData() or TODOS,
            texto=self.texto.text(),
        )

    def fijar(self, **valores: str) -> None:
        """Atajo para pruebas y capturas: ``fijar(nivel="L2")``."""

        for nombre, valor in valores.items():
            if nombre == "texto":
                self.texto.setText(valor)
                continue
            combo: QComboBox = getattr(self, nombre)
            indice = combo.findData(valor)
            if indice >= 0:
                combo.setCurrentIndex(indice)
        self.cambiado.emit()

    def limpiar(self) -> None:
        for combo in (self.nivel, self.estado, self.regla, self.capitulo):
            combo.setCurrentIndex(0)
        self.texto.clear()
