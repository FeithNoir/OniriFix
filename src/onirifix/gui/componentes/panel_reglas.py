"""Elección de niveles y reglas que entran en el análisis."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from onirifix.gui.tema import COLORES
from onirifix.modelo import Nivel, Regla


class PanelReglas(QWidget):
    """Casillas L1/L2/L3 y un árbol de reglas agrupadas por nivel."""

    cambiado = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        niveles = QHBoxLayout()
        self.casillas: dict[Nivel, QCheckBox] = {}
        for nivel in Nivel:
            casilla = QCheckBox(nivel.value)
            casilla.setChecked(True)
            casilla.setToolTip(nivel.etiqueta)
            casilla.toggled.connect(self._nivel_cambiado)
            self.casillas[nivel] = casilla
            niveles.addWidget(casilla)
        niveles.addStretch(1)
        ayuda = QLabel("L1 mecánico · L2 asistido · L3 solo aviso")
        ayuda.setObjectName("Faint")
        self.arbol = QTreeWidget()
        self.arbol.setHeaderHidden(True)
        self.arbol.setRootIsDecorated(True)
        self.arbol.setMinimumHeight(220)
        self.arbol.setStyleSheet(
            "QTreeWidget { background: #12151b; border: 1px solid #2a303b; border-radius: 6px; }"
        )
        self.arbol.itemChanged.connect(self._item_cambiado)
        botones = QHBoxLayout()
        todas = QPushButton("Todas")
        todas.setProperty("variant", "ghost")
        todas.clicked.connect(lambda: self.marcar_todas(True))
        ninguna = QPushButton("Ninguna")
        ninguna.setProperty("variant", "ghost")
        ninguna.clicked.connect(lambda: self.marcar_todas(False))
        defecto = QPushButton("Por defecto")
        defecto.setProperty("variant", "ghost")
        defecto.clicked.connect(self.restaurar)
        botones.addWidget(todas)
        botones.addWidget(ninguna)
        botones.addWidget(defecto)
        botones.addStretch(1)
        self.resumen = QLabel("")
        self.resumen.setObjectName("Muted")
        layout.addLayout(niveles)
        layout.addWidget(ayuda)
        layout.addWidget(self.arbol)
        layout.addLayout(botones)
        layout.addWidget(self.resumen)
        self._grupos: dict[Nivel, QTreeWidgetItem] = {}
        self._items: dict[str, QTreeWidgetItem] = {}
        self._defecto: dict[str, bool] = {}
        self._silencio = False

    def cargar(self, catalogo: list[tuple[Regla, bool]]) -> None:
        self._silencio = True
        self.arbol.clear()
        self._grupos.clear()
        self._items.clear()
        self._defecto = {regla.id: activa for regla, activa in catalogo}
        for nivel in Nivel:
            grupo = QTreeWidgetItem([f"{nivel.value} · {nivel.etiqueta}"])
            grupo.setForeground(0, _color(COLORES[nivel.value]))
            grupo.setFlags(grupo.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.arbol.addTopLevelItem(grupo)
            self._grupos[nivel] = grupo
        for regla, activa in sorted(catalogo, key=lambda par: par[0].id):
            item = QTreeWidgetItem([regla.id])
            item.setToolTip(0, regla.descripcion)
            item.setData(0, Qt.ItemDataRole.UserRole, regla.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Checked if activa else Qt.CheckState.Unchecked)
            item.setText(0, f"{regla.id}  {regla.descripcion}")
            self._grupos[regla.nivel].addChild(item)
            self._items[regla.id] = item
        for grupo in self._grupos.values():
            grupo.setExpanded(False)
        self._silencio = False
        self._actualizar_resumen()

    def seleccion(self) -> list[str]:
        """IDs de reglas marcadas cuyo nivel también está marcado."""

        elegidas: list[str] = []
        for nivel, grupo in self._grupos.items():
            if not self.casillas[nivel].isChecked():
                continue
            for indice in range(grupo.childCount()):
                item = grupo.child(indice)
                if item.checkState(0) == Qt.CheckState.Checked:
                    elegidas.append(str(item.data(0, Qt.ItemDataRole.UserRole)))
        return elegidas

    def marcar_todas(self, marcar: bool) -> None:
        self._silencio = True
        for item in self._items.values():
            item.setCheckState(0, Qt.CheckState.Checked if marcar else Qt.CheckState.Unchecked)
        self._silencio = False
        self._actualizar_resumen()
        self.cambiado.emit()

    def restaurar(self) -> None:
        self._silencio = True
        for regla_id, item in self._items.items():
            activa = self._defecto.get(regla_id, True)
            item.setCheckState(0, Qt.CheckState.Checked if activa else Qt.CheckState.Unchecked)
        for casilla in self.casillas.values():
            casilla.setChecked(True)
        self._silencio = False
        self._actualizar_resumen()
        self.cambiado.emit()

    def desplegar(self, nivel: Nivel) -> None:
        self._grupos[nivel].setExpanded(True)

    def _nivel_cambiado(self, _marcado: bool) -> None:
        for nivel, grupo in self._grupos.items():
            grupo.setDisabled(not self.casillas[nivel].isChecked())
        self._actualizar_resumen()
        self.cambiado.emit()

    def _item_cambiado(self, _item: QTreeWidgetItem, _columna: int) -> None:
        if self._silencio:
            return
        self._actualizar_resumen()
        self.cambiado.emit()

    def _actualizar_resumen(self) -> None:
        total = len(self._items)
        elegidas = len(self.seleccion())
        self.resumen.setText(f"{elegidas} de {total} reglas en el próximo análisis")


def _color(hex_color: str):  # type: ignore[no-untyped-def]
    from PySide6.QtGui import QBrush, QColor

    return QBrush(QColor(hex_color))
