"""Repositorios del registro.

Cada repositorio posee su SQL y devuelve dataclasses del dominio. La CLI y las
reglas nunca hablan con ``sqlite3`` directamente.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from onirifix.db.conexion import abrir_conexion
from onirifix.modelo import (
    Glosario,
    Hallazgo,
    Lugar,
    Obra,
    Personaje,
    Termino,
    Variante,
)
from onirifix.util import separar_alias, slugify, unir_alias

_TIPOS_TERMINO = {"nombre", "glosario", "toponimo", "expresion", "otro"}


def _bool(valor: Any) -> bool:
    return bool(valor)


class ObraRepositorio:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @staticmethod
    def _fila(fila: sqlite3.Row) -> Obra:
        return Obra(
            id=int(fila["id"]),
            slug=str(fila["slug"]),
            titulo=str(fila["titulo"]),
            autor=fila["autor"],
            idioma=str(fila["idioma"]),
            genero=fila["genero"],
            descripcion=fila["descripcion"],
        )

    def crear(
        self,
        *,
        slug: str | None = None,
        titulo: str,
        autor: str | None = None,
        idioma: str = "es",
        genero: str | None = None,
        descripcion: str | None = None,
    ) -> Obra:
        titulo = titulo.strip()
        if not titulo:
            raise ValueError("El título de la obra no puede estar vacío.")
        slug_final = slugify(slug or titulo)
        try:
            cursor = self.conn.execute(
                """
                INSERT INTO obras (slug, titulo, autor, idioma, genero, descripcion)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (slug_final, titulo, autor, idioma or "es", genero, descripcion),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"Ya existe una obra con el slug '{slug_final}'. "
                "Usa otro slug o consulta `onirifix registro obras listar`."
            ) from exc
        self.conn.commit()
        assert cursor.lastrowid is not None
        obra = self.por_id(int(cursor.lastrowid))
        assert obra is not None
        return obra

    def por_id(self, obra_id: int) -> Obra | None:
        fila = self.conn.execute("SELECT * FROM obras WHERE id = ?", (obra_id,)).fetchone()
        return self._fila(fila) if fila else None

    def obtener(self, slug: str) -> Obra | None:
        fila = self.conn.execute(
            "SELECT * FROM obras WHERE slug = ?", (slugify(slug),)
        ).fetchone()
        return self._fila(fila) if fila else None

    def listar(self) -> list[Obra]:
        filas = self.conn.execute(
            "SELECT * FROM obras ORDER BY titulo COLLATE NOCASE"
        ).fetchall()
        return [self._fila(fila) for fila in filas]

    def actualizar(self, slug: str, **campos: Any) -> Obra:
        permitidos = {"titulo", "autor", "idioma", "genero", "descripcion"}
        cambios = {clave: valor for clave, valor in campos.items() if clave in permitidos}
        if not cambios:
            obra = self.obtener(slug)
            if obra is None:
                raise ValueError(f"No existe la obra '{slug}'.")
            return obra
        sets = ", ".join(f"{clave} = ?" for clave in cambios)
        valores = [*cambios.values(), slugify(slug)]
        cursor = self.conn.execute(
            f"""
            UPDATE obras
               SET {sets},
                   actualizada_en = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
             WHERE slug = ?
            """,
            valores,
        )
        self.conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"No existe la obra '{slug}'.")
        obra = self.obtener(slug)
        assert obra is not None
        return obra

    def eliminar(self, slug: str) -> bool:
        cursor = self.conn.execute("DELETE FROM obras WHERE slug = ?", (slugify(slug),))
        self.conn.commit()
        return cursor.rowcount > 0

    def asegurar(self, slug: str = "general", titulo: str = "Obra general") -> Obra:
        existente = self.obtener(slug)
        if existente is not None:
            return existente
        return self.crear(slug=slug, titulo=titulo)


