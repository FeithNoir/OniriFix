"""Configuración y ajustes de entorno.

La configuración es un diccionario YAML fusionado con defaults internos. Las
variables de entorno y las opciones de CLI tienen prioridad, de modo que el
mismo proyecto se puede ejecutar en local, en CI o sobre otra base de datos sin
editar el YAML.
"""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULTS: dict[str, Any] = {
    "version": 1,
    "idioma": "es",
    "umbral_l2": 0.90,
    "backup": True,
    "auditoria": True,
    "informes": {
        "max_por_regla": 300,
        "incluir_contexto": True,
    },
    "reglas": {
        "TIP-001": True,
        "TIP-002": True,
        "TIP-003": True,
        "TIP-004": True,
        "TIP-005": True,
        "TIP-006": True,
        "TIP-007": True,
        "TIP-008": True,
        "TIP-009": True,
        "TIP-010": False,
        "DIA-001": True,
        "DIA-002": True,
        "DIA-003": False,
        "DIA-004": True,
        "DIA-005": True,
        "TIL-001": True,
        "TIL-002": True,
        "HOM-001": True,
        "HOM-002": True,
        "ORT-001": True,
        "ORT-002": True,
        "ORT-003": True,
        "CON-001": True,
        "CON-002": True,
        "REP-001": True,
        "REP-002": True,
        "REP-003": True,
        "REP-004": True,
    },
    "tipografia": {
        "comillas": "«»",
        "convertir_comillas": True,
        "convertir_apostrofos": True,
        "puntos_suspensivos": True,
        "rayas": True,
        "espacios": True,
        "puntuacion": True,
        "guion_dialogo": True,
        "normalizar_saltos": True,
    },
    "dialogos": {
        "rae_estricto": False,
        "verbos_extra": [],
    },
    "tildes": {
        "hacia": True,
        "futuros_truncados": True,
        "permitir_voseo": False,
        "palabras_validas_extra": [],
    },
    "ortografia": {
        "diccionario": None,
        "lista_palabras": None,
        "usar_diccionario": True,
        "correcciones": {
            "q": "que",
            "xq": "porque",
            "pq": "porque",
            "tmb": "también",
            "d": "de",
        },
        "palabras_ignoradas": [],
    },
    "consistencia": {
        "similitud_minima": 92,
        "incluir_personajes": True,
        "incluir_lugares": True,
        "incluir_terminos": True,
    },
    "repeticion": {
        "top": 50,
        "minimo_palabras": 8,
        "min_longitud": 4,
        "incluir_glosario": False,
        "por_capitulo": True,
        "longitud_frase": 60,
        "stopwords": [
            "a",
            "al",
            "algo",
            "algunas",
            "algunos",
            "ante",
            "antes",
            "aqui",
            "así",
            "aun",
            "aunque",
            "bajo",
            "bien",
            "cada",
            "casi",
            "como",
            "con",
            "contra",
            "cual",
            "cuando",
            "de",
            "del",
            "desde",
            "donde",
            "dos",
            "el",
            "ella",
            "ellas",
            "ellos",
            "en",
            "entre",
            "era",
            "eran",
            "eres",
            "es",
            "esa",
            "esas",
            "ese",
            "eso",
            "esos",
            "esta",
            "estaba",
            "estaban",
            "estado",
            "estas",
            "este",
            "esto",
            "estos",
            "fue",
            "fueron",
            "ha",
            "había",
            "habían",
            "han",
            "hasta",
            "hay",
            "la",
            "las",
            "le",
            "les",
            "lo",
            "los",
            "más",
            "me",
            "mi",
            "mientras",
            "muy",
            "nada",
            "ni",
            "no",
            "nos",
            "nosotros",
            "o",
            "os",
            "otra",
            "otras",
            "otro",
            "otros",
            "para",
            "pero",
            "poco",
            "por",
            "porque",
            "que",
            "quien",
            "se",
            "sea",
            "ser",
            "si",
            "sin",
            "sobre",
            "solo",
            "son",
            "su",
            "sus",
            "también",
            "tan",
            "tanto",
            "te",
            "tener",
            "tiene",
            "todo",
            "todos",
            "tu",
            "tus",
            "un",
            "una",
            "unas",
            "uno",
            "unos",
            "y",
            "ya",
            "yo",
        ],
    },
    "duplicados": {
        "minimo_palabras": 8,
        "similitud": 92,
        "maximo_parrafos": 2000,
    },
    "residuo_ia": {
        "frases": [
            "en el vasto tapiz",
            "un testimonio de",
            "no solo",
            "en resumen",
            "es importante destacar",
            "en conclusión",
            "como si el tiempo se detuviera",
            "un torbellino de emociones",
            "en la encrucijada de",
            "una sinfonía de",
            "el eco de",
            "una danza de",
            "en el corazón de",
            "un recordatorio de que",
            "un viaje de autodescubrimiento",
            "con cada fibra de su ser",
            "el peso de",
            "la esencia misma de",
        ]
    },
}


