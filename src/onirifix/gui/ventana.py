"""Ventana principal de OniriFix: abrir, analizar, revisar, aplicar y exportar."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtGui import QAction, QColor, QFontMetrics, QIcon, QKeySequence, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from onirifix import __version__
from onirifix.config import Configuracion, Settings, cargar_settings
from onirifix.db.repositorios import Registro
from onirifix.gui.componentes.barra_filtros import BarraFiltros
from onirifix.gui.componentes.capa_ocupado import CapaOcupado
from onirifix.gui.componentes.dialogos import DialogoRegistro
from onirifix.gui.componentes.inspector import Inspector
from onirifix.gui.componentes.panel_estadisticas import PanelEstadisticas
from onirifix.gui.componentes.panel_reglas import PanelReglas
from onirifix.gui.componentes.plegable import SeccionPlegable
from onirifix.gui.componentes.tabla_hallazgos import TablaHallazgos
from onirifix.gui.revision import Estado, Resumen, SesionRevision
from onirifix.gui.tema import COLORES
from onirifix.gui.trabajadores import TrabajadorAnalisis, TrabajadorAplicar, TrabajadorExportar
from onirifix.io.cargadores import SUFIJOS_DOCX, SUFIJOS_TEXTO
from onirifix.modelo import ResultadoAnalisis, ResultadoCorreccion
from onirifix.servicio import catalogo_reglas

log = logging.getLogger(__name__)

FILTRO_ARCHIVOS = (
    "Manuscritos ("
    + " ".join(f"*{sufijo}" for sufijo in sorted(SUFIJOS_TEXTO | SUFIJOS_DOCX))
    + ");;Todos los archivos (*)"
)


class _Marca(QWidget):
    """Marca de OniriFix: una luna creciente ámbar, dibujada sin archivos."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(38, 38)

    def paintEvent(self, _event) -> None:  # type: ignore[no-untyped-def]
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        pintor.setPen(Qt.PenStyle.NoPen)
        pintor.setBrush(QColor(COLORES["acento"]))
        pintor.drawEllipse(1, 1, 36, 36)
        pintor.setBrush(QColor(COLORES["superficie"]))
        pintor.drawEllipse(10, 4, 28, 28)
        pintor.setPen(QPen(QColor(COLORES["acento"]), 1.4))
        pintor.setBrush(Qt.BrushStyle.NoBrush)
        pintor.drawEllipse(5, 5, 28, 28)


class _Anfitrion(QWidget):
    """Contenedor central: mantiene la capa de ocupado encima del trabajo."""

    capa: CapaOcupado | None = None

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        if self.capa is not None:
            self.capa.setGeometry(self.rect())
            self.capa.raise_()


