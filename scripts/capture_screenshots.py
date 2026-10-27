"""Abre el ejecutable en ventanas de consola reales y guarda capturas.

OniriFix es una aplicación de terminal: no tiene ventana propia. Para que las
capturas de la documentación salgan de la aplicación en ejecución, este script
lanza el ejecutable instalado en una consola de Windows, espera a que termine
cada comando y fotografía la ventana resultante.

Uso:
    python scripts/capture_screenshots.py
    python scripts/capture_screenshots.py --exe "C:\\ruta\\OniriFix.exe"
"""

from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

from PIL import Image, ImageGrab

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "docs" / "screenshots"
TRABAJO = RAIZ / ".onirifix-demo"
HOME = TRABAJO / "home"

COLS = 140

CREATE_NEW_CONSOLE = 0x00000010
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
WM_CLOSE = 0x0010


def _preparar_win32():
    user32 = ctypes.windll.user32
    user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.FindWindowW.restype = wintypes.HWND
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
    ]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user32.PostMessageW.argtypes = [wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        user32.SetProcessDPIAware()
    return user32


def _caja_cliente(user32, hwnd: int) -> tuple[int, int, int, int]:
    """Devuelve el área de texto de la consola en coordenadas de pantalla."""

    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    origen = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(origen))
    return (
        origen.x,
        origen.y,
        origen.x + rect.right,
        origen.y + rect.bottom,
    )



def _escribir_lote(lineas: list[str]) -> Path:
    lote = TRABAJO / "captura.cmd"
    contenido = "\r\n".join(lineas) + "\r\n"
    lote.write_text(contenido, encoding="utf-8")
    return lote


def _recortar(imagen: Image.Image) -> Image.Image:
    """Quita el relleno negro inferior y el cursor de la consola."""

    ancho, alto = imagen.size
    pixeles = imagen.convert("RGB").load()
    ultimo = alto - 1
    while ultimo > 0:
        fila = (pixeles[x, ultimo] for x in range(20, max(21, ancho - 20)))
        if any(max(color) > 24 for color in fila):
            break
        ultimo -= 1
    return imagen.crop((0, 0, ancho, min(alto, ultimo + 5)))


def _lanzar(exe: Path, comando: str, titulo: str, destino: Path, lineas: int) -> None:
    marcador = TRABAJO / "captura.lista"
    if marcador.exists():
        marcador.unlink()

    lineas_lote = [
        "@echo off",
        "chcp 65001 >nul",
        f"title {titulo}",
        f"mode con cols={COLS} lines={lineas}",
        f'set "ONIRIFIX_HOME={HOME}"',
        "set \"PYTHONIOENCODING=utf-8\"",
        "set \"PYTHONUTF8=1\"",
        f'cd /d "{TRABAJO}"',
        comando,
        "echo.",
        "powershell -NoProfile -Command \"[Console]::CursorVisible = $false\" >nul 2>nul",
        f'type nul > "{marcador}"',
        "ping -n 30 127.0.0.1 >nul",
    ]
    lote = _escribir_lote(lineas_lote)

    entorno = os.environ.copy()
    entorno["ONIRIFIX_HOME"] = str(HOME)
    entorno["PYTHONIOENCODING"] = "utf-8"
    entorno["PYTHONUTF8"] = "1"
    for clave in ("ONIRIFIX_DB", "ONIRIFIX_CONFIG", "ONIRIFIX_OBRA", "ONIRIFIX_SALIDA"):
        entorno.pop(clave, None)

    proceso = subprocess.Popen(
        ["cmd.exe", "/c", str(lote)],
        cwd=str(TRABAJO),
        env=entorno,
        creationflags=CREATE_NEW_CONSOLE,
    )

    user32 = _preparar_win32()
    hwnd = 0
    limite = time.monotonic() + 90
    while time.monotonic() < limite:
        if hwnd == 0:
            hwnd = user32.FindWindowW(None, titulo) or 0
        if hwnd and marcador.exists():
            break
        if proceso.poll() is not None and not marcador.exists():
            raise RuntimeError(f"la consola termino antes de tiempo: {titulo}")
        time.sleep(0.1)
    else:
        proceso.kill()
        raise TimeoutError(f"sin ventana o sin marcador para: {titulo}")

    # Deja que la consola repinte el último bloque antes de fotografiar.
    time.sleep(0.9)
    user32.ShowWindow(hwnd, 9)
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 40, 8, 0, 0, SWP_NOSIZE | SWP_SHOWWINDOW)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.4)

    caja = _caja_cliente(user32, hwnd)
    imagen = ImageGrab.grab(bbox=caja, all_screens=True)
    imagen = _recortar(imagen)
    destino.parent.mkdir(parents=True, exist_ok=True)
    imagen.save(destino)
    print(f"captura {destino.name} {imagen.width}x{imagen.height}")

    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOSIZE)
    user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
    try:
        proceso.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proceso.terminate()


def _copiar_ejemplos(exe: Path) -> Path:
    candidatos = [exe.parent / "examples", RAIZ / "examples"]
    origen = next((ruta for ruta in candidatos if ruta.is_dir()), None)
    if origen is None:
        raise FileNotFoundError("no se encontro la carpeta examples")
    destino = TRABAJO / "examples"
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(origen, destino)
    return destino


def main() -> None:
    parser = argparse.ArgumentParser(description="Captura la CLI de OniriFix en consolas reales.")
    parser.add_argument(
        "--exe",
        type=Path,
        default=RAIZ / "dist" / "OniriFix.exe",
        help="Ejecutable a fotografiar (por defecto dist/OniriFix.exe).",
    )
    args = parser.parse_args()
    exe = args.exe.resolve()
    if not exe.exists():
        raise FileNotFoundError(f"no existe el ejecutable: {exe}")

    if TRABAJO.exists():
        shutil.rmtree(TRABAJO)
    HOME.mkdir(parents=True)
    SALIDA.mkdir(parents=True, exist_ok=True)
    _copiar_ejemplos(exe)

    comillas = f'"{exe}"'
    pasos = [
        ("OniriFix - bienvenida", "01-bienvenida.png", f"{comillas} init", 20),
        ("OniriFix - ayuda", "02-ayuda.png", f"{comillas} --help", 32),
        ("OniriFix - diagnostico", "03-doctor.png", f"{comillas} doctor", 22),
        (
            "OniriFix - registro",
            "04-registro.png",
            f"{comillas} registro importar examples\\obra.ejemplo.yaml",
            14,
        ),
        (
            "OniriFix - analisis",
            "05-analisis.png",
            f"{comillas} --obra oniriums analizar examples\\manuscrito_ejemplo.md",
            30,
        ),
        (
            "OniriFix - correccion",
            "06-correccion.png",
            f"{comillas} --obra oniriums corregir examples\\manuscrito_ejemplo.md --aplicar",
            40,
        ),
        ("OniriFix - reglas", "07-reglas.png", f"{comillas} reglas", 40),
        (
            "OniriFix - informes",
            "08-informes.png",
            "powershell -NoProfile -ExecutionPolicy Bypass -Command "
            "\"Get-Content -LiteralPath 'home/informes/informe.md' -TotalCount 30\"",
            36,
        ),
    ]

    for titulo, nombre, comando, lineas in pasos:
        _lanzar(exe, comando, titulo, SALIDA / nombre, lineas)

    print(f"\n{len(pasos)} capturas en {SALIDA}")


if __name__ == "__main__":
    sys.exit(main())
