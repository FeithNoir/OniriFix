"""Pruebas de configuración y resolución de ajustes."""

from __future__ import annotations

from pathlib import Path

import pytest

from onirifix.config import Configuracion, cargar_settings


def test_configuracion_fusiona_defaults() -> None:
    config = Configuracion({"umbral_l2": 0.5, "reglas": {"TIP-001": False}})
    assert config.obtener("umbral_l2") == 0.5
    assert config.obtener("idioma") == "es"
    assert not config.regla_activa("TIP-001", True)
    assert config.regla_activa("TIP-002", True)


def test_configuracion_cargar_yaml(tmp_path: Path) -> None:
    ruta = tmp_path / "reglas.yaml"
    ruta.write_text("umbral_l2: 0.8\nreglas:\n  DIA-003: true\n", encoding="utf-8")
    config = Configuracion.cargar(ruta)
    assert config.umbral_l2() == 0.8
    assert config.regla_activa("DIA-003", False)


def test_configuracion_yaml_invalido(tmp_path: Path) -> None:
    ruta = tmp_path / "reglas.yaml"
    ruta.write_text("clave: [sin cerrar", encoding="utf-8")
    with pytest.raises(ValueError, match="YAML inválido"):
        Configuracion.cargar(ruta)


def test_configuracion_yaml_no_es_objeto(tmp_path: Path) -> None:
    ruta = tmp_path / "reglas.yaml"
    ruta.write_text("- uno\n- dos\n", encoding="utf-8")
    with pytest.raises(ValueError, match="objeto YAML"):
        Configuracion.cargar(ruta)


def test_comillas_invalidas_caen_al_default() -> None:
    config = Configuracion({"tipografia": {"comillas": "«"}})
    assert config.comillas == "«»"
    assert any("comillas" in aviso for aviso in config.validar())


def test_umbral_l2_se_limita() -> None:
    config = Configuracion({"umbral_l2": 4})
    assert config.umbral_l2() == 1.0
    assert config.umbral_l2(-1) == 0.0


def test_validar_idioma_y_reglas() -> None:
    config = Configuracion({"idioma": "fr", "reglas": []})
    avisos = config.validar()
    assert any("idioma" in aviso for aviso in avisos)
    assert any("reglas" in aviso for aviso in avisos)


def test_guardar_plantilla_no_sobrescribe(tmp_path: Path) -> None:
    ruta = tmp_path / "config" / "reglas.yaml"
    ruta.parent.mkdir()
    ruta.write_text("idioma: en\n", encoding="utf-8")
    config = Configuracion()
    assert config.guardar_plantilla(ruta) == ruta
    assert ruta.read_text(encoding="utf-8") == "idioma: en\n"
    config.guardar_plantilla(ruta, sobrescribir=True)
    assert "umbral_l2" in ruta.read_text(encoding="utf-8")


def test_settings_prioriza_cli_y_entorno(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ONIRIFIX_HOME", str(tmp_path))
    monkeypatch.setenv("ONIRIFIX_DB", "env.db")
    monkeypatch.setenv("ONIRIFIX_OBRA", "desde-entorno")
    monkeypatch.setenv("ONIRIFIX_BACKUP", "false")
    monkeypatch.setenv("ONIRIFIX_UMBRAL_L2", "0.75")

    settings = cargar_settings(db="cli.db", obra="desde-cli")
    assert settings.db == (tmp_path / "cli.db").resolve()
    assert settings.obra == "desde-cli"
    assert settings.backup is False
    assert settings.umbral_l2 == 0.75


def test_dotenv_no_sobrescribe_entorno(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ONIRIFIX_HOME", str(tmp_path))
    monkeypatch.setenv("ONIRIFIX_OBRA", "shell")
    (tmp_path / ".env").write_text(
        "ONIRIFIX_OBRA=archivo\nONIRIFIX_DB=desde.env.db\n",
        encoding="utf-8",
    )
    settings = cargar_settings()
    assert settings.obra == "shell"
    assert settings.db == (tmp_path / "desde.env.db").resolve()


def test_por_capitulo_esta_en_defaults() -> None:
    assert Configuracion().obtener("repeticion.por_capitulo") is True
