"""Registro y descubrimiento de reglas.

Añadir una regla = añadir un módulo a ``onirifix.reglas``. El motor no conoce
IDs concretos: solo ejecuta lo que el registro le entrega.
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterable
from functools import lru_cache

from onirifix.modelo import Regla


class ErrorRegistro(ValueError):
    pass


class RegistroReglas:
    def __init__(self) -> None:
        self._reglas: dict[str, Regla] = {}

    def registrar(self, regla: Regla) -> Regla:
        if not getattr(regla, "id", None):
            raise ErrorRegistro("Una regla debe declarar un id.")
        if regla.id in self._reglas:
            raise ErrorRegistro(f"La regla '{regla.id}' ya está registrada.")
        self._reglas[regla.id] = regla
        return regla

    def todas(self) -> list[Regla]:
        return sorted(self._reglas.values(), key=lambda r: (r.prioridad, r.id))

    def obtener(self, regla_id: str) -> Regla | None:
        return self._reglas.get(regla_id)

    def ids(self) -> set[str]:
        return set(self._reglas)

    def filtrar(self, ids: Iterable[str]) -> list[Regla]:
        buscados = set(ids)
        return [regla for regla in self.todas() if regla.id in buscados]

    def limpiar(self) -> None:
        """Solo para pruebas que registran reglas temporales."""

        self._reglas.clear()


REGISTRO = RegistroReglas()


def registrar(regla: Regla | type[Regla]) -> Regla:
    """Decorador de registro.

    Acepta tanto una instancia como una clase de regla. Las clases se
    instancian aquí para que el motor siempre reciba objetos con estado
    independiente y pueda llamar a ``aplicar`` como método de instancia.
    """

    if isinstance(regla, type):
        regla = regla()
    return REGISTRO.registrar(regla)


@lru_cache(maxsize=1)
def descubrir_reglas() -> list[Regla]:
    import onirifix.reglas as paquete_reglas

    for info in pkgutil.iter_modules(paquete_reglas.__path__):
        if info.name.startswith("_"):
            continue
        importlib.import_module(f"{paquete_reglas.__name__}.{info.name}")
    return REGISTRO.todas()
