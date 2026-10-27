"""Interfaz de línea de comandos de OniriFix."""

from __future__ import annotations

import functools
import importlib.util
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from onirifix import __version__
from onirifix.config import Configuracion, Settings, cargar_settings
from onirifix.db.importador import escribir_yaml, exportar_yaml, importar_yaml
from onirifix.db.repositorios import Registro
from onirifix.informes import escribir_informes
from onirifix.informes.terminal import (
    mostrar_aviso,
    mostrar_correccion,
    mostrar_duplicados,
    mostrar_frecuencias,
    mostrar_ok,
    mostrar_reglas,
    mostrar_resultado,
    mostrar_tabla,
)
from onirifix.io.cargadores import ErrorLectura
from onirifix.log import configurar_logging
from onirifix.modelo import Nivel, Obra, Parche, ResultadoCorreccion
from onirifix.nucleo.backups import crear_backup
from onirifix.nucleo.parches import aplicar_parches
from onirifix.nucleo.registro_reglas import descubrir_reglas
from onirifix.servicio import (
    abrir_contexto,
    analizar,
    corregir,
    parsear_niveles,
    registrar_auditoria,
)
from onirifix.util import configurar_salida_utf8, slugify

TIPO_TERMINO = click.Choice(["nombre", "glosario", "toponimo", "expresion", "otro"])


def manejar_errores(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except click.ClickException:
            raise
        except (ValueError, OSError, UnicodeError, ErrorLectura) as exc:
            raise click.ClickException(str(exc)) from exc

    return wrapper


def _settings(obj: dict[str, Any]) -> Settings:
    return obj["settings"]


def _lista_ids(valor: str | None) -> list[str] | None:
    if not valor:
        return None
    return [parte.strip() for parte in valor.split(",") if parte.strip()]


def _max_por_regla(config: Configuracion) -> int:
    try:
        return int(config.obtener("informes.max_por_regla", 300) or 300)
    except (TypeError, ValueError):
        return 300


def _escribir(
    settings: Settings,
    config: Configuracion,
    resultado,
    *,
    salida: Path | None,
    formato: str,
    correccion: ResultadoCorreccion | None = None,
) -> dict[str, Path]:
    return escribir_informes(
        resultado,
        salida or settings.salida,
        formatos=formato,
        correccion=correccion,
        max_por_regla=_max_por_regla(config),
    )


def _obra_de(registro: Registro, settings: Settings) -> Obra:
    obra = registro.obras.obtener(settings.obra)
    if obra is None:
        if settings.obra == "general":
            obra = registro.obras.asegurar(settings.obra, titulo="Obra general")
        else:
            raise click.ClickException(
                f"No existe la obra '{settings.obra}'. "
                "Crea una con `onirifix registro obras crear` o usa `--obra`."
            )
    return obra


@click.group(
    context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 110}
)
@click.version_option(__version__, "-V", "--version", prog_name="onirifix")
@click.option(
    "--db",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Ruta de la base SQLite (por defecto ONIRIFIX_DB o data/onirifix.db).",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Ruta del YAML de reglas (por defecto config/reglas.yaml).",
)
@click.option(
    "--obra",
    "-o",
    default=None,
    help="Slug de la obra activa (por defecto ONIRIFIX_OBRA o general).",
)
@click.option("--verbose", "-v", count=True, help="Más detalle en el log (-vv para debug).")
@click.pass_context
def cli(
    ctx: click.Context,
    db: Path | None,
    config_path: Path | None,
    obra: str | None,
    verbose: int,
) -> None:
    """OniriFix: corrección editorial offline para obras de ficción."""

    configurar_salida_utf8()
    settings = cargar_settings(db=db, config=config_path, obra=obra)
    configurar_logging(verbose, settings.log_level)
    ctx.ensure_object(dict)
    ctx.obj["settings"] = settings


# ---------------------------------------------------------------------------
# Inicialización
# ---------------------------------------------------------------------------


@cli.command("init")
@click.pass_obj
@manejar_errores
def init_cmd(obj: dict[str, Any]) -> None:
    """Crea la base de datos, la configuración y la obra por defecto."""

    settings = _settings(obj)
    settings.asegurar_directorios()
    if not settings.config.exists():
        Configuracion().guardar_plantilla(settings.config)
        mostrar_ok(f"Configuración creada: {settings.config}")
    else:
        mostrar_ok(f"Configuración existente: {settings.config}")

    with Registro(settings.db) as registro:
        obra = registro.obras.asegurar(
            settings.obra, titulo=settings.obra.replace("-", " ").title()
        )
        total = len(registro.obras.listar())
    mostrar_ok(f"Base de datos lista: {settings.db}")
    mostrar_ok(f"Obra activa: {obra.slug} · {obra.titulo} ({total} obra(s))")
    mostrar_tabla(
        "Siguientes pasos",
        ["Comando", "Para qué"],
        [
            ("onirifix registro importar obra.yaml", "Sembrar personajes, lugares y términos"),
            ("onirifix analizar manuscrito.md", "Ver el informe sin tocar el archivo"),
            ("onirifix corregir manuscrito.md --aplicar", "Aplicar L1 con copia de seguridad"),
            ("onirifix reglas", "Consultar el catálogo de reglas"),
        ],
    )


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------


