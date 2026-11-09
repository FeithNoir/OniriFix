"""Tabla de hallazgos con casilla de aceptación por fila."""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableView

from onirifix.gui.revision import Estado, SesionRevision
from onirifix.gui.tema import COLORES

_Indice = QModelIndex | QPersistentModelIndex

COLUMNAS = ("Estado", "Nivel", "Regla", "Línea", "Capítulo", "Original", "Sugerencia", "Conf.")


def _visible(texto: str | None, maximo: int = 60) -> str:
    if texto is None:
        return "—"
    if texto == "":
        return "∅ (borrar)"
    limpio = texto.replace("\n", " ⏎ ").replace("\t", " ")
    if not limpio.strip():
        return repr(texto)
    return limpio if len(limpio) <= maximo else limpio[: maximo - 1] + "…"


class ModeloHallazgos(QAbstractTableModel):
    """Vista de los índices filtrados de una ``SesionRevision``."""

    decisiones_cambiadas = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.sesion: SesionRevision | None = None
        self.indices: list[int] = []

    def cargar(self, sesion: SesionRevision | None, indices: list[int]) -> None:
        self.beginResetModel()
        self.sesion = sesion
        self.indices = list(indices)
        self.endResetModel()

    def rowCount(self, parent: _Indice = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self.indices)

    def columnCount(self, parent: _Indice = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(COLUMNAS)

    def headerData(
        self, seccion: int, orientacion: Qt.Orientation, rol: int = Qt.ItemDataRole.DisplayRole
    ):  # type: ignore[no-untyped-def]
        if orientacion == Qt.Orientation.Horizontal and rol == Qt.ItemDataRole.DisplayRole:
            return COLUMNAS[seccion]
        return None

    def indice_sesion(self, fila: int) -> int:
        return self.indices[fila]

    def fila_de(self, indice_sesion: int) -> int:
        try:
            return self.indices.index(indice_sesion)
        except ValueError:
            return -1

    def flags(self, index: _Indice) -> Qt.ItemFlag:
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if (
            index.column() == 0
            and self.sesion is not None
            and self.sesion.estados[self.indices[index.row()]] != Estado.AVISO
        ):
            base |= Qt.ItemFlag.ItemIsUserCheckable
        return base

    def data(self, index: _Indice, rol: int = Qt.ItemDataRole.DisplayRole):  # type: ignore[no-untyped-def]
        if self.sesion is None or not index.isValid():
            return None
        i = self.indices[index.row()]
        hallazgo = self.sesion.hallazgos[i]
        estado = self.sesion.estados[i]
        columna = index.column()
        if rol == Qt.ItemDataRole.DisplayRole:
            return (
                estado.etiqueta,
                hallazgo.nivel.value,
                hallazgo.regla,
                str(hallazgo.linea),
                self.sesion.capitulo(i),
                _visible(hallazgo.original),
                _visible(hallazgo.sugerencia),
                f"{hallazgo.confianza:.2f}",
            )[columna]
        if rol == Qt.ItemDataRole.CheckStateRole and columna == 0 and estado != Estado.AVISO:
            return Qt.CheckState.Checked if estado == Estado.ACEPTADO else Qt.CheckState.Unchecked
        if rol == Qt.ItemDataRole.ForegroundRole:
            if columna == 0:
                return QBrush(QColor(COLORES[estado.value if estado != Estado.AVISO else "L3"]))
            if columna == 1:
                return QBrush(QColor(COLORES[hallazgo.nivel.value]))
            if columna == 5 and hallazgo.sugerencia is not None:
                return QBrush(QColor("#e0a39a"))
            if columna == 6:
                return QBrush(QColor("#9fd3bf"))
        if rol == Qt.ItemDataRole.ToolTipRole:
            descripcion = self.sesion.descripcion(hallazgo.regla)
            return f"{hallazgo.regla}: {descripcion}\n{hallazgo.nota}".strip()
        if rol == Qt.ItemDataRole.TextAlignmentRole and columna in (1, 3, 7):
            return int(Qt.AlignmentFlag.AlignCenter)
        return None

    def setData(self, index: _Indice, valor, rol: int = Qt.ItemDataRole.EditRole) -> bool:  # type: ignore[no-untyped-def]
        if self.sesion is None or rol != Qt.ItemDataRole.CheckStateRole or index.column() != 0:
            return False
        marcado = Qt.CheckState(valor) == Qt.CheckState.Checked
        i = self.indices[index.row()]
        cambiados = self.sesion.decidir(i, Estado.ACEPTADO if marcado else Estado.RECHAZADO)
        if cambiados:
            self.refrescar_filas([index.row()])
            self.decisiones_cambiadas.emit()
        return bool(cambiados)

    def refrescar_filas(self, filas: list[int] | None = None) -> None:
        if not self.indices:
            return
        if filas is None:
            filas = [0, len(self.indices) - 1]
        self.dataChanged.emit(self.index(min(filas), 0), self.index(max(filas), len(COLUMNAS) - 1))


class TablaHallazgos(QTableView):
    """Tabla con selección múltiple. Emite el índice de sesión de la fila activa."""

    activo = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.modelo = ModeloHallazgos()
        self.setModel(self.modelo)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(28)
        cabecera = self.horizontalHeader()
        cabecera.setHighlightSections(False)
        for columna, ancho in enumerate((112, 48, 74, 54, 120, 0, 0, 50)):
            if ancho:
                cabecera.setSectionResizeMode(columna, QHeaderView.ResizeMode.Interactive)
                self.setColumnWidth(columna, ancho)
            else:
                cabecera.setSectionResizeMode(columna, QHeaderView.ResizeMode.Stretch)
        self.selectionModel().currentRowChanged.connect(self._fila_actual)

    def cargar(self, sesion: SesionRevision | None, indices: list[int]) -> None:
        actual = self.indice_actual()
        self.modelo.cargar(sesion, indices)
        fila = self.modelo.fila_de(actual) if actual is not None else -1
        if fila < 0 and indices:
            fila = 0
        if fila >= 0:
            self.selectRow(fila)
        else:
            self.activo.emit(None)

    def indice_actual(self) -> int | None:
        fila = self.currentIndex().row()
        if fila < 0 or fila >= len(self.modelo.indices):
            return None
        return self.modelo.indice_sesion(fila)

    def indices_seleccionados(self) -> list[int]:
        filas = sorted({indice.row() for indice in self.selectionModel().selectedRows()})
        return [self.modelo.indice_sesion(fila) for fila in filas]

    def _fila_actual(self, actual: QModelIndex, _previo: QModelIndex) -> None:
        if not actual.isValid():
            self.activo.emit(None)
            return
        self.activo.emit(self.modelo.indice_sesion(actual.row()))
