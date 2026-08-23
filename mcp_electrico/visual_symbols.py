"""Biblioteca SVG para unifilares técnicos.

Los símbolos priorizan legibilidad de ingeniería y consistencia gráfica. No
pretenden reemplazar una librería CAD normativa completa, pero sí ofrecer una
familia coherente de fuente, protecciones, transformador, barras y cargas.
"""

from __future__ import annotations

from html import escape

INK = "#111827"
BLUE = "#0b3a6e"
DIM = "#6b7280"
OPEN = "#c62828"
DEENERGIZED = "#9ca3af"
WARN = "#b7791f"


def _n(v: float) -> str:
    return f"{float(v):.1f}".rstrip("0").rstrip(".")


def _stroke(color: str, width: float = 1.8) -> str:
    return (
        f'stroke="{color}" stroke-width="{_n(width)}" fill="none" '
        'stroke-linecap="round" stroke-linejoin="round"'
    )


def source(x: float, y: float, color: str = INK) -> str:
    """Fuente/red de suministro."""
    r = 19
    return (
        f'<g data-symbol="source" {_stroke(color, 1.8)}>'
        f'<circle cx="{_n(x)}" cy="{_n(y)}" r="{r}"/>'
        f'<path d="M {_n(x-12)} {_n(y)} C {_n(x-8)} {_n(y-8)}, '
        f'{_n(x-3)} {_n(y+8)}, {_n(x+1)} {_n(y)} '
        f'S {_n(x+10)} {_n(y-8)}, {_n(x+13)} {_n(y)}"/>'
        '</g>'
    )


def breaker(
    x: float,
    y: float,
    abierto: bool = False,
    color: str | None = None,
    tipo: str = "breaker",
) -> str:
    """Interruptor unifilar sin caja exterior.

    MCCB/ACB comparten el contacto eléctrico y se distinguen por el rótulo
    técnico externo del alimentador.
    """
    color = color or (OPEN if abierto else INK)
    t = tipo.lower()
    top = y - 11
    bottom = y + 11
    blade_x = x + 8 if abierto else x
    blade_y = y - 4 if abierto else top
    return (
        f'<g data-symbol="breaker" data-protection="{escape(t)}" '
        f'data-state="{"open" if abierto else "closed"}" {_stroke(color, 1.9)}>'
        f'<circle cx="{_n(x)}" cy="{_n(top)}" r="2.2" fill="{color}" stroke="none"/>'
        f'<circle cx="{_n(x)}" cy="{_n(bottom)}" r="2.2" fill="{color}" stroke="none"/>'
        f'<line x1="{_n(x)}" y1="{_n(bottom)}" '
        f'x2="{_n(blade_x)}" y2="{_n(blade_y)}"/>'
        '</g>'
    )


def fuse(x: float, y: float, color: str = INK) -> str:
    return (
        f'<g data-symbol="fuse" {_stroke(color, 1.8)}>'
        f'<line x1="{_n(x)}" y1="{_n(y-17)}" x2="{_n(x)}" y2="{_n(y-8)}"/>'
        f'<rect x="{_n(x-5)}" y="{_n(y-8)}" width="10" height="16"/>'
        f'<line x1="{_n(x)}" y1="{_n(y+8)}" x2="{_n(x)}" y2="{_n(y+17)}"/>'
        '</g>'
    )


def isolator(x: float, y: float, abierto: bool = True, color: str = INK) -> str:
    c = OPEN if abierto else color
    return (
        f'<g data-symbol="isolator" data-state="{"open" if abierto else "closed"}" {_stroke(c, 1.8)}>'
        f'<circle cx="{_n(x)}" cy="{_n(y-11)}" r="2" fill="{c}" stroke="none"/>'
        f'<circle cx="{_n(x)}" cy="{_n(y+11)}" r="2" fill="{c}" stroke="none"/>'
        f'<line x1="{_n(x)}" y1="{_n(y+11)}" '
        f'x2="{_n(x + (9 if abierto else 0))}" y2="{_n(y-7 if abierto else y-11)}"/>'
        '</g>'
    )


def protection(
    x: float,
    y: float,
    tipo: str = "breaker",
    abierto: bool = False,
    color: str | None = None,
) -> str:
    t = (tipo or "breaker").lower()
    color = color or (OPEN if abierto else INK)
    if t == "fuse":
        return fuse(x, y, color)
    if t == "isolator":
        return isolator(x, y, abierto=True if abierto else False, color=color)
    return breaker(x, y, abierto, color, t)


def transformer(
    x: float,
    y: float,
    color: str = INK,
    orientation: str = "vertical",
) -> str:
    r = 15
    if orientation == "horizontal":
        c1, c2 = (x - 10, y), (x + 10, y)
    else:
        c1, c2 = (x, y - 10), (x, y + 10)
    return (
        f'<g data-symbol="transformer" {_stroke(color, 1.8)}>'
        f'<circle cx="{_n(c1[0])}" cy="{_n(c1[1])}" r="{r}"/>'
        f'<circle cx="{_n(c2[0])}" cy="{_n(c2[1])}" r="{r}"/>'
        '</g>'
    )


def busbar(
    x1: float,
    x2: float,
    y: float,
    color: str = INK,
    width: float = 5.0,
) -> str:
    return (
        f'<g data-symbol="busbar">'
        f'<line x1="{_n(x1)}" y1="{_n(y)}" x2="{_n(x2)}" y2="{_n(y)}" '
        f'stroke="{color}" stroke-width="{_n(width)}" stroke-linecap="square"/>'
        '</g>'
    )


