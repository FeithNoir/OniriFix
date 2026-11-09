"""Carga de manuscritos en texto plano, Markdown, Word o PDF."""

from __future__ import annotations

from pathlib import Path

try:  # pragma: no cover
    import regex as re
except ImportError:  # pragma: no cover
    import re  # type: ignore[no-redef]

from onirifix.modelo import Capitulo, Documento

SUFIJOS_TEXTO = {".txt", ".md", ".markdown", ".rst", ".text"}
SUFIJOS_DOCX = {".docx"}
SUFIJOS_PDF = {".pdf"}
# Formatos que no se reescriben en su sitio: el texto corregido va a un .md.
CODIFICACIONES_DERIVADAS = {"docx", "pdf"}

_ORDINALES = (
    r"uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|"
    r"primer[oa]?|segund[oa]|tercer[oa]?|cuart[oa]|quint[oa]|sext[oa]|"
    r"s[eé]ptim[oa]|octav[oa]|noven[oa]|d[eé]cim[oa]|[uú]ltim[oa]|final"
)
# Encabezado de capítulo en texto plano: «Capítulo 3», «CAPÍTULO III: El faro»,
# «Epílogo: …». Una línea de prosa que empieza por «Parte de…» o «Libro de
# cuentas» no es un capítulo, así que tras la palabra clave se exige un número
# u ordinal (o nada, en prólogos y epílogos) y, opcionalmente, un título.
PATRON_ENCABEZADO = re.compile(
    r"^\s*(?:(?:cap[ií]tulo|cap\.|parte|libro|acto|escena)\s+(?:\d+|[ivxlcdm]+|"
    + _ORDINALES
    + r")\b(?:\s*[:.—–-]\s*\S.*)?"
    r"|(?:pr[oó]logo|ep[ií]logo|interludio|prefacio|introducci[oó]n|ap[eé]ndice)"
    r"(?:\s*[:.—–-]\s*\S.*)?)\s*$",
    flags=re.IGNORECASE | re.UNICODE,
)
_MAXIMO_ENCABEZADO = 90
_PATRON_MARKDOWN = re.compile(r"^\s*#{1,3}\s+\S")


class ErrorLectura(ValueError):
    pass


def sufijo_soportado(ruta: Path) -> bool:
    return ruta.suffix.lower() in SUFIJOS_TEXTO | SUFIJOS_DOCX | SUFIJOS_PDF


def leer_texto(ruta: Path) -> tuple[str, str]:
    ruta = ruta.expanduser()
    if not ruta.exists():
        raise ErrorLectura(f"No existe el archivo: {ruta}")
    if ruta.suffix.lower() in SUFIJOS_DOCX:
        return _leer_docx(ruta), "docx"
    if ruta.suffix.lower() in SUFIJOS_PDF:
        from onirifix.io.pdf import ErrorPdf, leer_pdf

        try:
            return leer_pdf(ruta), "pdf"
        except ErrorPdf as exc:
            raise ErrorLectura(str(exc)) from exc
    if ruta.suffix.lower() not in SUFIJOS_TEXTO:
        raise ErrorLectura(
            f"Formato no soportado: {ruta.suffix or '(sin extensión)'}. "
            "Usa .txt, .md, .docx o .pdf."
        )

    datos = ruta.read_bytes()
    if datos.startswith(b"\xef\xbb\xbf"):
        texto = datos.decode("utf-8-sig")
        encoding = "utf-8"
    else:
        for encoding in ("utf-8", "cp1252", "latin-1"):
            try:
                texto = datos.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:  # pragma: no cover - latin-1 nunca falla
            raise ErrorLectura(f"No se pudo decodificar {ruta}.")

    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    return texto, encoding


def _leer_docx(ruta: Path) -> str:
    try:
        from docx import Document  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise ErrorLectura(
            "Para leer .docx instala el extra: pip install -e '.[docx]'"
        ) from exc

    documento = Document(str(ruta))
    bloques: list[str] = []
    for parrafo in documento.paragraphs:
        bloques.append(parrafo.text)
    for tabla in documento.tables:
        for fila in tabla.rows:
            celdas = [celda.text.strip() for celda in fila.cells]
            if any(celdas):
                bloques.append(" | ".join(celdas))
    texto = "\n".join(bloques)
    return texto.replace("\r\n", "\n").replace("\r", "\n")


def detectar_capitulos(texto: str) -> tuple[Capitulo, ...]:
    """Detecta capítulos/escenas por encabezados o líneas canónicas."""

    inicios: list[tuple[int, int, str]] = []
    posicion = 0
    lineas = texto.splitlines(keepends=True)
    # Si el manuscrito usa Markdown, los encabezados manda: una línea de prosa
    # que empiece por «Prefacio» no debe convertirse en un capítulo falso.
    hay_markdown = any(_PATRON_MARKDOWN.match(linea.rstrip("\n")) for linea in lineas)
    for numero_linea, contenido_linea in enumerate(lineas, start=1):
        contenido = contenido_linea.rstrip("\n")
        es_encabezado = (
            bool(_PATRON_MARKDOWN.match(contenido))
            if hay_markdown
            else len(contenido) <= _MAXIMO_ENCABEZADO and bool(PATRON_ENCABEZADO.match(contenido))
        )
        if es_encabezado:
            inicios.append((posicion, numero_linea, contenido.strip()))
        posicion += len(contenido_linea)

    if not inicios:
        return (Capitulo(titulo="Texto completo", inicio=0, fin=len(texto), linea=1),)

    capitulos: list[Capitulo] = []
    if inicios[0][0] > 0 and texto[: inicios[0][0]].strip():
        capitulos.append(
            Capitulo(titulo="Preámbulo", inicio=0, fin=inicios[0][0], linea=1)
        )
    for indice, (inicio, numero_linea, titulo) in enumerate(inicios):
        fin = inicios[indice + 1][0] if indice + 1 < len(inicios) else len(texto)
        capitulos.append(
            Capitulo(
                titulo=titulo.lstrip("#").strip() or f"Capítulo {indice + 1}",
                inicio=inicio,
                fin=fin,
                linea=numero_linea,
            )
        )
    return tuple(capitulos)


def cargar_documento(ruta: Path) -> Documento:
    texto, encoding = leer_texto(ruta)
    return Documento(
        ruta=ruta,
        texto=texto,
        encoding=encoding,
        capitulos=detectar_capitulos(texto),
    )


def escribir_texto(ruta: Path, texto: str, encoding: str = "utf-8") -> Path:
    ruta = ruta.expanduser()
    if encoding in CODIFICACIONES_DERIVADAS:
        encoding = "utf-8"
    if ruta.suffix.lower() in SUFIJOS_DOCX | SUFIJOS_PDF:
        raise ErrorLectura(
            f"OniriFix no reescribe {ruta.suffix}: guarda el texto como .md o .txt "
            "(o exporta el manuscrito corregido a PDF)."
        )
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding=encoding, newline="\n") as archivo:
        archivo.write(texto)
    return ruta


def destino_corregido(ruta: Path) -> Path:
    """Dónde se guarda el texto corregido de un .docx o .pdf (nunca se pisan)."""

    return ruta.with_name(f"{ruta.stem}.corregido.md")
