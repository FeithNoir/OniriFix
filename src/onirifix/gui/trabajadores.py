"""Hilos de trabajo: la ventana nunca llama al motor desde el hilo de la UI.

Cada hilo abre su propio contexto (y su propia conexión SQLite), así no se
comparte ningún objeto de base de datos entre hilos.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from onirifix.config import Settings
from onirifix.modelo import Parche, ResultadoAnalisis, ResultadoCorreccion
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
    """Carga el manuscrito y ejecuta las reglas elegidas sin modificar nada."""

    terminado = Signal(object)

    def __init__(self, settings: Settings, archivo: Path, reglas: list[str] | None) -> None:
        super().__init__(settings)
        self.archivo = archivo
        self.reglas = reglas

    def run(self) -> None:
        try:
            with abrir_contexto(self.settings, crear_obra=True) as ctx:
                resultado = analizar(ctx, self.archivo, solo_reglas=self.reglas, incluir_l3=True)
        except Exception as exc:
            self._informar(exc)
            return
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
    """Escribe los informes Markdown, CSV, JSON (y diff si hubo corrección)."""

    terminado = Signal(object)

    def __init__(
        self,
        settings: Settings,
        resultado: ResultadoAnalisis,
        carpeta: Path,
        *,
        formatos: str,
        correccion: ResultadoCorreccion | None = None,
    ) -> None:
        super().__init__(settings)
        self.resultado = resultado
        self.carpeta = carpeta
        self.formatos = formatos
        self.correccion = correccion

    def run(self) -> None:
        try:
            with abrir_contexto(self.settings, crear_obra=True) as ctx:
                rutas = exportar_informes(
                    ctx,
                    self.resultado,
                    self.carpeta,
                    formatos=self.formatos,
                    correccion=self.correccion,
                )
        except Exception as exc:
            self._informar(exc)
            return
        self.terminado.emit(rutas)
