"""Esquema SQLite versionado.

El registro es deliberadamente genérico: una obra puede ser una novela, un
guion, una saga o una antología. Personajes, lugares y términos viven en tablas
propias porque cada uno tiene atributos distintos y las reglas los consultan
con frecuencia.
"""

from __future__ import annotations

VERSION_ESQUEMA = 1

ESQUEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS obras (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT    NOT NULL UNIQUE,
    titulo          TEXT    NOT NULL,
    autor           TEXT,
    idioma          TEXT    NOT NULL DEFAULT 'es',
    genero          TEXT,
    descripcion     TEXT,
    creada_en       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    actualizada_en  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS personajes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    obra_id         INTEGER NOT NULL REFERENCES obras(id) ON DELETE CASCADE,
    nombre          TEXT    NOT NULL,
    rol             TEXT,
    alias           TEXT,
    descripcion     TEXT,
    notas           TEXT,
    activo          INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    creado_en       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    actualizado_en  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (obra_id, nombre)
);

CREATE INDEX IF NOT EXISTS idx_personajes_obra ON personajes(obra_id);

CREATE TABLE IF NOT EXISTS lugares (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    obra_id         INTEGER NOT NULL REFERENCES obras(id) ON DELETE CASCADE,
    nombre          TEXT    NOT NULL,
    tipo            TEXT,
    alias           TEXT,
    descripcion     TEXT,
    notas           TEXT,
    creado_en       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    actualizado_en  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (obra_id, nombre)
);

CREATE INDEX IF NOT EXISTS idx_lugares_obra ON lugares(obra_id);

CREATE TABLE IF NOT EXISTS terminos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    obra_id         INTEGER NOT NULL REFERENCES obras(id) ON DELETE CASCADE,
    termino         TEXT    NOT NULL,
    tipo            TEXT    NOT NULL DEFAULT 'glosario'
                    CHECK (tipo IN ('nombre', 'glosario', 'toponimo', 'expresion', 'otro')),
    definicion      TEXT,
    notas           TEXT,
    sensible        INTEGER NOT NULL DEFAULT 0 CHECK (sensible IN (0, 1)),
    creado_en       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    actualizado_en  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (obra_id, termino, tipo)
);

CREATE INDEX IF NOT EXISTS idx_terminos_obra ON terminos(obra_id);

CREATE TABLE IF NOT EXISTS variantes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    termino_id      INTEGER NOT NULL REFERENCES terminos(id) ON DELETE CASCADE,
    variante        TEXT    NOT NULL,
    es_error        INTEGER NOT NULL DEFAULT 1 CHECK (es_error IN (0, 1)),
    notas           TEXT,
    creado_en       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (termino_id, variante)
);

CREATE INDEX IF NOT EXISTS idx_variantes_termino ON variantes(termino_id);

CREATE TABLE IF NOT EXISTS verbos_habla (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    obra_id         INTEGER REFERENCES obras(id) ON DELETE CASCADE,
    verbo           TEXT    NOT NULL,
    creado_en       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (obra_id, verbo)
);

CREATE INDEX IF NOT EXISTS idx_verbos_obra ON verbos_habla(obra_id);

CREATE TABLE IF NOT EXISTS correcciones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    obra_id         INTEGER REFERENCES obras(id) ON DELETE SET NULL,
    archivo         TEXT    NOT NULL,
    regla           TEXT    NOT NULL,
    nivel           TEXT    NOT NULL CHECK (nivel IN ('L1', 'L2', 'L3')),
    linea           INTEGER,
    columna         INTEGER,
    original        TEXT,
    sugerencia      TEXT,
    confianza       REAL,
    aplicado        INTEGER NOT NULL DEFAULT 0 CHECK (aplicado IN (0, 1)),
    creada_en       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_correcciones_obra ON correcciones(obra_id, creada_en);
"""
