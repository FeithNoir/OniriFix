"""Salida de terminal con Rich: tablas, resúmenes y avisos."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.text import Text

from onirifix.config import Configuracion
from onirifix.modelo import Nivel, Regla, ResultadoAnalisis, ResultadoCorreccion
from onirifix.ui import ESTILOS, NIVEL_ESTILO


def _consola() -> Console:
    # Se crea en cada llamada para respetar NO_COLOR/COLUMNS y la captura de
    # salida de click en las pruebas.
    return Console(highlight=False, soft_wrap=False)


def mostrar_ok(mensaje: str) -> None:
    _consola().print(Text("✔ ", style=ESTILOS["ok"]) + Text(mensaje))


def mostrar_aviso(mensaje: str) -> None:
    _consola().print(Text("! ", style=ESTILOS["aviso"]) + Text(mensaje))


def mostrar_error(mensaje: str) -> None:
    _consola().print(Text("✖ ", style=ESTILOS["error"]) + Text(mensaje))


def mostrar_tabla(
    titulo: str, columnas: Sequence[str], filas: Iterable[Sequence[str]]
) -> None:
    tabla = Table(title=titulo, header_style=ESTILOS["titulo"])
    for columna in columnas:
        tabla.add_column(columna, overflow="fold")
    for fila in filas:
        tabla.add_row(*(str(celda) for celda in fila))
    _consola().print(tabla)


def _nivel(nivel: Nivel | str) -> Text:
    valor = nivel.value if isinstance(nivel, Nivel) else str(nivel)
    return Text(valor, style=NIVEL_ESTILO.get(valor, ""))


def mostrar_reglas(reglas: Iterable[Regla], config: Configuracion) -> None:
    tabla = Table(title="Catálogo de reglas", header_style=ESTILOS["titulo"])
    tabla.add_column("ID", style=ESTILOS["codigo"])
    tabla.add_column("Nivel")
    tabla.add_column("Activa")
    tabla.add_column("Descripción", overflow="fold")
    for regla in reglas:
        activa = config.regla_activa(regla.id, regla.por_defecto)
        tabla.add_row(
            regla.id,
            _nivel(regla.nivel),
            Text("sí" if activa else "no", style=ESTILOS["ok"] if activa else ESTILOS["sutil"]),
            regla.descripcion,
        )
    _consola().print(tabla)


def mostrar_resultado(
    resultado: ResultadoAnalisis,
    *,
    obra: str | None = None,
    rutas: dict[str, Path] | None = None,
) -> None:
    consola = _consola()
    doc = resultado.documento
    consola.print(
        Text("OniriFix · ", style=ESTILOS["titulo"])
        + Text(doc.ruta.name, style=ESTILOS["archivo"])
    )
    if obra:
        consola.print(Text("Obra: ") + Text(obra, style=ESTILOS["acento"]))
    consola.print(
        f"Palabras: {doc.palabras} · Capítulos: {len(doc.capitulos)} · "
        f"Reglas: {len(resultado.reglas_ejecutadas)}"
    )

    if resultado.hallazgos:
        niveles = Table(title="Hallazgos por nivel", header_style=ESTILOS["titulo"])
        niveles.add_column("Nivel")
        niveles.add_column("Hallazgos")
        niveles.add_column("Aplicables")
        for nivel in Nivel:
            grupo = resultado.por_nivel(nivel)
            niveles.add_row(
                _nivel(nivel) + Text(f" · {nivel.value}"),
                str(len(grupo)),
                str(sum(1 for h in grupo if h.aplicable)),
            )
        consola.print(niveles)

        reglas = Table(title="Reglas con más hallazgos", header_style=ESTILOS["titulo"])
        reglas.add_column("Regla", style=ESTILOS["codigo"])
        reglas.add_column("Nivel")
        reglas.add_column("Total")
        niveles_por_regla = {h.regla: h.nivel for h in resultado.hallazgos}
        for regla_id, total in list(resultado.conteo_por_regla().items())[:15]:
            reglas.add_row(regla_id, _nivel(niveles_por_regla[regla_id]), str(total))
        consola.print(reglas)
    else:
        consola.print(Text("Sin hallazgos.", style=ESTILOS["ok"]))

    for error in resultado.errores:
        consola.print(Text(f"Error en regla: {error}", style=ESTILOS["error"]))

    if rutas:
        consola.print("Informes:")
        for formato, ruta in rutas.items():
            consola.print(Text(f"  · {formato}: ") + Text(str(ruta), style=ESTILOS["archivo"]))


def mostrar_correccion(correccion: ResultadoCorreccion) -> None:
    consola = _consola()
    consola.print(Text("Corrección", style=ESTILOS["titulo"]))
    consola.print(f"Parches aplicados: {len(correccion.aplicados)}")
    if correccion.omitidos:
        consola.print(
            Text(f"Parches omitidos: {len(correccion.omitidos)}", style=ESTILOS["aviso"])
        )
        for parche, motivo in correccion.omitidos[:10]:
            consola.print(Text(f"  · {parche.regla}: {motivo}", style=ESTILOS["sutil"]))
    if correccion.backup:
        consola.print(
            Text("Copia de seguridad: ") + Text(str(correccion.backup), style=ESTILOS["archivo"])
        )
    if correccion.escrito and correccion.destino:
        consola.print(
            Text("Archivo escrito: ") + Text(str(correccion.destino), style=ESTILOS["archivo"])
        )
    elif correccion.aplicados:
        consola.print(
            Text(
                "Dry-run: no se escribió nada. Añade --aplicar para guardar los cambios.",
                style=ESTILOS["aviso"],
            )
        )
    else:
        consola.print(Text("Dry-run: no hay cambios que aplicar.", style=ESTILOS["sutil"]))


def mostrar_frecuencias(resultado: ResultadoAnalisis, *, top: int = 50) -> None:
    tabla = Table(title="Frecuencia léxica", header_style=ESTILOS["titulo"])
    tabla.add_column("#", justify="right")
    tabla.add_column("Palabra", style=ESTILOS["acento"])
    tabla.add_column("Línea", justify="right")
    tabla.add_column("Detalle", overflow="fold")
    hallazgos = [h for h in resultado.hallazgos if h.regla == "REP-001"][:top]
    for indice, hallazgo in enumerate(hallazgos, start=1):
        tabla.add_row(str(indice), hallazgo.original, str(hallazgo.linea), hallazgo.nota)
    consola = _consola()
    consola.print(tabla)
    if not hallazgos:
        consola.print(Text("Ninguna palabra supera el mínimo configurado.", style=ESTILOS["sutil"]))


def mostrar_duplicados(resultado: ResultadoAnalisis) -> None:
    tabla = Table(title="Párrafos duplicados", header_style=ESTILOS["titulo"])
    tabla.add_column("Línea", justify="right")
    tabla.add_column("Nota", overflow="fold")
    tabla.add_column("Inicio del párrafo", overflow="fold")
    hallazgos = [h for h in resultado.hallazgos if h.regla == "REP-002"]
    for hallazgo in hallazgos:
        tabla.add_row(str(hallazgo.linea), hallazgo.nota, " ".join(hallazgo.original.split())[:80])
    consola = _consola()
    consola.print(tabla)
    if not hallazgos:
        consola.print(Text("No se encontraron párrafos duplicados.", style=ESTILOS["sutil"]))
