"""Exportación a PDF: informe editorial y manuscrito corregido.

Usa reportlab (extra ``[pdf]``). Las fuentes se buscan en el sistema (DejaVu,
Liberation, Arial/Georgia de Windows) para cubrir rayas, comillas y tildes; si
no hay ninguna se usa Helvetica/Times, que también cubren el español.
"""

from __future__ import annotations

import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from onirifix.modelo import Hallazgo, Nivel, ResultadoAnalisis, ResultadoCorreccion


class ErrorExportacionPdf(RuntimeError):
    """No se pudo generar el PDF (normalmente, falta reportlab)."""


_NOMBRES_NIVEL = {
    Nivel.L1: "L1 · Mecánico",
    Nivel.L2: "L2 · Asistido",
    Nivel.L3: "L3 · Solo informe",
}
_ENCABEZADO = re.compile(r"^#{1,3}[ \t]+(?P<titulo>.+?)[ \t]*$")


def _reportlab():
    try:
        import reportlab  # noqa: F401
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise ErrorExportacionPdf(
            "Para exportar a PDF instala el extra: pip install 'onirifix[pdf]'."
        ) from exc


# ---------------------------------------------------------------------------
# Fuentes
# ---------------------------------------------------------------------------

_CANDIDATAS = {
    "sans": [
        ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
        ("LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf"),
        ("arial.ttf", "arialbd.ttf"),
        ("Arial.ttf", "Arial Bold.ttf"),
    ],
    "serif": [
        ("DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf"),
        ("LiberationSerif-Regular.ttf", "LiberationSerif-Bold.ttf"),
        ("georgia.ttf", "georgiab.ttf"),
        ("times.ttf", "timesbd.ttf"),
        ("Georgia.ttf", "Georgia Bold.ttf"),
    ],
}
_FUENTES: dict[str, tuple[str, str]] = {}


def _directorios_fuentes() -> list[Path]:
    dirs = [
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
        Path.home() / ".fonts",
        Path("/Library/Fonts"),
        Path("/System/Library/Fonts/Supplemental"),
    ]
    windir = os.environ.get("WINDIR") or os.environ.get("SYSTEMROOT")
    if windir:
        dirs.insert(0, Path(windir) / "Fonts")
    return [d for d in dirs if d.is_dir()]


def _buscar(nombre: str, dirs: list[Path]) -> Path | None:
    for d in dirs:
        directo = d / nombre
        if directo.is_file():
            return directo
        for encontrado in d.rglob(nombre):
            return encontrado
    return None


def _fuente(familia: str) -> tuple[str, str]:
    """Registra (una vez) y devuelve ``(normal, negrita)`` para la familia."""

    if familia in _FUENTES:
        return _FUENTES[familia]
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    dirs = _directorios_fuentes()
    for normal, negrita in _CANDIDATAS[familia]:
        ruta_n, ruta_b = _buscar(normal, dirs), _buscar(negrita, dirs)
        if ruta_n is None:
            continue
        try:
            nombre = f"OniriFix-{familia}"
            pdfmetrics.registerFont(TTFont(nombre, str(ruta_n)))
            nombre_b = nombre
            if ruta_b is not None:
                nombre_b = f"{nombre}-Bold"
                pdfmetrics.registerFont(TTFont(nombre_b, str(ruta_b)))
            pdfmetrics.registerFontFamily(nombre, normal=nombre, bold=nombre_b)
            _FUENTES[familia] = (nombre, nombre_b)
            return _FUENTES[familia]
        except Exception:  # pragma: no cover - fuente corrupta
            continue
    _FUENTES[familia] = (
        ("Helvetica", "Helvetica-Bold") if familia == "sans" else ("Times-Roman", "Times-Bold")
    )
    return _FUENTES[familia]


def _pie(etiqueta: str):
    def dibujar(canvas, doc) -> None:
        sans, _ = _fuente("sans")
        canvas.saveState()
        canvas.setFont(sans, 8)
        canvas.setFillGray(0.45)
        canvas.drawString(doc.leftMargin, 1.2 * 28.35, etiqueta)
        canvas.drawRightString(
            doc.pagesize[0] - doc.rightMargin, 1.2 * 28.35, f"Página {doc.page}"
        )
        canvas.restoreState()

    return dibujar


