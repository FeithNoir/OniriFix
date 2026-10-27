"""Pruebas de utilidades transversales."""

from __future__ import annotations

import sys

import pytest

from onirifix.util import configurar_salida_utf8


class FlujoFalso:
    """Flujo mínimo con la misma superficie que usa la utilidad."""

    def __init__(self, encoding: str, *, tty: bool = False) -> None:
        self.encoding = encoding
        self.tty = tty
        self.llamada: dict[str, str] | None = None

    def isatty(self) -> bool:
        return self.tty

    def reconfigure(self, **kwargs: str) -> None:
        self.llamada = kwargs


def test_configurar_salida_utf8_redirigida(monkeypatch: pytest.MonkeyPatch) -> None:
    salida = FlujoFalso("cp1252")
    error = FlujoFalso("cp1252")
    monkeypatch.setattr(sys, "stdout", salida)
    monkeypatch.setattr(sys, "stderr", error)

    configurar_salida_utf8()

    assert salida.llamada == {"encoding": "utf-8", "errors": "replace"}
    assert error.llamada == {"encoding": "utf-8", "errors": "replace"}


def test_configurar_salida_utf8_respeta_consola(monkeypatch: pytest.MonkeyPatch) -> None:
    salida = FlujoFalso("cp1252", tty=True)
    monkeypatch.setattr(sys, "stdout", salida)
    monkeypatch.setattr(sys, "stderr", FlujoFalso("utf-8", tty=True))

    configurar_salida_utf8()

    assert salida.llamada is None


def test_configurar_salida_utf8_ignora_utf8(monkeypatch: pytest.MonkeyPatch) -> None:
    salida = FlujoFalso("utf-8")
    monkeypatch.setattr(sys, "stdout", salida)
    monkeypatch.setattr(sys, "stderr", FlujoFalso("utf-8"))

    configurar_salida_utf8()

    assert salida.llamada is None
