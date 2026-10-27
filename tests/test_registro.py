"""Pruebas del registro SQLite y del intercambio YAML."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from onirifix.db.importador import (
    ErrorImportacion,
    escribir_yaml,
    exportar_yaml,
    importar_yaml,
)
from onirifix.db.repositorios import Registro
from onirifix.modelo import Hallazgo, Nivel

YAML_BASE = """\
obra:
  slug: oniriums
  titulo: Oniriums
  autor: Feith Noir
  genero: fantasía
personajes:
  - nombre: Feith Noir
    rol: protagonista
    alias: [Feith]
    descripcion: Portadora del Velo.
  - nombre: Mico
    rol: secundario
    alias: [Miki]
lugares:
  - nombre: Villa Gris
    tipo: ciudad
    alias: [Villa]
terminos:
  - termino: Oniriums
    tipo: glosario
    definicion: Mundo onírico.
    notas: Sensible en el canon.
    sensible: true
    variantes: [Onirium, Oniriums\']
  - termino: Kaar'Tcha
    tipo: nombre
    variantes: [KaarTcha]
verbos_habla:
  - trinó
  - silbó
"""


def _importar(registro: Registro, ruta: Path, contenido: str = YAML_BASE):
    ruta.write_text(contenido, encoding="utf-8")
    return importar_yaml(registro, ruta)


def test_esquema_versionado_y_tablas(registro: Registro) -> None:
    with sqlite3.connect(registro.ruta) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        tablas = {
            fila[0]
            for fila in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert version == 1
    assert {
        "obras",
        "personajes",
        "lugares",
        "terminos",
        "variantes",
        "verbos_habla",
        "correcciones",
    } <= tablas


def test_obras_crud_y_slug(registro: Registro) -> None:
    obra = registro.obras.crear(titulo="Mi Novela", autor="Autora")
    assert obra.slug == "mi-novela"
    assert registro.obras.obtener("Mi Novela") == obra
    assert registro.obras.por_id(obra.id) == obra
    assert [o.slug for o in registro.obras.listar()] == ["mi-novela"]

    with pytest.raises(ValueError, match="Ya existe"):
        registro.obras.crear(slug="mi-novela", titulo="Otra")

    actualizada = registro.obras.actualizar("mi-novela", titulo="Mi Novela II")
    assert actualizada.titulo == "Mi Novela II"
    assert registro.obras.actualizar("mi-novela").titulo == "Mi Novela II"

    with pytest.raises(ValueError, match="No existe"):
        registro.obras.actualizar("fantasma", titulo="X")

    assert registro.obras.eliminar("mi-novela")
    assert not registro.obras.eliminar("mi-novela")
    assert registro.obras.listar() == []


def test_asegurar_es_idempotente(registro: Registro) -> None:
    una = registro.obras.asegurar("general", titulo="Obra general")
    dos = registro.obras.asegurar("general", titulo="Otro título")

    assert una == dos


def test_glosario_agrega_personajes_lugares_terminos_y_verbos(
    registro: Registro,
) -> None:
    obra = registro.obras.crear(slug="oniriums", titulo="Oniriums")
    registro.personajes.agregar(
        obra.id, "Feith Noir", alias=["Feith", "La Vidente"], rol="protagonista"
    )
    personaje = registro.personajes.agregar(obra.id, "Mico")
    assert personaje.activo
    registro.personajes.actualizar(obra.id, "Mico", activo=False)
    assert [p.nombre for p in registro.personajes.listar(obra.id)] == ["Feith Noir"]
    assert [p.nombre for p in registro.personajes.listar(obra.id, incluir_inactivos=True)] == [
        "Feith Noir",
        "Mico",
    ]
    registro.personajes.actualizar(obra.id, "Mico", activo=True)

    registro.lugares.agregar(obra.id, "Villa Gris", tipo="ciudad", alias="Villa")
    termino = registro.terminos.agregar(
        obra.id, "Oniriums", tipo="glosario", definicion="Mundo onírico."
    )
    registro.terminos.agregar(obra.id, "M'dir", tipo="toponimo")
    registro.terminos.agregar_variante(termino.id, "Onirium")
    registro.terminos.agregar_variante(termino.id, "Oniriums'")
    registro.verbos.agregar(None, "dijo")
    registro.verbos.agregar(obra.id, "trinó")

    glosario = registro.glosario("oniriums")

    assert {"Feith Noir", "Mico"} <= glosario.nombres
    assert {"Feith", "La Vidente", "Villa"} <= glosario.alias
    assert {"Villa Gris", "M'dir"} <= glosario.toponimos
    assert {"Oniriums"} <= glosario.terminos
    assert glosario.canonico("onirium") == "Oniriums"
    assert {"dijo", "trinó"} == glosario.verbos_habla


def test_personajes_y_lugares_actualizan_alias(registro: Registro) -> None:
    obra = registro.obras.crear(slug="x", titulo="X")
    personaje = registro.personajes.agregar(obra.id, "Mico", alias=["Miki"])
    assert personaje.alias == "Miki"

    actualizado = registro.personajes.actualizar(obra.id, "Mico", alias=["Miko", "Mik"])
    assert actualizado.alias == "Miko, Mik"

    registro.lugares.agregar(obra.id, "Villa Gris", alias=["Villa"])
    assert registro.lugares.actualizar(obra.id, "Villa Gris", alias="Villa G.").alias == "Villa G."

    with pytest.raises(ValueError, match="No existe"):
        registro.personajes.actualizar(obra.id, "Nadie", rol="x")
    with pytest.raises(ValueError, match="No existe"):
        registro.lugares.actualizar(obra.id, "Ninguno", tipo="x")


def test_terminos_validan_tipo_y_variantes(registro: Registro) -> None:
    obra = registro.obras.crear(slug="x", titulo="X")
    termino = registro.terminos.agregar(obra.id, "Oniriums")
    registro.terminos.agregar_variante(termino.id, "Onirium")

    with pytest.raises(ValueError, match="Tipo de término inválido"):
        registro.terminos.agregar(obra.id, "Otro", tipo="inventado")
    with pytest.raises(ValueError, match="ya existe"):
        registro.terminos.agregar_variante(termino.id, "Onirium")
    with pytest.raises(ValueError, match="Tipo de término inválido"):
        registro.terminos.actualizar(obra.id, "Oniriums", tipo="inventado")

    assert [v.variante for v in registro.terminos.variantes(termino.id)] == ["Onirium"]
    assert [v.variante for v in registro.terminos.obtener(obra.id, "Oniriums").variantes] == [
        "Onirium"
    ]
    assert registro.terminos.buscar(obra.id, "onir")[0].termino == "Oniriums"
    assert registro.terminos.eliminar_variante(termino.id, "Onirium")
    assert not registro.terminos.eliminar_variante(termino.id, "Onirium")


def test_verbos_globales_y_propios(registro: Registro) -> None:
    obra = registro.obras.crear(slug="x", titulo="X")
    registro.verbos.agregar(None, "Dijo")
    registro.verbos.agregar(obra.id, "trinó")
    registro.verbos.agregar(obra.id, "trinó")

    assert registro.verbos.listar(obra.id) == ["dijo", "trinó"]
    assert registro.verbos.listar_propios(obra.id) == ["trinó"]
    assert registro.verbos.eliminar(None, "dijo")
    assert registro.verbos.eliminar(obra.id, "trinó")
    assert registro.verbos.listar(obra.id) == []


def test_eliminar_obra_elimina_datos_asociados(registro: Registro) -> None:
    obra = registro.obras.crear(slug="x", titulo="X")
    registro.personajes.agregar(obra.id, "Mico")
    registro.lugares.agregar(obra.id, "Villa Gris")
    registro.terminos.agregar(obra.id, "Oniriums")

    assert registro.obras.eliminar("x")

    assert registro.personajes.listar(obra.id) == []
    assert registro.lugares.listar(obra.id) == []
    assert registro.terminos.listar(obra.id) == []


def test_glosario_exige_obra_existente(registro: Registro) -> None:
    with pytest.raises(ValueError, match="No existe la obra"):
        registro.glosario("fantasma")
    with pytest.raises(ValueError, match="No existe la obra"):
        registro.resumen("fantasma")


def test_resumen_cuenta_entidades(registro: Registro) -> None:
    obra = registro.obras.crear(slug="x", titulo="X")
    registro.personajes.agregar(obra.id, "Mico")
    registro.lugares.agregar(obra.id, "Villa Gris")
    registro.terminos.agregar(obra.id, "Oniriums")
    registro.verbos.agregar(obra.id, "trinó")

    assert registro.resumen("x") == {
        "personajes": 1,
        "lugares": 1,
        "terminos": 1,
        "verbos": 1,
    }


def test_correcciones_se_registran_y_listan(registro: Registro) -> None:
    obra = registro.obras.crear(slug="x", titulo="X")
    hallazgo = Hallazgo(
        regla="TIP-001",
        nivel=Nivel.L1,
        inicio=1,
        fin=4,
        original="   ",
        sugerencia=" ",
        confianza=0.99,
        linea=2,
        columna=3,
        contexto="a   b",
    )

    registro.correcciones.registrar(
        obra_id=obra.id,
        archivo="manuscrito.md",
        hallazgo=hallazgo,
        aplicado=True,
    )

    filas = registro.correcciones.listar(obra.id)
    assert len(filas) == 1
    assert filas[0]["regla"] == "TIP-001"
    assert filas[0]["nivel"] == "L1"
    assert filas[0]["aplicado"] == 1


def test_importar_yaml_es_idempotente_y_conserva_campos(
    registro: Registro, tmp_path: Path
) -> None:
    ruta = tmp_path / "obra.yaml"
    primero = _importar(registro, ruta)

    assert primero.creados == {
        "personajes": 2,
        "lugares": 1,
        "terminos": 2,
        "variantes": 3,
        "verbos": 2,
    }
    assert primero.omitidos == 0
    assert primero.actualizados == {"personajes": 0, "lugares": 0, "terminos": 0}

    segundo = _importar(registro, ruta)

    assert segundo.creados == {
        "personajes": 0,
        "lugares": 0,
        "terminos": 0,
        "variantes": 0,
        "verbos": 0,
    }
    assert segundo.omitidos == 5

    actualizado = """\
obra:
  slug: oniriums
  titulo: Oniriums II
personajes:
  - nombre: Mico
    rol: protagonista
terminos:
  - termino: Oniriums
    definicion: Definición nueva.
"""
    tercero = _importar(registro, ruta, actualizado)

    assert tercero.obra.titulo == "Oniriums II"
    mico = registro.personajes.obtener(tercero.obra.id, "Mico")
    assert mico is not None
    assert mico.rol == "protagonista"
    assert mico.alias == "Miki"
    termino = registro.terminos.obtener(tercero.obra.id, "Oniriums")
    assert termino is not None
    assert termino.definicion == "Definición nueva."
    assert termino.notas == "Sensible en el canon."
    assert termino.sensible is True


def test_exportar_e_importar_roundtrip(
    registro: Registro, tmp_path: Path
) -> None:
    _importar(registro, tmp_path / "origen.yaml")
    datos = exportar_yaml(registro, "oniriums")
    ruta_export = escribir_yaml(datos, tmp_path / "exportado.yaml")

    otro = Registro(tmp_path / "otro.db")
    try:
        importar_yaml(otro, ruta_export)
        assert exportar_yaml(otro, "oniriums") == datos
    finally:
        otro.cerrar()


def test_importar_yaml_invalido(registro: Registro, tmp_path: Path) -> None:
    ruta = tmp_path / "mal.yaml"
    ruta.write_text("- no es un objeto\n", encoding="utf-8")
    with pytest.raises(ErrorImportacion, match="objeto"):
        importar_yaml(registro, ruta)

    ruta.write_text("personajes: no-es-lista\n", encoding="utf-8")
    with pytest.raises(ErrorImportacion, match="lista"):
        importar_yaml(registro, ruta)

    with pytest.raises(FileNotFoundError, match="No existe"):
        importar_yaml(registro, tmp_path / "no.yaml")


def test_importar_yaml_omite_elementos_sin_nombre(
    registro: Registro, tmp_path: Path
) -> None:
    contenido = """\
obra:
  slug: x
personajes:
  - rol: sin nombre
lugares:
  - tipo: ruina
terminos:
  - tipo: glosario
"""
    resultado = _importar(registro, tmp_path / "x.yaml", contenido)

    assert resultado.omitidos == 3
    assert len(resultado.avisos) == 3
    assert resultado.creados["personajes"] == 0
