"""Apertura, versión y ciclo de vida de la base SQLite."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from onirifix.db.esquema import ESQUEMA_SQL, VERSION_ESQUEMA


class ErrorEsquema(RuntimeError):
    """La base de datos usa una versión de esquema incompatible."""


def aplicar_esquema(conn: sqlite3.Connection) -> None:
    version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    if version == 0:
        conn.executescript(ESQUEMA_SQL)
        conn.execute(f"PRAGMA user_version = {VERSION_ESQUEMA}")
        conn.commit()
        return
    if version < VERSION_ESQUEMA:
        raise ErrorEsquema(
            f"La base de datos usa el esquema v{version}; OniriFix espera "
            f"v{VERSION_ESQUEMA}. Exporta el registro y vuelve a importarlo."
        )
    if version > VERSION_ESQUEMA:
        raise ErrorEsquema(
            f"La base de datos usa el esquema v{version}, más reciente que "
            f"v{VERSION_ESQUEMA}. Actualiza OniriFix."
        )


def abrir_conexion(ruta: Path) -> sqlite3.Connection:
    ruta = ruta.expanduser().resolve()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(ruta, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    aplicar_esquema(conn)
    return conn


@contextmanager
def conexion(ruta: Path) -> Iterator[sqlite3.Connection]:
    conn = abrir_conexion(ruta)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