# ---------------------------------------------------------------------------
# Informe
# ---------------------------------------------------------------------------


def _clave(h: Hallazgo) -> tuple[str, int]:
    return (h.regla, h.inicio)


def _contexto_marcado(h: Hallazgo) -> str:
    """Contexto con el fragmento original en negrita y la sugerencia al lado."""

    contexto = " ".join(h.contexto.split())
    original = " ".join(h.original.split())
    posicion = contexto.find(original) if original else -1
    if posicion < 0:
        return escape(contexto)
    return (
        escape(contexto[:posicion])
        + f"<b>{escape(original)}</b>"
        + escape(contexto[posicion + len(original) :])
    )


def escribir_informe_pdf(
    resultado: ResultadoAnalisis,
    ruta: Path,
    *,
    correccion: ResultadoCorreccion | None = None,
    max_por_regla: int = 300,
    max_aplicados_por_regla: int = 15,
    segundos: float | None = None,
    titulo: str | None = None,
) -> Path:
    """Escribe el informe editorial en PDF y devuelve su ruta."""

    _reportlab()
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        KeepTogether,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    sans, sans_b = _fuente("sans")
    base = ParagraphStyle("base", fontName=sans, fontSize=9, leading=12, alignment=TA_LEFT)
    pequeño = ParagraphStyle("pequeno", parent=base, fontSize=8, leading=10.5)
    sutil = ParagraphStyle("sutil", parent=pequeño, textColor=colors.HexColor("#555555"))
    h1 = ParagraphStyle("h1", parent=base, fontName=sans_b, fontSize=18, leading=22, spaceAfter=8)
    h2 = ParagraphStyle(
        "h2", parent=base, fontName=sans_b, fontSize=13, leading=16, spaceBefore=12, spaceAfter=6,
        textColor=colors.HexColor("#3b2a63"),
    )
    h3 = ParagraphStyle("h3", parent=base, fontName=sans_b, fontSize=10.5, leading=13, spaceBefore=8)

    documento = resultado.documento
    aplicados = {(p.regla, p.inicio) for p in correccion.aplicados} if correccion else set()
    por_regla: dict[str, list[Hallazgo]] = defaultdict(list)
    for h in resultado.hallazgos:
        por_regla[h.regla].append(h)
    nivel_de = {regla: lista[0].nivel for regla, lista in por_regla.items()}

    def estilo_tabla(cabecera_color: str = "#3b2a63") -> TableStyle:
        return TableStyle([
            ("FONT", (0, 0), (-1, -1), sans, 8),
            ("FONT", (0, 0), (-1, 0), sans_b, 8),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(cabecera_color)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f0fa")]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c9c2dc")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ])

    historia: list = []
    nombre = titulo or documento.ruta.name
    historia.append(Paragraph("Informe editorial · OniriFix", h1))
    meta = [
        f"<b>Manuscrito:</b> {escape(nombre)}",
        f"<b>Fecha:</b> {datetime.now():%Y-%m-%d %H:%M}",
        f"<b>Palabras:</b> {documento.palabras:,}".replace(",", "."),
        f"<b>Capítulos detectados:</b> {len(documento.capitulos)}",
        f"<b>Reglas ejecutadas:</b> {len(resultado.reglas_ejecutadas)}",
    ]
    if segundos is not None:
        meta.append(f"<b>Tiempo de análisis:</b> {segundos:.1f} s")
    for linea in meta:
        historia.append(Paragraph(linea, base))
    historia.append(Spacer(1, 6))
    historia.append(Paragraph(
        "Cómo leerlo: <b>L1</b> son correcciones mecánicas que se aplican solas; "
        "<b>L2</b> son correcciones asistidas que solo se aplican si la regla está en la lista de "
        "«L2 seguras» y alcanza su umbral (el resto queda pendiente de revisión humana); "
        "<b>L3</b> son avisos de estilo que nunca se aplican. El fragmento original aparece "
        "en negrita dentro de su contexto.",
        sutil,
    ))

    # Resumen por nivel.
    historia.append(Paragraph("Resumen por nivel", h2))
    filas = [["Nivel", "Hallazgos", "Aplicados", "Pendientes"]]
    for nivel in Nivel:
        lista = resultado.por_nivel(nivel)
        hechos = sum(1 for h in lista if _clave(h) in aplicados)
        filas.append([_NOMBRES_NIVEL[nivel], len(lista), hechos, len(lista) - hechos])
    filas.append([
        "Total", resultado.total, len(aplicados & {_clave(h) for h in resultado.hallazgos}),
        resultado.total - len(aplicados & {_clave(h) for h in resultado.hallazgos}),
    ])
    tabla = Table(filas, colWidths=[6 * cm, 3 * cm, 3 * cm, 3 * cm], repeatRows=1)
    estilo = estilo_tabla()
    estilo.add("FONT", (0, len(filas) - 1), (-1, len(filas) - 1), sans_b, 8)
    tabla.setStyle(estilo)
    historia.append(tabla)

    # Por regla.
    historia.append(Paragraph("Hallazgos por regla", h2))
    filas = [["Regla", "Nivel", "Total", "Aplic.", "Pend.", "Descripción"]]
    for regla, lista in sorted(por_regla.items(), key=lambda it: (nivel_de[it[0]].orden, -len(it[1]))):
        hechos = sum(1 for h in lista if _clave(h) in aplicados)
        filas.append([
            regla, nivel_de[regla].value, len(lista), hechos, len(lista) - hechos,
            Paragraph(escape(resultado.descripciones.get(regla, "")), pequeño),
        ])
    tabla = Table(
        filas, colWidths=[1.6 * cm, 1.1 * cm, 1.3 * cm, 1.3 * cm, 1.3 * cm, 10.4 * cm],
        repeatRows=1,
    )
    tabla.setStyle(estilo_tabla())
    historia.append(tabla)

    # Por capítulo.
    if documento.capitulos:
        historia.append(Paragraph("Hallazgos por capítulo", h2))
        conteo: dict[str, Counter] = defaultdict(Counter)
        orden: list[str] = [c.titulo for c in documento.capitulos]
        for h in resultado.hallazgos:
            capitulo = documento.capitulo_de(h.inicio)
            titulo_cap = capitulo.titulo if capitulo else "(sin capítulo)"
            if titulo_cap not in orden:
                orden.append(titulo_cap)
            conteo[titulo_cap][h.nivel] += 1
        filas = [["Capítulo", "L1", "L2", "L3", "Total"]]
        for titulo_cap in orden:
            c = conteo.get(titulo_cap, Counter())
            filas.append([
                Paragraph(escape(titulo_cap), pequeño),
                c[Nivel.L1], c[Nivel.L2], c[Nivel.L3], sum(c.values()),
            ])
        tabla = Table(filas, colWidths=[9 * cm, 2 * cm, 2 * cm, 2 * cm, 2 * cm], repeatRows=1)
        tabla.setStyle(estilo_tabla())
        historia.append(tabla)

    def seccion(titulo_seccion: str, explicacion: str, filtro, limite: int) -> None:
        reglas = [
            (regla, [h for h in lista if filtro(h)])
            for regla, lista in sorted(por_regla.items(), key=lambda it: (nivel_de[it[0]].orden, it[0]))
        ]
        reglas = [(r, lista) for r, lista in reglas if lista]
        if not reglas:
            return
        historia.append(PageBreak())
        historia.append(Paragraph(titulo_seccion, h2))
        historia.append(Paragraph(explicacion, sutil))
        for regla, lista in reglas:
            lista.sort(key=lambda h: h.inicio)
            cabecera = Paragraph(
                f"{regla} · {escape(resultado.descripciones.get(regla, ''))} "
                f"<font color='#666666'>({len(lista)})</font>",
                h3,
            )
            bloques = [cabecera]
            for h in lista[:limite]:
                capitulo = documento.capitulo_de(h.inicio)
                donde = f"l. {h.linea}" + (f" · {escape(capitulo.titulo)}" if capitulo else "")
                cambio = (
                    f" → <b>{escape(h.sugerencia)}</b>" if h.sugerencia is not None else ""
                )
                nota = f" <i>{escape(h.nota)}</i>" if h.nota else ""
                bloques.append(Paragraph(
                    f"<font color='#666666'>{donde} · conf. {h.confianza:.2f}</font> "
                    f"«{escape(h.original)}»{cambio}<br/>{_contexto_marcado(h)}{nota}",
                    pequeño,
                ))
                bloques.append(Spacer(1, 3))
            if len(lista) > limite:
                bloques.append(Paragraph(
                    f"… y {len(lista) - limite} más (están todos en hallazgos.csv).", sutil
                ))
            historia.append(KeepTogether(bloques[:3]))
            historia.extend(bloques[3:])

    seccion(
        "Avisos de estilo (L3)",
        "Señales para el autor o el editor: repeticiones, muletillas, posibles restos de "
        "borrador. Nunca se aplican solas.",
        lambda h: h.nivel == Nivel.L3,
        max_por_regla,
    )
    seccion(
        "Pendientes de revisión",
        "Correcciones con sugerencia que no se aplicaron: necesitan el criterio del autor.",
        lambda h: h.nivel != Nivel.L3 and _clave(h) not in aplicados,
        max_por_regla,
    )
    if aplicados:
        seccion(
            "Cambios aplicados (muestra)",
            f"Se muestran hasta {max_aplicados_por_regla} cambios por regla; el diff y el CSV "
            "tienen la lista completa.",
            lambda h: _clave(h) in aplicados,
            max_aplicados_por_regla,
        )
    if resultado.errores:
        historia.append(Paragraph("Errores de reglas", h2))
        for error in resultado.errores:
            historia.append(Paragraph(escape(error), pequeño))

    ruta = Path(ruta).expanduser()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(ruta), pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        topMargin=1.8 * cm, bottomMargin=2 * cm,
        title=f"Informe OniriFix · {nombre}", author="OniriFix",
    )
    pie = _pie(f"OniriFix · informe de {nombre}")
    doc.build(historia, onFirstPage=pie, onLaterPages=pie)
    return ruta


