"""Genera el icono de OniriFix para la ventana, el ejecutable y el instalador."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

FONDO = (23, 26, 33, 255)
AMARILLO = (232, 165, 75, 255)
TEAL = (63, 182, 168, 255)
BORDE = (48, 54, 66, 255)


def _punto(size: int, x: float, y: float) -> tuple[int, int]:
    return round(size * x), round(size * y)


def dibujar_icono(size: int = 1024) -> Image.Image:
    """Dibuja una luna creciente con una marca de corrección."""

    imagen = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)

    margen = size * 0.055
    radio = size * 0.23
    dibujo.rounded_rectangle(
        (margen, margen, size - margen, size - margen),
        radius=radio,
        fill=FONDO,
        outline=BORDE,
        width=max(2, round(size * 0.012)),
    )

    # Luna: un círculo ámbar recortado por otro del color del fondo.
    centro = _punto(size, 0.42, 0.44)
    radio_luna = size * 0.235
    dibujo.ellipse(
        (
            centro[0] - radio_luna,
            centro[1] - radio_luna,
            centro[0] + radio_luna,
            centro[1] + radio_luna,
        ),
        fill=AMARILLO,
    )
    recorte = _punto(size, 0.55, 0.33)
    radio_recorte = size * 0.21
    dibujo.ellipse(
        (
            recorte[0] - radio_recorte,
            recorte[1] - radio_recorte,
            recorte[0] + radio_recorte,
            recorte[1] + radio_recorte,
        ),
        fill=FONDO,
    )

    # Marca de corrección.
    puntos = [
        _punto(size, 0.54, 0.64),
        _punto(size, 0.64, 0.74),
        _punto(size, 0.82, 0.48),
    ]
    grosor = max(4, round(size * 0.072))
    dibujo.line(puntos, fill=TEAL, width=grosor, joint="curve")
    for x, y in puntos:
        dibujo.ellipse(
            (x - grosor // 2, y - grosor // 2, x + grosor // 2, y + grosor // 2),
            fill=TEAL,
        )

    # Chispa editorial.
    chispa = _punto(size, 0.77, 0.26)
    radio_chispa = size * 0.026
    dibujo.ellipse(
        (
            chispa[0] - radio_chispa,
            chispa[1] - radio_chispa,
            chispa[0] + radio_chispa,
            chispa[1] + radio_chispa,
        ),
        fill=AMARILLO,
    )
    return imagen


def main() -> None:
    raiz = Path(__file__).resolve().parents[1] / "src" / "onirifix" / "assets"
    raiz.mkdir(parents=True, exist_ok=True)
    grande = dibujar_icono(1024)
    grande.resize((512, 512), Image.Resampling.LANCZOS).save(raiz / "icon.png")
    grande.resize((256, 256), Image.Resampling.LANCZOS).save(
        raiz / "icon.ico",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    print(f"icono generado: {raiz / 'icon.ico'}")


if __name__ == "__main__":
    main()