@cli.command("reglas")
@click.pass_obj
@manejar_errores
def reglas_cmd(obj: dict[str, Any]) -> None:
    """Lista las reglas disponibles y su estado."""

    settings = _settings(obj)
    config = Configuracion.cargar(settings.config)
    mostrar_reglas(descubrir_reglas(), config)


# ---------------------------------------------------------------------------
# Análisis y corrección
# ---------------------------------------------------------------------------


@cli.command("analizar")
@click.argument("archivo", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--salida", "-s", type=click.Path(file_okay=False, path_type=Path), default=None)
@click.option("--reglas", "-r", default=None, help="IDs de regla separados por coma.")
@click.option("--sin-l3", is_flag=True, help="Oculta los hallazgos de solo informe.")
@click.option("--sin-informes", is_flag=True, help="No escribe archivos de informe.")
@click.option("--formato", "-f", default="md,csv,json", show_default=True)
@click.option("--estricto", is_flag=True, help="Sale con código 1 si hay hallazgos L1/L2.")
@click.pass_obj
@manejar_errores
def analizar_cmd(
    obj: dict[str, Any],
    archivo: Path,
    salida: Path | None,
    reglas: str | None,
    sin_l3: bool,
    sin_informes: bool,
    formato: str,
    estricto: bool,
) -> None:
    """Analiza un manuscrito y genera informes sin modificar el archivo."""

    settings = _settings(obj)
    with abrir_contexto(settings) as ctx:
        resultado = analizar(
            ctx,
            archivo,
            solo_reglas=_lista_ids(reglas),
            incluir_l3=not sin_l3,
        )
        rutas: dict[str, Path] = {}
        if not sin_informes:
            rutas = _escribir(
                settings,
                ctx.config,
                resultado,
                salida=salida,
                formato=formato,
            )
        mostrar_resultado(resultado, obra=ctx.obra.slug, rutas=rutas)
    if estricto and any(
        hallazgo.nivel in {Nivel.L1, Nivel.L2} for hallazgo in resultado.hallazgos
    ):
        raise click.exceptions.Exit(1)


@cli.command("corregir")
@click.argument("archivo", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--nivel",
    type=click.Choice(["L1", "L2", "L1,L2"], case_sensitive=False),
    default="L1",
    show_default=True,
    help="Niveles que se pueden aplicar.",
)
@click.option("--aplicar", is_flag=True, help="Escribe los cambios (por defecto dry-run).")
@click.option("--aplicar-l2", is_flag=True, help="Permite aplicar hallazgos L2.")
@click.option("--umbral", type=click.FloatRange(0.0, 1.0), default=None, help="Confianza mínima L2.")
@click.option("--backup/--sin-backup", "backup", default=None, help="Copia de seguridad antes de escribir.")
@click.option("--destino", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--salida", "-s", type=click.Path(file_okay=False, path_type=Path), default=None)
@click.option("--sin-informes", is_flag=True)
@click.option("--formato", "-f", default="md,csv,json,diff", show_default=True)
@click.pass_obj
@manejar_errores
def corregir_cmd(
    obj: dict[str, Any],
    archivo: Path,
    nivel: str,
    aplicar: bool,
    aplicar_l2: bool,
    umbral: float | None,
    backup: bool | None,
    destino: Path | None,
    salida: Path | None,
    sin_informes: bool,
    formato: str,
) -> None:
    """Aplica correcciones L1 (y L2 con umbral) a un manuscrito."""

    settings = _settings(obj)
    niveles = parsear_niveles(nivel)
    if aplicar_l2:
        niveles.add(Nivel.L2)
    if Nivel.L2 in niveles and not aplicar_l2:
        raise click.UsageError(
            "Para aplicar L2 añade --aplicar-l2 (y revisa --umbral)."
        )
    umbral_final = settings.umbral_l2 if umbral is None else umbral
    backup_final = settings.backup if backup is None else backup

    with abrir_contexto(settings) as ctx:
        correccion = corregir(
            ctx,
            archivo,
            niveles=niveles,
            aplicar=aplicar,
            aplicar_l2=aplicar_l2,
            umbral_l2=umbral_final,
            backup=backup_final,
            destino=destino,
        )
        rutas: dict[str, Path] = {}
        if not sin_informes:
            rutas = _escribir(
                settings,
                ctx.config,
                correccion.analisis,
                salida=salida,
                formato=formato,
                correccion=correccion,
            )
        mostrar_resultado(
            correccion.analisis,
            obra=ctx.obra.slug,
            rutas=rutas,
        )
        mostrar_correccion(correccion)


@cli.command("revisar")
@click.argument("archivo", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--reglas", "-r", default=None, help="IDs de regla separados por coma.")
@click.option(
    "--nivel",
    type=click.Choice(["L1", "L2", "L1,L2"], case_sensitive=False),
    default="L1,L2",
    show_default=True,
)
@click.option("--umbral", type=click.FloatRange(0.0, 1.0), default=0.0, show_default=True)
@click.option("--limite", type=click.IntRange(1), default=100, show_default=True)
@click.option("--destino", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--backup/--sin-backup", "backup", default=None)
@click.option("--simular", is_flag=True, help="No escribe; solo muestra las decisiones.")
@click.option("--salida", "-s", type=click.Path(file_okay=False, path_type=Path), default=None)
@click.option("--formato", "-f", default="md,csv,json,diff", show_default=True)
@click.pass_obj
@manejar_errores
def revisar_cmd(
    obj: dict[str, Any],
    archivo: Path,
    reglas: str | None,
    nivel: str,
    umbral: float,
    limite: int,
    destino: Path | None,
    backup: bool | None,
    simular: bool,
    salida: Path | None,
    formato: str,
) -> None:
    """Revisa hallazgos uno a uno y aplica solo los que decidas."""

    settings = _settings(obj)
    niveles = parsear_niveles(nivel)
    backup_final = settings.backup if backup is None else backup
    console = Console()

    with abrir_contexto(settings) as ctx:
        resultado = analizar(
            ctx,
            archivo,
            solo_reglas=_lista_ids(reglas),
            incluir_l3=False,
        )
        candidatos = [
            hallazgo
            for hallazgo in resultado.hallazgos
            if hallazgo.sugerencia is not None
            and hallazgo.nivel in niveles
            and (hallazgo.nivel != Nivel.L2 or hallazgo.confianza >= umbral)
        ][:limite]

        if not candidatos:
            mostrar_ok("No hay hallazgos revisables con esos filtros.")
            return

        console.print(
            f"[bold]Revisión interactiva[/] · {len(candidatos)} hallazgo(s) · "
            f"{resultado.documento.ruta.name}"
        )
        parches: list[Parche] = []
        aplicar_todo = False
        for indice, hallazgo in enumerate(candidatos, start=1):
            if aplicar_todo:
                parche = Parche.desde_hallazgo(hallazgo)
                if parche:
                    parches.append(parche)
                continue

            console.rule(
                f"[{indice}/{len(candidatos)}] {hallazgo.regla} · "
                f"L{hallazgo.nivel.value[-1]} · línea {hallazgo.linea}"
            )
            console.print(Panel(Text(hallazgo.contexto), border_style="cyan"))
            console.print(Text("Original:    ", style="bold"), Text(hallazgo.original))
            console.print(Text("Sugerencia:  ", style="bold"), Text(hallazgo.sugerencia or ""))
            if hallazgo.nota:
                console.print(Text(hallazgo.nota, style="dim"))

            respuesta = click.prompt(
                "¿Aplicar? [s]í / [n]o / [e]ditar / [t]odos / [q]uitar",
                type=click.Choice(["s", "n", "e", "t", "q"], case_sensitive=False),
                default="n",
                show_choices=False,
            ).lower()

            if respuesta == "q":
                break
            if respuesta == "n":
                continue
            if respuesta == "t":
                aplicar_todo = True
                parche = Parche.desde_hallazgo(hallazgo)
                if parche:
                    parches.append(parche)
                continue
            if respuesta == "e":
                nuevo = click.prompt("Nuevo texto", default=hallazgo.sugerencia or "")
                parche = Parche.desde_hallazgo(hallazgo)
                if parche is not None:
                    parches.append(replace(parche, reemplazo=nuevo))
                continue
            parche = Parche.desde_hallazgo(hallazgo)
            if parche:
                parches.append(parche)

        texto, aplicados, omitidos = aplicar_parches(resultado.documento.texto, parches)
        correccion = ResultadoCorreccion(
            analisis=resultado,
            texto_corregido=texto,
            parches_seleccionados=parches,
            aplicados=aplicados,
            omitidos=omitidos,
        )
        if aplicados and not simular:
            destino_final = (destino or archivo).expanduser()
            if (
                resultado.documento.encoding == "docx"
                and destino_final.suffix.lower() == ".docx"
            ):
                raise click.ClickException(
                    "La escritura .docx no está implementada; usa --destino archivo.md."
                )
            if destino_final.resolve() == archivo.resolve() and backup_final:
                correccion.backup = crear_backup(archivo, settings.backups)
            from onirifix.io.cargadores import escribir_texto

            encoding = (
                "utf-8"
                if resultado.documento.encoding == "docx"
                else resultado.documento.encoding
            )
            escribir_texto(destino_final, texto, encoding=encoding)
            correccion.escrito = True
            correccion.destino = destino_final
            if settings.auditoria:
                registrar_auditoria(ctx, resultado, aplicados)
        elif simular:
            correccion.escrito = False

        if salida is not None:
            rutas = _escribir(
                settings,
                ctx.config,
                resultado,
                salida=salida,
                formato=formato,
                correccion=correccion,
            )
            mostrar_resultado(resultado, obra=ctx.obra.slug, rutas=rutas)
        mostrar_correccion(correccion)


# ---------------------------------------------------------------------------
# Informes concretos
# ---------------------------------------------------------------------------


@cli.command("frecuencia")
@click.argument("archivo", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--top", type=click.IntRange(1), default=50, show_default=True)
@click.option("--por-capitulo/--sin-capitulos", default=True, show_default=True)
@click.option("--salida", "-s", type=click.Path(file_okay=False, path_type=Path), default=None)
@click.option("--formato", "-f", default="md,csv,json", show_default=True)
@click.pass_obj
@manejar_errores
def frecuencia_cmd(
    obj: dict[str, Any],
    archivo: Path,
    top: int,
    por_capitulo: bool,
    salida: Path | None,
    formato: str,
) -> None:
    """Informe de repetición léxica (L3, nunca modifica el archivo)."""

    settings = _settings(obj)
    with abrir_contexto(settings) as ctx:
        ctx.config.datos.setdefault("repeticion", {})["top"] = top
        ctx.config.datos["repeticion"]["por_capitulo"] = por_capitulo
        resultado = analizar(ctx, archivo, solo_reglas=["REP-001"], incluir_l3=True)
        mostrar_frecuencias(resultado, top=top)
        if salida is not None:
            rutas = _escribir(
                settings, ctx.config, resultado, salida=salida, formato=formato
            )
            mostrar_resultado(resultado, obra=ctx.obra.slug, rutas=rutas)


@cli.command("duplicados")
@click.argument("archivo", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--similitud", type=click.FloatRange(0.0, 100.0), default=None)
@click.option("--minimo-palabras", type=click.IntRange(1), default=None)
@click.option("--salida", "-s", type=click.Path(file_okay=False, path_type=Path), default=None)
@click.option("--formato", "-f", default="md,csv,json", show_default=True)
@click.pass_obj
@manejar_errores
def duplicados_cmd(
    obj: dict[str, Any],
    archivo: Path,
    similitud: float | None,
    minimo_palabras: int | None,
    salida: Path | None,
    formato: str,
) -> None:
    """Informe de párrafos duplicados exactos o difusos (L3)."""

    settings = _settings(obj)
    with abrir_contexto(settings) as ctx:
        if similitud is not None:
            ctx.config.datos.setdefault("duplicados", {})["similitud"] = similitud
        if minimo_palabras is not None:
            ctx.config.datos.setdefault("duplicados", {})["minimo_palabras"] = minimo_palabras
        resultado = analizar(ctx, archivo, solo_reglas=["REP-002"], incluir_l3=True)
        mostrar_duplicados(resultado)
        if salida is not None:
            rutas = _escribir(
                settings, ctx.config, resultado, salida=salida, formato=formato
            )
            mostrar_resultado(resultado, obra=ctx.obra.slug, rutas=rutas)


# ---------------------------------------------------------------------------
# Diagnóstico
# ---------------------------------------------------------------------------


@cli.command("doctor")
@click.pass_obj
@manejar_errores
def doctor_cmd(obj: dict[str, Any]) -> None:
    """Comprueba dependencias, rutas, base de datos y reglas."""

    settings = _settings(obj)
    filas: list[tuple[str, str, str]] = [
        ("Python", sys.version.split()[0], "ok"),
        ("OniriFix", __version__, "ok"),
        ("Raíz", str(settings.raiz), "info"),
        ("Base de datos", str(settings.db), "ok" if settings.db.exists() else "se creará"),
        (
            "Configuración",
            str(settings.config),
            "ok" if settings.config.exists() else "defaults internos",
        ),
    ]

    for modulo, paquete, obligatorio in (
        ("click", "click", True),
        ("rich", "rich", True),
        ("yaml", "PyYAML", True),
        ("regex", "regex", False),
        ("rapidfuzz", "rapidfuzz", False),
        ("spacy", "spacy", False),
        ("spylls", "spylls", False),
        ("docx", "python-docx", False),
    ):
        presente = importlib.util.find_spec(modulo) is not None
        estado = "ok" if presente else ("falta" if obligatorio else "opcional, no instalado")
        filas.append((paquete, "instalado" if presente else "no instalado", estado))

    try:
        import spacy  # type: ignore[import-not-found]

        modelos = spacy.util.get_installed_models()
        filas.append(
            (
                "Modelo spaCy",
                ", ".join(modelos) if modelos else "ninguno",
                "ok" if modelos else "opcional",
            )
        )
    except ImportError:
        filas.append(("Modelo spaCy", "spaCy no instalado", "opcional"))

    config = Configuracion.cargar(settings.config)
    for aviso in config.validar():
        filas.append(("Configuración", aviso, "aviso"))

    filas.append(("Reglas registradas", str(len(descubrir_reglas())), "ok"))

    if settings.db.exists():
        with Registro(settings.db) as registro:
            obras = registro.obras.listar()
            filas.append(("Obras en el registro", str(len(obras)), "ok"))
            if obras:
                resumen = ", ".join(f"{o.slug} ({o.titulo})" for o in obras[:6])
                if len(obras) > 6:
                    resumen += "…"
                filas.append(("Obras", resumen, "info"))

    mostrar_tabla("Diagnóstico de OniriFix", ["Elemento", "Valor", "Estado"], filas)


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------


@cli.group("registro")
def registro_group() -> None:
    """Gestiona obras, personajes, lugares, términos y verbos."""


@registro_group.group("obras")
def obras_group() -> None:
    """Obras del registro."""


@obras_group.command("listar")
@click.pass_obj
@manejar_errores
def obras_listar(obj: dict[str, Any]) -> None:
    settings = _settings(obj)
    with Registro(settings.db) as registro:
        obras = registro.obras.listar()
        filas = []
        for obra in obras:
            resumen = registro.resumen(obra.slug)
            filas.append(
                (
                    obra.slug,
                    obra.titulo,
                    obra.autor or "",
                    str(resumen["personajes"]),
                    str(resumen["lugares"]),
                    str(resumen["terminos"]),
                )
            )
    if not filas:
        mostrar_aviso("Todavía no hay obras. Crea una con `onirifix registro obras crear`.")
        return
    mostrar_tabla(
        "Obras",
        ["Slug", "Título", "Autor", "Personajes", "Lugares", "Términos"],
        filas,
    )


@obras_group.command("crear")
@click.argument("slug", required=False)
@click.option("--titulo", "-t", default=None, help="Título de la obra.")
@click.option("--autor", "-a", default=None)
@click.option("--idioma", default="es", show_default=True)
@click.option("--genero", "-g", default=None)
@click.option("--descripcion", "-d", default=None)
@click.pass_obj
@manejar_errores
def obras_crear(
    obj: dict[str, Any],
    slug: str | None,
    titulo: str | None,
    autor: str | None,
    idioma: str,
    genero: str | None,
    descripcion: str | None,
) -> None:
    if not slug and not titulo:
        raise click.UsageError("Indica un slug o un --titulo.")
    slug_final = slugify(slug or titulo or "obra")
    titulo_final = titulo or slug_final.replace("-", " ").title()
    settings = _settings(obj)
    with Registro(settings.db) as registro:
        obra = registro.obras.crear(
            slug=slug_final,
            titulo=titulo_final,
            autor=autor,
            idioma=idioma,
            genero=genero,
            descripcion=descripcion,
        )
    mostrar_ok(f"Obra creada: {obra.slug} · {obra.titulo}")
    mostrar_aviso(f"Actívala con `--obra {obra.slug}` o en ONIRIFIX_OBRA.")


@obras_group.command("ver")
@click.argument("slug")
@click.pass_obj
@manejar_errores
def obras_ver(obj: dict[str, Any], slug: str) -> None:
    settings = _settings(obj)
    with Registro(settings.db) as registro:
        obra = registro.obras.obtener(slug)
        if obra is None:
            raise click.ClickException(f"No existe la obra '{slug}'.")
        resumen = registro.resumen(obra.slug)
    mostrar_tabla(
        "Obra",
        ["Campo", "Valor"],
        [
            ("Slug", obra.slug),
            ("Título", obra.titulo),
            ("Autor", obra.autor or ""),
            ("Idioma", obra.idioma),
            ("Género", obra.genero or ""),
            ("Descripción", obra.descripcion or ""),
            ("Personajes", str(resumen["personajes"])),
            ("Lugares", str(resumen["lugares"])),
            ("Términos", str(resumen["terminos"])),
            ("Verbos de habla", str(resumen["verbos"])),
        ],
    )


@obras_group.command("eliminar")
@click.argument("slug")
@click.option("--si", is_flag=True, help="No pidas confirmación.")
@click.pass_obj
@manejar_errores
def obras_eliminar(obj: dict[str, Any], slug: str, si: bool) -> None:
    settings = _settings(obj)
    if not si and not click.confirm(
        f"¿Eliminar la obra '{slug}' y todos sus datos asociados?", default=False
    ):
        raise click.Abort()
    with Registro(settings.db) as registro:
        if not registro.obras.eliminar(slug):
            raise click.ClickException(f"No existe la obra '{slug}'.")
    mostrar_ok(f"Obra eliminada: {slug}")


def _agregar_personaje(
    registro: Registro,
    obra: Obra,
    nombre: str,
    rol: str | None,
    alias: tuple[str, ...],
    descripcion: str | None,
    notas: str | None,
) -> None:
    personaje = registro.personajes.agregar(
        obra.id,
        nombre,
        rol=rol,
        alias=list(alias),
        descripcion=descripcion,
        notas=notas,
    )
    mostrar_ok(f"Personaje añadido: {personaje.nombre}")


@registro_group.group("personajes")
def personajes_group() -> None:
    """Personajes de la obra activa."""


@personajes_group.command("listar")
@click.pass_obj
@manejar_errores
def personajes_listar(obj: dict[str, Any]) -> None:
    settings = _settings(obj)
    with Registro(settings.db) as registro:
        obra = _obra_de(registro, settings)
        personajes = registro.personajes.listar(obra.id, incluir_inactivos=True)
    if not personajes:
        mostrar_aviso("No hay personajes registrados.")
        return
    mostrar_tabla(
        "Personajes",
        ["Nombre", "Rol", "Alias", "Descripción"],
        [
            (p.nombre, p.rol or "", p.alias or "", p.descripcion or "")
            for p in personajes
        ],
    )


@personajes_group.command("agregar")
@click.argument("nombre")
@click.option("--rol", "-r", default=None)
@click.option("--alias", "-a", multiple=True, help="Repite la opción para varios alias.")
@click.option("--descripcion", "-d", default=None)
@click.option("--notas", "-n", default=None)
@click.pass_obj
@manejar_errores
def personajes_agregar(
    obj: dict[str, Any],
    nombre: str,
    rol: str | None,
    alias: tuple[str, ...],
    descripcion: str | None,
    notas: str | None,
) -> None:
    settings = _settings(obj)
    with Registro(settings.db) as registro:
        obra = _obra_de(registro, settings)
        _agregar_personaje(registro, obra, nombre, rol, alias, descripcion, notas)


@personajes_group.command("eliminar")
@click.argument("nombre")
@click.option("--si", is_flag=True)
@click.pass_obj
@manejar_errores
def personajes_eliminar(obj: dict[str, Any], nombre: str, si: bool) -> None:
    settings = _settings(obj)
    if not si and not click.confirm(f"¿Eliminar el personaje '{nombre}'?", default=False):
        raise click.Abort()
    with Registro(settings.db) as registro:
        obra = _obra_de(registro, settings)
        if not registro.personajes.eliminar(obra.id, nombre):
            raise click.ClickException(f"No existe el personaje '{nombre}'.")
    mostrar_ok(f"Personaje eliminado: {nombre}")


@registro_group.group("lugares")
def lugares_group() -> None:
    """Lugares de la obra activa."""


@lugares_group.command("listar")
@click.pass_obj
@manejar_errores
def lugares_listar(obj: dict[str, Any]) -> None:
    settings = _settings(obj)
    with Registro(settings.db) as registro:
        obra = _obra_de(registro, settings)
        lugares = registro.lugares.listar(obra.id)
    if not lugares:
        mostrar_aviso("No hay lugares registrados.")
        return
    mostrar_tabla(
        "Lugares",
        ["Nombre", "Tipo", "Alias", "Descripción"],
        [(lugar.nombre, lugar.tipo or "", lugar.alias or "", lugar.descripcion or "") for lugar in lugares],
    )


@lugares_group.command("agregar")
@click.argument("nombre")
@click.option("--tipo", "-t", default=None)
@click.option("--alias", "-a", multiple=True)
@click.option("--descripcion", "-d", default=None)
@click.option("--notas", "-n", default=None)
@click.pass_obj
@manejar_errores
def lugares_agregar(
    obj: dict[str, Any],
    nombre: str,
    tipo: str | None,
    alias: tuple[str, ...],
    descripcion: str | None,
    notas: str | None,
) -> None:
    settings = _settings(obj)
    with Registro(settings.db) as registro:
        obra = _obra_de(registro, settings)
        lugar = registro.lugares.agregar(
            obra.id,
            nombre,
            tipo=tipo,
            alias=list(alias),
            descripcion=descripcion,
            notas=notas,
        )
    mostrar_ok(f"Lugar añadido: {lugar.nombre}")


@lugares_group.command("eliminar")
@click.argument("nombre")
@click.option("--si", is_flag=True)
@click.pass_obj
@manejar_errores
def lugares_eliminar(obj: dict[str, Any], nombre: str, si: bool) -> None:
    settings = _settings(obj)
    if not si and not click.confirm(f"¿Eliminar el lugar '{nombre}'?", default=False):
        raise click.Abort()
    with Registro(settings.db) as registro:
        obra = _obra_de(registro, settings)
        if not registro.lugares.eliminar(obra.id, nombre):
            raise click.ClickException(f"No existe el lugar '{nombre}'.")
    mostrar_ok(f"Lugar eliminado: {nombre}")


@registro_group.group("terminos")
def terminos_group() -> None:
    """Términos, glosario y variantes de la obra activa."""


@terminos_group.command("listar")
@click.option("--tipo", type=TIPO_TERMINO, default=None)
@click.pass_obj
@manejar_errores
def terminos_listar(obj: dict[str, Any], tipo: str | None) -> None:
    settings = _settings(obj)
    with Registro(settings.db) as registro:
        obra = _obra_de(registro, settings)
        terminos = registro.terminos.listar(obra.id, tipo=tipo)
    if not terminos:
        mostrar_aviso("No hay términos registrados.")
        return
    mostrar_tabla(
        "Términos",
        ["Término", "Tipo", "Sensible", "Variantes", "Definición"],
        [
            (
                t.termino,
                t.tipo,
                "sí" if t.sensible else "",
                ", ".join(v.variante for v in t.variantes),
                t.definicion or "",
            )
            for t in terminos
        ],
    )


@terminos_group.command("agregar")
@click.argument("termino")
@click.option("--tipo", type=TIPO_TERMINO, default="glosario", show_default=True)
@click.option("--definicion", "-d", default=None)
@click.option("--notas", "-n", default=None)
@click.option("--sensible", is_flag=True)
@click.pass_obj
@manejar_errores
def terminos_agregar(
    obj: dict[str, Any],
    termino: str,
    tipo: str,
    definicion: str | None,
    notas: str | None,
    sensible: bool,
) -> None:
    settings = _settings(obj)
    with Registro(settings.db) as registro:
        obra = _obra_de(registro, settings)
        creado = registro.terminos.agregar(
            obra.id,
            termino,
            tipo=tipo,
            definicion=definicion,
            notas=notas,
            sensible=sensible,
        )
    mostrar_ok(f"Término añadido: {creado.termino} ({creado.tipo})")


@terminos_group.command("variante")
@click.argument("termino")
@click.argument("variante")
@click.option("--correcta", is_flag=True, help="La variante es legítima, no un error.")
@click.option("--notas", "-n", default=None)
@click.pass_obj
@manejar_errores
def terminos_variante(
    obj: dict[str, Any],
    termino: str,
    variante: str,
    correcta: bool,
    notas: str | None,
) -> None:
    settings = _settings(obj)
    with Registro(settings.db) as registro:
        obra = _obra_de(registro, settings)
        encontrado = registro.terminos.obtener(obra.id, termino)
        if encontrado is None:
            raise click.ClickException(f"No existe el término '{termino}'.")
        creada = registro.terminos.agregar_variante(
            encontrado.id, variante, es_error=not correcta, notas=notas
        )
    mostrar_ok(
        f"Variante añadida: {creada.variante} "
        f"({'legítima' if correcta else 'error'}) de {termino}"
    )


@terminos_group.command("variantes")
@click.argument("termino")
@click.pass_obj
@manejar_errores
def terminos_variantes(obj: dict[str, Any], termino: str) -> None:
    settings = _settings(obj)
    with Registro(settings.db) as registro:
        obra = _obra_de(registro, settings)
        encontrado = registro.terminos.obtener(obra.id, termino)
        if encontrado is None:
            raise click.ClickException(f"No existe el término '{termino}'.")
        variantes = registro.terminos.variantes(encontrado.id)
    if not variantes:
        mostrar_aviso(f"El término '{termino}' no tiene variantes.")
        return
    mostrar_tabla(
        "Variantes",
        ["Variante", "Tipo", "Notas"],
        [
            (v.variante, "error" if v.es_error else "legítima", v.notas or "")
            for v in variantes
        ],
    )


@terminos_group.command("eliminar")
@click.argument("termino")
@click.option("--si", is_flag=True)
@click.pass_obj
@manejar_errores
def terminos_eliminar(obj: dict[str, Any], termino: str, si: bool) -> None:
    settings = _settings(obj)
    if not si and not click.confirm(f"¿Eliminar el término '{termino}'?", default=False):
        raise click.Abort()
    with Registro(settings.db) as registro:
        obra = _obra_de(registro, settings)
        if not registro.terminos.eliminar(obra.id, termino):
            raise click.ClickException(f"No existe el término '{termino}'.")
    mostrar_ok(f"Término eliminado: {termino}")


@registro_group.group("verbos")
def verbos_group() -> None:
    """Verbos de habla adicionales de la obra activa."""


@verbos_group.command("listar")
@click.pass_obj
@manejar_errores
def verbos_listar(obj: dict[str, Any]) -> None:
    settings = _settings(obj)
    with Registro(settings.db) as registro:
        obra = _obra_de(registro, settings)
        verbos = registro.verbos.listar(obra.id)
    if not verbos:
        mostrar_aviso("No hay verbos de habla registrados.")
        return
    mostrar_tabla("Verbos de habla", ["Verbo"], [(v,) for v in verbos])


@verbos_group.command("agregar")
@click.argument("verbo")
@click.pass_obj
@manejar_errores
def verbos_agregar(obj: dict[str, Any], verbo: str) -> None:
    settings = _settings(obj)
    with Registro(settings.db) as registro:
        obra = _obra_de(registro, settings)
        registro.verbos.agregar(obra.id, verbo)
    mostrar_ok(f"Verbo añadido: {verbo}")


@verbos_group.command("eliminar")
@click.argument("verbo")
@click.option("--si", is_flag=True)
@click.pass_obj
@manejar_errores
def verbos_eliminar(obj: dict[str, Any], verbo: str, si: bool) -> None:
    settings = _settings(obj)
    if not si and not click.confirm(f"¿Eliminar el verbo '{verbo}'?", default=False):
        raise click.Abort()
    with Registro(settings.db) as registro:
        obra = _obra_de(registro, settings)
        if not registro.verbos.eliminar(obra.id, verbo):
            raise click.ClickException(f"No existe el verbo '{verbo}'.")
    mostrar_ok(f"Verbo eliminado: {verbo}")


@registro_group.command("importar")
@click.argument("ruta", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.pass_obj
@manejar_errores
def registro_importar(obj: dict[str, Any], ruta: Path) -> None:
    """Importa una obra desde YAML (idempotente)."""

    settings = _settings(obj)
    with Registro(settings.db) as registro:
        resultado = importar_yaml(registro, ruta)
    mostrar_ok(f"Obra importada: {resultado.obra.slug} · {resultado.obra.titulo}")
    creados = {k: v for k, v in resultado.creados.items() if v}
    actualizados = {k: v for k, v in resultado.actualizados.items() if v}
    mostrar_tabla(
        "Resultado de la importación",
        ["Tipo", "Creados", "Actualizados"],
        [
            (
                clave,
                str(creados.get(clave, 0)),
                str(actualizados.get(clave, 0)),
            )
            for clave in ("personajes", "lugares", "terminos", "variantes", "verbos")
        ],
    )
    for aviso in resultado.avisos:
        mostrar_aviso(aviso)


@registro_group.command("exportar")
@click.argument("ruta", required=False, type=click.Path(dir_okay=False, path_type=Path))
@click.pass_obj
@manejar_errores
def registro_exportar(obj: dict[str, Any], ruta: Path | None) -> None:
    """Exporta la obra activa a YAML."""

    settings = _settings(obj)
    with Registro(settings.db) as registro:
        obra = _obra_de(registro, settings)
        datos = exportar_yaml(registro, obra.slug)
    destino = ruta or (settings.raiz / f"{obra.slug}.yaml")
    escribir_yaml(datos, destino)
    mostrar_ok(f"Obra exportada: {destino}")


@registro_group.command("historial")
@click.option("--limite", type=click.IntRange(1), default=50, show_default=True)
@click.pass_obj
@manejar_errores
def registro_historial(obj: dict[str, Any], limite: int) -> None:
    """Muestra los cambios aplicados registrados en SQLite."""

    settings = _settings(obj)
    with Registro(settings.db) as registro:
        obra = _obra_de(registro, settings)
        filas = registro.correcciones.listar(obra.id, limite=limite)
    if not filas:
        mostrar_aviso("No hay cambios registrados todavía.")
        return
    mostrar_tabla(
        "Historial de correcciones",
        ["Fecha", "Regla", "Nivel", "Línea", "Original", "Sugerencia"],
        [
            (
                fila["creada_en"],
                fila["regla"],
                fila["nivel"],
                str(fila["linea"] or ""),
                fila["original"] or "",
                fila["sugerencia"] or "",
            )
            for fila in filas
        ],
    )