def _fusionar(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Fusiona diccionarios de forma recursiva sin mutar los originales."""

    resultado = copy.deepcopy(base)
    for clave, valor in override.items():
        if (
            isinstance(valor, dict)
            and valor
            and isinstance(resultado.get(clave), dict)
        ):
            resultado[clave] = _fusionar(resultado[clave], valor)
        else:
            # Un mapa vacío es una decisión explícita: vacía los defaults.
            resultado[clave] = copy.deepcopy(valor)
    return resultado


def _a_bool(valor: Any, defecto: bool = False) -> bool:
    if isinstance(valor, bool):
        return valor
    if valor is None:
        return defecto
    return str(valor).strip().lower() in {"1", "true", "si", "sí", "yes", "on"}


class Configuracion:
    """Acceso tipado y tolerante a la configuración YAML."""

    def __init__(self, datos: dict[str, Any] | None = None, ruta: Path | None = None):
        self.datos = _fusionar(DEFAULTS, datos or {})
        self.ruta = ruta

    @classmethod
    def cargar(cls, ruta: Path | None) -> Configuracion:
        if ruta is None or not ruta.exists():
            return cls(ruta=ruta)
        try:
            contenido = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"YAML inválido en {ruta}: {exc}") from exc
        if not isinstance(contenido, dict):
            raise ValueError(f"La configuración debe ser un objeto YAML: {ruta}")
        return cls(contenido, ruta=ruta)

    def obtener(self, clave: str, defecto: Any = None) -> Any:
        actual: Any = self.datos
        for parte in clave.split("."):
            if not isinstance(actual, dict) or parte not in actual:
                return defecto
            actual = actual[parte]
        return actual

    def regla_activa(self, regla_id: str, por_defecto: bool = True) -> bool:
        reglas = self.obtener("reglas", {}) or {}
        if regla_id in reglas:
            return _a_bool(reglas[regla_id], por_defecto)
        return por_defecto

    def umbral_l2(self, override: float | None = None) -> float:
        valor = override if override is not None else self.obtener("umbral_l2", 0.90)
        try:
            umbral = float(valor)
        except (TypeError, ValueError):
            umbral = 0.90
        return max(0.0, min(1.0, umbral))

    @property
    def comillas(self) -> str:
        valor = str(self.obtener("tipografia.comillas", "«»"))
        return valor if len(valor) == 2 else "«»"

    @property
    def idioma(self) -> str:
        return str(self.obtener("idioma", "es")).lower()

    def validar(self) -> list[str]:
        avisos: list[str] = []
        if self.obtener("idioma") not in {"es", "en"}:
            avisos.append(
                "idioma distinto de 'es'/'en': las reglas están pensadas para español."
            )
        comillas = str(self.obtener("tipografia.comillas", "«»"))
        if len(comillas) != 2:
            avisos.append("tipografia.comillas debe tener exactamente dos caracteres.")
        try:
            float(self.obtener("umbral_l2", 0.90))
        except (TypeError, ValueError):
            avisos.append("umbral_l2 no es numérico; se usará 0.90.")
        reglas = self.obtener("reglas", {})
        if not isinstance(reglas, dict):
            avisos.append("reglas debe ser un mapa de ID → booleano.")
        return avisos

    def guardar_plantilla(self, ruta: Path, *, sobrescribir: bool = False) -> Path:
        if ruta.exists() and not sobrescribir:
            return ruta
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(
            yaml.safe_dump(
                DEFAULTS,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            ),
            encoding="utf-8",
        )
        return ruta


# ---------------------------------------------------------------------------
# Ajustes de ejecución
# ---------------------------------------------------------------------------


def _cargar_dotenv(ruta: Path) -> None:
    """Carga un ``.env`` sencillo sin dependencias externas.

    No pisa variables ya definidas en el entorno: el shell y el CI mandan.
    """

    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        if linea.startswith("export "):
            linea = linea[7:].strip()
        clave, valor = linea.split("=", 1)
        clave = clave.strip()
        valor = valor.strip().strip('"').strip("'")
        if clave and clave not in os.environ:
            os.environ[clave] = valor


def _ruta(valor: str | Path | None, raiz: Path, defecto: str) -> Path:
    if valor is None or str(valor).strip() == "":
        return (raiz / defecto).resolve()
    candidata = Path(valor).expanduser()
    if not candidata.is_absolute():
        candidata = raiz / candidata
    return candidata.resolve()


@dataclass(slots=True)
class Settings:
    """Ajustes resueltos para una ejecución."""

    raiz: Path
    db: Path
    config: Path
    salida: Path
    backups: Path
    obra: str = "general"
    idioma: str = "es"
    log_level: str = "WARNING"
    umbral_l2: float = 0.90
    backup: bool = True
    auditoria: bool = True

    def asegurar_directorios(self) -> None:
        for ruta in (self.db.parent, self.salida, self.backups):
            ruta.mkdir(parents=True, exist_ok=True)

    def relativa(self, ruta: Path) -> str:
        try:
            return str(ruta.resolve().relative_to(self.raiz))
        except ValueError:
            return str(ruta)


def cargar_settings(
    *,
    db: str | Path | None = None,
    config: str | Path | None = None,
    salida: str | Path | None = None,
    backups: str | Path | None = None,
    obra: str | None = None,
    idioma: str | None = None,
    umbral_l2: float | None = None,
    backup: bool | None = None,
    auditoria: bool | None = None,
    log_level: str | None = None,
) -> Settings:
    """Resuelve CLI, entorno y defaults en un único objeto."""

    raiz = Path(os.environ.get("ONIRIFIX_HOME", Path.cwd())).expanduser().resolve()
    _cargar_dotenv(raiz / ".env")

    db_final = _ruta(db or os.environ.get("ONIRIFIX_DB"), raiz, "data/onirifix.db")
    config_final = _ruta(
        config or os.environ.get("ONIRIFIX_CONFIG"), raiz, "config/reglas.yaml"
    )
    salida_final = _ruta(
        salida or os.environ.get("ONIRIFIX_SALIDA"), raiz, "informes"
    )
    backups_final = _ruta(
        backups or os.environ.get("ONIRIFIX_BACKUPS"), raiz, ".onirifix/backups"
    )

    umbral_env = os.environ.get("ONIRIFIX_UMBRAL_L2")
    if umbral_l2 is None and umbral_env:
        try:
            umbral_l2 = float(umbral_env)
        except ValueError:
            umbral_l2 = None

    backup_env = os.environ.get("ONIRIFIX_BACKUP")
    auditoria_env = os.environ.get("ONIRIFIX_AUDITORIA")

    return Settings(
        raiz=raiz,
        db=db_final,
        config=config_final,
        salida=salida_final,
        backups=backups_final,
        obra=(obra or os.environ.get("ONIRIFIX_OBRA") or "general").strip(),
        idioma=(idioma or os.environ.get("ONIRIFIX_IDIOMA") or "es").strip().lower(),
        log_level=(log_level or os.environ.get("ONIRIFIX_LOG_LEVEL") or "WARNING")
        .strip()
        .upper(),
        umbral_l2=max(0.0, min(1.0, float(umbral_l2 if umbral_l2 is not None else 0.90))),
        backup=backup if backup is not None else _a_bool(backup_env, True),
        auditoria=auditoria if auditoria is not None else _a_bool(auditoria_env, True),
    )
