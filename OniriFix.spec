# -*- mode: python ; coding: utf-8 -*-
"""Empaquetado de OniriFix con PyInstaller.

Genera dos ejecutables en ``dist/``:

- ``OniriFix.exe``: la CLI de consola de siempre (sin Qt, ligera).
- ``OniriFix-GUI.exe``: la interfaz de escritorio PySide6, sin consola.

El instalador de Inno Setup toma ambos y añade configuración, ejemplos y
documentación. Para construir la GUI hace falta el extra ``[build]`` (incluye
PySide6).
"""

from pathlib import Path

RAIZ = Path(SPECPATH)
ASSETS = RAIZ / "src" / "onirifix" / "assets"

# El motor descubre las reglas con pkgutil en tiempo de ejecución. PyInstaller
# no puede ver esos imports dinámicos, así que los declaramos explícitamente.
REGLAS = [
    "onirifix.reglas.consistencia",
    "onirifix.reglas.diacriticas",
    "onirifix.reglas.dialogos",
    "onirifix.reglas.homofonos",
    "onirifix.reglas.ortografia",
    "onirifix.reglas.preterito",
    "onirifix.reglas.repeticion",
    "onirifix.reglas.tildes",
    "onirifix.reglas.tipografia",
    "onirifix.reglas._comun",
]

EXCLUIR_SIEMPRE = ["docx", "mypy", "pytest", "ruff", "spacy", "spylls"]

# Módulos de Qt que la interfaz no usa: recortan cientos de MB.
EXCLUIR_QT = [
    "PySide6.QtWebEngine",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtQuick",
    "PySide6.QtQml",
    "PySide6.Qt3DCore",
    "PySide6.QtMultimedia",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
]

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

a_cli = Analysis(
    [str(RAIZ / "src" / "onirifix" / "__main__.py")],
    pathex=[str(RAIZ / "src")],
    binaries=[],
    datas=[],
    hiddenimports=REGLAS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[*EXCLUIR_SIEMPRE, "PySide6", "shiboken6"],
    noarchive=False,
    optimize=0,
)
pyz_cli = PYZ(a_cli.pure)

exe_cli = EXE(
    pyz_cli,
    a_cli.scripts,
    a_cli.binaries,
    a_cli.datas,
    [],
    name="OniriFix",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(ASSETS / "icon.ico")],
    version=str(ASSETS / "version_info.txt"),
)

# ---------------------------------------------------------------------------
# Interfaz de escritorio
# ---------------------------------------------------------------------------

a_gui = Analysis(
    [str(RAIZ / "src" / "onirifix" / "gui" / "__main__.py")],
    pathex=[str(RAIZ / "src")],
    binaries=[],
    datas=[(str(ASSETS), "onirifix/assets")],
    hiddenimports=[*REGLAS, "onirifix.gui.ventana"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[*EXCLUIR_SIEMPRE, *EXCLUIR_QT],
    noarchive=False,
    optimize=0,
)
pyz_gui = PYZ(a_gui.pure)

exe_gui = EXE(
    pyz_gui,
    a_gui.scripts,
    a_gui.binaries,
    a_gui.datas,
    [],
    name="OniriFix-GUI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(ASSETS / "icon.ico")],
    version=str(ASSETS / "version_info.txt"),
)
