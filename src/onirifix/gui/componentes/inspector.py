"""Detalle del hallazgo activo: regla, nota y vista previa antes/después."""

from __future__ import annotations

import html

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from onirifix.gui.revision import Estado
from onirifix.gui.tema import COLORES
from onirifix.modelo import Hallazgo, Nivel

_RADIO = 140


def _ventana(texto: str, inicio: int, fin: int) -> tuple[int, int]:
    """Amplía el contexto hasta un límite de palabra para no cortar a medias."""

    desde = max(0, inicio - _RADIO)
    hasta = min(len(texto), fin + _RADIO)
    while desde > 0 and not texto[desde - 1].isspace() and inicio - desde < _RADIO + 30:
        desde -= 1
    while hasta < len(texto) and not texto[hasta].isspace() and hasta - fin < _RADIO + 30:
        hasta += 1
    return desde, hasta


def _fragmento(texto: str) -> str:
    return html.escape(texto).replace("\n", "<br>")


def vista_previa(texto: str, hallazgo: Hallazgo) -> tuple[str, str]:
    """HTML «antes» (original tachado) y «después» (sugerencia resaltada)."""

    desde, hasta = _ventana(texto, hallazgo.inicio, hallazgo.fin)
    prefijo = ("…" if desde > 0 else "") + texto[desde : hallazgo.inicio]
    sufijo = texto[hallazgo.fin : hasta] + ("…" if hasta < len(texto) else "")
    original = hallazgo.original if hallazgo.original.strip() else "␣" * len(hallazgo.original)
    antes = (
        f"{_fragmento(prefijo)}<span style='background:{COLORES['borrado']};"
        f"color:#ffd9d2;text-decoration:line-through'>{_fragmento(original)}</span>"
        f"{_fragmento(sufijo)}"
    )
    if hallazgo.sugerencia is None:
        despues = ""
    else:
        sugerencia = hallazgo.sugerencia
        visible = (
            _fragmento(sugerencia)
            if sugerencia.strip()
            else ("<i>(se borra)</i>" if sugerencia == "" else "␣" * len(sugerencia))
        )
        despues = (
            f"{_fragmento(prefijo)}<span style='background:{COLORES['insertado']};"
            f"color:#d8fff0'>{visible}</span>{_fragmento(sufijo)}"
        )
    return antes, despues


class Inspector(QWidget):
    """Panel derecho. Emite ``decision`` con el estado elegido."""

    decision = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.vacio = QLabel("Selecciona un hallazgo para ver el contexto y decidir.")
        self.vacio.setObjectName("Muted")
        self.vacio.setWordWrap(True)
        self.cabecera = QLabel()
        self.cabecera.setTextFormat(Qt.TextFormat.RichText)
        self.descripcion = QLabel()
        self.descripcion.setWordWrap(True)
        self.descripcion.setObjectName("Muted")
        self.ubicacion = QLabel()
        self.ubicacion.setObjectName("Faint")
        self.ubicacion.setWordWrap(True)
        self.confianza = QProgressBar()
        self.confianza.setRange(0, 100)
        self.confianza.setTextVisible(False)
        self.confianza.setFixedHeight(6)
        self.nota = QLabel()
        self.nota.setWordWrap(True)
        self.nota.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.rotulo_antes = QLabel("ANTES")
        self.rotulo_antes.setObjectName("Section")
        self.antes = QTextBrowser()
        self.antes.setMinimumHeight(110)
        self.rotulo_despues = QLabel("DESPUÉS")
        self.rotulo_despues.setObjectName("Section")
        self.despues = QTextBrowser()
        self.despues.setMinimumHeight(110)
        self.aviso = QLabel("Solo aviso (L3): OniriFix no cambia este texto. Decide tú al revisar.")
        self.aviso.setWordWrap(True)
        self.aviso.setStyleSheet(f"color: {COLORES['L3']};")
        botones = QHBoxLayout()
        self.boton_aceptar = QPushButton("Aceptar")
        self.boton_aceptar.setProperty("variant", "ok")
        self.boton_aceptar.clicked.connect(lambda: self.decision.emit(Estado.ACEPTADO))
        self.boton_rechazar = QPushButton("Rechazar")
        self.boton_rechazar.setProperty("variant", "danger")
        self.boton_rechazar.clicked.connect(lambda: self.decision.emit(Estado.RECHAZADO))
        botones.addWidget(self.boton_aceptar)
        botones.addWidget(self.boton_rechazar)
        for widget in (
            self.vacio,
            self.cabecera,
            self.descripcion,
            self.ubicacion,
            self.confianza,
            self.nota,
            self.rotulo_antes,
            self.antes,
            self.rotulo_despues,
            self.despues,
            self.aviso,
        ):
            layout.addWidget(widget)
        layout.addLayout(botones)
        layout.addStretch(1)
        self._detalle = [
            self.cabecera,
            self.descripcion,
            self.ubicacion,
            self.confianza,
            self.nota,
            self.rotulo_antes,
            self.antes,
            self.rotulo_despues,
            self.despues,
            self.aviso,
            self.boton_aceptar,
            self.boton_rechazar,
        ]
        self.limpiar()

    def limpiar(self) -> None:
        self.vacio.show()
        for widget in self._detalle:
            widget.hide()

    def mostrar(
        self,
        hallazgo: Hallazgo,
        *,
        estado: Estado,
        texto: str,
        descripcion: str,
        capitulo: str,
    ) -> None:
        self.vacio.hide()
        for widget in self._detalle:
            widget.show()
        color_nivel = COLORES[hallazgo.nivel.value]
        color_estado = COLORES[estado.value if estado != Estado.AVISO else "L3"]
        self.cabecera.setText(
            f"<span style='font-size:13pt;font-weight:700'>{html.escape(hallazgo.regla)}</span>"
            f"&nbsp;&nbsp;<span style='color:{color_nivel};font-weight:700'>"
            f"{hallazgo.nivel.value}</span>&nbsp;&nbsp;"
            f"<span style='color:{color_estado}'>{estado.etiqueta}</span>"
        )
        self.descripcion.setText(descripcion)
        lugar = f"Línea {hallazgo.linea}, columna {hallazgo.columna}"
        if capitulo:
            lugar += f" · {capitulo}"
        self.ubicacion.setText(f"{lugar} · confianza {hallazgo.confianza:.2f}")
        self.confianza.setValue(round(hallazgo.confianza * 100))
        self.confianza.setStyleSheet(
            "QProgressBar { background: #2a303b; border: none; border-radius: 3px; }"
            f"QProgressBar::chunk {{ background: {color_nivel}; border-radius: 3px; }}"
        )
        self.nota.setText(hallazgo.nota or "")
        antes, despues = vista_previa(texto, hallazgo)
        self.antes.setHtml(antes)
        es_aviso = estado == Estado.AVISO
        self.rotulo_antes.setText("CONTEXTO" if es_aviso else "ANTES")
        self.despues.setHtml(despues)
        self.despues.setVisible(not es_aviso)
        self.rotulo_despues.setVisible(not es_aviso)
        self.aviso.setVisible(es_aviso or hallazgo.nivel == Nivel.L3)
        self.boton_aceptar.setVisible(not es_aviso)
        self.boton_rechazar.setVisible(not es_aviso)
        self.boton_aceptar.setEnabled(estado != Estado.ACEPTADO)
        self.boton_rechazar.setEnabled(estado != Estado.RECHAZADO)
