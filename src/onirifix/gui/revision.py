"""Estado de una revisión: decisiones, filtros y estadísticas.

Este módulo no importa Qt para poder probarlo sin pantalla. No reimplementa
nada del motor: solo recuerda qué hallazgos aceptó o rechazó la persona y
convierte los aceptados en parches con ``Parche.desde_hallazgo``.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum

from onirifix.modelo import Hallazgo, Nivel, Parche, ResultadoAnalisis


class Estado(StrEnum):
    PENDIENTE = "pendiente"
    ACEPTADO = "aceptado"
    RECHAZADO = "rechazado"
    AVISO = "aviso"

    @property
    def etiqueta(self) -> str:
        return {
            "pendiente": "Pendiente",
            "aceptado": "Aceptado",
            "rechazado": "Rechazado",
            "aviso": "Solo aviso",
        }[self.value]


TODOS = ""


@dataclass(slots=True)
class Filtro:
    nivel: str = TODOS
    regla: str = TODOS
    capitulo: str = TODOS
    estado: str = TODOS
    texto: str = ""

    def activo(self) -> bool:
        return any((self.nivel, self.regla, self.capitulo, self.estado, self.texto.strip()))


@dataclass(slots=True)
class Resumen:
    total: int = 0
    por_nivel: dict[str, int] = field(default_factory=dict)
    por_estado: dict[str, int] = field(default_factory=dict)
    por_regla: list[tuple[str, int]] = field(default_factory=list)
    por_capitulo: list[tuple[str, int]] = field(default_factory=list)


class SesionRevision:
    """Hallazgos de un análisis más la decisión que se tomó sobre cada uno."""

    def __init__(self, resultado: ResultadoAnalisis, *, aceptar_l1: bool = True) -> None:
        self.resultado = resultado
        self.hallazgos: list[Hallazgo] = list(resultado.hallazgos)
        self.estados: list[Estado] = [self._estado_inicial(h, aceptar_l1) for h in self.hallazgos]
        self._capitulos = [self._capitulo(h) for h in self.hallazgos]

    # -- consulta -------------------------------------------------------

    @staticmethod
    def _estado_inicial(hallazgo: Hallazgo, aceptar_l1: bool) -> Estado:
        if not hallazgo.aplicable:
            return Estado.AVISO
        if hallazgo.nivel == Nivel.L1 and aceptar_l1:
            return Estado.ACEPTADO
        return Estado.PENDIENTE

    def _capitulo(self, hallazgo: Hallazgo) -> str:
        capitulo = self.resultado.documento.capitulo_de(hallazgo.inicio)
        return capitulo.titulo if capitulo else ""

    def capitulo(self, indice: int) -> str:
        return self._capitulos[indice]

    def __len__(self) -> int:
        return len(self.hallazgos)

    def reglas(self) -> list[str]:
        return sorted({h.regla for h in self.hallazgos})

    def capitulos(self) -> list[str]:
        vistos: list[str] = []
        for titulo in self._capitulos:
            if titulo and titulo not in vistos:
                vistos.append(titulo)
        return vistos

    def descripcion(self, regla: str) -> str:
        return self.resultado.descripciones.get(regla, "")

    def filtrar(self, filtro: Filtro) -> list[int]:
        texto = filtro.texto.strip().casefold()
        indices: list[int] = []
        for indice, hallazgo in enumerate(self.hallazgos):
            if filtro.nivel and hallazgo.nivel.value != filtro.nivel:
                continue
            if filtro.regla and hallazgo.regla != filtro.regla:
                continue
            if filtro.capitulo and self._capitulos[indice] != filtro.capitulo:
                continue
            if filtro.estado and self.estados[indice].value != filtro.estado:
                continue
            if texto and not any(
                texto in (campo or "").casefold()
                for campo in (
                    hallazgo.original,
                    hallazgo.sugerencia,
                    hallazgo.contexto,
                    hallazgo.nota,
                    hallazgo.regla,
                )
            ):
                continue
            indices.append(indice)
        return indices

    # -- decisiones -----------------------------------------------------

    def decidir(self, indices: list[int] | int, estado: Estado) -> int:
        """Cambia el estado de los hallazgos aplicables. Devuelve cuántos cambió."""

        if isinstance(indices, int):
            indices = [indices]
        if estado == Estado.AVISO:
            raise ValueError("«Solo aviso» no es una decisión.")
        cambiados = 0
        for indice in indices:
            if self.estados[indice] == Estado.AVISO:
                continue  # L3 o sin sugerencia: solo lectura.
            if self.estados[indice] != estado:
                self.estados[indice] = estado
                cambiados += 1
        return cambiados

    def aceptados(self) -> list[int]:
        return [i for i, estado in enumerate(self.estados) if estado == Estado.ACEPTADO]

    def parches_aceptados(self) -> list[Parche]:
        parches: list[Parche] = []
        for indice in self.aceptados():
            parche = Parche.desde_hallazgo(self.hallazgos[indice])
            if parche is not None:
                parches.append(parche)
        return parches

    # -- estadísticas ---------------------------------------------------

    def resumen(self, indices: list[int] | None = None) -> Resumen:
        seleccion = range(len(self.hallazgos)) if indices is None else indices
        niveles: Counter[str] = Counter()
        estados: Counter[str] = Counter()
        reglas: Counter[str] = Counter()
        capitulos: Counter[str] = Counter()
        total = 0
        for indice in seleccion:
            hallazgo = self.hallazgos[indice]
            total += 1
            niveles[hallazgo.nivel.value] += 1
            estados[self.estados[indice].value] += 1
            reglas[hallazgo.regla] += 1
            capitulos[self._capitulos[indice] or "Sin capítulo"] += 1
        return Resumen(
            total=total,
            por_nivel={nivel.value: niveles.get(nivel.value, 0) for nivel in Nivel},
            por_estado={estado.value: estados.get(estado.value, 0) for estado in Estado},
            por_regla=sorted(reglas.items(), key=lambda item: (-item[1], item[0])),
            por_capitulo=sorted(capitulos.items(), key=lambda item: (-item[1], item[0])),
        )
