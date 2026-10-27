"""Similitud de cadenas con degradación elegante.

``rapidfuzz`` es la opción rápida; si no está instalada, ``difflib`` mantiene
la herramienta funcional (más lenta, pero suficiente para textos pequeños).
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

_fuzz: Any
try:  # pragma: no cover - depende del entorno
    from rapidfuzz import fuzz as _rapidfuzz

    _fuzz = _rapidfuzz
except ImportError:  # pragma: no cover
    _fuzz = None


def ratio(a: str, b: str) -> float:
    """Devuelve una similitud entre 0 y 100."""

    if a == b:
        return 100.0
    if not a or not b:
        return 0.0
    if _fuzz is not None:
        return float(_fuzz.ratio(a, b))
    return SequenceMatcher(None, a, b).ratio() * 100.0


def similitud(a: str, b: str) -> float:
    """Alias expresivo de :func:`ratio`."""

    return ratio(a, b)
