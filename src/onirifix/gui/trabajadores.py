"""Hilos de trabajo: la ventana nunca llama al motor desde el hilo de la UI.

Cada hilo abre su propio contexto (y su propia conexión SQLite), así no se
comparte ningún objeto de base de datos entre hilos.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from onirifix.config import Settings
from onirifix.modelo import Parche, ResultadoAnalisis, ResultadoCorreccion
from onirifix.nucleo.motor import AnalisisCancelado
from onirifix.servicio import abrir_contexto, analizar, aplicar_seleccion, exportar_informes

log = logging.getLogger(__name__)


class _Trabajador(QThread):
    fallo = Signal(str)

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings

    def _informar(self, exc: Exception) -> None:
        log.debug("Fallo en %s", type(self).__name__, exc_info=True)
        self.fallo.emit(str(exc) or type(exc).__name__)


class TrabajadorAnalisis(_Trabajador):
    """Carga el manuscrito y ejecuta las reglas elegidas sin modificar nada.

    Emite ``avance(hechas, total, detalle)`` (total 0 = fase sin medida, como
    leer un PDF) y se puede cancelar entre regla y regla.
    """

    terminado = Signal(object)
    avance = Signal(int, int, str)
    cancelado = Signal()

    def __init__(self, settings: Settings, archivo: Path, reglas: list[str] | None) -> None:
        super().__init__(settings)
        self.archivo = archivo
        self.reglas = reglas
        self.segundos: float | None = None
        self._cancelar = False

    def cancelar(self) -> None:
        self._cancelar = True

    def _progreso(self, hechas: int, total: int, regla: str) -> bool:
        detalle = f"Regla {regla} · {hechas + 1} de {total}" if regla else "Ordenando hallazgos…"
        self.avance.emit(hechas, total, detalle)
        return not self._cancelar

    def run(self) -> None:
        inicio = time.perf_counter()
        try:
            self.avance.emit(0, 0, f"Leyendo {self.archivo.name}…")
            with abrir_contexto(self.settings, crear_obra=True) as ctx:
                resultado = analizar(
                    ctx, self.archivo, solo_reglas=self.reglas, incluir_l3=True,
                    progreso=self._progreso,
                )
        except AnalisisCancelado:
            self.cancelado.emit()
            return
        except Exception as exc:
            self._informar(exc)
            return
        self.segundos = time.perf_counter() - inicio
        self.terminado.emit(resultado)


class TrabajadorAplicar(_Trabajador):
    """Aplica los parches aceptados con copia de seguridad y auditoría."""

    terminado = Signal(object)

    def __init__(
        self,
        settings: Settings,
        analisis: ResultadoAnalisis,
        parches: list[Parche],
        *,
        backup: bool,
        destino: Path | None = None,
    ) -> None:
        super().__init__(settings)
        self.analisis = analisis
        self.parches = parches
        self.backup = backup
        self.destino = destino

    def run(self) -> None:
        try:
            with abrir_contexto(self.settings, crear_obra=True) as ctx:
                correccion = aplicar_seleccion(
                    ctx,
                    self.analisis,
                    self.parches,
                    aplicar=True,
                    backup=self.backup,
                    destino=self.destino,
                )
        except Exception as exc:
            self._informar(exc)
            return
        self.terminado.emit(correccion)


class TrabajadorExportar(_Trabajador):
    """Escribe los informes (Markdown, CSV, JSON, PDF) y el diff y el PDF corregido si hubo corrección."""

    terminado = Signal(object)

    def __init__(
        self,
        settings: Settings,
        resultado: ResultadoAnalisis,
        carpeta: Path,
        *,
        formatos: str,
        correccion: ResultadoCorreccion | None = None,
        segundos: float | None = None,
    ) -> None:
        super().__init__(settings)
        # Tras aplicar, el informe describe el análisis que se corrigió (así
        # cuadran aplicados y pendientes), no el nuevo análisis del texto ya
        # corregido.
        self.resultado = correccion.analisis if correccion is not None else resultado
        self.carpeta = carpeta
        self.formatos = formatos
        self.correccion = correccion
        self.segundos = segundos

    def run(self) -> None:
        try:
            with abrir_contexto(self.settings, crear_obra=True) as ctx:
                rutas = exportar_informes(
                    ctx,
                    self.resultado,
                    self.carpeta,
                    formatos=self.formatos,
                    correccion=self.correccion,
                    segundos=self.segundos,
                )
        except Exception as exc:
            self._informar(exc)
            return
        self.terminado.emit(rutas)
