"""Capa de servicio: une configuración, registro, motor, IO e informes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from onirifix.config import Configuracion, Settings
from onirifix.db.repositorios import Registro
from onirifix.io.cargadores import cargar_documento, escribir_texto
from onirifix.linguistica import crear_analizador, crear_corrector
from onirifix.modelo import (
    Documento,
    Nivel,
    Obra,
    Parche,
    ResultadoAnalisis,
    ResultadoCorreccion,
)
from onirifix.nucleo.backups import crear_backup
from onirifix.nucleo.motor import Motor
from onirifix.nucleo.parches import aplicar_parches, seleccionar_parches


@dataclass(slots=True)
class ContextoEjecucion:
    settings: Settings
    config: Configuracion
    registro: Registro
    obra: Obra
    _motor: Motor | None = None

    def motor(self) -> Motor:
        if self._motor is None:
            self._motor = Motor(
                self.config,
                self.registro.glosario_para_id(self.obra.id),
                analizador=crear_analizador(self.config),
                corrector=crear_corrector(self.config),
            )
        return self._motor

    def __enter__(self) -> ContextoEjecucion:
        return self

    def __exit__(self, *exc: object) -> None:
        self.registro.cerrar()


def abrir_contexto(settings: Settings, *, crear_obra: bool = False) -> ContextoEjecucion:
    settings.asegurar_directorios()
    config = Configuracion.cargar(settings.config)
    registro = Registro(settings.db)
    try:
        obra = registro.obras.obtener(settings.obra)
        if obra is None:
            if crear_obra or settings.obra == "general":
                titulo = settings.obra.replace("-", " ").replace("_", " ").title()
                obra = registro.obras.asegurar(settings.obra, titulo=titulo)
            else:
                raise ValueError(
                    f"No existe la obra '{settings.obra}' en {settings.db}. "
                    "Créala con `onirifix registro obras crear` o importa un YAML."
                )
    except Exception:
        registro.cerrar()
        raise
    return ContextoEjecucion(settings=settings, config=config, registro=registro, obra=obra)


def analizar(
    ctx: ContextoEjecucion,
    archivo: Path,
    *,
    solo_reglas: list[str] | None = None,
    incluir_l3: bool = True,
) -> ResultadoAnalisis:
    documento = cargar_documento(archivo)
    return ctx.motor().analizar(
        documento,
        solo_reglas=solo_reglas,
        incluir_l3=incluir_l3,
        obra=ctx.obra,
    )


def parsear_niveles(valor: str) -> set[Nivel]:
    if not valor or not valor.strip():
        return {Nivel.L1}
    return {Nivel.desde(parte) for parte in valor.split(",") if parte.strip()}


def corregir(
    ctx: ContextoEjecucion,
    archivo: Path,
    *,
    niveles: set[Nivel],
    aplicar: bool,
    aplicar_l2: bool,
    umbral_l2: float,
    backup: bool,
    destino: Path | None = None,
    solo_reglas: list[str] | None = None,
) -> ResultadoCorreccion:
    analisis = analizar(ctx, archivo, solo_reglas=solo_reglas, incluir_l3=True)
    parches = seleccionar_parches(
        analisis.hallazgos,
        niveles=niveles,
        aplicar_l2=aplicar_l2,
        umbral_l2=umbral_l2,
    )
    texto_corregido, aplicados, omitidos = aplicar_parches(
        analisis.documento.texto, parches
    )
    correccion = ResultadoCorreccion(
        analisis=analisis,
        texto_corregido=texto_corregido,
        parches_seleccionados=parches,
        aplicados=aplicados,
        omitidos=omitidos,
    )

    if not aplicar or not aplicados:
        return correccion

    destino_final = (destino or archivo).expanduser()
    if analisis.documento.encoding == "docx" and destino_final.suffix.lower() == ".docx":
        raise ValueError(
            "La escritura de .docx todavía no está implementada. "
            "Usa `--destino manuscrito.md` o exporta el documento a texto."
        )
    if destino_final.resolve() == archivo.resolve() and backup:
        correccion.backup = crear_backup(archivo, ctx.settings.backups)

    encoding = "utf-8" if analisis.documento.encoding == "docx" else analisis.documento.encoding
    escribir_texto(destino_final, texto_corregido, encoding=encoding)
    correccion.escrito = True
    correccion.destino = destino_final

    if ctx.settings.auditoria:
        registrar_auditoria(ctx, analisis, aplicados)

    return correccion


def registrar_auditoria(
    ctx: ContextoEjecucion,
    analisis: ResultadoAnalisis,
    aplicados: list[Parche],
) -> None:
    """Registra en SQLite los parches que se han aplicado al manuscrito."""

    indice = {(h.regla, h.inicio): h for h in analisis.hallazgos}
    for parche in aplicados:
        hallazgo = indice.get((parche.regla, parche.inicio))
        if hallazgo is None:
            continue
        ctx.registro.correcciones.registrar(
            obra_id=ctx.obra.id,
            archivo=str(analisis.documento.ruta),
            hallazgo=hallazgo,
            aplicado=True,
        )


def escribir_corregido(
    ctx: ContextoEjecucion,
    documento: Documento,
    texto: str,
    *,
    destino: Path,
    backup: bool,
) -> Path | None:
    """Utilidad para el modo interactivo."""

    respaldo = None
    if destino.resolve() == documento.ruta.resolve() and backup:
        respaldo = crear_backup(documento.ruta, ctx.settings.backups)
    encoding = "utf-8" if documento.encoding == "docx" else documento.encoding
    escribir_texto(destino, texto, encoding=encoding)
    return respaldo
