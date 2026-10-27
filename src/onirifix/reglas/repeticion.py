"""Repetición, duplicados y residuo de IA (siempre L3)."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass

try:  # pragma: no cover
    import regex as re
except ImportError:  # pragma: no cover
    import re  # type: ignore[no-redef]

from onirifix.config import Configuracion
from onirifix.modelo import Capitulo, Contexto, Documento, Glosario, Hallazgo, Nivel, crear_hallazgo
from onirifix.nucleo.registro_reglas import registrar
from onirifix.reglas._comun import dividir_oraciones
from onirifix.similitud import ratio
from onirifix.util import (
    clave,
    contar_palabras,
    indices_de_linea,
    linea_en,
    parrafos_con_offset,
)

_PALABRA = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)?", re.UNICODE)


@dataclass(frozen=True, slots=True)
class Frecuencia:
    palabra: str
    conteo: int
    linea: int
    inicio: int
    por_capitulo: dict[str, int]


def _capitulo_de(
    capitulos: tuple[Capitulo, ...], offset: int
) -> Capitulo | None:
    for capitulo in capitulos:
        if capitulo.inicio <= offset < capitulo.fin:
            return capitulo
    return None


def calcular_frecuencias(
    texto: str,
    glosario: Glosario,
    config: Configuracion,
    documento: Documento | None = None,
) -> list[Frecuencia]:
    stopwords = {
        clave(str(p)) for p in (config.obtener("repeticion.stopwords", []) or [])
    }
    min_longitud = int(config.obtener("repeticion.min_longitud", 4) or 4)
    incluir_glosario = bool(config.obtener("repeticion.incluir_glosario", False))
    claves_glosario = {
        clave(p)
        for p in (
            *glosario.nombres,
            *glosario.alias,
            *glosario.toponimos,
            *glosario.terminos,
            *glosario.variantes,
        )
    }

    conteos: dict[str, int] = {}
    primera_linea: dict[str, int] = {}
    primer_offset: dict[str, int] = {}
    por_capitulo: dict[str, dict[str, int]] = {}
    capitulos = documento.capitulos if documento else ()
    indices_linea = indices_de_linea(texto)

    for match in _PALABRA.finditer(texto):
        palabra = match.group(0)
        normalizada = palabra.casefold()
        if len(palabra) < min_longitud:
            continue
        if normalizada in stopwords:
            continue
        if not incluir_glosario and clave(palabra) in claves_glosario:
            continue
        conteos[normalizada] = conteos.get(normalizada, 0) + 1
        if normalizada not in primer_offset:
            primer_offset[normalizada] = match.start()
            primera_linea[normalizada] = linea_en(indices_linea, match.start())
        capitulo = _capitulo_de(capitulos, match.start())
        if capitulo is not None:
            capitulo_conteo = por_capitulo.setdefault(normalizada, {})
            capitulo_conteo[capitulo.titulo] = (
                capitulo_conteo.get(capitulo.titulo, 0) + 1
            )

    frecuencias = [
        Frecuencia(
            palabra=palabra,
            conteo=conteo,
            linea=primera_linea.get(palabra, 1),
            inicio=primer_offset.get(palabra, 0),
            por_capitulo=por_capitulo.get(palabra, {}),
        )
        for palabra, conteo in conteos.items()
    ]
    frecuencias.sort(key=lambda f: (-f.conteo, f.palabra))
    return frecuencias


@registrar
class FrecuenciaLexica:
    id = "REP-001"
    nivel = Nivel.L3
    descripcion = "Informa de las palabras de contenido más repetidas."
    prioridad = 90
    por_defecto = True

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        minimo = int(ctx.config.obtener("repeticion.minimo_palabras", 8) or 8)
        top = int(ctx.config.obtener("repeticion.top", 50) or 50)
        if top < 0:
            return
        frecuencias = calcular_frecuencias(
            texto, ctx.glosario, ctx.config, ctx.documento
        )
        mostrar_capitulos = bool(ctx.config.obtener("repeticion.por_capitulo", True))
        seleccionadas = [f for f in frecuencias if f.conteo >= minimo]
        if top > 0:
            seleccionadas = seleccionadas[:top]
        total_palabras = max(1, contar_palabras(texto))

        for frecuencia in seleccionadas:
            posicion = frecuencia.inicio
            fin = posicion + len(frecuencia.palabra)
            detalle_capitulos = ""
            if mostrar_capitulos and frecuencia.por_capitulo:
                detalle_capitulos = " Capítulos: " + "; ".join(
                    f"{titulo}: {conteo}"
                    for titulo, conteo in frecuencia.por_capitulo.items()
                )
            densidad = frecuencia.conteo / total_palabras * 1000
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=posicion,
                fin=max(posicion + 1, fin),
                sugerencia=None,
                confianza=1.0,
                nota=(
                    f"{frecuencia.conteo} apariciones; "
                    f"{densidad:.1f} por 1000 palabras.{detalle_capitulos}"
                ),
            )
            if hallazgo:
                yield hallazgo


@registrar
class ParrafosDuplicados:
    id = "REP-002"
    nivel = Nivel.L3
    descripcion = "Señala párrafos duplicados exactos o casi idénticos."
    prioridad = 91
    por_defecto = True

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        minimo = int(ctx.config.obtener("duplicados.minimo_palabras", 8) or 8)
        umbral = float(ctx.config.obtener("duplicados.similitud", 92) or 92)
        maximo = int(ctx.config.obtener("duplicados.maximo_parrafos", 2000) or 2000)

        exactos: dict[str, tuple[int, int]] = {}
        previos: list[tuple[str, int, int]] = []

        for indice, (parrafo, inicio, fin) in enumerate(parrafos_con_offset(texto)):
            if indice >= maximo:
                break
            normalizado = " ".join(parrafo.split()).casefold()
            if contar_palabras(normalizado) < minimo:
                continue
            linea = texto.count("\n", 0, inicio) + 1
            huella = hashlib.sha1(normalizado.encode("utf-8")).hexdigest()

            if huella in exactos:
                linea_original, _ = exactos[huella]
                hallazgo = crear_hallazgo(
                    texto,
                    regla=self.id,
                    nivel=self.nivel,
                    inicio=inicio,
                    fin=fin,
                    sugerencia=None,
                    confianza=1.0,
                    nota=f"Duplicado exacto del párrafo de la línea {linea_original}.",
                    radio_contexto=20,
                )
                if hallazgo:
                    yield hallazgo
            else:
                encontrado = False
                for normal_previo, inicio_previo, _ in reversed(previos[-200:]):
                    if abs(len(normalizado) - len(normal_previo)) > max(
                        20, int(max(len(normalizado), len(normal_previo)) * 0.25)
                    ):
                        continue
                    similitud = ratio(normalizado, normal_previo)
                    if similitud >= umbral:
                        linea_original = texto.count("\n", 0, inicio_previo) + 1
                        hallazgo = crear_hallazgo(
                            texto,
                            regla=self.id,
                            nivel=self.nivel,
                            inicio=inicio,
                            fin=fin,
                            sugerencia=None,
                            confianza=round(similitud / 100, 3),
                            nota=(
                                f"Duplicado difuso ({similitud:.1f}%) del párrafo "
                                f"de la línea {linea_original}."
                            ),
                            radio_contexto=20,
                        )
                        if hallazgo:
                            yield hallazgo
                        encontrado = True
                        break
                if not encontrado:
                    exactos[huella] = (linea, inicio)
                    previos.append((normalizado, inicio, fin))


@registrar
class ResiduoIA:
    id = "REP-003"
    nivel = Nivel.L3
    descripcion = "Señala frases típicas de residuo de IA sin reescribirlas."
    prioridad = 92
    por_defecto = True

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        frases = ctx.config.obtener("residuo_ia.frases", []) or []
        if not isinstance(frases, list) or not frases:
            return
        patron = re.compile(
            r"(?<![^\W\d_])(?:"
            + "|".join(re.escape(str(f)) for f in sorted(frases, key=len, reverse=True))
            + r")(?![^\W\d_])",
            flags=re.IGNORECASE | re.UNICODE,
        )
        for match in patron.finditer(texto):
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=None,
                confianza=0.5,
                nota="Frase de residuo de IA; solo informe, no se reescribe.",
            )
            if hallazgo:
                yield hallazgo


@registrar
class FrasesLargas:
    id = "REP-004"
    nivel = Nivel.L3
    descripcion = "Señala frases que superan el umbral de longitud configurado."
    prioridad = 93
    por_defecto = True

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        maximo = int(ctx.config.obtener("repeticion.longitud_frase", 60) or 60)
        if maximo <= 0:
            return
        for oracion, inicio, fin in dividir_oraciones(texto):
            if oracion.lstrip().startswith("#"):
                continue
            palabras = contar_palabras(oracion)
            if palabras <= maximo:
                continue
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=inicio,
                fin=fin,
                sugerencia=None,
                confianza=0.6,
                nota=f"Frase de {palabras} palabras (umbral: {maximo}).",
            )
            if hallazgo:
                yield hallazgo
