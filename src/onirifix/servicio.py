"""Capa de servicio: une configuración, registro, motor, IO e informes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from onirifix.config import Configuracion, Settings
from onirifix.db.repositorios import Registro
from onirifix.io.cargadores import (
    CODIFICACIONES_DERIVADAS,
    cargar_documento,
    destino_corregido,
    escribir_texto,
)
from onirifix.linguistica import crear_analizador, crear_corrector
from onirifix.modelo import (
    Documento,
    Nivel,
    Obra,
    Parche,
    Regla,
    ResultadoAnalisis,
    ResultadoCorreccion,
)
from onirifix.nucleo.backups import crear_backup
from onirifix.nucleo.motor import Motor
from onirifix.nucleo.parches import aplicar_parches, seleccionar_parches
from onirifix.nucleo.registro_reglas import descubrir_reglas


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
    progreso: Callable[[int, int, str], bool | None] | None = None,
) -> ResultadoAnalisis:
    documento = cargar_documento(archivo)
    return ctx.motor().analizar(
        documento,
        solo_reglas=solo_reglas,
        incluir_l3=incluir_l3,
        obra=ctx.obra,
        progreso=progreso,
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
    l2_seguras: bool = False,
    analisis: ResultadoAnalisis | None = None,
) -> ResultadoCorreccion:
    if analisis is None:
        analisis = analizar(ctx, archivo, solo_reglas=solo_reglas, incluir_l3=True)
    parches = seleccionar_parches(
        analisis.hallazgos,
        niveles=niveles,
        aplicar_l2=aplicar_l2,
        umbral_l2=umbral_l2,
        l2_seguras=ctx.config.l2_seguras() if l2_seguras else None,
    )
    return aplicar_seleccion(
        ctx,
        analisis,
        parches,
        aplicar=aplicar,
        backup=backup,
        destino=destino,
        archivo=archivo,
    )


def aplicar_seleccion(
    ctx: ContextoEjecucion,
    analisis: ResultadoAnalisis,
    parches: list[Parche],
    *,
    aplicar: bool = True,
    backup: bool = True,
    destino: Path | None = None,
    archivo: Path | None = None,
) -> ResultadoCorreccion:
    """Aplica una selección concreta de parches sobre el texto analizado.

    Es el único camino de escritura: lo usan ``corregir`` (selección por nivel
    y umbral) y la interfaz de escritorio (selección hecha a mano). Crea la
    copia de seguridad si se escribe sobre el original y registra la auditoría.
    """

    archivo = archivo or analisis.documento.ruta
    texto_corregido, aplicados, omitidos = aplicar_parches(
        analisis.documento.texto, parches
    )
    correccion = ResultadoCorreccion(
        analisis=analisis,
        texto_corregido=texto_corregido,
        parches_seleccionados=list(parches),
        aplicados=aplicados,
        omitidos=omitidos,
    )

    if not aplicar or not aplicados:
        return correccion

    derivado = analisis.documento.encoding in CODIFICACIONES_DERIVADAS
    if destino is None and derivado:
        # Un .docx o .pdf no se reescribe: el texto corregido va a un .md
        # hermano y el original queda intacto.
        destino = destino_corregido(archivo)
    destino_final = (destino or archivo).expanduser()
    if derivado and destino_final.suffix.lower() in {".docx", ".pdf"}:
        raise ValueError(
            f"OniriFix no reescribe {destino_final.suffix}. "
            "Usa `--destino manuscrito.md`; el PDF corregido se exporta aparte."
        )
    if backup and destino_final.exists() and (
        destino_final.resolve() == archivo.resolve() or derivado
    ):
        correccion.backup = crear_backup(destino_final, ctx.settings.backups)

    encoding = "utf-8" if derivado else analisis.documento.encoding
    escribir_texto(destino_final, texto_corregido, encoding=encoding)
    correccion.escrito = True
    correccion.destino = destino_final

    if ctx.settings.auditoria:
        registrar_auditoria(ctx, analisis, aplicados)

    return correccion


def max_por_regla(config: Configuracion) -> int:
    try:
        return int(config.obtener("informes.max_por_regla", 300) or 300)
    except (TypeError, ValueError):
        return 300


def exportar_informes(
    ctx: ContextoEjecucion,
    resultado: ResultadoAnalisis,
    salida: Path,
    *,
    formatos: str = "md,csv,json",
    correccion: ResultadoCorreccion | None = None,
    segundos: float | None = None,
) -> dict[str, Path]:
    """Escribe los informes de un análisis (y su corrección, si la hay)."""

    from onirifix.informes import escribir_informes

    return escribir_informes(
        resultado,
        salida,
        formatos=formatos,
        correccion=correccion,
        max_por_regla=max_por_regla(ctx.config),
        segundos=segundos,
    )


def catalogo_reglas(config: Configuracion) -> list[tuple[Regla, bool]]:
    """Todas las reglas registradas con su estado según la configuración."""

    estricto = bool(config.obtener("dialogos.rae_estricto", False))
    return [
        (
            regla,
            config.regla_activa(regla.id, regla.por_defecto)
            # DIA-003 se activa también con `dialogos.rae_estricto`, como en el motor.
            or (regla.id == "DIA-003" and estricto),
        )
        for regla in descubrir_reglas()
    ]


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
    encoding = "utf-8" if documento.encoding in CODIFICACIONES_DERIVADAS else documento.encoding
    escribir_texto(destino, texto, encoding=encoding)
    return respaldo
