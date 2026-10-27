"""Pruebas de carga y escritura de manuscritos."""

from __future__ import annotations

from pathlib import Path

import pytest

from onirifix.io.cargadores import (
    ErrorLectura,
    cargar_documento,
    detectar_capitulos,
    escribir_texto,
    leer_texto,
    sufijo_soportado,
)


def test_leer_texto_utf8_sin_bom(tmp_path: Path) -> None:
    ruta = tmp_path / "texto.md"
    ruta.write_bytes("Año de nieve".encode())
    texto, encoding = leer_texto(ruta)
    assert texto == "Año de nieve"
    assert encoding == "utf-8"


def test_leer_texto_utf8_con_bom_lo_elimina(tmp_path: Path) -> None:
    ruta = tmp_path / "texto.md"
    ruta.write_bytes(b"\xef\xbb\xbf# Titulo\n")
    texto, encoding = leer_texto(ruta)
    assert texto.startswith("# Titulo")
    assert "\ufeff" not in texto
    assert encoding == "utf-8"


def test_leer_texto_cp1252(tmp_path: Path) -> None:
    ruta = tmp_path / "texto.txt"
    ruta.write_bytes("canción".encode("cp1252"))
    texto, encoding = leer_texto(ruta)
    assert texto == "canción"
    assert encoding == "cp1252"


def test_leer_texto_normaliza_saltos(tmp_path: Path) -> None:
    ruta = tmp_path / "texto.txt"
    ruta.write_bytes(b"uno\r\ndos\rtres")
    texto, _ = leer_texto(ruta)
    assert texto == "uno\ndos\ntres"


def test_leer_texto_inexistente(tmp_path: Path) -> None:
    with pytest.raises(ErrorLectura, match="No existe"):
        leer_texto(tmp_path / "no.md")


def test_formato_no_soportado(tmp_path: Path) -> None:
    ruta = tmp_path / "texto.pdf"
    ruta.write_bytes(b"%PDF")
    with pytest.raises(ErrorLectura, match="Formato no soportado"):
        leer_texto(ruta)


def test_sufijos_soportados() -> None:
    assert sufijo_soportado(Path("a.md"))
    assert sufijo_soportado(Path("a.TXT"))
    assert sufijo_soportado(Path("a.docx"))
    assert not sufijo_soportado(Path("a.pdf"))


def test_detectar_capitulos_markdown_y_preamble() -> None:
    texto = "Prefacio breve.\n\n# Capítulo 1\n\nTexto.\n\n## Segunda parte\n\nMás."
    capitulos = detectar_capitulos(texto)
    assert [c.titulo for c in capitulos] == [
        "Preámbulo",
        "Capítulo 1",
        "Segunda parte",
    ]
    assert capitulos[0].inicio == 0
    assert capitulos[-1].fin == len(texto)
    assert [c.linea for c in capitulos] == [1, 3, 7]


def test_detectar_capitulos_sin_encabezados() -> None:
    (capitulo,) = detectar_capitulos("Solo texto.")
    assert capitulo.titulo == "Texto completo"
    assert (capitulo.inicio, capitulo.fin, capitulo.linea) == (0, 11, 1)


def test_detectar_capitulos_linea_canonica() -> None:
    capitulos = detectar_capitulos("Capítulo primero\nTexto\nEpílogo\nFinal")
    assert [c.titulo for c in capitulos] == ["Capítulo primero", "Epílogo"]


def test_cargar_documento(tmp_path: Path) -> None:
    ruta = tmp_path / "obra.md"
    ruta.write_text("# Uno\nHola mundo.\n", encoding="utf-8")
    documento = cargar_documento(ruta)
    assert documento.ruta == ruta
    assert documento.palabras == 4
    assert documento.capitulos[0].titulo == "Uno"


def test_escribir_texto_crea_directorios_y_normaliza_saltos(tmp_path: Path) -> None:
    ruta = tmp_path / "sub" / "salida.md"
    escribir_texto(ruta, "uno\r\ndos", encoding="utf-8")
    assert ruta.read_text(encoding="utf-8") == "uno\ndos"


def test_escribir_docx_no_implementado(tmp_path: Path) -> None:
    with pytest.raises(ErrorLectura, match="docx"):
        escribir_texto(tmp_path / "salida.docx", "hola", encoding="docx")
