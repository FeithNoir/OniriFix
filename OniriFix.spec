# -*- mode: python ; coding: utf-8 -*-
"""Empaquetado de OniriFix con PyInstaller.

Genera un único ejecutable de consola en ``dist/OniriFix.exe``. El instalador
de Inno Setup toma ese archivo y añade configuración, ejemplos y documentación.
"""

from pathlib import Path

RAIZ = Path(SPECPATH)
ASSETS = RAIZ / "src" / "onirifix" / "assets"

# El motor descubre las reglas con pkgutil en tiempo de ejecución. PyInstaller
# no puede ver esos imports dinámicos, así que los declaramos explícitamente.
REGLAS = [
    "onirifix.reglas.consistencia",
    "onirifix.reglas.dialogos",
    "onirifix.reglas.homofonos",
    "onirifix.reglas.ortografia",
    "onirifix.reglas.repeticion",
    "onirifix.reglas.tildes",
    "onirifix.reglas.tipografia",
    "onirifix.reglas._comun",
]

a = Analysis(
    [str(RAIZ / "src" / "onirifix" / "__main__.py")],
    pathex=[str(RAIZ / "src")],
    binaries=[],
    datas=[],
    hiddenimports=REGLAS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["docx", "mypy", "pytest", "ruff", "spacy", "spylls"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
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
