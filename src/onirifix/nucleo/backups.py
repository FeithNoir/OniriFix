"""Copias de seguridad con marca de tiempo antes de tocar un archivo."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from shutil import copy2


def crear_backup(ruta: Path, directorio: Path | None = None) -> Path:
    ruta = ruta.expanduser().resolve()
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el archivo a respaldar: {ruta}")
    destino_dir = (directorio or ruta.parent).expanduser().resolve()
    destino_dir.mkdir(parents=True, exist_ok=True)

    marca = datetime.now().strftime("%Y%m%d-%H%M%S")
    destino = destino_dir / f"{ruta.name}.{marca}.bak"
    contador = 1
    while destino.exists():
        destino = destino_dir / f"{ruta.name}.{marca}-{contador}.bak"
        contador += 1
    copy2(ruta, destino)
    return destino
