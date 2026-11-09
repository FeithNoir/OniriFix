"""Permite ``python -m onirifix.gui`` y es la entrada del ejecutable con ventana."""

from __future__ import annotations

from onirifix.gui.app import main

if __name__ == "__main__":
    raise SystemExit(main())
