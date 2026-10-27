"""Estilos de terminal con nombres de rol, no de pigmento.

Adaptación de la guía de diseño de Angular: los componentes no eligen colores
sueltos; consumen estilos semánticos definidos una sola vez.
"""

from __future__ import annotations

ESTILOS: dict[str, str] = {
    "titulo": "bold cyan",
    "acento": "bold yellow",
    "ok": "bold green",
    "error": "bold red",
    "aviso": "yellow",
    "sutil": "dim",
    "nivel_l1": "green",
    "nivel_l2": "yellow",
    "nivel_l3": "magenta",
    "archivo": "cyan",
    "codigo": "bright_white",
}

NIVEL_ESTILO: dict[str, str] = {
    "L1": ESTILOS["nivel_l1"],
    "L2": ESTILOS["nivel_l2"],
    "L3": ESTILOS["nivel_l3"],
}
