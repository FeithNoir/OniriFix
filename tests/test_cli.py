"""Pruebas de integración de la CLI (sin red ni dependencias opcionales)."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner
from tests.conftest import EntornoCLI

from onirifix.cli import cli

EJEMPLOS = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def runner(entorno_cli: EntornoCLI, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    monkeypatch.setenv("ONIRIFIX_HOME", str(entorno_cli.raiz))
    monkeypatch.setenv("ONIRIFIX_BACKUPS", str(entorno_cli.backups))
    monkeypatch.setenv("COLUMNS", "120")
    monkeypatch.setenv("NO_COLOR", "1")
    return CliRunner()


def _ok(runner: CliRunner, *args: str, input: str | None = None):
    resultado = runner.invoke(cli, list(args), input=input, catch_exceptions=False)
    assert resultado.exit_code == 0, resultado.output
    return resultado


def test_init_crea_base_y_obra(runner: CliRunner, entorno_cli: EntornoCLI) -> None:
    resultado = _ok(runner, "init")

    assert entorno_cli.db.exists()
    assert entorno_cli.config.exists()
    assert "Base de datos lista" in resultado.output
    assert "Obra activa: general" in resultado.output


def test_importar_ejemplo_y_analizar(
    runner: CliRunner, entorno_cli: EntornoCLI
) -> None:
    importado = _ok(
        runner, "registro", "importar", str(EJEMPLOS / "obra.ejemplo.yaml")
    )
    assert "Obra importada: oniriums" in importado.output

    resultado = _ok(
        runner,
        "--obra",
        "oniriums",
        "analizar",
        str(EJEMPLOS / "manuscrito_ejemplo.md"),
        "--sin-informes",
    )

    assert "OniriFix" in resultado.output
    assert "oniriums" in resultado.output
    assert "Reglas: 26" in resultado.output


def test_analizar_escribe_informes_y_estricto_falla(
    runner: CliRunner, entorno_cli: EntornoCLI
) -> None:
    _ok(runner, "registro", "importar", str(EJEMPLOS / "obra.ejemplo.yaml"))
    salida = entorno_cli.raiz / "salida"

    resultado = _ok(
        runner,
        "--obra",
        "oniriums",
        "analizar",
        str(EJEMPLOS / "manuscrito_ejemplo.md"),
        "--salida",
        str(salida),
    )

    assert (salida / "informe.md").exists()
    assert (salida / "hallazgos.csv").exists()
    assert (salida / "hallazgos.json").exists()
    assert "informe.md" in resultado.output

    estricto = runner.invoke(
        cli,
        [
            "--obra",
            "oniriums",
            "analizar",
            str(EJEMPLOS / "manuscrito_ejemplo.md"),
            "--sin-informes",
            "--estricto",
        ],
    )
    assert estricto.exit_code == 1


def test_corregir_dry_run_y_aplicar_con_backup(
    runner: CliRunner, entorno_cli: EntornoCLI
) -> None:
    archivo = entorno_cli.raiz / "texto.md"
    archivo.write_text('Dijo "hola" y se fue...\n', encoding="utf-8")

    dry = _ok(runner, "corregir", str(archivo), "--sin-informes")

    assert "Dry-run" in dry.output
    assert archivo.read_text(encoding="utf-8") == 'Dijo "hola" y se fue...\n'

    aplicado = _ok(runner, "corregir", str(archivo), "--aplicar", "--sin-informes")

    assert "Archivo escrito" in aplicado.output
    texto = archivo.read_text(encoding="utf-8")
    assert "«hola»" in texto
    assert "…" in texto
    assert list(entorno_cli.backups.glob("*.bak"))

    historial = _ok(runner, "registro", "historial")
    assert "TIP-004" in historial.output or "TIP-005" in historial.output


def test_corregir_destino_y_formato_diff(
    runner: CliRunner, entorno_cli: EntornoCLI
) -> None:
    archivo = entorno_cli.raiz / "texto.md"
    archivo.write_text('Dijo "hola" y se fue...\n', encoding="utf-8")
    destino = entorno_cli.raiz / "limpio.md"
    salida = entorno_cli.raiz / "informes-correccion"

    resultado = _ok(
        runner,
        "corregir",
        str(archivo),
        "--aplicar",
        "--destino",
        str(destino),
        "--salida",
        str(salida),
        "--formato",
        "md,json,diff",
    )

    assert destino.exists()
    assert "«hola»" in destino.read_text(encoding="utf-8")
    assert '"hola"' in archivo.read_text(encoding="utf-8")
    assert (salida / "parches.diff").exists()
    assert "Corrección" in resultado.output


def test_revisar_simular_no_escribe(runner: CliRunner, entorno_cli: EntornoCLI) -> None:
    archivo = entorno_cli.raiz / "revisar.md"
    archivo.write_text("Hola , mundo.\n", encoding="utf-8")

    resultado = _ok(runner, "revisar", str(archivo), "--simular", input="s\n")

    assert "Dry-run" in resultado.output
    assert archivo.read_text(encoding="utf-8") == "Hola , mundo.\n"


def test_revisar_aplica_la_decision(runner: CliRunner, entorno_cli: EntornoCLI) -> None:
    archivo = entorno_cli.raiz / "revisar.md"
    archivo.write_text("Hola , mundo.\n", encoding="utf-8")

    _ok(runner, "revisar", str(archivo), input="s\n")

    assert archivo.read_text(encoding="utf-8") == "Hola, mundo.\n"
    assert list(entorno_cli.backups.glob("*.bak"))


def test_frecuencia_y_duplicados(runner: CliRunner, entorno_cli: EntornoCLI) -> None:
    frecuencia = entorno_cli.raiz / "frecuencia.md"
    frecuencia.write_text("dragón " * 8 + "La espada brillaba.\n", encoding="utf-8")
    resultado = _ok(runner, "frecuencia", str(frecuencia))
    assert "Frecuencia léxica" in resultado.output
    assert "dragón" in resultado.output

    parrafo = "Esta es una frase larga con muchas palabras para duplicar."
    duplicado = entorno_cli.raiz / "duplicado.md"
    duplicado.write_text(f"{parrafo}\n\n{parrafo}\n", encoding="utf-8")
    resultado = _ok(runner, "duplicados", str(duplicado))
    assert "Párrafos duplicados" in resultado.output


def test_reglas_y_doctor(runner: CliRunner) -> None:
    reglas = _ok(runner, "reglas")
    assert "TIP-001" in reglas.output
    assert "DIA-003" in reglas.output

    doctor = _ok(runner, "doctor")
    assert "Diagnóstico de OniriFix" in doctor.output
    assert "Reglas registradas" in doctor.output


def test_registro_gestiona_entidades(
    runner: CliRunner, entorno_cli: EntornoCLI
) -> None:
    _ok(
        runner,
        "registro",
        "obras",
        "crear",
        "mi-novela",
        "--titulo",
        "Mi Novela",
        "--autor",
        "Autora",
    )
    _ok(
        runner,
        "--obra",
        "mi-novela",
        "registro",
        "personajes",
        "agregar",
        "Mico",
        "--alias",
        "Miki",
    )
    _ok(
        runner,
        "--obra",
        "mi-novela",
        "registro",
        "lugares",
        "agregar",
        "Villa Gris",
        "--tipo",
        "ciudad",
    )
    _ok(
        runner,
        "--obra",
        "mi-novela",
        "registro",
        "terminos",
        "agregar",
        "Oniriums",
        "--sensible",
    )
    _ok(
        runner,
        "--obra",
        "mi-novela",
        "registro",
        "terminos",
        "variante",
        "Oniriums",
        "Onirium",
    )
    _ok(runner, "--obra", "mi-novela", "registro", "verbos", "agregar", "trinó")

    personajes = _ok(runner, "--obra", "mi-novela", "registro", "personajes", "listar")
    assert "Mico" in personajes.output
    assert "Miki" in personajes.output

    lugares = _ok(runner, "--obra", "mi-novela", "registro", "lugares", "listar")
    assert "Villa Gris" in lugares.output

    terminos = _ok(runner, "--obra", "mi-novela", "registro", "terminos", "listar")
    assert "Oniriums" in terminos.output
    assert "Onirium" in terminos.output

    variantes = _ok(
        runner, "--obra", "mi-novela", "registro", "terminos", "variantes", "Oniriums"
    )
    assert "Onirium" in variantes.output

    verbos = _ok(runner, "--obra", "mi-novela", "registro", "verbos", "listar")
    assert "trinó" in verbos.output

    obra = _ok(runner, "registro", "obras", "ver", "mi-novela")
    assert "Mi Novela" in obra.output
    assert "Autora" in obra.output


def test_registro_exportar_obras_y_eliminar(
    runner: CliRunner, entorno_cli: EntornoCLI
) -> None:
    _ok(runner, "registro", "obras", "crear", "mi-novela", "--titulo", "Mi Novela")
    exportado = entorno_cli.raiz / "mi-novela.yaml"

    _ok(runner, "--obra", "mi-novela", "registro", "exportar", str(exportado))
    assert exportado.exists()
    assert "mi-novela" in exportado.read_text(encoding="utf-8")

    listado = _ok(runner, "registro", "obras", "listar")
    assert "mi-novela" in listado.output

    _ok(runner, "registro", "obras", "eliminar", "mi-novela", "--si")
    vacio = _ok(runner, "registro", "obras", "listar")
    assert "Todavía no hay obras" in vacio.output
