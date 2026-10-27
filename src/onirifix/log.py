"""Configuración de logging para la CLI."""

from __future__ import annotations

import logging

from rich.console import Console
from rich.logging import RichHandler


def configurar_logging(verbose: int = 0, nivel: str = "WARNING") -> None:
    if verbose >= 2:
        level = logging.DEBUG
    elif verbose == 1:
        level = logging.INFO
    else:
        level = getattr(logging, str(nivel).upper(), logging.WARNING)

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%H:%M:%S]",
        handlers=[
            RichHandler(
                console=Console(stderr=True),
                show_path=False,
                show_time=False,
                rich_tracebacks=True,
            )
        ],
        force=True,
    )
