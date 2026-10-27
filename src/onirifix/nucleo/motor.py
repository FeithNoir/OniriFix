"""Motor de ejecución de reglas.

El motor no sabe qué es un diálogo ni una tilde: solo activa reglas, recoge
hallazgos, elimina solapamientos y los ordena por posición.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from onirifix.config import Configuracion
from onirifix.linguistica import AnalizadorLinguistico, CorrectorOrtografico
from onirifix.modelo import (
    Contexto,
    Documento,
    Glosario,
    Hallazgo,
    Nivel,
    Obra,
    Regla,
    ResultadoAnalisis,
)
from onirifix.nucleo.registro_reglas import descubrir_reglas

log = logging.getLogger(__name__)


class Motor:
    def __init__(
        self,
        config: Configuracion,
        glosario: Glosario,
        *,
        analizador: AnalizadorLinguistico | None = None,
        corrector: CorrectorOrtografico | None = None,
        reglas: Iterable[Regla] | None = None,
    ):
        self.config = config
        self.glosario = glosario
        self.analizador = analizador
        self.corrector = corrector
        self.reglas = list(reglas if reglas is not None else descubrir_reglas())
        self._prioridades = {regla.id: regla.prioridad for regla in self.reglas}

    def _debe_ejecutar(self, regla: Regla, solo: set[str] | None) -> bool:
        if solo is not None:
            return regla.id in solo
        if regla.id == "DIA-003" and bool(
            self.config.obtener("dialogos.rae_estricto", False)
        ):
            return True
        return self.config.regla_activa(regla.id, regla.por_defecto)

    def reglas_activas(self, solo_reglas: Iterable[str] | None = None) -> list[Regla]:
        solo = {r.strip().upper() for r in solo_reglas} if solo_reglas else None
        return [regla for regla in self.reglas if self._debe_ejecutar(regla, solo)]

    def analizar(
        self,
        documento: Documento,
        *,
        solo_reglas: Iterable[str] | None = None,
        incluir_l3: bool = True,
        obra: Obra | None = None,
    ) -> ResultadoAnalisis:
        solo = {r.strip().upper() for r in solo_reglas} if solo_reglas else None
        if solo:
            desconocidas = solo - {regla.id for regla in self.reglas}
            if desconocidas:
                raise ValueError(
                    "Reglas desconocidas: "
                    + ", ".join(sorted(desconocidas))
                    + ". Usa `onirifix reglas` para ver el catálogo."
                )

        contexto = Contexto(
            config=self.config,
            glosario=self.glosario,
            idioma=self.config.idioma,
            analizador=self.analizador,
            corrector=self.corrector,
            obra=obra,
            documento=documento,
            ruta=documento.ruta,
        )

        hallazgos: list[Hallazgo] = []
        ejecutadas: list[str] = []
        descripciones: dict[str, str] = {}
        errores: list[str] = []

        for regla in self.reglas_activas(solo):
            ejecutadas.append(regla.id)
            descripciones[regla.id] = regla.descripcion
            try:
                for hallazgo in regla.aplicar(documento.texto, contexto):
                    if hallazgo is None:
                        continue
                    if not incluir_l3 and hallazgo.nivel == Nivel.L3:
                        continue
                    hallazgos.append(hallazgo)
            except Exception as exc:
                log.debug("La regla %s falló", regla.id, exc_info=True)
                errores.append(f"{regla.id}: {type(exc).__name__}: {exc}")

        hallazgos = self.deduplicar(hallazgos)
        return ResultadoAnalisis(
            documento=documento,
            hallazgos=hallazgos,
            reglas_ejecutadas=ejecutadas,
            descripciones=descripciones,
            errores=errores,
        )

    def deduplicar(self, hallazgos: list[Hallazgo]) -> list[Hallazgo]:
        """Elimina solapamientos priorizando reglas específicas y L1."""

        ordenados = sorted(
            hallazgos,
            key=lambda h: (
                h.inicio,
                self._prioridades.get(h.regla, 1000),
                h.nivel.orden,
                -(h.fin - h.inicio),
                -h.confianza,
            ),
        )
        resultado: list[Hallazgo] = []
        fin_actual = -1
        for hallazgo in ordenados:
            if hallazgo.inicio < fin_actual:
                continue
            resultado.append(hallazgo)
            fin_actual = max(fin_actual, hallazgo.fin)
        return sorted(resultado, key=lambda h: (h.inicio, h.regla))