class VentanaPrincipal(QMainWindow):
    """Revisión de un manuscrito con el motor de OniriFix."""

    analisis_listo = Signal(object)
    cambios_aplicados = Signal(object)
    informe_exportado = Signal(object)
    error_mostrado = Signal(str)

    def __init__(self, settings: Settings | None = None, *, restaurar: bool = True) -> None:
        super().__init__()
        self.settings = settings or cargar_settings()
        self.settings.asegurar_directorios()
        self.config = Configuracion.cargar(self.settings.config)
        self.preferencias = QSettings(
            str(self.settings.db.parent / "gui.ini"), QSettings.Format.IniFormat
        )
        self.archivo: Path | None = None
        self.resultado: ResultadoAnalisis | None = None
        self.sesion: SesionRevision | None = None
        self.ultima_correccion: ResultadoCorreccion | None = None
        self.ultimos_informes: dict[str, Path] = {}
        self.registro: list[str] = []
        self._trabajador: TrabajadorAnalisis | TrabajadorAplicar | TrabajadorExportar | None = None
        self._ocupado = False
        self._reanalizar_al_terminar = False
        self._modo_silencioso = False
        self._secciones: dict[str, SeccionPlegable] = {}
        self._botones_accion: list[QPushButton] = []
        self.setWindowTitle("OniriFix")
        self.resize(1440, 920)
        self.setMinimumSize(1180, 720)
        self._construir()
        self._aplicar_icono()
        self.reglas.cargar(catalogo_reglas(self.config))
        self._cargar_obras()
        self._sincronizar()
        if restaurar:
            self._restaurar_ultimo()

    # ------------------------------------------------------------------
    # API pública (la usan los menús, las pruebas y el script de capturas)
    # ------------------------------------------------------------------

    def esta_ocupado(self) -> bool:
        return self._ocupado or (self._trabajador is not None and self._trabajador.isRunning())

    def abrir_manuscrito(self, ruta: Path, *, analizar: bool = True) -> None:
        ruta = Path(ruta).expanduser()
        if not ruta.is_file():
            self._error(f"No existe el archivo: {ruta}")
            return
        self.archivo = ruta.resolve()
        self.ultima_correccion = None
        self.preferencias.setValue("ultimo_archivo", str(self.archivo))
        self._mostrar_ruta(str(self.archivo))
        self._anotar(f"Manuscrito abierto: {self.archivo}")
        self._sincronizar()
        if analizar:
            self.analizar()

    def analizar(self) -> None:
        if not self._puede_trabajar() or self.archivo is None:
            return
        reglas = self.reglas.seleccion()
        if not reglas:
            self._error("Elige al menos una regla (y su nivel) para analizar.")
            return
        trabajador = TrabajadorAnalisis(self._settings_activos(), self.archivo, reglas)
        trabajador.terminado.connect(self._analisis_terminado)
        self._lanzar(
            trabajador,
            "Analizando manuscrito…",
            f"{self.archivo.name} · {len(reglas)} reglas. No se modifica nada.",
        )

    def decidir_seleccion(self, estado: Estado) -> int:
        if self.sesion is None or self.esta_ocupado():
            return 0
        indices = self.tabla.indices_seleccionados()
        if not indices and (actual := self.tabla.indice_actual()) is not None:
            indices = [actual]
        return self._decidir(indices, estado)

    def decidir_visibles(self, estado: Estado) -> int:
        if self.sesion is None or self.esta_ocupado():
            return 0
        return self._decidir(list(self.tabla.modelo.indices), estado)

    def restablecer_decisiones(self) -> None:
        if self.resultado is None or self.esta_ocupado():
            return
        self.sesion = SesionRevision(self.resultado)
        self._refrescar_vista()
        self._estado("Decisiones restablecidas: L1 aceptados, L2 pendientes.")

    def aplicar_cambios(self, *, confirmar: bool = True, destino: Path | None = None) -> None:
        if not self._puede_trabajar() or self.sesion is None or self.resultado is None:
            return
        parches = self.sesion.parches_aceptados()
        if not parches:
            self._error("No hay cambios aceptados. Marca al menos un hallazgo L1 o L2.")
            return
        documento = self.resultado.documento
        if destino is None and documento.encoding == "docx":
            if not confirmar:
                self._error("Los .docx se guardan como texto: indica un destino .md.")
                return
            elegido, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar el texto corregido",
                str(documento.ruta.with_suffix(".md")),
                "Markdown (*.md);;Texto (*.txt)",
            )
            if not elegido:
                return
            destino = Path(elegido)
        backup = self.backup.isChecked()
        if confirmar:
            resumen = self.sesion.resumen(self.sesion.aceptados())
            l1 = resumen.por_nivel.get("L1", 0)
            l2 = resumen.por_nivel.get("L2", 0)
            donde = destino or documento.ruta
            copia = (
                "Antes se guardará una copia de seguridad con fecha."
                if backup and destino is None
                else "Sin copia de seguridad."
            )
            respuesta = QMessageBox.question(
                self,
                "Aplicar cambios",
                f"Se aplicarán {len(parches)} cambios ({l1} L1 y {l2} L2) en\n{donde}\n\n{copia}",
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return
        trabajador = TrabajadorAplicar(
            self._settings_activos(), self.resultado, parches, backup=backup, destino=destino
        )
        trabajador.terminado.connect(self._aplicacion_terminada)
        self._lanzar(trabajador, "Aplicando cambios…", f"{len(parches)} cambios aceptados.")

    def exportar_informe(
        self, carpeta: Path | None = None, *, formatos: str = "md,csv,json"
    ) -> None:
        if not self._puede_trabajar() or self.resultado is None:
            return
        if carpeta is None:
            inicial = self.preferencias.value("ultima_carpeta_informes", str(self.settings.salida))
            elegida = QFileDialog.getExistingDirectory(
                self, "Carpeta para el informe", str(inicial)
            )
            if not elegida:
                return
            carpeta = Path(elegida)
        self.preferencias.setValue("ultima_carpeta_informes", str(carpeta))
        if self.ultima_correccion is not None and self.ultima_correccion.aplicados:
            formatos = f"{formatos},diff"
        trabajador = TrabajadorExportar(
            self._settings_activos(),
            self.resultado,
            carpeta,
            formatos=formatos,
            correccion=self.ultima_correccion,
        )
        trabajador.terminado.connect(self._exportacion_terminada)
        self._lanzar(trabajador, "Exportando informe…", str(carpeta))

    def mostrar_registro(self) -> None:
        DialogoRegistro(self.registro, self).exec()

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self._trabajador is not None and self._trabajador.isRunning():
            self._trabajador.wait(10000)
        self._guardar_secciones()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------

    def _construir(self) -> None:
        central = QWidget()
        exterior = QVBoxLayout(central)
        exterior.setContentsMargins(0, 0, 0, 0)
        exterior.setSpacing(0)
        exterior.addWidget(self._construir_cabecera())
        cuerpo = QHBoxLayout()
        cuerpo.setContentsMargins(14, 14, 14, 14)
        cuerpo.setSpacing(14)
        cuerpo.addWidget(self._construir_lateral(), 0)
        cuerpo.addWidget(self._construir_centro(), 1)
        cuerpo.addWidget(self._construir_inspector(), 0)
        exterior.addLayout(cuerpo, 1)
        self.setCentralWidget(central)
        self._construir_menu()

    def _construir_cabecera(self) -> QWidget:
        marco = QFrame()
        marco.setObjectName("Header")
        marco.setFixedHeight(78)
        fila = QHBoxLayout(marco)
        fila.setContentsMargins(16, 10, 16, 10)
        titulos = QVBoxLayout()
        titulos.setSpacing(0)
        titulo = QLabel("OniriFix")
        titulo.setObjectName("Title")
        subtitulo = QLabel("Corrector editorial offline")
        subtitulo.setObjectName("Subtitle")
        titulos.addWidget(titulo)
        titulos.addWidget(subtitulo)
        self.etiqueta_estado = QLabel("Abre un manuscrito para empezar")
        self.etiqueta_estado.setObjectName("Muted")
        self.progreso = QProgressBar()
        self.progreso.setFixedWidth(180)
        self.progreso.hide()
        self.boton_registro = QPushButton("Registro")
        self.boton_registro.setProperty("variant", "ghost")
        self.boton_registro.clicked.connect(self.mostrar_registro)
        fila.addWidget(_Marca())
        fila.addLayout(titulos)
        fila.addStretch(1)
        fila.addWidget(self.etiqueta_estado)
        fila.addWidget(self.progreso)
        fila.addWidget(self.boton_registro)
        return marco

    def _construir_lateral(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setObjectName("SidebarScroll")
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(330)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        interior = QWidget()
        layout = QVBoxLayout(interior)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(12)

        manuscrito = QWidget()
        m = QVBoxLayout(manuscrito)
        m.setContentsMargins(0, 0, 0, 0)
        self.boton_abrir = QPushButton("Abrir manuscrito")
        self.boton_abrir.setProperty("variant", "primary")
        self.boton_abrir.clicked.connect(self._elegir_archivo)
        self.boton_reanalizar = QPushButton("Volver a analizar")
        self.boton_reanalizar.clicked.connect(self.analizar)
        self.etiqueta_ruta = QLabel("Ningún manuscrito abierto")
        self.etiqueta_ruta.setObjectName("Muted")
        rotulo_obra = QLabel("Obra (glosario del registro)")
        self.combo_obra = QComboBox()
        self.combo_obra.currentIndexChanged.connect(self._obra_cambiada)
        self.backup = QCheckBox("Copia de seguridad antes de escribir")
        self.backup.setChecked(self.settings.backup)
        m.addWidget(self.boton_abrir)
        m.addWidget(self.boton_reanalizar)
        m.addWidget(self.etiqueta_ruta)
        m.addWidget(rotulo_obra)
        m.addWidget(self.combo_obra)
        m.addWidget(self.backup)

        self.reglas = PanelReglas()
        self.reglas.cambiado.connect(self._sincronizar)
        self.filtros = BarraFiltros()
        self.filtros.cambiado.connect(self._refrescar_vista)
        self.estadisticas = PanelEstadisticas()

        plegadas = self._secciones_plegadas()
        for clave, titulo, contenido, abierta in (
            ("manuscrito", "Manuscrito", manuscrito, True),
            ("reglas", "Reglas y niveles", self.reglas, True),
            ("filtros", "Filtros", self.filtros, True),
            ("estadisticas", "Estadísticas", self.estadisticas, False),
        ):
            if plegadas is not None:
                abierta = clave not in plegadas
            seccion = SeccionPlegable(clave, titulo, contenido, abierta=abierta)
            seccion.cambiada.connect(lambda _c, _a: self._guardar_secciones())
            self._secciones[clave] = seccion
            layout.addWidget(seccion)
        layout.addStretch(1)
        scroll.setWidget(interior)
        self.lateral = interior
        return scroll

    def _construir_centro(self) -> QWidget:
        anfitrion = _Anfitrion()
        envoltura = QWidget(anfitrion)
        layout = QVBoxLayout(envoltura)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        arriba = QHBoxLayout()
        self.etiqueta_conteo = QLabel("0 visibles")
        self.etiqueta_conteo.setObjectName("Muted")
        arriba.addWidget(self.etiqueta_conteo)
        arriba.addStretch(1)
        for texto, accion in (
            ("Aceptar visibles", lambda: self.decidir_visibles(Estado.ACEPTADO)),
            ("Rechazar visibles", lambda: self.decidir_visibles(Estado.RECHAZADO)),
            ("Restablecer", self.restablecer_decisiones),
        ):
            boton = QPushButton(texto)
            boton.setProperty("variant", "ghost")
            boton.clicked.connect(accion)
            self._botones_accion.append(boton)
            arriba.addWidget(boton)
        self.etiqueta_vista = QLabel("")
        self.etiqueta_vista.setObjectName("Muted")
        self.etiqueta_vista.setWordWrap(True)

        acciones = QHBoxLayout()
        acciones.setSpacing(8)
        self.boton_analizar = QPushButton("Analizar")
        self.boton_analizar.clicked.connect(self.analizar)
        self.boton_aceptar = QPushButton("Aceptar")
        self.boton_aceptar.setProperty("variant", "ok")
        self.boton_aceptar.clicked.connect(lambda: self.decidir_seleccion(Estado.ACEPTADO))
        self.boton_rechazar = QPushButton("Rechazar")
        self.boton_rechazar.clicked.connect(lambda: self.decidir_seleccion(Estado.RECHAZADO))
        self.boton_aplicar = QPushButton("Aplicar cambios")
        self.boton_aplicar.setProperty("variant", "primary")
        self.boton_aplicar.clicked.connect(lambda: self.aplicar_cambios())
        self.boton_exportar = QPushButton("Exportar informe")
        self.boton_exportar.clicked.connect(lambda: self.exportar_informe())
        for boton in (
            self.boton_analizar,
            self.boton_aceptar,
            self.boton_rechazar,
            self.boton_aplicar,
            self.boton_exportar,
        ):
            self._botones_accion.append(boton)
            acciones.addWidget(boton)
        acciones.addStretch(1)

        self.pila = QStackedWidget()
        self.pila.addWidget(self._construir_vacio())
        self.tabla = TablaHallazgos()
        self.tabla.activo.connect(self._hallazgo_activo)
        self.tabla.modelo.decisiones_cambiadas.connect(self._decisiones_cambiadas)
        self.pila.addWidget(self.tabla)

        layout.addLayout(arriba)
        layout.addWidget(self.etiqueta_vista)
        layout.addLayout(acciones)
        layout.addWidget(self.pila, 1)
        contenedor = QVBoxLayout(anfitrion)
        contenedor.setContentsMargins(0, 0, 0, 0)
        contenedor.addWidget(envoltura)
        self.capa = CapaOcupado(anfitrion)
        anfitrion.capa = self.capa
        return anfitrion

    def _construir_vacio(self) -> QWidget:
        vacio = QWidget()
        layout = QVBoxLayout(vacio)
        layout.addStretch(1)
        self.vacio_titulo = QLabel("Ningún manuscrito abierto")
        self.vacio_titulo.setObjectName("EmptyTitle")
        self.vacio_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vacio_texto = QLabel(
            "Abre un .md, .txt o .docx. OniriFix lo analiza sin tocarlo;\n"
            "tú decides qué cambios aplicar."
        )
        self.vacio_texto.setObjectName("Muted")
        self.vacio_texto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        boton = QPushButton("Abrir manuscrito")
        boton.setProperty("variant", "primary")
        boton.clicked.connect(self._elegir_archivo)
        self.vacio_boton = boton
        layout.addWidget(self.vacio_titulo)
        layout.addWidget(self.vacio_texto)
        layout.addWidget(boton, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        return vacio

    def _construir_inspector(self) -> QWidget:
        self.inspector = Inspector()
        self.inspector.decision.connect(self._decision_inspector)
        scroll = QScrollArea()
        scroll.setObjectName("SidebarScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.inspector)
        seccion = SeccionPlegable("inspector", "Hallazgo", scroll, abierta=True)
        seccion.setFixedWidth(370)
        return seccion

    def _construir_menu(self) -> None:
        archivo = self.menuBar().addMenu("Archivo")
        for texto, atajo, accion in (
            ("Abrir manuscrito", "Ctrl+O", self._elegir_archivo),
            ("Volver a analizar", "F5", self.analizar),
            ("Aplicar cambios", "Ctrl+S", lambda: self.aplicar_cambios()),
            ("Exportar informe", "Ctrl+E", lambda: self.exportar_informe()),
        ):
            accion_qt = QAction(texto, self)
            accion_qt.setShortcut(QKeySequence(atajo))
            accion_qt.triggered.connect(accion)
            archivo.addAction(accion_qt)
        archivo.addSeparator()
        salir = QAction("Salir", self)
        salir.triggered.connect(self.close)
        archivo.addAction(salir)

        revision = self.menuBar().addMenu("Revisión")
        for texto, atajo, accion in (
            ("Aceptar selección", "A", lambda: self.decidir_seleccion(Estado.ACEPTADO)),
            ("Rechazar selección", "R", lambda: self.decidir_seleccion(Estado.RECHAZADO)),
            ("Aceptar visibles", "", lambda: self.decidir_visibles(Estado.ACEPTADO)),
            ("Rechazar visibles", "", lambda: self.decidir_visibles(Estado.RECHAZADO)),
            ("Restablecer decisiones", "", self.restablecer_decisiones),
        ):
            accion_qt = QAction(texto, self)
            if atajo:
                # Atajos de una letra solo dentro de la tabla, para no robar el
                # teclado al buscador.
                accion_qt.setShortcut(QKeySequence(atajo))
                accion_qt.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
                self.tabla.addAction(accion_qt)
            accion_qt.triggered.connect(accion)
            revision.addAction(accion_qt)

        herramientas = self.menuBar().addMenu("Herramientas")
        registro = QAction("Registro de la sesión", self)
        registro.triggered.connect(self.mostrar_registro)
        herramientas.addAction(registro)
        ayuda = self.menuBar().addMenu("Ayuda")
        acerca = QAction("Acerca de OniriFix", self)
        acerca.triggered.connect(self._acerca_de)
        ayuda.addAction(acerca)

    # ------------------------------------------------------------------
    # Trabajo en segundo plano
    # ------------------------------------------------------------------

    def _puede_trabajar(self) -> bool:
        if self.esta_ocupado():
            self._estado("Espera a que termine la tarea en curso.")
            return False
        return True

    def _lanzar(self, trabajador, titulo: str, detalle: str) -> None:  # type: ignore[no-untyped-def]
        self._trabajador = trabajador
        trabajador.fallo.connect(self._trabajo_fallido)
        trabajador.finished.connect(lambda t=trabajador: self._trabajo_finalizado(t))
        self._fijar_ocupado(True, titulo, detalle)
        trabajador.start()

    def _trabajo_finalizado(self, trabajador: object) -> None:
        if trabajador is not self._trabajador:
            return
        self._trabajador = None
        self._fijar_ocupado(False)
        if self._reanalizar_al_terminar:
            self._reanalizar_al_terminar = False
            self.analizar()

    def _trabajo_fallido(self, mensaje: str) -> None:
        self._error(mensaje)

    def _fijar_ocupado(self, ocupado: bool, titulo: str = "", detalle: str = "") -> None:
        self._ocupado = ocupado
        self.progreso.setVisible(ocupado)
        if ocupado:
            self.progreso.setRange(0, 0)
            self._estado(titulo)
            self.capa.mostrar(titulo, detalle)
        else:
            self.capa.ocultar()
        for widget in (self.lateral, self.inspector, self.tabla):
            widget.setEnabled(not ocupado)
        self._sincronizar()

    def _analisis_terminado(self, resultado: ResultadoAnalisis) -> None:
        self.resultado = resultado
        self.sesion = SesionRevision(resultado)
        self.filtros.cargar_opciones(self.sesion.reglas(), self.sesion.capitulos())
        resumen = self.sesion.resumen()
        self._anotar(
            f"Análisis de {resultado.documento.ruta.name}: {resumen.total} hallazgos "
            f"(L1 {resumen.por_nivel['L1']}, L2 {resumen.por_nivel['L2']}, "
            f"L3 {resumen.por_nivel['L3']})."
        )
        for error in resultado.errores:
            self._anotar(f"Error en regla: {error}")
        self._estado(
            f"{resumen.total} hallazgos · {resumen.por_estado['aceptado']} L1 listos para aplicar"
        )
        self._refrescar_vista()
        self.analisis_listo.emit(resultado)

    def _aplicacion_terminada(self, correccion: ResultadoCorreccion) -> None:
        self.ultima_correccion = correccion
        partes = [f"{len(correccion.aplicados)} cambios aplicados"]
        if correccion.omitidos:
            partes.append(f"{len(correccion.omitidos)} omitidos por solaparse")
        if correccion.backup:
            partes.append(f"copia en {correccion.backup}")
        mensaje = " · ".join(partes)
        self._anotar(f"Escrito {correccion.destino}: {mensaje}.")
        for parche, motivo in correccion.omitidos:
            self._anotar(f"  Omitido {parche.regla} (línea aprox. {parche.inicio}): {motivo}")
        self._estado(mensaje)
        self.cambios_aplicados.emit(correccion)
        # Los offsets cambiaron: se vuelve a analizar el archivo escrito.
        if correccion.destino is not None:
            destino = correccion.destino.resolve()
            if self.archivo is not None and destino != self.archivo:
                self._anotar(f"El texto corregido se guardó aparte: {destino}")
            self.archivo = destino
            self._mostrar_ruta(str(destino))
            self._reanalizar_al_terminar = True

    def _exportacion_terminada(self, rutas: dict[str, Path]) -> None:
        self.ultimos_informes = dict(rutas)
        for formato, ruta in rutas.items():
            self._anotar(f"Informe {formato}: {ruta}")
        carpeta = next(iter(rutas.values())).parent if rutas else None
        self._estado(f"Informe exportado en {carpeta}" if carpeta else "Nada que exportar")
        self.informe_exportado.emit(rutas)

    # ------------------------------------------------------------------
    # Vista
    # ------------------------------------------------------------------

    def _refrescar_vista(self) -> None:
        if self.sesion is None:
            self.pila.setCurrentIndex(0)
            self.etiqueta_conteo.setText("0 visibles")
            self.etiqueta_vista.setText("")
            self.estadisticas.mostrar(Resumen())
            self._sincronizar()
            return
        indices = self.sesion.filtrar(self.filtros.filtro())
        self.tabla.cargar(self.sesion, indices)
        self.pila.setCurrentIndex(1 if len(self.sesion) else 0)
        if not len(self.sesion):
            self.vacio_titulo.setText("Sin hallazgos")
            self.vacio_texto.setText(
                "Ninguna regla encontró nada. La lectura en voz alta sigue siendo tuya."
            )
            self.vacio_boton.hide()
        self.etiqueta_conteo.setText(f"{len(indices)} visibles de {len(self.sesion)}")
        documento = self.sesion.resultado.documento
        self.etiqueta_vista.setText(
            f"{documento.ruta.name} · {documento.palabras} palabras · "
            f"{len(documento.capitulos)} capítulos · "
            f"{len(self.sesion.resultado.reglas_ejecutadas)} reglas"
        )
        self.estadisticas.mostrar(self.sesion.resumen(indices), palabras=documento.palabras)
        self._sincronizar()

    def _hallazgo_activo(self, indice: int | None) -> None:
        if indice is None or self.sesion is None:
            self.inspector.limpiar()
            return
        hallazgo = self.sesion.hallazgos[indice]
        self.inspector.mostrar(
            hallazgo,
            estado=self.sesion.estados[indice],
            texto=self.sesion.resultado.documento.texto,
            descripcion=self.sesion.descripcion(hallazgo.regla),
            capitulo=self.sesion.capitulo(indice),
        )

    def _decision_inspector(self, estado: Estado) -> None:
        actual = self.tabla.indice_actual()
        if actual is not None:
            self._decidir([actual], estado)
            # Avanza a la siguiente fila para revisar con ritmo.
            fila = self.tabla.currentIndex().row()
            if fila + 1 < self.tabla.modelo.rowCount():
                self.tabla.selectRow(fila + 1)

    def _decidir(self, indices: list[int], estado: Estado) -> int:
        if self.sesion is None:
            return 0
        cambiados = self.sesion.decidir(indices, estado)
        if cambiados:
            self.tabla.modelo.refrescar_filas()
            self._decisiones_cambiadas()
        return cambiados

    def _decisiones_cambiadas(self) -> None:
        if self.sesion is None:
            return
        self.estadisticas.mostrar(
            self.sesion.resumen(self.tabla.modelo.indices),
            palabras=self.sesion.resultado.documento.palabras,
        )
        self._hallazgo_activo(self.tabla.indice_actual())
        self._sincronizar()

    def _sincronizar(self) -> None:
        libre = not self._ocupado
        hay_archivo = self.archivo is not None
        hay_sesion = self.sesion is not None and len(self.sesion) > 0
        aceptados = len(self.sesion.aceptados()) if self.sesion is not None else 0
        self.boton_abrir.setEnabled(libre)
        self.boton_reanalizar.setEnabled(libre and hay_archivo)
        self.boton_analizar.setEnabled(libre and hay_archivo and bool(self.reglas.seleccion()))
        for boton in (self.boton_aceptar, self.boton_rechazar, *self._botones_accion[:3]):
            boton.setEnabled(libre and hay_sesion)
        self.boton_aplicar.setEnabled(libre and aceptados > 0)
        self.boton_aplicar.setText(
            f"Aplicar cambios ({aceptados})" if aceptados else "Aplicar cambios"
        )
        self.boton_exportar.setEnabled(libre and self.resultado is not None)

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def _settings_activos(self) -> Settings:
        obra = self.combo_obra.currentData() or self.settings.obra
        return replace(self.settings, obra=str(obra), backup=self.backup.isChecked())

    def _cargar_obras(self) -> None:
        self.combo_obra.blockSignals(True)
        self.combo_obra.clear()
        slugs: list[tuple[str, str]] = []
        try:
            with Registro(self.settings.db) as registro:
                slugs = [(o.slug, o.titulo) for o in registro.obras.listar()]
        except Exception as exc:  # pragma: no cover - base dañada
            self._anotar(f"No pude leer las obras del registro: {exc}")
        if self.settings.obra not in {slug for slug, _ in slugs}:
            slugs.insert(0, (self.settings.obra, self.settings.obra.replace("-", " ").title()))
        for slug, titulo in slugs:
            self.combo_obra.addItem(f"{titulo} ({slug})", slug)
        indice = self.combo_obra.findData(self.settings.obra)
        self.combo_obra.setCurrentIndex(max(indice, 0))
        self.combo_obra.blockSignals(False)

    def _obra_cambiada(self, _indice: int) -> None:
        if self.archivo is not None and self.resultado is not None:
            self._estado("Obra cambiada: vuelve a analizar para usar su glosario.")

    def _elegir_archivo(self) -> None:
        if not self._puede_trabajar():
            return
        inicial = str(self.archivo.parent) if self.archivo else str(Path.home())
        elegido, _ = QFileDialog.getOpenFileName(self, "Abrir manuscrito", inicial, FILTRO_ARCHIVOS)
        if elegido:
            self.abrir_manuscrito(Path(elegido))

    def _restaurar_ultimo(self) -> None:
        ultimo = self.preferencias.value("ultimo_archivo", "")
        if ultimo and Path(str(ultimo)).is_file():
            self.archivo = Path(str(ultimo))
            self._mostrar_ruta(str(self.archivo))
            self._estado("Manuscrito anterior listo. Pulsa Analizar para revisarlo.")
            self._sincronizar()

    def _mostrar_ruta(self, ruta: str) -> None:
        self.etiqueta_ruta.setToolTip(ruta)
        metricas = QFontMetrics(self.etiqueta_ruta.font())
        self.etiqueta_ruta.setText(metricas.elidedText(ruta, Qt.TextElideMode.ElideMiddle, 280))

    def _secciones_plegadas(self) -> set[str] | None:
        valor = self.preferencias.value("secciones_plegadas", None)
        if valor is None:
            return None
        if isinstance(valor, str):
            return {parte for parte in valor.split(",") if parte}
        return {str(parte) for parte in valor}

    def _guardar_secciones(self) -> None:
        plegadas = [clave for clave, s in self._secciones.items() if not s.esta_abierta()]
        self.preferencias.setValue("secciones_plegadas", ",".join(sorted(plegadas)))

    def _estado(self, texto: str) -> None:
        self.etiqueta_estado.setText(texto)

    def _anotar(self, texto: str) -> None:
        self.registro.append(f"[{datetime.now():%H:%M:%S}] {texto}")
        errores = sum(1 for linea in self.registro if "] Error" in linea)
        self.boton_registro.setText(f"Registro ({errores})" if errores else "Registro")

    def _error(self, mensaje: str) -> None:
        self._anotar(f"Error: {mensaje}")
        self._estado("Algo salió mal; revisa el registro.")
        self.error_mostrado.emit(mensaje)
        if not self._modo_silencioso:
            QMessageBox.warning(self, "OniriFix", mensaje)

    def _acerca_de(self) -> None:
        QMessageBox.about(
            self,
            "Acerca de OniriFix",
            f"OniriFix {__version__}\n\nCorrector editorial offline y determinista para "
            "ficción en español. L1 son cambios mecánicos, L2 se revisan uno a uno y "
            "L3 son avisos: lo creativo sigue siendo tuyo.",
        )

    def _aplicar_icono(self) -> None:
        icono = Path(__file__).resolve().parents[1] / "assets" / "icon.png"
        if icono.is_file():
            self.setWindowIcon(QIcon(str(icono)))


__all__ = ["VentanaPrincipal"]
