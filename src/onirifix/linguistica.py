"""Servicios lingüísticos opcionales.

El núcleo funciona sin spaCy ni Hunspell: las reglas que los necesitan bajan su
confianza o se desactivan solas. Esto mantiene la promesa offline-first y evita
obligar a descargar modelos de cientos de megabytes para una primera pasada.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path

from onirifix.config import Configuracion

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Token:
    texto: str
    lema: str
    pos: str


class AnalizadorLinguistico:
    """Envoltura mínima de spaCy con POS-tagging y lematización."""

    def __init__(self, modelo: str | None = None):
        self.modelo = modelo or os.environ.get("ONIRIFIX_SPACY_MODEL", "es_core_news_sm")
        self.nlp = None
        self.error: str | None = None
        self._cache: dict[str, tuple[Token, ...] | None] = {}
        self._cargar()

    def _cargar(self) -> None:
        try:
            import spacy  # type: ignore[import-not-found]
        except ImportError:
            self.error = "spaCy no está instalado (extra [nlp])."
            return
        try:
            self.nlp = spacy.load(self.modelo)
        except Exception as exc:  # pragma: no cover - depende del modelo instalado
            self.error = (
                f"No se pudo cargar el modelo spaCy '{self.modelo}': {exc}. "
                "Instala con `python -m spacy download es_core_news_sm`."
            )

    @property
    def disponible(self) -> bool:
        return self.nlp is not None

    def _tokens(self, texto: str) -> tuple[Token, ...] | None:
        if self.nlp is None:
            return None
        if texto in self._cache:
            return self._cache[texto]
        if len(self._cache) >= 2048:
            self._cache.clear()
        try:
            doc = self.nlp(texto)
        except Exception as exc:  # pragma: no cover
            log.debug("spaCy falló al analizar un fragmento: %s", exc)
            self._cache[texto] = None
            return None
        tokens = tuple(
            Token(texto=token.text, lema=token.lemma_.lower(), pos=token.pos_)
            for token in doc
        )
        self._cache[texto] = tokens
        return tokens

    def tokens(self, texto: str) -> tuple[Token, ...] | None:
        return self._tokens(texto)

    def pos_de(self, palabra: str, contexto: str) -> str | None:
        """Devuelve la etiqueta POS de la primera aparición de ``palabra``."""

        tokens = self._tokens(contexto)
        if not tokens:
            return None
        buscada = palabra.casefold()
        for token in tokens:
            if token.texto.casefold() == buscada:
                return token.pos
        return None

    def lema_de(self, palabra: str, contexto: str) -> str | None:
        tokens = self._tokens(contexto)
        if not tokens:
            return None
        buscada = palabra.casefold()
        for token in tokens:
            if token.texto.casefold() == buscada:
                return token.lema
        return None

    def es_verbo(self, palabra: str, contexto: str) -> bool | None:
        pos = self.pos_de(palabra, contexto)
        if pos is None:
            return None
        return pos in {"VERB", "AUX"}

    def es_preposicion(self, palabra: str, contexto: str) -> bool | None:
        pos = self.pos_de(palabra, contexto)
        if pos is None:
            return None
        return pos in {"ADP", "ADV"}


class CorrectorOrtografico:
    """Diccionario Hunspell opcional o lista de palabras ligera."""

    def __init__(
        self,
        *,
        diccionario: str | Path | None = None,
        lista_palabras: str | Path | None = None,
        ignoradas: set[str] | None = None,
    ):
        self.error: str | None = None
        self._hunspell = None
        self._palabras: set[str] = {p.casefold() for p in (ignoradas or set())}
        self._lista = False
        if diccionario:
            self._cargar_hunspell(Path(diccionario))
        elif lista_palabras:
            self._cargar_lista(Path(lista_palabras))

    def _cargar_hunspell(self, ruta: Path) -> None:
        try:
            from spylls.hunspell import Dictionary  # type: ignore[import-not-found]
        except ImportError:
            self.error = "spylls no está instalado (extra [ortografia])."
            return
        base = self._resolver_base(ruta)
        if base is None:
            self.error = f"No se encontró un diccionario Hunspell en {ruta}."
            return
        try:
            self._hunspell = Dictionary.from_files(str(base))
        except Exception as exc:  # pragma: no cover
            self.error = f"No se pudo cargar el diccionario {base}: {exc}"

    @staticmethod
    def _resolver_base(ruta: Path) -> Path | None:
        ruta = ruta.expanduser()
        if ruta.is_file() and ruta.suffix.lower() in {".dic", ".aff"}:
            base = ruta.with_suffix("")
            return base if base.with_suffix(".dic").exists() else None
        if ruta.is_dir():
            for nombre in ("es_ES", "es", "es_MX", "es_AR"):
                base = ruta / nombre
                if base.with_suffix(".dic").exists():
                    return base
            candidatos = sorted(ruta.glob("*.dic"))
            if candidatos:
                return candidatos[0].with_suffix("")
        if ruta.with_suffix(".dic").exists() and ruta.with_suffix(".aff").exists():
            return ruta
        return None

    def _cargar_lista(self, ruta: Path) -> None:
        try:
            lineas = ruta.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            self.error = f"No se pudo leer la lista de palabras {ruta}: {exc}"
            return
        self._palabras.update(
            linea.strip().casefold()
            for linea in lineas
            if linea.strip() and not linea.startswith("#")
        )
        self._lista = True

    @property
    def disponible(self) -> bool:
        return self._hunspell is not None or self._lista

    def conocida(self, palabra: str) -> bool:
        if not self.disponible:
            return True
        limpia = palabra.strip()
        if not limpia or not any(c.isalpha() for c in limpia):
            return True
        if limpia.casefold() in self._palabras:
            return True
        if self._hunspell is not None:
            try:
                return bool(self._hunspell.lookup(limpia).is_correct)
            except Exception:  # pragma: no cover
                return True
        return False

    def sugerencias(self, palabra: str, limite: int = 3) -> list[str]:
        if self._hunspell is not None:
            try:
                return list(self._hunspell.suggest(palabra)[:limite])
            except Exception:  # pragma: no cover
                return []
        if self._lista:
            return get_close_matches(palabra, self._palabras, n=limite, cutoff=0.72)
        return []


def crear_analizador(config: Configuracion) -> AnalizadorLinguistico | None:
    """Crea spaCy solo si hay una regla activa que pueda aprovecharlo."""

    reglas = config.obtener("reglas", {}) or {}
    if not any(reglas.get(regla_id, False) for regla_id in ("TIL-001", "TIL-002")):
        return None
    analizador = AnalizadorLinguistico()
    if not analizador.disponible:
        log.debug("Analizador lingüístico no disponible: %s", analizador.error)
    return analizador


def crear_corrector(config: Configuracion) -> CorrectorOrtografico | None:
    if not bool(config.obtener("ortografia.usar_diccionario", True)):
        return None
    ruta_dicc = config.obtener("ortografia.diccionario")
    ruta_lista = config.obtener("ortografia.lista_palabras")
    if not ruta_dicc and not ruta_lista:
        return None
    ignoradas = {str(p) for p in (config.obtener("ortografia.palabras_ignoradas", []) or [])}
    corrector = CorrectorOrtografico(
        diccionario=ruta_dicc,
        lista_palabras=ruta_lista,
        ignoradas=ignoradas,
    )
    if not corrector.disponible:
        log.debug("Corrector ortográfico no disponible: %s", corrector.error)
    return corrector
