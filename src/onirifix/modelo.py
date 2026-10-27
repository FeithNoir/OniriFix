"""Modelo de dominio de OniriFix.

El motor y las reglas solo conocen estos tipos. La persistencia vive en
``onirifix.db`` y la presentación en ``onirifix.cli`` / ``onirifix.informes``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from onirifix.config import Configuracion
    from onirifix.linguistica import AnalizadorLinguistico, CorrectorOrtografico


class Nivel(StrEnum):
    """Los tres niveles de confianza editorial."""

    L1 = "L1"
    L2 = "L2"
    L3 = "L3"

    @property
    def orden(self) -> int:
        return {"L1": 1, "L2": 2, "L3": 3}[self.value]

    @property
    def etiqueta(self) -> str:
        return {
            "L1": "Mecánico (se puede aplicar)",
            "L2": "Asistido (requiere umbral)",
            "L3": "Solo informe",
        }[self.value]

    @classmethod
    def desde(cls, valor: str | Nivel) -> Nivel:
        if isinstance(valor, Nivel):
            return valor
        normalizado = str(valor).strip().upper()
        try:
            return cls(normalizado)
        except ValueError as exc:
            raise ValueError(
                f"Nivel desconocido: {valor!r}. Usa L1, L2 o L3."
            ) from exc


@dataclass(frozen=True, slots=True)
class Hallazgo:
    """Un punto concreto del texto que merece atención.

    ``inicio`` y ``fin`` son offsets de caracteres sobre el texto completo.
    ``linea`` y ``columna`` son 1-based para que el informe sea legible.
    """

    regla: str
    nivel: Nivel
    inicio: int
    fin: int
    original: str
    sugerencia: str | None
    confianza: float
    linea: int
    columna: int
    contexto: str
    nota: str = ""

    def se_solapa(self, otro: Hallazgo) -> bool:
        return self.inicio < otro.fin and otro.inicio < self.fin

    @property
    def aplicable(self) -> bool:
        return self.sugerencia is not None and self.nivel in (Nivel.L1, Nivel.L2)


def crear_hallazgo(
    texto: str,
    *,
    regla: str,
    nivel: Nivel,
    inicio: int,
    fin: int,
    sugerencia: str | None,
    confianza: float,
    nota: str = "",
    radio_contexto: int = 60,
) -> Hallazgo | None:
    """Construye un hallazgo con línea, columna y contexto ya calculados.

    Devuelve ``None`` si el reemplazo es idéntico al original: una regla no
    debe generar ruido cuando no cambia nada.
    """

    if not (0 <= inicio < fin <= len(texto)):
        raise ValueError(f"Span inválido: {inicio}:{fin} para un texto de {len(texto)}")
    original = texto[inicio:fin]
    if sugerencia is not None and sugerencia == original:
        return None

    linea = texto.count("\n", 0, inicio) + 1
    inicio_linea = texto.rfind("\n", 0, inicio)
    columna = inicio - inicio_linea

    contexto_inicio = max(0, inicio - radio_contexto)
    contexto_fin = min(len(texto), fin + radio_contexto)
    contexto = texto[contexto_inicio:contexto_fin]

    return Hallazgo(
        regla=regla,
        nivel=nivel,
        inicio=inicio,
        fin=fin,
        original=original,
        sugerencia=sugerencia,
        confianza=round(max(0.0, min(1.0, float(confianza))), 4),
        linea=linea,
        columna=columna,
        contexto=contexto,
        nota=nota,
    )


@dataclass(frozen=True, slots=True)
class Parche:
    """Reemplazo verificado que el motor puede aplicar sobre el texto."""

    inicio: int
    fin: int
    original: str
    reemplazo: str
    regla: str
    nivel: Nivel
    confianza: float

    @classmethod
    def desde_hallazgo(cls, hallazgo: Hallazgo) -> Parche | None:
        if hallazgo.sugerencia is None:
            return None
        return cls(
            inicio=hallazgo.inicio,
            fin=hallazgo.fin,
            original=hallazgo.original,
            reemplazo=hallazgo.sugerencia,
            regla=hallazgo.regla,
            nivel=hallazgo.nivel,
            confianza=hallazgo.confianza,
        )

    def se_solapa(self, otro: Parche) -> bool:
        return self.inicio < otro.fin and otro.inicio < self.fin


@runtime_checkable
class Regla(Protocol):
    """Contrato mínimo de una regla enchufable."""

    id: str
    nivel: Nivel
    descripcion: str
    prioridad: int
    por_defecto: bool

    def aplicar(self, texto: str, ctx: Contexto) -> Iterable[Hallazgo]:
        ...


@dataclass(slots=True)
class Contexto:
    """Todo lo que una regla puede necesitar sin conocer la CLI ni SQLite."""

    config: Configuracion
    glosario: Glosario
    idioma: str = "es"
    analizador: AnalizadorLinguistico | None = None
    corrector: CorrectorOrtografico | None = None
    obra: Obra | None = None
    documento: Documento | None = None
    ruta: Path | None = None

    def activa(self, regla_id: str, por_defecto: bool = True) -> bool:
        return self.config.regla_activa(regla_id, por_defecto)


@dataclass(frozen=True, slots=True)
class Obra:
    id: int
    slug: str
    titulo: str
    autor: str | None = None
    idioma: str = "es"
    genero: str | None = None
    descripcion: str | None = None


@dataclass(frozen=True, slots=True)
class Personaje:
    id: int
    obra_id: int
    nombre: str
    rol: str | None = None
    alias: str | None = None
    descripcion: str | None = None
    notas: str | None = None
    activo: bool = True


@dataclass(frozen=True, slots=True)
class Lugar:
    id: int
    obra_id: int
    nombre: str
    tipo: str | None = None
    alias: str | None = None
    descripcion: str | None = None
    notas: str | None = None


@dataclass(frozen=True, slots=True)
class Variante:
    id: int
    termino_id: int
    variante: str
    es_error: bool = True
    notas: str | None = None


@dataclass(frozen=True, slots=True)
class Termino:
    id: int
    obra_id: int
    termino: str
    tipo: str = "glosario"
    definicion: str | None = None
    notas: str | None = None
    sensible: bool = False
    variantes: tuple[Variante, ...] = ()


@dataclass(frozen=True, slots=True)
class Glosario:
    """Vista agregada del registro que consumen las reglas."""

    nombres: frozenset[str] = frozenset()
    alias: frozenset[str] = frozenset()
    toponimos: frozenset[str] = frozenset()
    terminos: frozenset[str] = frozenset()
    variantes: Mapping[str, str] = field(default_factory=dict)
    verbos_habla: frozenset[str] = frozenset()

    @property
    def palabras(self) -> frozenset[str]:
        return (
            self.nombres
            | self.alias
            | self.toponimos
            | self.terminos
            | frozenset(self.variantes)
        )

    def canonico(self, palabra: str) -> str | None:
        return self.variantes.get(palabra.casefold())


@dataclass(frozen=True, slots=True)
class Capitulo:
    titulo: str
    inicio: int
    fin: int
    linea: int


@dataclass(frozen=True, slots=True)
class Documento:
    ruta: Path
    texto: str
    encoding: str = "utf-8"
    capitulos: tuple[Capitulo, ...] = ()

    @property
    def palabras(self) -> int:
        return len(self.texto.split())

    def capitulo_de(self, offset: int) -> Capitulo | None:
        for capitulo in self.capitulos:
            if capitulo.inicio <= offset < capitulo.fin:
                return capitulo
        return None


@dataclass(slots=True)
class ResultadoAnalisis:
    documento: Documento
    hallazgos: list[Hallazgo] = field(default_factory=list)
    reglas_ejecutadas: list[str] = field(default_factory=list)
    descripciones: dict[str, str] = field(default_factory=dict)
    errores: list[str] = field(default_factory=list)

    def por_nivel(self, nivel: Nivel) -> list[Hallazgo]:
        return [h for h in self.hallazgos if h.nivel == nivel]

    def conteo_por_regla(self) -> dict[str, int]:
        conteo: dict[str, int] = {}
        for hallazgo in self.hallazgos:
            conteo[hallazgo.regla] = conteo.get(hallazgo.regla, 0) + 1
        return dict(sorted(conteo.items(), key=lambda item: (-item[1], item[0])))

    @property
    def total(self) -> int:
        return len(self.hallazgos)


@dataclass(slots=True)
class ResultadoCorreccion:
    analisis: ResultadoAnalisis
    texto_corregido: str
    parches_seleccionados: list[Parche] = field(default_factory=list)
    aplicados: list[Parche] = field(default_factory=list)
    omitidos: list[tuple[Parche, str]] = field(default_factory=list)
    backup: Path | None = None
    escrito: bool = False
    destino: Path | None = None

    @property
    def hubo_cambios(self) -> bool:
        return bool(self.aplicados)
