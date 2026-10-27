"""Entrada y salida de manuscritos."""

from __future__ import annotations

from onirifix.io.cargadores import (
    ErrorLectura,
    cargar_documento,
    detectar_capitulos,
    escribir_texto,
    leer_texto,
    sufijo_soportado,
)

__all__ = [
    "ErrorLectura",
    "cargar_documento",
    "detectar_capitulos",
    "escribir_texto",
    "leer_texto",
    "sufijo_soportado",
]