class PersonajeRepositorio:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @staticmethod
    def _fila(fila: sqlite3.Row) -> Personaje:
        return Personaje(
            id=int(fila["id"]),
            obra_id=int(fila["obra_id"]),
            nombre=str(fila["nombre"]),
            rol=fila["rol"],
            alias=fila["alias"],
            descripcion=fila["descripcion"],
            notas=fila["notas"],
            activo=_bool(fila["activo"]),
        )

    def agregar(
        self,
        obra_id: int,
        nombre: str,
        *,
        rol: str | None = None,
        alias: str | list[str] | None = None,
        descripcion: str | None = None,
        notas: str | None = None,
        activo: bool = True,
    ) -> Personaje:
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre del personaje no puede estar vacío.")
        try:
            self.conn.execute(
                """
                INSERT INTO personajes
                    (obra_id, nombre, rol, alias, descripcion, notas, activo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (obra_id, nombre, rol, unir_alias(alias), descripcion, notas, int(activo)),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"El personaje '{nombre}' ya existe en esta obra."
            ) from exc
        self.conn.commit()
        personaje = self.obtener(obra_id, nombre)
        assert personaje is not None
        return personaje

    def listar(self, obra_id: int, *, incluir_inactivos: bool = False) -> list[Personaje]:
        sql = "SELECT * FROM personajes WHERE obra_id = ?"
        if not incluir_inactivos:
            sql += " AND activo = 1"
        sql += " ORDER BY nombre COLLATE NOCASE"
        filas = self.conn.execute(sql, (obra_id,)).fetchall()
        return [self._fila(fila) for fila in filas]

    def obtener(self, obra_id: int, nombre: str) -> Personaje | None:
        fila = self.conn.execute(
            "SELECT * FROM personajes WHERE obra_id = ? AND nombre = ?",
            (obra_id, nombre.strip()),
        ).fetchone()
        return self._fila(fila) if fila else None

    def actualizar(self, obra_id: int, nombre: str, **campos: Any) -> Personaje:
        permitidos = {"nombre", "rol", "alias", "descripcion", "notas", "activo"}
        cambios = {clave: valor for clave, valor in campos.items() if clave in permitidos}
        if "alias" in cambios:
            cambios["alias"] = unir_alias(cambios["alias"])
        if not cambios:
            personaje = self.obtener(obra_id, nombre)
            if personaje is None:
                raise ValueError(f"No existe el personaje '{nombre}'.")
            return personaje
        sets = ", ".join(f"{clave} = ?" for clave in cambios)
        valores = [*cambios.values(), obra_id, nombre]
        cursor = self.conn.execute(
            f"""
            UPDATE personajes
               SET {sets},
                   actualizado_en = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
             WHERE obra_id = ? AND nombre = ?
            """,
            valores,
        )
        self.conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"No existe el personaje '{nombre}'.")
        personaje = self.obtener(obra_id, str(cambios.get("nombre", nombre)))
        assert personaje is not None
        return personaje

    def eliminar(self, obra_id: int, nombre: str) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM personajes WHERE obra_id = ? AND nombre = ?",
            (obra_id, nombre.strip()),
        )
        self.conn.commit()
        return cursor.rowcount > 0


class LugarRepositorio:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @staticmethod
    def _fila(fila: sqlite3.Row) -> Lugar:
        return Lugar(
            id=int(fila["id"]),
            obra_id=int(fila["obra_id"]),
            nombre=str(fila["nombre"]),
            tipo=fila["tipo"],
            alias=fila["alias"],
            descripcion=fila["descripcion"],
            notas=fila["notas"],
        )

    def agregar(
        self,
        obra_id: int,
        nombre: str,
        *,
        tipo: str | None = None,
        alias: str | list[str] | None = None,
        descripcion: str | None = None,
        notas: str | None = None,
    ) -> Lugar:
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre del lugar no puede estar vacío.")
        try:
            self.conn.execute(
                """
                INSERT INTO lugares (obra_id, nombre, tipo, alias, descripcion, notas)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (obra_id, nombre, tipo, unir_alias(alias), descripcion, notas),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"El lugar '{nombre}' ya existe en esta obra.") from exc
        self.conn.commit()
        lugar = self.obtener(obra_id, nombre)
        assert lugar is not None
        return lugar

    def listar(self, obra_id: int) -> list[Lugar]:
        filas = self.conn.execute(
            "SELECT * FROM lugares WHERE obra_id = ? ORDER BY nombre COLLATE NOCASE",
            (obra_id,),
        ).fetchall()
        return [self._fila(fila) for fila in filas]

    def obtener(self, obra_id: int, nombre: str) -> Lugar | None:
        fila = self.conn.execute(
            "SELECT * FROM lugares WHERE obra_id = ? AND nombre = ?",
            (obra_id, nombre.strip()),
        ).fetchone()
        return self._fila(fila) if fila else None

    def actualizar(self, obra_id: int, nombre: str, **campos: Any) -> Lugar:
        permitidos = {"nombre", "tipo", "alias", "descripcion", "notas"}
        cambios = {clave: valor for clave, valor in campos.items() if clave in permitidos}
        if "alias" in cambios:
            cambios["alias"] = unir_alias(cambios["alias"])
        if not cambios:
            lugar = self.obtener(obra_id, nombre)
            if lugar is None:
                raise ValueError(f"No existe el lugar '{nombre}'.")
            return lugar
        sets = ", ".join(f"{clave} = ?" for clave in cambios)
        valores = [*cambios.values(), obra_id, nombre]
        cursor = self.conn.execute(
            f"""
            UPDATE lugares
               SET {sets},
                   actualizado_en = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
             WHERE obra_id = ? AND nombre = ?
            """,
            valores,
        )
        self.conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"No existe el lugar '{nombre}'.")
        lugar = self.obtener(obra_id, str(cambios.get("nombre", nombre)))
        assert lugar is not None
        return lugar

    def eliminar(self, obra_id: int, nombre: str) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM lugares WHERE obra_id = ? AND nombre = ?",
            (obra_id, nombre.strip()),
        )
        self.conn.commit()
        return cursor.rowcount > 0


