"""Exportación a PDF: informe y manuscrito corregido (historia inventada)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("reportlab")
pdfminer = pytest.importorskip("pdfminer.high_level")

from click.testing import CliRunner  # noqa: E402
from tests.conftest import aplicar_hallazgos  # noqa: E402

from onirifix.cli import cli  # noqa: E402
from onirifix.config import Configuracion  # noqa: E402
from onirifix.informes import escribir_informes  # noqa: E402
from onirifix.informes.pdf import escribir_manuscrito_pdf  # noqa: E402
from onirifix.io.cargadores import detectar_capitulos  # noqa: E402
from onirifix.modelo import (  # noqa: E402
    Documento,
    Glosario,
    ResultadoCorreccion,
)
from onirifix.nucleo.motor import Motor  # noqa: E402
from onirifix.nucleo.parches import aplicar_parches, seleccionar_parches  # noqa: E402

TEXTO = (
    "# Capítulo 1\n\n"
    "Lina miró el faro apagado... No había luz desde el invierno.\n\n"
    "—¿Subimos?\n\nPreguntó Bruno sin soltar el farol.\n\n"
    "—Aun asi, alguien tiene que hacerlo —dijo ella.\n\n"
    "# Capítulo 2\n\n"
    "El viento golpeaba la puerta. Bruno se rio sin ganas.\n"
)


def _texto_pdf(ruta: Path) -> str:
    # El texto justificado sale con espacios dobles: se normalizan por línea.
    return "\n".join(" ".join(linea.split()) for linea in pdfminer.extract_text(str(ruta)).split("\n"))


def _analisis(tmp_path: Path):
    ruta = tmp_path / "faro.md"
    ruta.write_text(TEXTO, encoding="utf-8")
    documento = Documento(ruta=ruta, texto=TEXTO, capitulos=detectar_capitulos(TEXTO))
    return Motor(Configuracion(), Glosario()).analizar(documento)


def test_informe_pdf_tiene_resumen_reglas_y_capitulos(tmp_path: Path) -> None:
    analisis = _analisis(tmp_path)
    parches = seleccionar_parches(
        analisis.hallazgos, l2_seguras=Configuracion().l2_seguras()
    )
    texto, aplicados, omitidos = aplicar_parches(analisis.documento.texto, parches)
    correccion = ResultadoCorreccion(
        analisis=analisis, texto_corregido=texto, parches_seleccionados=parches,
        aplicados=aplicados, omitidos=omitidos,
    )
    rutas = escribir_informes(
        analisis, tmp_path / "informes", formatos="pdf", correccion=correccion, segundos=1.5
    )
    assert set(rutas) == {"pdf", "manuscrito_pdf"}
    informe = _texto_pdf(rutas["pdf"])
    assert "Informe editorial" in informe
    assert "Resumen por nivel" in informe
    assert "Hallazgos por capítulo" in informe
    assert "DIA-006" in informe
    assert "1.5 s" in informe
    manuscrito = _texto_pdf(rutas["manuscrito_pdf"])
    assert "—¿Subimos? —preguntó Bruno" in manuscrito
    assert "Lina miró el faro apagado…" in manuscrito


def test_manuscrito_pdf_un_capitulo_por_pagina(tmp_path: Path) -> None:
    ruta = escribir_manuscrito_pdf(TEXTO, tmp_path / "m.pdf", titulo="El faro")
    paginas = pdfminer.extract_text(str(ruta)).split("\f")
    assert "El faro" in paginas[0]
    con_capitulo = [i for i, p in enumerate(paginas) if "Capítulo" in p]
    assert len(con_capitulo) == 2 and con_capitulo[0] != con_capitulo[1]
    assert "#" not in "".join(paginas)


def test_l2_seguras_solo_deja_pasar_su_umbral() -> None:
    from onirifix.modelo import Hallazgo, Nivel

    def h(regla: str, conf: float) -> Hallazgo:
        return Hallazgo(regla, Nivel.L2, 0, 1, "a", "b", conf, 1, 1, "a")

    parches = seleccionar_parches(
        [h("DIA-006", 0.92), h("DIA-006", 0.75), h("TIL-002", 0.99)],
        l2_seguras={"DIA-006": 0.9},
    )
    assert [(p.regla, p.confianza) for p in parches] == [("DIA-006", 0.92)]


def test_cli_corregir_pdf_con_l2_seguras(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ONIRIFIX_HOME", str(tmp_path / "home"))
    ruta = tmp_path / "faro.md"
    ruta.write_text(TEXTO, encoding="utf-8")
    runner = CliRunner()
    assert runner.invoke(cli, ["init"]).exit_code == 0
    resultado = runner.invoke(
        cli,
        ["corregir", str(ruta), "--l2-seguras", "--aplicar", "--salida",
         str(tmp_path / "out"), "--formato", "json,pdf"],
    )
    assert resultado.exit_code == 0, resultado.output
    assert (tmp_path / "out" / "informe.pdf").exists()
    assert (tmp_path / "out" / "manuscrito-corregido.pdf").exists()
    corregido = ruta.read_text(encoding="utf-8")
    assert "—¿Subimos? —preguntó Bruno" in corregido
    assert "Análisis:" in resultado.output
    # El original tiene copia de seguridad.
    assert list((tmp_path / "home").rglob("faro*.md*"))
    assert aplicar_hallazgos([], corregido) == corregido


def test_titulo_de_portada_sale_del_preambulo(tmp_path: Path) -> None:
    from onirifix.informes import _titulo

    texto = "El faro apagado\n\n# Capítulo 1\n\nLina subió.\n"
    doc = Documento(ruta=tmp_path / "borrador.md", texto=texto, capitulos=detectar_capitulos(texto))
    assert _titulo(doc) == "El faro apagado"
    sin = Documento(ruta=tmp_path / "borrador.md", texto="# Capítulo 1\n\nLina.\n",
                    capitulos=detectar_capitulos("# Capítulo 1\n\nLina.\n"))
    assert _titulo(sin) == "borrador"
