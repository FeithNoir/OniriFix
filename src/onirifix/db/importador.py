"""Importación y exportación YAML del registro.

El YAML es el formato de intercambio, no la fuente de verdad. Sirve para
sembrar una obra, migrar una biblioteca antigua o revisar el registro en un
editor de texto.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from onirifix.db.repositorios import Registro
from onirifix.modelo import Obra
from onirifix.util import separar_alias, slugify


class ErrorImportacion(ValueError):
    """El YAML no tiene la forma esperada."""


@dataclass(slots=True)
class ResultadoImportacion:
    obra: Obra
    creados: dict[str, int] = field(default_factory=dict)
    actualizados: dict[str, int] = field(default_factory=dict)
    omitidos: int = 0
    avisos: list[str] = field(default_factory=list)

    def sumar(self, diccionario: dict[str, int], clave: str) -> None:
        diccionario[clave] = diccionario.get(clave, 0) + 1


def _lista(datos: dict[str, Any], clave: str) -> list[dict[str, Any]]:
    valor = datos.get(clave) or []
    if not isinstance(valor, list):
        raise ErrorImportacion(f"'{clave}' debe ser una lista.")
    resultado: list[dict[str, Any]] = []
    for indice, elemento in enumerate(valor, start=1):
        if isinstance(elemento, str):
            resultado.append({"nombre": elemento})
            continue
        if not isinstance(elemento, dict):
            raise ErrorImportacion(f"'{clave}[{indice}]' debe ser un objeto o una cadena.")
        resultado.append(elemento)
    return resultado


def _texto(valor: Any) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def importar_yaml(registro: Registro, ruta: Path) -> ResultadoImportacion:
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el archivo YAML: {ruta}")
    try:
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ErrorImportacion(f"YAML inválido en {ruta}: {exc}") from exc
    if not isinstance(datos, dict):
        raise ErrorImportacion("La raíz del YAML debe ser un objeto.")

    obra_datos = datos.get("obra") or {}
    if not isinstance(obra_datos, dict):
        raise ErrorImportacion("'obra' debe ser un objeto.")
    titulo = _texto(obra_datos.get("titulo"))
    slug = slugify(str(obra_datos.get("slug") or titulo or ruta.stem))
    if not titulo:
        titulo = slug.replace("-", " ").title()

    existente = registro.obras.obtener(slug)
    if existente is None:
        obra = registro.obras.crear(
            slug=slug,
            titulo=titulo,
            autor=_texto(obra_datos.get("autor")),
            idioma=_texto(obra_datos.get("idioma")) or "es",
            genero=_texto(obra_datos.get("genero")),
            descripcion=_texto(obra_datos.get("descripcion")),
        )
    else:
        campos_obra = {
            clave: _texto(obra_datos.get(clave))
            for clave in ("titulo", "autor", "idioma", "genero", "descripcion")
            if _texto(obra_datos.get(clave)) is not None
        }
        obra = (
            registro.obras.actualizar(slug, **campos_obra)
            if campos_obra
            else existente
        )

    resultado = ResultadoImportacion(obra=obra)
    resultado.creados.update(
        {"personajes": 0, "lugares": 0, "terminos": 0, "variantes": 0, "verbos": 0}
    )
    resultado.actualizados.update({"personajes": 0, "lugares": 0, "terminos": 0})

    # ------------------------------------------------------------------
    # Personajes
    # ------------------------------------------------------------------
    for datos_personaje in _lista(datos, "personajes"):
        nombre = _texto(datos_personaje.get("nombre"))
        if not nombre:
            resultado.avisos.append("Personaje sin nombre; se omite.")
            resultado.omitidos += 1
            continue
        campos_personaje: dict[str, Any] = {}
        for clave, valor in (
            ("rol", _texto(datos_personaje.get("rol"))),
            ("alias", datos_personaje.get("alias")),
            ("descripcion", _texto(datos_personaje.get("descripcion"))),
            ("notas", _texto(datos_personaje.get("notas"))),
        ):
            if clave in datos_personaje:
                campos_personaje[clave] = valor
        personaje_actual = registro.personajes.obtener(obra.id, nombre)
        if personaje_actual is None:
            registro.personajes.agregar(obra.id, nombre, **campos_personaje)
            resultado.sumar(resultado.creados, "personajes")
        else:
            registro.personajes.actualizar(obra.id, nombre, **campos_personaje)
            resultado.sumar(resultado.actualizados, "personajes")

    # ------------------------------------------------------------------
    # Lugares
    # ------------------------------------------------------------------
    for datos_lugar in _lista(datos, "lugares"):
        nombre = _texto(datos_lugar.get("nombre"))
        if not nombre:
            resultado.avisos.append("Lugar sin nombre; se omite.")
            resultado.omitidos += 1
            continue
        campos_lugar: dict[str, Any] = {}
        for clave, valor in (
            ("tipo", _texto(datos_lugar.get("tipo"))),
            ("alias", datos_lugar.get("alias")),
            ("descripcion", _texto(datos_lugar.get("descripcion"))),
            ("notas", _texto(datos_lugar.get("notas"))),
        ):
            if clave in datos_lugar:
                campos_lugar[clave] = valor
        lugar_actual = registro.lugares.obtener(obra.id, nombre)
        if lugar_actual is None:
            registro.lugares.agregar(obra.id, nombre, **campos_lugar)
            resultado.sumar(resultado.creados, "lugares")
        else:
            registro.lugares.actualizar(obra.id, nombre, **campos_lugar)
            resultado.sumar(resultado.actualizados, "lugares")

    # ------------------------------------------------------------------
    # Términos y variantes
    # ------------------------------------------------------------------
    for datos_termino in _lista(datos, "terminos"):
        nombre = _texto(datos_termino.get("termino") or datos_termino.get("nombre"))
        if not nombre:
            resultado.avisos.append("Término sin nombre; se omite.")
            resultado.omitidos += 1
            continue
        tipo = _texto(datos_termino.get("tipo")) or "glosario"
        termino_actual = registro.terminos.obtener(obra.id, nombre, tipo)
        if termino_actual is None:
            termino_actual = registro.terminos.agregar(
                obra.id,
                nombre,
                tipo=tipo,
                definicion=_texto(datos_termino.get("definicion")),
                notas=_texto(datos_termino.get("notas")),
                sensible=bool(datos_termino.get("sensible", False)),
            )
            resultado.sumar(resultado.creados, "terminos")
        else:
            campos_termino: dict[str, Any] = {}
            for clave, valor in (
                ("definicion", _texto(datos_termino.get("definicion"))),
                ("notas", _texto(datos_termino.get("notas"))),
                (
                    "sensible",
                    bool(datos_termino.get("sensible", termino_actual.sensible)),
                ),
            ):
                if clave in datos_termino:
                    campos_termino[clave] = valor
            if campos_termino:
                registro.terminos.actualizar(obra.id, nombre, **campos_termino)
            resultado.sumar(resultado.actualizados, "terminos")

        variantes_termino = datos_termino.get("variantes") or []
        if not isinstance(variantes_termino, list):
            resultado.avisos.append(f"Las variantes de '{nombre}' deben ser una lista.")
            continue
        for variante in variantes_termino:
            variante_texto = _texto(variante)
            if not variante_texto:
                continue
            try:
                registro.terminos.agregar_variante(
                    termino_actual.id, variante_texto, es_error=True
                )
                resultado.sumar(resultado.creados, "variantes")
            except ValueError:
                resultado.omitidos += 1

    # Atajo: mapa canónico -> variantes. Busca el término en cualquier tipo.
    variantes_sueltas = datos.get("variantes") or {}
    if variantes_sueltas and not isinstance(variantes_sueltas, dict):
        raise ErrorImportacion("'variantes' debe ser un objeto canónico → lista.")
    for canonico, variantes_canonicas in (variantes_sueltas or {}).items():
        nombre = _texto(canonico)
        if not nombre:
            continue
        termino = registro.terminos.obtener(obra.id, nombre)
        if termino is None:
            resultado.avisos.append(
                f"No existe el término canónico '{nombre}'; se omiten sus variantes."
            )
            continue
        if not isinstance(variantes_canonicas, list):
            resultado.avisos.append(f"Las variantes de '{nombre}' deben ser una lista.")
            continue
        for variante in variantes_canonicas:
            variante_texto = _texto(variante)
            if not variante_texto:
                continue
            try:
                registro.terminos.agregar_variante(termino.id, variante_texto, es_error=True)
                resultado.sumar(resultado.creados, "variantes")
            except ValueError:
                resultado.omitidos += 1

    # ------------------------------------------------------------------
    # Verbos de habla
    # ------------------------------------------------------------------
    verbos = datos.get("verbos_habla") or []
    if not isinstance(verbos, list):
        raise ErrorImportacion("'verbos_habla' debe ser una lista.")
    for verbo in verbos:
        verbo_texto = _texto(verbo)
        if not verbo_texto:
            continue
        antes = len(registro.verbos.listar_propios(obra.id))
        registro.verbos.agregar(obra.id, verbo_texto)
        despues = len(registro.verbos.listar_propios(obra.id))
        if despues > antes:
            resultado.sumar(resultado.creados, "verbos")
        else:
            resultado.omitidos += 1

    return resultado


def exportar_yaml(registro: Registro, slug: str) -> dict[str, Any]:
    obra = registro.obras.obtener(slug)
    if obra is None:
        raise ValueError(f"No existe la obra '{slug}'.")

    personajes = [
        {
            "nombre": personaje.nombre,
            **({"rol": personaje.rol} if personaje.rol else {}),
            **({"alias": separar_alias(personaje.alias)} if personaje.alias else {}),
            **(
                {"descripcion": personaje.descripcion}
                if personaje.descripcion
                else {}
            ),
            **({"notas": personaje.notas} if personaje.notas else {}),
        }
        for personaje in registro.personajes.listar(obra.id, incluir_inactivos=True)
    ]
    lugares = [
        {
            "nombre": lugar.nombre,
            **({"tipo": lugar.tipo} if lugar.tipo else {}),
            **({"alias": separar_alias(lugar.alias)} if lugar.alias else {}),
            **({"descripcion": lugar.descripcion} if lugar.descripcion else {}),
            **({"notas": lugar.notas} if lugar.notas else {}),
        }
        for lugar in registro.lugares.listar(obra.id)
    ]
    terminos = []
    for termino in registro.terminos.listar(obra.id):
        elemento: dict[str, Any] = {
            "termino": termino.termino,
            "tipo": termino.tipo,
        }
        if termino.definicion:
            elemento["definicion"] = termino.definicion
        if termino.notas:
            elemento["notas"] = termino.notas
        if termino.sensible:
            elemento["sensible"] = True
        variantes = [v.variante for v in termino.variantes if v.es_error]
        if variantes:
            elemento["variantes"] = variantes
        terminos.append(elemento)

    return {
        "obra": {
            "slug": obra.slug,
            "titulo": obra.titulo,
            **({"autor": obra.autor} if obra.autor else {}),
            **({"idioma": obra.idioma} if obra.idioma else {}),
            **({"genero": obra.genero} if obra.genero else {}),
            **({"descripcion": obra.descripcion} if obra.descripcion else {}),
        },
        "personajes": personajes,
        "lugares": lugares,
        "terminos": terminos,
        "verbos_habla": registro.verbos.listar_propios(obra.id),
    }


def escribir_yaml(datos: dict[str, Any], ruta: Path) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        yaml.safe_dump(
            datos,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )
    return ruta
