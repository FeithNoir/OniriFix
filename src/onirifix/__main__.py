"""Permite ``python -m onirifix``."""

from __future__ import annotations

from onirifix.cli import cli
from onirifix.util import configurar_salida_utf8

if __name__ == "__main__":
    configurar_salida_utf8()
    cli()