class TerminoRepositorio:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @staticmethod
    def _fila(fila: sqlite3.Row, variantes: tuple[Variante, ...] = ()) -> Termino:
        return Termino(
            id=int(fila["id"]),
            obra_id=int(fila["obra_id"]),
            termino=str(fila["termino"]),
            tipo=str(fila["tipo"]),
            definicion=fila["definicion"],
            notas=fila["notas"],
            sensible=_bool(fila["sensible"]),
            variantes=variantes,
        )

    def agregar(
        self,
        obra_id: int,
        termino: str,
        *,
        tipo: str = "glosario",
        definicion: str | None = None,
        notas: str | None = None,
        sensible: bool = False,
    ) -> Termino:
        termino = termino.strip()
        if not termino:
            raise ValueError("El término no puede estar vacío.")
        if tipo not in _TIPOS_TERMINO:
            raise ValueError(
                f"Tipo de término inválido: {tipo!r}. "
                f"Usa uno de: {', '.join(sorted(_TIPOS_TERMINO))}."
            )
        try:
            self.conn.execute(
                """
                INSERT INTO terminos
                    (obra_id, termino, tipo, definicion, notas, sensible)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (obra_id, termino, tipo, definicion, notas, int(sensible)),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"El término '{termino}' ({tipo}) ya existe en esta obra."
            ) from exc
        self.conn.commit()
        creado = self.obtener(obra_id, termino, tipo)
        assert creado is not None
        return creado

    def listar(self, obra_id: int, *, tipo: str | None = None) -> list[Termino]:
        sql = "SELECT * FROM terminos WHERE obra_id = ?"
        parametros: list[Any] = [obra_id]
        if tipo:
            sql += " AND tipo = ?"
            parametros.append(tipo)
        sql += " ORDER BY termino COLLATE NOCASE"
        filas = self.conn.execute(sql, parametros).fetchall()
        variantes_por_termino = self._variantes_de_obra(obra_id)
        return [
            self._fila(fila, tuple(variantes_por_termino.get(int(fila["id"]), ())))
            for fila in filas
        ]

    def _variantes_de_obra(self, obra_id: int) -> dict[int, list[Variante]]:
        filas = self.conn.execute(
            """
            SELECT v.*
              FROM variantes v
              JOIN terminos t ON t.id = v.termino_id
             WHERE t.obra_id = ?
             ORDER BY v.variante COLLATE NOCASE
            """,
            (obra_id,),
        ).fetchall()
        agrupadas: dict[int, list[Variante]] = {}
        for fila in filas:
            variante = self._fila_variante(fila)
            agrupadas.setdefault(variante.termino_id, []).append(variante)
        return agrupadas

    @staticmethod
    def _fila_variante(fila: sqlite3.Row) -> Variante:
        return Variante(
            id=int(fila["id"]),
            termino_id=int(fila["termino_id"]),
            variante=str(fila["variante"]),
            es_error=_bool(fila["es_error"]),
            notas=fila["notas"],
        )

    def obtener(
        self, obra_id: int, termino: str, tipo: str | None = None
    ) -> Termino | None:
        sql = "SELECT * FROM terminos WHERE obra_id = ? AND termino = ?"
        parametros: list[Any] = [obra_id, termino.strip()]
        if tipo:
            sql += " AND tipo = ?"
            parametros.append(tipo)
        fila = self.conn.execute(sql, parametros).fetchone()
        if not fila:
            return None
        variantes = tuple(self.variantes(int(fila["id"])))
        return self._fila(fila, variantes)

    def buscar(self, obra_id: int, consulta: str) -> list[Termino]:
        patron = f"%{consulta.strip()}%"
        filas = self.conn.execute(
            """
            SELECT * FROM terminos
             WHERE obra_id = ? AND termino LIKE ? COLLATE NOCASE
             ORDER BY termino COLLATE NOCASE
            """,
            (obra_id, patron),
        ).fetchall()
        variantes = self._variantes_de_obra(obra_id)
        return [
            self._fila(fila, tuple(variantes.get(int(fila["id"]), ())))
            for fila in filas
        ]

    def actualizar(self, obra_id: int, termino: str, **campos: Any) -> Termino:
        permitidos = {"termino", "tipo", "definicion", "notas", "sensible"}
        cambios = {clave: valor for clave, valor in campos.items() if clave in permitidos}
        if "tipo" in cambios and cambios["tipo"] not in _TIPOS_TERMINO:
            raise ValueError(f"Tipo de término inválido: {cambios['tipo']!r}.")
        if not cambios:
            encontrado = self.obtener(obra_id, termino)
            if encontrado is None:
                raise ValueError(f"No existe el término '{termino}'.")
            return encontrado
        sets = ", ".join(f"{clave} = ?" for clave in cambios)
        valores = [*cambios.values(), obra_id, termino]
        cursor = self.conn.execute(
            f"""
            UPDATE terminos
               SET {sets},
                   actualizado_en = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
             WHERE obra_id = ? AND termino = ?
            """,
            valores,
        )
        self.conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"No existe el término '{termino}'.")
        encontrado = self.obtener(obra_id, str(cambios.get("termino", termino)))
        assert encontrado is not None
        return encontrado

    def eliminar(self, obra_id: int, termino: str) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM terminos WHERE obra_id = ? AND termino = ?",
            (obra_id, termino.strip()),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def variantes(self, termino_id: int) -> list[Variante]:
        filas = self.conn.execute(
            "SELECT * FROM variantes WHERE termino_id = ? ORDER BY variante COLLATE NOCASE",
            (termino_id,),
        ).fetchall()
        return [self._fila_variante(fila) for fila in filas]

    def agregar_variante(
        self,
        termino_id: int,
        variante: str,
        *,
        es_error: bool = True,
        notas: str | None = None,
    ) -> Variante:
        variante = variante.strip()
        if not variante:
            raise ValueError("La variante no puede estar vacía.")
        try:
            cursor = self.conn.execute(
                """
                INSERT INTO variantes (termino_id, variante, es_error, notas)
                VALUES (?, ?, ?, ?)
                """,
                (termino_id, variante, int(es_error), notas),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"La variante '{variante}' ya existe para este término."
            ) from exc
        self.conn.commit()
        assert cursor.lastrowid is not None
        fila = self.conn.execute(
            "SELECT * FROM variantes WHERE id = ?", (int(cursor.lastrowid),)
        ).fetchone()
        assert fila is not None
        return self._fila_variante(fila)

    def eliminar_variante(self, termino_id: int, variante: str) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM variantes WHERE termino_id = ? AND variante = ?",
            (termino_id, variante.strip()),
        )
        self.conn.commit()
        return cursor.rowcount > 0


class VerboRepositorio:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def agregar(self, obra_id: int | None, verbo: str) -> None:
        verbo = verbo.strip().lower()
        if not verbo:
            raise ValueError("El verbo no puede estar vacío.")
        self.conn.execute(
            "INSERT OR IGNORE INTO verbos_habla (obra_id, verbo) VALUES (?, ?)",
            (obra_id, verbo),
        )
        self.conn.commit()

    def listar(self, obra_id: int | None) -> list[str]:
        filas = self.conn.execute(
            """
            SELECT verbo FROM verbos_habla
             WHERE obra_id IS NULL OR obra_id = ?
             ORDER BY verbo COLLATE NOCASE
            """,
            (obra_id,),
        ).fetchall()
        return [str(fila["verbo"]) for fila in filas]

    def listar_propios(self, obra_id: int) -> list[str]:
        filas = self.conn.execute(
            "SELECT verbo FROM verbos_habla WHERE obra_id = ? ORDER BY verbo COLLATE NOCASE",
            (obra_id,),
        ).fetchall()
        return [str(fila["verbo"]) for fila in filas]

    def eliminar(self, obra_id: int | None, verbo: str) -> bool:
        if obra_id is None:
            cursor = self.conn.execute(
                "DELETE FROM verbos_habla WHERE verbo = ? AND obra_id IS NULL",
                (verbo.strip().lower(),),
            )
        else:
            cursor = self.conn.execute(
                "DELETE FROM verbos_habla WHERE verbo = ? AND obra_id = ?",
                (verbo.strip().lower(), obra_id),
            )
        self.conn.commit()
        return cursor.rowcount > 0


class CorreccionRepositorio:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def registrar(
        self,
        *,
        obra_id: int | None,
        archivo: str,
        hallazgo: Hallazgo,
        aplicado: bool,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO correcciones
                (obra_id, archivo, regla, nivel, linea, columna,
                 original, sugerencia, confianza, aplicado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obra_id,
                archivo,
                hallazgo.regla,
                hallazgo.nivel.value,
                hallazgo.linea,
                hallazgo.columna,
                hallazgo.original,
                hallazgo.sugerencia,
                hallazgo.confianza,
                int(aplicado),
            ),
        )
        self.conn.commit()

    def listar(self, obra_id: int, limite: int = 100) -> list[dict[str, Any]]:
        filas = self.conn.execute(
            """
            SELECT * FROM correcciones
             WHERE obra_id = ?
             ORDER BY creada_en DESC, id DESC
             LIMIT ?
            """,
            (obra_id, limite),
        ).fetchall()
        return [dict(fila) for fila in filas]


class Registro:
    """Fachada de persistencia para CLI, importador y motor."""

    def __init__(self, ruta: Path):
        self.ruta = Path(ruta)
        self._conn = abrir_conexion(self.ruta)
        self.obras = ObraRepositorio(self._conn)
        self.personajes = PersonajeRepositorio(self._conn)
        self.lugares = LugarRepositorio(self._conn)
        self.terminos = TerminoRepositorio(self._conn)
        self.verbos = VerboRepositorio(self._conn)
        self.correcciones = CorreccionRepositorio(self._conn)

    def cerrar(self) -> None:
        self._conn.close()

    def __enter__(self) -> Registro:
        return self

    def __exit__(self, *exc: object) -> None:
        self.cerrar()

    def glosario(self, obra_slug: str) -> Glosario:
        obra = self.obras.obtener(obra_slug)
        if obra is None:
            raise ValueError(
                f"No existe la obra '{obra_slug}'. "
                "Crea una con `onirifix registro obras crear` o importa un YAML."
            )
        return self.glosario_para_id(obra.id)

    def glosario_para_id(self, obra_id: int) -> Glosario:
        nombres: set[str] = set()
        alias: set[str] = set()
        for personaje in self.personajes.listar(obra_id):
            nombres.add(personaje.nombre)
            alias.update(separar_alias(personaje.alias))

        toponimos: set[str] = set()
        for lugar in self.lugares.listar(obra_id):
            toponimos.add(lugar.nombre)
            alias.update(separar_alias(lugar.alias))

        terminos: set[str] = set()
        variantes: dict[str, str] = {}
        for termino in self.terminos.listar(obra_id):
            if termino.tipo == "toponimo":
                toponimos.add(termino.termino)
            else:
                terminos.add(termino.termino)
            for variante in termino.variantes:
                if variante.es_error:
                    variantes[variante.variante.casefold()] = termino.termino

        return Glosario(
            nombres=frozenset(nombres),
            alias=frozenset(alias),
            toponimos=frozenset(toponimos),
            terminos=frozenset(terminos),
            variantes=variantes,
            verbos_habla=frozenset(self.verbos.listar(obra_id)),
        )

    def resumen(self, obra_slug: str) -> dict[str, int]:
        obra = self.obras.obtener(obra_slug)
        if obra is None:
            raise ValueError(f"No existe la obra '{obra_slug}'.")
        return {
            "personajes": len(self.personajes.listar(obra.id)),
            "lugares": len(self.lugares.listar(obra.id)),
            "terminos": len(self.terminos.listar(obra.id)),
            "verbos": len(self.verbos.listar(obra.id)),
        }