def busbar_vertical(
    x: float,
    y1: float,
    y2: float,
    color: str = INK,
    width: float = 5.0,
) -> str:
    return (
        f'<g data-symbol="busbar">'
        f'<line x1="{_n(x)}" y1="{_n(y1)}" x2="{_n(x)}" y2="{_n(y2)}" '
        f'stroke="{color}" stroke-width="{_n(width)}" stroke-linecap="square"/>'
        '</g>'
    )


def junction(x: float, y: float, color: str = INK) -> str:
    return (
        f'<g data-symbol="junction"><circle cx="{_n(x)}" cy="{_n(y)}" '
        f'r="2.4" fill="{color}" stroke="none"/></g>'
    )


def panel(x: float, y: float, color: str = INK) -> str:
    """Tablero: gabinete con barra interior y tres derivaciones."""
    w, h = 38, 44
    return (
        f'<g data-symbol="panel" {_stroke(color, 1.7)}>'
        f'<rect x="{_n(x-w/2)}" y="{_n(y-h/2)}" width="{w}" height="{h}" rx="1"/>'
        f'<line x1="{_n(x-12)}" y1="{_n(y-7)}" x2="{_n(x+12)}" y2="{_n(y-7)}"/>'
        f'<line x1="{_n(x-8)}" y1="{_n(y-7)}" x2="{_n(x-8)}" y2="{_n(y+8)}"/>'
        f'<line x1="{_n(x)}" y1="{_n(y-7)}" x2="{_n(x)}" y2="{_n(y+8)}"/>'
        f'<line x1="{_n(x+8)}" y1="{_n(y-7)}" x2="{_n(x+8)}" y2="{_n(y+8)}"/>'
        '</g>'
    )


def motor(x: float, y: float, color: str = INK) -> str:
    return (
        f'<g data-symbol="motor" {_stroke(color, 1.8)}>'
        f'<circle cx="{_n(x)}" cy="{_n(y)}" r="20"/>'
        f'<text x="{_n(x)}" y="{_n(y+5)}" class="sym-main" '
        f'text-anchor="middle" stroke="none">M</text>'
        '</g>'
    )


def load(x: float, y: float, color: str = INK) -> str:
    return (
        f'<g data-symbol="load" {_stroke(color, 1.8)}>'
        f'<polygon points="{_n(x-17)},{_n(y-14)} {_n(x+17)},{_n(y-14)} {_n(x)},{_n(y+17)}"/>'
        '</g>'
    )


def ats(x: float, y: float, color: str = INK) -> str:
    """ATS con dos entradas superiores y una salida común."""
    w, h = 58, 42
    return (
        f'<g data-symbol="ats" {_stroke(color, 1.7)}>'
        f'<rect x="{_n(x-w/2)}" y="{_n(y-h/2)}" width="{w}" height="{h}" rx="2"/>'
        f'<circle cx="{_n(x-14)}" cy="{_n(y-14)}" r="2" fill="{color}" stroke="none"/>'
        f'<circle cx="{_n(x+14)}" cy="{_n(y-14)}" r="2" fill="{color}" stroke="none"/>'
        f'<circle cx="{_n(x)}" cy="{_n(y+13)}" r="2" fill="{color}" stroke="none"/>'
        f'<line x1="{_n(x-14)}" y1="{_n(y-14)}" x2="{_n(x)}" y2="{_n(y+13)}"/>'
        f'<line x1="{_n(x+14)}" y1="{_n(y-14)}" x2="{_n(x+3)}" y2="{_n(y+9)}" '
        f'stroke-dasharray="3,3"/>'
        f'<text x="{_n(x)}" y="{_n(y+4)}" class="sym-small" '
        f'text-anchor="middle" stroke="none">ATS</text>'
        '</g>'
    )


def ups(x: float, y: float, color: str = INK) -> str:
    w, h = 52, 38
    return (
        f'<g data-symbol="ups" {_stroke(color, 1.7)}>'
        f'<rect x="{_n(x-w/2)}" y="{_n(y-h/2)}" width="{w}" height="{h}" rx="2"/>'
        f'<line x1="{_n(x-20)}" y1="{_n(y+14)}" x2="{_n(x+20)}" y2="{_n(y-14)}"/>'
        f'<text x="{_n(x-12)}" y="{_n(y-4)}" class="sym-small" '
        f'text-anchor="middle" stroke="none">~</text>'
        f'<text x="{_n(x+12)}" y="{_n(y+10)}" class="sym-small" '
        f'text-anchor="middle" stroke="none">=</text>'
        f'<text x="{_n(x)}" y="{_n(y-24)}" class="sym-small" '
        f'text-anchor="middle" stroke="none">UPS</text>'
        '</g>'
    )


def generator(x: float, y: float, color: str = INK) -> str:
    return (
        f'<g data-symbol="generator" {_stroke(color, 1.8)}>'
        f'<circle cx="{_n(x)}" cy="{_n(y)}" r="21"/>'
        f'<text x="{_n(x)}" y="{_n(y+5)}" class="sym-main" '
        f'text-anchor="middle" stroke="none">G</text>'
        '</g>'
    )


def ground(x: float, y: float, color: str = INK) -> str:
    return (
        f'<g data-symbol="ground" {_stroke(color, 1.5)}>'
        f'<line x1="{_n(x)}" y1="{_n(y)}" x2="{_n(x)}" y2="{_n(y+7)}"/>'
        f'<line x1="{_n(x-9)}" y1="{_n(y+7)}" x2="{_n(x+9)}" y2="{_n(y+7)}"/>'
        f'<line x1="{_n(x-6)}" y1="{_n(y+12)}" x2="{_n(x+6)}" y2="{_n(y+12)}"/>'
        f'<line x1="{_n(x-3)}" y1="{_n(y+17)}" x2="{_n(x+3)}" y2="{_n(y+17)}"/>'
        '</g>'
    )
