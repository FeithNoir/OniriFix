"""Resumen estadístico de los hallazgos visibles."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from onirifix.gui.revision import Estado, Resumen
from onirifix.gui.tema import COLORES
from onirifix.modelo import Nivel


class PanelEstadisticas(QWidget):
    """Cifras y barras de la vista filtrada."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.resumen = QLabel("Todavía no hay hallazgos en esta vista.")
        self.resumen.setObjectName("Muted")
        self.resumen.setWordWrap(True)
        self.barras = QVBoxLayout()
        self.barras.setSpacing(6)
        layout.addWidget(self.resumen)
        layout.addLayout(self.barras)

    def mostrar(self, resumen: Resumen, *, palabras: int = 0) -> None:
        self._limpiar()
        if resumen.total == 0:
            self.resumen.setText("Todavía no hay hallazgos en esta vista.")
            return
        densidad = (
            f"\n{resumen.total / max(palabras, 1) * 1000:.1f} por 1000 palabras" if palabras else ""
        )
        self.resumen.setText(
            f"{resumen.total} hallazgos{densidad}\n"
            f"{resumen.por_estado.get(Estado.ACEPTADO.value, 0)} aceptados · "
            f"{resumen.por_estado.get(Estado.PENDIENTE.value, 0)} pendientes · "
            f"{resumen.por_estado.get(Estado.RECHAZADO.value, 0)} rechazados"
        )
        self._titulo("Niveles")
        maximo = max(resumen.por_nivel.values(), default=1)
        for nivel in Nivel:
            self._barra(
                nivel.value, resumen.por_nivel.get(nivel.value, 0), maximo, COLORES[nivel.value]
            )
        self._titulo("Reglas")
        if resumen.por_regla:
            tope = resumen.por_regla[0][1]
            for regla, total in resumen.por_regla[:6]:
                self._barra(regla, total, tope, COLORES["acento"])
        self._titulo("Capítulos")
        if resumen.por_capitulo:
            tope = resumen.por_capitulo[0][1]
            for capitulo, total in resumen.por_capitulo[:5]:
                self._barra(capitulo, total, tope, COLORES["rechazado"])

    def _titulo(self, texto: str) -> None:
        etiqueta = QLabel(texto.upper())
        etiqueta.setObjectName("Section")
        self.barras.addWidget(etiqueta)

    def _barra(self, nombre: str, valor: int, maximo: int, color: str) -> None:
        etiqueta = QLabel(f"{nombre}  ·  {valor}")
        etiqueta.setObjectName("StatValue")
        barra = QProgressBar()
        barra.setRange(0, max(maximo, 1))
        barra.setValue(valor)
        barra.setTextVisible(False)
        barra.setFixedHeight(8)
        barra.setStyleSheet(
            "QProgressBar { background: #2a303b; border: none; border-radius: 4px; }"
            f"QProgressBar::chunk {{ background: {color}; border-radius: 4px; }}"
        )
        self.barras.addWidget(etiqueta)
        self.barras.addWidget(barra)

    def _limpiar(self) -> None:
        while self.barras.count():
            item = self.barras.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # Fuera del layout ya: se oculta para que no se pinte encima
                # de las barras nuevas mientras espera a destruirse.
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
