"""Pruebas de la capa de servicio y del flujo de corrección."""

from __future__ import annotations

from pathlib import Path

import pytest

from onirifix.config import Settings
from onirifix.modelo import Nivel
from onirifix.servicio import (
    abrir_contexto,
    analizar,
    corregir,
    parsear_niveles,
)


def _settings(tmp_path: Path, **cambios: object) -> Settings:
    valores: dict[str, object] = {
        "raiz": tmp_path,
        "db": tmp_path / "data" / "onirifix.db",
        "config": tmp_path / "config" / "reglas.yaml",
        "salida": tmp_path / "informes",
        "backups": tmp_path / "backups",
        "obra": "general",
    }
    valores.update(cambios)
    return Settings(**valores)  # type: ignore[arg-type]


def _manuscrito(tmp_path: Path) -> Path:
    ruta = tmp_path / "manuscrito.md"
    ruta.write_text('Dijo "hola" y se fue...\n', encoding="utf-8")
    return ruta


def test_parsear_niveles() -> None:
    assert parsear_niveles("") == {Nivel.L1}
    assert parsear_niveles("l1,l2") == {Nivel.L1, Nivel.L2}
    with pytest.raises(ValueError, match="Nivel desconocido"):
        parsear_niveles("L1,L9")


def test_abrir_contexto_crea_obra_general(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    with abrir_contexto(settings, crear_obra=True) as ctx:
        assert ctx.obra.slug == "general"
        assert ctx.obra.titulo == "General"
        assert ctx.registro.obras.obtener("general") == ctx.obra


def test_abrir_contexto_exige_obra_existente(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No existe la obra 'fantasma'"):
        abrir_contexto(_settings(tmp_path, obra="fantasma"))


def test_corregir_dry_run_no_toca_el_archivo(tmp_path: Path) -> None:
    archivo = _manuscrito(tmp_path)
    original = archivo.read_text(encoding="utf-8")

    with abrir_contexto(_settings(tmp_path)) as ctx:
        analisis = analizar(ctx, archivo)
        assert analisis.total > 0
        assert any(h.nivel == Nivel.L1 for h in analisis.hallazgos)

        correccion = corregir(
            ctx,
            archivo,
            niveles={Nivel.L1},
            aplicar=False,
            aplicar_l2=False,
            umbral_l2=0.9,
            backup=True,
        )

        assert correccion.aplicados
        assert not correccion.escrito
        assert correccion.backup is None
        assert archivo.read_text(encoding="utf-8") == original
        assert ctx.registro.correcciones.listar(ctx.obra.id) == []


def test_corregir_aplicado_es_idempotente_y_auditado(tmp_path: Path) -> None:
    archivo = _manuscrito(tmp_path)
    settings = _settings(tmp_path)

    with abrir_contexto(settings) as ctx:
        primera = corregir(
            ctx,
            archivo,
            niveles={Nivel.L1},
            aplicar=True,
            aplicar_l2=False,
            umbral_l2=0.9,
            backup=True,
        )

        assert primera.escrito
        assert primera.backup is not None
        assert primera.backup.exists()
        assert "«hola»" in archivo.read_text(encoding="utf-8")
        assert "…" in archivo.read_text(encoding="utf-8")
        assert len(ctx.registro.correcciones.listar(ctx.obra.id)) == len(primera.aplicados)

        segunda = corregir(
            ctx,
            archivo,
            niveles={Nivel.L1},
            aplicar=True,
            aplicar_l2=False,
            umbral_l2=0.9,
            backup=True,
        )
        assert segunda.aplicados == []
        assert not segunda.escrito
        assert len(list(settings.backups.glob("*.bak"))) == 1

        solo_tipografia = analizar(ctx, archivo, solo_reglas=["TIP-004", "TIP-005"])
        assert solo_tipografia.por_nivel(Nivel.L1) == []


def test_corregir_destino_distinto_no_crea_backup(tmp_path: Path) -> None:
    archivo = _manuscrito(tmp_path)
    destino = tmp_path / "corregido.md"

    with abrir_contexto(_settings(tmp_path)) as ctx:
        correccion = corregir(
            ctx,
            archivo,
            niveles={Nivel.L1},
            aplicar=True,
            aplicar_l2=False,
            umbral_l2=0.9,
            backup=True,
            destino=destino,
        )

    assert correccion.escrito
    assert correccion.backup is None
    assert destino.exists()
    assert '"hola"' in archivo.read_text(encoding="utf-8")
    assert "«hola»" in destino.read_text(encoding="utf-8")


def test_auditoria_se_puede_desactivar(tmp_path: Path) -> None:
    archivo = _manuscrito(tmp_path)

    with abrir_contexto(_settings(tmp_path, auditoria=False)) as ctx:
        corregir(
            ctx,
            archivo,
            niveles={Nivel.L1},
            aplicar=True,
            aplicar_l2=False,
            umbral_l2=0.9,
            backup=False,
        )
        assert ctx.registro.correcciones.listar(ctx.obra.id) == []
