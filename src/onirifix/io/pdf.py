"""Lectura de manuscritos en PDF (exportados desde Word, LibreOffice…).

Un PDF no guarda párrafos: guarda líneas posicionadas en páginas. Este módulo
reconstruye el texto corrido:

1. extrae bloques y líneas con sus coordenadas, con ``pdftotext -bbox-layout``
   (Poppler) si está instalado o con ``pdfminer.six`` (extra ``[pdf]``);
2. descarta cabeceras, pies y números de página repetidos;
3. une las líneas de cada párrafo, deshaciendo la partición silábica con guion;
4. une los párrafos que cruzan un salto de página;
5. marca los encabezados de capítulo como ``# Capítulo N`` para que la
   detección de capítulos sea fiable.

El resultado es Markdown sencillo: un párrafo por bloque, separados por una
línea en blanco. El PDF original nunca se modifica.
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from onirifix.io.cargadores import PATRON_ENCABEZADO


class ErrorPdf(ValueError):
    pass


@dataclass(slots=True)
class Linea:
    texto: str
    x0: float
    x1: float
    y0: float


@dataclass(slots=True)
class Bloque:
    lineas: list[Linea] = field(default_factory=list)

    @property
    def texto(self) -> str:
        return " ".join(linea.texto for linea in self.lineas)


@dataclass(slots=True)
class Pagina:
    alto: float
    bloques: list[Bloque] = field(default_factory=list)


_FINAL_DE_FRASE = tuple(".!?…»”\"'):;")
_SOLO_NUMERO = re.compile(r"^[\W\d_]*\d+[\W\d_]*$|^[ivxlcdm]+$", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Extracción
# ---------------------------------------------------------------------------


def _extraer_pdftotext(ruta: Path, ejecutable: str) -> list[Pagina]:
    try:
        salida = subprocess.run(
            [ejecutable, "-bbox-layout", "-enc", "UTF-8", str(ruta), "-"],
            check=True,
            capture_output=True,
            timeout=600,
        ).stdout.decode("utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError) as exc:
        raise ErrorPdf(f"pdftotext no pudo leer {ruta.name}: {exc}") from exc

    paginas: list[Pagina] = []
    patron_pagina = re.compile(r'<page width="[\d.]+" height="([\d.]+)">(.*?)</page>', re.S)
    patron_bloque = re.compile(r"<block [^>]*>(.*?)</block>", re.S)
    patron_linea = re.compile(
        r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="[\d.]+">(.*?)</line>', re.S
    )
    patron_palabra = re.compile(r"<word [^>]*>(.*?)</word>", re.S)
    for pagina in patron_pagina.finditer(salida):
        actual = Pagina(alto=float(pagina.group(1)))
        for bloque in patron_bloque.finditer(pagina.group(2)):
            lineas = [
                Linea(
                    texto=" ".join(html.unescape(p) for p in patron_palabra.findall(linea.group(4))),
                    x0=float(linea.group(1)),
                    y0=float(linea.group(2)),
                    x1=float(linea.group(3)),
                )
                for linea in patron_linea.finditer(bloque.group(1))
            ]
            lineas = [linea for linea in lineas if linea.texto.strip()]
            if lineas:
                actual.bloques.append(Bloque(lineas))
        paginas.append(actual)
    return paginas


def _extraer_pdfminer(ruta: Path) -> list[Pagina]:
    try:
        from pdfminer.high_level import extract_pages  # type: ignore[import-not-found]
        from pdfminer.layout import (  # type: ignore[import-not-found]
            LAParams,
            LTTextBox,
            LTTextLine,
        )
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise ErrorPdf(
            "Para leer PDF instala Poppler (pdftotext) o el extra: pip install -e \".[pdf]\""
        ) from exc

    paginas: list[Pagina] = []
    try:
        for pagina in extract_pages(str(ruta), laparams=LAParams()):
            alto = float(pagina.height)
            actual = Pagina(alto=alto)
            cajas = [c for c in pagina if isinstance(c, LTTextBox)]
            cajas.sort(key=lambda c: (-c.y1, c.x0))
            for caja in cajas:
                lineas = [
                    Linea(
                        texto=" ".join(linea.get_text().split()),
                        x0=float(linea.x0),
                        x1=float(linea.x1),
                        y0=alto - float(linea.y1),
                    )
                    for linea in caja
                    if isinstance(linea, LTTextLine) and linea.get_text().strip()
                ]
                if lineas:
                    actual.bloques.append(Bloque(lineas))
            paginas.append(actual)
    except Exception as exc:  # pdfminer lanza tipos muy variados
        raise ErrorPdf(f"No se pudo leer el PDF {ruta.name}: {exc}") from exc
    return paginas


def extraer_paginas(ruta: Path, *, motor: str | None = None) -> list[Pagina]:
    """Páginas con bloques y líneas. ``motor`` fuerza ``pdftotext`` o ``pdfminer``."""

    ejecutable = shutil.which("pdftotext")
    if motor == "pdfminer" or (motor is None and ejecutable is None):
        return _extraer_pdfminer(ruta)
    if ejecutable is None:
        raise ErrorPdf("No se encontró pdftotext (Poppler) en el PATH.")
    return _extraer_pdftotext(ruta, ejecutable)


# ---------------------------------------------------------------------------
# Reconstrucción
# ---------------------------------------------------------------------------


def _normalizar_repetido(texto: str) -> str:
    return re.sub(r"\d+", "#", texto.strip().casefold())


def _quitar_cabeceras_y_pies(paginas: list[Pagina]) -> None:
    """Quita números de página y líneas que se repiten arriba o abajo."""

    candidatos: Counter[str] = Counter()
    for pagina in paginas:
        extremos = {id(b): b for b in (pagina.bloques[:1] + pagina.bloques[-1:])}
        for bloque in extremos.values():
            if len(bloque.lineas) == 1:
                candidatos[_normalizar_repetido(bloque.texto)] += 1
    umbral = max(2, int(len(paginas) * 0.3))
    repetidos = {texto for texto, total in candidatos.items() if total >= umbral}

    for pagina in paginas:
        conservar: list[Bloque] = []
        for posicion, bloque in enumerate(pagina.bloques):
            extremo = posicion == 0 or posicion == len(pagina.bloques) - 1
            texto = bloque.texto.strip()
            if extremo and len(bloque.lineas) == 1:
                cerca_del_borde = (
                    bloque.lineas[0].y0 < pagina.alto * 0.12
                    or bloque.lineas[0].y0 > pagina.alto * 0.85
                )
                if _SOLO_NUMERO.match(texto) and cerca_del_borde:
                    continue
                if _normalizar_repetido(texto) in repetidos and len(texto) < 90:
                    continue
            conservar.append(bloque)
        pagina.bloques = conservar


def _fusionar_lineas_partidas(paginas: list[Pagina]) -> None:
    """Reúne los trozos de una misma línea que el extractor separó en bloques.

    Una línea justificada a la fuerza (salto de línea manual en Word) deja
    huecos tan grandes que el extractor parte cada palabra en un bloque propio.
    Los manuscritos son de una sola columna: todo lo que comparte altura en la
    página pertenece a la misma línea.
    """

    for pagina in paginas:
        vistas: dict[int, Linea] = {}
        for bloque in pagina.bloques:
            conservar: list[Linea] = []
            for linea in bloque.lineas:
                clave = round(linea.y0)
                base = vistas.get(clave) or vistas.get(clave - 1) or vistas.get(clave + 1)
                if base is None:
                    vistas[clave] = linea
                    conservar.append(linea)
                    continue
                trozos = sorted(
                    [(base.x0, base.texto), (linea.x0, linea.texto)], key=lambda t: t[0]
                )
                base.texto = " ".join(t for _, t in trozos)
                base.x0 = min(base.x0, linea.x0)
                base.x1 = max(base.x1, linea.x1)
            bloque.lineas = conservar
        pagina.bloques = [b for b in pagina.bloques if b.lineas]


def _unir_lineas(lineas: list[str]) -> str:
    texto = ""
    for linea in lineas:
        linea = linea.strip()
        if not texto:
            texto = linea
        elif re.search(r"\w-$", texto) and linea[:1].islower():
            texto = texto[:-1] + linea  # partición silábica: «capi- tulo»
        else:
            texto = f"{texto} {linea}"
    return texto


def _es_encabezado(bloque: Bloque) -> bool:
    texto = bloque.texto.strip()
    return len(bloque.lineas) == 1 and len(texto) <= 80 and bool(PATRON_ENCABEZADO.match(texto))


def reconstruir_texto(paginas: list[Pagina]) -> str:
    """Convierte páginas con coordenadas en Markdown de párrafos."""

    _fusionar_lineas_partidas(paginas)
    _quitar_cabeceras_y_pies(paginas)
    finales = sorted(linea.x1 for p in paginas for b in p.bloques for linea in b.lineas)
    if not finales:
        return ""
    margen_derecho = finales[int(len(finales) * 0.9)]
    inicios = Counter(round(linea.x0) for p in paginas for b in p.bloques for linea in b.lineas)
    margen_izquierdo = inicios.most_common(1)[0][0]
    ancho = max(margen_derecho - margen_izquierdo, 1.0)
    parrafos: list[str] = []
    pendiente: list[str] = []  # líneas del párrafo en curso
    ultima: Linea | None = None  # última línea del párrafo en curso

    def cerrar() -> None:
        nonlocal pendiente, ultima
        if pendiente:
            parrafos.append(_unir_lineas(pendiente))
        pendiente, ultima = [], None

    for pagina in paginas:
        for indice, bloque in enumerate(pagina.bloques):
            if _es_encabezado(bloque):
                cerrar()
                parrafos.append(f"# {bloque.texto.strip()}")
                continue
            primera = bloque.lineas[0].texto.lstrip()
            # Párrafo que cruza el salto de página: la última línea no cierra
            # la frase y la siguiente página no abre un diálogo, o empieza en
            # minúscula.
            continua = (
                indice == 0
                and ultima is not None
                and (
                    primera[:1].islower()
                    or (
                        not ultima.texto.rstrip().endswith(_FINAL_DE_FRASE)
                        and not primera.startswith(("—", "-", "–", "«", "“", '"'))
                    )
                )
            )
            if not continua:
                cerrar()
            for linea in bloque.lineas:
                # Dentro de un bloque, una línea claramente corta (más de un
                # cuarto del ancho libre) que cierra frase, seguida de otra que
                # empieza en mayúscula o raya, marca el final de un párrafo. El
                # texto alineado a la izquierda deja finales irregulares, así
                # que el umbral es amplio.
                if (
                    ultima is not None
                    and pendiente
                    and ultima.x1 < margen_derecho - ancho * 0.25
                    and (linea.texto[:1].isupper() or linea.texto.startswith(("—", "«")))
                    and ultima.texto.rstrip().endswith(_FINAL_DE_FRASE)
                ):
                    cerrar()
                pendiente.append(linea.texto)
                ultima = linea
    cerrar()
    return "\n\n".join(p for p in parrafos if p.strip()) + "\n"


def leer_pdf(ruta: Path, *, motor: str | None = None) -> str:
    paginas = extraer_paginas(ruta, motor=motor)
    texto = reconstruir_texto(paginas)
    if not texto.strip():
        raise ErrorPdf(
            f"{ruta.name} no tiene texto extraíble (¿es un escaneo?). "
            "Exporta el manuscrito desde el procesador de textos."
        )
    return texto


__all__ = ["ErrorPdf", "leer_pdf", "reconstruir_texto"]