# ---------------------------------------------------------------------------
# Manuscrito corregido
# ---------------------------------------------------------------------------


def escribir_manuscrito_pdf(
    texto: str,
    ruta: Path,
    *,
    titulo: str | None = None,
    subtitulo: str | None = None,
) -> Path:
    """Maqueta el texto (Markdown ligero: ``# Capítulo``) como un PDF legible."""

    _reportlab()
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

    serif, serif_b = _fuente("serif")
    cuerpo = ParagraphStyle(
        "cuerpo", fontName=serif, fontSize=10, leading=13.6, alignment=TA_JUSTIFY,
        firstLineIndent=0.6 * cm, spaceAfter=1,
    )
    capitulo = ParagraphStyle(
        "capitulo", fontName=serif_b, fontSize=15, leading=19, alignment=TA_CENTER,
        spaceBefore=2.2 * cm, spaceAfter=1 * cm,
    )
    portada = ParagraphStyle(
        "portada", fontName=serif_b, fontSize=20, leading=25, alignment=TA_CENTER,
        spaceBefore=5 * cm, spaceAfter=0.8 * cm,
    )
    nota = ParagraphStyle("nota", parent=cuerpo, alignment=TA_CENTER, firstLineIndent=0, fontSize=9)

    historia: list = []
    if titulo:
        historia.append(Paragraph(escape(titulo), portada))
        if subtitulo:
            historia.append(Paragraph(escape(subtitulo), nota))
        historia.append(PageBreak())

    primero = True
    for bloque in re.split(r"\n[ \t]*\n", texto.replace("\r\n", "\n")):
        bloque = bloque.strip()
        if not bloque:
            continue
        encabezado = _ENCABEZADO.match(bloque) if "\n" not in bloque else None
        if encabezado:
            if not primero:
                historia.append(PageBreak())
            historia.append(Paragraph(escape(encabezado.group("titulo")), capitulo))
        else:
            for linea in bloque.split("\n"):
                linea = linea.strip()
                if linea:
                    historia.append(Paragraph(escape(linea), cuerpo))
        primero = False
    if not historia:
        historia.append(Spacer(1, 1))

    ruta = Path(ruta).expanduser()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(ruta), pagesize=A5, leftMargin=1.7 * cm, rightMargin=1.7 * cm,
        topMargin=1.7 * cm, bottomMargin=2 * cm,
        title=titulo or ruta.stem, author="OniriFix",
    )
    pie = _pie(titulo or ruta.stem)
    doc.build(historia, onFirstPage=lambda c, d: None, onLaterPages=pie)
    return ruta


__all__ = ["ErrorExportacionPdf", "escribir_informe_pdf", "escribir_manuscrito_pdf"]
