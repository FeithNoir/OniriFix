"""Lectura de manuscritos PDF: párrafos, saltos de página, cabeceras y capítulos.

Los PDF de prueba se generan con reportlab a partir de un relato inventado,
imitando lo que exporta Word: texto alineado a la izquierda, número de página
y cabecera repetida en cada hoja.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from onirifix.io.cargadores import ErrorLectura, cargar_documento
from onirifix.io.pdf import Bloque, Linea, Pagina, leer_pdf, reconstruir_texto

reportlab = pytest.importorskip("reportlab")

PARRAFO_LARGO = (
    "La barca avanzaba despacio entre la niebla del puerto mientras los "
    "pescadores recogían las redes y el viento del norte empujaba las velas "
    "remendadas hacia la escollera. Nadie hablaba. "
) * 6


def _crear_pdf(ruta: Path) -> None:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    lienzo = canvas.Canvas(str(ruta), pagesize=letter)
    ancho, alto = letter
    pagina = 1

    def cabecera_y_pie() -> None:
        lienzo.setFont("Helvetica", 9)
        lienzo.drawString(72, alto - 40, "El faro apagado — borrador")
        lienzo.drawString(ancho / 2, 30, str(pagina))
        lienzo.setFont("Helvetica", 12)

    def nueva_pagina() -> None:
        nonlocal pagina, y
        lienzo.showPage()
        pagina += 1
        cabecera_y_pie()
        y = alto - 90

    cabecera_y_pie()
    y = alto - 90
    from reportlab.lib.utils import simpleSplit

    bloques = [
        ("titulo", "Capítulo 1"),
        ("p", "—No pienso volver —dijo Lina."),
        ("p", PARRAFO_LARGO),
        ("p", PARRAFO_LARGO),
        ("p", PARRAFO_LARGO),
        ("p", "Tomás guardó silencio."),
        ("titulo", "Capítulo 2"),
        ("p", "Parte de la tripulación dormía en cubierta."),
        ("p", "El capitán revisó la carta de navegación con cui-"),
        ("p", "dado antes de dar la orden."),
    ]
    for tipo, texto in bloques:
        if tipo == "titulo":
            if y < alto - 100:
                nueva_pagina()
            lienzo.setFont("Helvetica-Bold", 16)
            lienzo.drawString(72, y, texto)
            lienzo.setFont("Helvetica", 12)
            y -= 36
            continue
        lineas = [texto] if texto.endswith("cui-") else simpleSplit(texto, "Helvetica", 12, ancho - 144)
        for linea in lineas:
            if y < 90:
                nueva_pagina()
            lienzo.drawString(72, y, linea)
            y -= 15
        if not texto.endswith("cui-"):
            y -= 12
    lienzo.save()


@pytest.fixture
def pdf_relato(tmp_path: Path) -> Path:
    ruta = tmp_path / "relato.pdf"
    _crear_pdf(ruta)
    return ruta


def _requiere(motor: str) -> None:
    if motor == "pdfminer":
        pytest.importorskip("pdfminer")


@pytest.mark.parametrize("motor", ["pdftotext", "pdfminer"])
def test_pdf_reconstruye_parrafos_y_capitulos(pdf_relato: Path, motor: str) -> None:
    if motor == "pdftotext" and shutil.which("pdftotext") is None:
        pytest.skip("sin Poppler")
    _requiere(motor)
    texto = leer_pdf(pdf_relato, motor=motor)
    parrafos = texto.strip().split("\n\n")

    assert "# Capítulo 1" in parrafos and "# Capítulo 2" in parrafos
    # Cabecera repetida y números de página fuera.
    assert "borrador" not in texto
    assert not any(p.strip().isdigit() for p in parrafos)
    # El párrafo largo cruza de página y sigue entero.
    assert PARRAFO_LARGO.strip() in parrafos
    assert "—No pienso volver —dijo Lina." in parrafos
    # «Parte de…» es prosa, no un encabezado.
    assert "Parte de la tripulación dormía en cubierta." in parrafos
    # Partición silábica deshecha.
    assert "con cuidado antes de dar la orden." in texto


def test_pdf_como_documento(pdf_relato: Path) -> None:
    if shutil.which("pdftotext") is None:
        pytest.importorskip("pdfminer")
    documento = cargar_documento(pdf_relato)
    assert documento.encoding == "pdf"
    assert [c.titulo for c in documento.capitulos] == ["Capítulo 1", "Capítulo 2"]


def test_pdf_sin_texto(tmp_path: Path) -> None:
    from reportlab.pdfgen import canvas

    ruta = tmp_path / "escaneo.pdf"
    lienzo = canvas.Canvas(str(ruta))
    lienzo.rect(100, 100, 200, 200)
    lienzo.save()
    with pytest.raises(ErrorLectura, match="texto extraíble"):
        cargar_documento(ruta)


def _linea(texto: str, x1: float, y0: float) -> Linea:
    return Linea(texto=texto, x0=72, x1=x1, y0=y0)


def test_reconstruir_fusiona_linea_partida_en_bloques() -> None:
    # Una línea justificada a la fuerza llega troceada en varios bloques.
    pagina = Pagina(
        alto=792,
        bloques=[
            Bloque([_linea("—Vaya. Seguro que", 200, 100)]),
            Bloque([Linea(texto="estás", x0=300, x1=330, y0=100)]),
            Bloque([Linea(texto="cansado.", x0=480, x1=530, y0=100)]),
            Bloque([_linea("Ana se encogió de hombros.", 300, 130)]),
        ],
    )
    texto = reconstruir_texto([pagina])
    assert texto.split("\n\n")[0] == "—Vaya. Seguro que estás cansado."


def test_reconstruir_no_une_dialogo_tras_salto_de_pagina() -> None:
    primera = Pagina(alto=792, bloques=[Bloque([_linea("Ana miró el mar sin decir nada", 400, 700)])])
    segunda = Pagina(alto=792, bloques=[Bloque([_linea("—¿Vienes?", 150, 80)])])
    texto = reconstruir_texto([primera, segunda])
    assert texto.strip().split("\n\n") == ["Ana miró el mar sin decir nada", "—¿Vienes?"]
