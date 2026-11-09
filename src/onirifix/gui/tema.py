"""Tema oscuro Fusion con la paleta de TagFlow (ámbar sobre grafito)."""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

# Paleta compartida: los componentes piden colores por rol, no por pigmento.
COLORES: dict[str, str] = {
    "fondo": "#12141a",
    "superficie": "#171a21",
    "superficie_alta": "#1c2028",
    "borde": "#2a303b",
    "texto": "#f3efe6",
    "sutil": "#9a9286",
    "tenue": "#c4bdb0",
    "acento": "#e8a54b",
    "acento_oscuro": "#1c1408",
    "peligro": "#7a3434",
    "L1": "#7eb8a8",
    "L2": "#e8a54b",
    "L3": "#b48ead",
    "aceptado": "#7eb8a8",
    "rechazado": "#c9846a",
    "pendiente": "#9a9286",
    "borrado": "#5c2f2f",
    "insertado": "#2f5c4a",
}

HOJA_DE_ESTILO = """
QWidget { color: #f3efe6; }
QMainWindow, QDialog { background: #12141a; }
QMenuBar { background: #12141a; color: #f3efe6; }
QMenuBar::item:selected { background: #2a303b; }
QMenu { background: #1c2028; border: 1px solid #2a303b; }
QMenu::item:selected { background: #e8a54b; color: #1c1408; }
QToolTip { background: #1c2028; color: #f3efe6; border: 1px solid #2a303b; }

#Header { background: #171a21; border-bottom: 1px solid #2a303b; }
#Title { font-size: 16pt; font-weight: 700; }
#Subtitle { color: #c4bdb0; }
#Muted { color: #c4bdb0; }
#Faint { color: #9a9286; }
#Section { color: #e8a54b; font-size: 8pt; font-weight: 700; letter-spacing: 1px; }
#CollapseChevron { color: #e8a54b; font-size: 8pt; }
#StatValue { color: #c4bdb0; font-size: 9pt; }
#EmptyTitle { font-size: 14pt; font-weight: 700; }
#BusyTitle { font-size: 13pt; font-weight: 700; }
#Badge { border-radius: 8px; padding: 2px 8px; font-weight: 700; font-size: 9pt; }

#Card { background: #171a21; border: 1px solid #2a303b; border-radius: 10px; }
#BusyOverlay { background: rgba(10, 12, 16, 200); }
#BusyPanel { background: #171a21; border: 1px solid #2a303b; border-radius: 14px; }
#SidebarScroll, #SidebarScroll > QWidget > QWidget { background: transparent; border: none; }

QPushButton {
    background: #2a303b; border: 1px solid #343b48; border-radius: 6px;
    padding: 6px 12px; color: #f3efe6;
}
QPushButton:hover { background: #343b48; }
QPushButton:disabled { color: #6c665d; background: #1f232b; border-color: #262b34; }
QPushButton[variant="primary"] {
    background: #e8a54b; color: #1c1408; border: none; font-weight: 700;
}
QPushButton[variant="primary"]:hover { background: #f0b45f; }
QPushButton[variant="primary"]:disabled { background: #5b4628; color: #2a2116; }
QPushButton[variant="ghost"] { background: transparent; border: none; color: #e8a54b; padding: 4px 6px; }
QPushButton[variant="ghost"]:hover { color: #f6c27a; }
QPushButton[variant="ghost"]:disabled { color: #6c665d; }
QPushButton[variant="danger"] { background: #7a3434; border: none; }
QPushButton[variant="danger"]:hover { background: #8c3d3d; }
QPushButton[variant="ok"] { background: #2f5c4a; border: none; }
QPushButton[variant="ok"]:hover { background: #3a6f5a; }

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #12151b; border: 1px solid #2a303b; border-radius: 6px; padding: 5px 7px;
}
QLineEdit:focus, QComboBox:focus { border-color: #e8a54b; }
QComboBox QAbstractItemView { background: #1c2028; selection-background-color: #e8a54b;
    selection-color: #1c1408; border: 1px solid #2a303b; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 14px; height: 14px; border-radius: 3px; border: 1px solid #4a5260;
    background: #12151b; }
QCheckBox::indicator:checked { background: #e8a54b; border-color: #e8a54b; }
QCheckBox:disabled { color: #6c665d; }

QProgressBar { background: #2a303b; border: none; border-radius: 4px; height: 8px; }
QProgressBar::chunk { background: #e8a54b; border-radius: 4px; }

QTableView {
    background: #12151b; alternate-background-color: #161a21; border: 1px solid #2a303b;
    border-radius: 8px; gridline-color: transparent; selection-background-color: #3a3122;
    selection-color: #f3efe6;
}
QHeaderView::section { background: #171a21; color: #9a9286; border: none;
    border-bottom: 1px solid #2a303b; padding: 6px; font-weight: 700; }
QTextBrowser, QPlainTextEdit { background: #12151b; border: 1px solid #2a303b; border-radius: 8px;
    padding: 6px; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #2a303b; border-radius: 4px; min-height: 30px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #2a303b; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
"""


def aplicar_tema(app: QApplication) -> None:
    """Aplica Fusion, la paleta oscura y la hoja de estilo."""

    app.setStyle("Fusion")
    fuente = QFont()
    fuente.setFamilies(["Segoe UI", "Noto Sans", "DejaVu Sans"])
    fuente.setPointSize(10)
    app.setFont(fuente)
    paleta = QPalette()
    paleta.setColor(QPalette.ColorRole.Window, QColor(COLORES["fondo"]))
    paleta.setColor(QPalette.ColorRole.WindowText, QColor(COLORES["texto"]))
    paleta.setColor(QPalette.ColorRole.Base, QColor("#12151b"))
    paleta.setColor(QPalette.ColorRole.AlternateBase, QColor(COLORES["superficie_alta"]))
    paleta.setColor(QPalette.ColorRole.Text, QColor(COLORES["texto"]))
    paleta.setColor(QPalette.ColorRole.Button, QColor(COLORES["borde"]))
    paleta.setColor(QPalette.ColorRole.ButtonText, QColor(COLORES["texto"]))
    paleta.setColor(QPalette.ColorRole.Highlight, QColor(COLORES["acento"]))
    paleta.setColor(QPalette.ColorRole.HighlightedText, QColor(COLORES["acento_oscuro"]))
    paleta.setColor(QPalette.ColorRole.ToolTipBase, QColor(COLORES["superficie_alta"]))
    paleta.setColor(QPalette.ColorRole.ToolTipText, QColor(COLORES["texto"]))
    paleta.setColor(QPalette.ColorRole.PlaceholderText, QColor(COLORES["sutil"]))
    app.setPalette(paleta)
    app.setStyleSheet(HOJA_DE_ESTILO)
