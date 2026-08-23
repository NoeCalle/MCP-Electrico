"""Biblioteca SVG de símbolos para el unifilar técnico.

Los símbolos son deliberadamente simples y consistentes: no pretenden sustituir
una biblioteca CAD normativa completa, pero sí evitar la estética de grafo y
producir un diagrama unifilar reconocible para ingeniería eléctrica.
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


def _stroke(color: str, width: float = 2.0) -> str:
    return f'stroke="{color}" stroke-width="{_n(width)}" fill="none"'


def source(x: float, y: float, color: str = INK) -> str:
    r = 22
    return (
        f'<g data-symbol="source" {_stroke(color)}>'
        f'<circle cx="{_n(x)}" cy="{_n(y)}" r="{r}"/>'
        f'<line x1="{_n(x-r*0.65)}" y1="{_n(y-r*0.65)}" x2="{_n(x+r*0.65)}" y2="{_n(y+r*0.65)}"/>'
        f'<line x1="{_n(x-r*0.65)}" y1="{_n(y+r*0.65)}" x2="{_n(x+r*0.65)}" y2="{_n(y-r*0.65)}"/>'
        f'<line x1="{_n(x-r)}" y1="{_n(y)}" x2="{_n(x+r)}" y2="{_n(y)}" stroke-width="1"/>'
        f'<line x1="{_n(x)}" y1="{_n(y-r)}" x2="{_n(x)}" y2="{_n(y+r)}" stroke-width="1"/>'
        '</g>'
    )


def breaker(x: float, y: float, abierto: bool = False, color: str | None = None) -> str:
    color = color or (OPEN if abierto else INK)
    s = 22
    x0, y0 = x - s / 2, y - s / 2
    if abierto:
        blade = (
            f'<line x1="{_n(x-7)}" y1="{_n(y+7)}" x2="{_n(x+6)}" y2="{_n(y-3)}"/>'
            f'<circle cx="{_n(x-7)}" cy="{_n(y+7)}" r="1.8" fill="{color}" stroke="none"/>'
            f'<circle cx="{_n(x+7)}" cy="{_n(y-7)}" r="1.8" fill="{color}" stroke="none"/>'
        )
    else:
        blade = f'<line x1="{_n(x-7)}" y1="{_n(y+7)}" x2="{_n(x+7)}" y2="{_n(y-7)}"/>'
    return (
        f'<g data-symbol="breaker" data-state="{"open" if abierto else "closed"}" {_stroke(color)}>'
        f'<rect x="{_n(x0)}" y="{_n(y0)}" width="{s}" height="{s}"/>'
        f'{blade}</g>'
    )


def transformer(
    x: float,
    y: float,
    color: str = INK,
    conexion_primario: str | None = None,
    conexion_secundario: str | None = None,
) -> str:
    r = 19
    prim = "Δ" if (conexion_primario or "").lower() == "delta" else "Y"
    sec = "Δ" if (conexion_secundario or "").lower() == "delta" else "Y"
    return (
        f'<g data-symbol="transformer" {_stroke(color)}>'
        f'<circle cx="{_n(x)}" cy="{_n(y-12)}" r="{r}"/>'
        f'<circle cx="{_n(x)}" cy="{_n(y+12)}" r="{r}"/>'
        f'<text x="{_n(x+29)}" y="{_n(y-13)}" class="sym-note">{escape(prim)}</text>'
        f'<text x="{_n(x+29)}" y="{_n(y+20)}" class="sym-note">{escape(sec)}</text>'
        '</g>'
    )


def busbar(x1: float, x2: float, y: float, color: str = INK) -> str:
    return (
        f'<g data-symbol="busbar">'
        f'<line x1="{_n(x1)}" y1="{_n(y)}" x2="{_n(x2)}" y2="{_n(y)}" '
        f'stroke="{color}" stroke-width="5" stroke-linecap="square"/>'
        '</g>'
    )


def panel(x: float, y: float, color: str = INK) -> str:
    w, h = 36, 46
    lines = "".join(
        f'<line x1="{_n(x-11)}" y1="{_n(y-12+i*8)}" x2="{_n(x+11)}" y2="{_n(y-12+i*8)}"/>'
        for i in range(4)
    )
    return (
        f'<g data-symbol="panel" {_stroke(color)}>'
        f'<rect x="{_n(x-w/2)}" y="{_n(y-h/2)}" width="{w}" height="{h}"/>'
        f'{lines}</g>'
    )


def motor(x: float, y: float, color: str = INK) -> str:
    return (
        f'<g data-symbol="motor" {_stroke(color)}>'
        f'<circle cx="{_n(x)}" cy="{_n(y)}" r="22"/>'
        f'<text x="{_n(x)}" y="{_n(y-2)}" class="sym-main" text-anchor="middle">M</text>'
        f'<text x="{_n(x)}" y="{_n(y+12)}" class="sym-small" text-anchor="middle">3~</text>'
        '</g>'
    )


def load(x: float, y: float, color: str = INK) -> str:
    return (
        f'<g data-symbol="load" {_stroke(color)}>'
        f'<polygon points="{_n(x-18)},{_n(y-17)} {_n(x+18)},{_n(y-17)} {_n(x)},{_n(y+18)}"/>'
        '</g>'
    )


def ats(x: float, y: float, color: str = INK) -> str:
    w, h = 52, 40
    return (
        f'<g data-symbol="ats" {_stroke(color)}>'
        f'<rect x="{_n(x-w/2)}" y="{_n(y-h/2)}" width="{w}" height="{h}"/>'
        f'<circle cx="{_n(x-15)}" cy="{_n(y-10)}" r="2.3" fill="{color}" stroke="none"/>'
        f'<circle cx="{_n(x+15)}" cy="{_n(y-10)}" r="2.3" fill="{color}" stroke="none"/>'
        f'<circle cx="{_n(x)}" cy="{_n(y+11)}" r="2.3" fill="{color}" stroke="none"/>'
        f'<line x1="{_n(x-15)}" y1="{_n(y-10)}" x2="{_n(x)}" y2="{_n(y+11)}"/>'
        f'<line x1="{_n(x+15)}" y1="{_n(y-10)}" x2="{_n(x+3)}" y2="{_n(y+7)}" stroke-dasharray="3,3"/>'
        f'<text x="{_n(x)}" y="{_n(y-25)}" class="sym-small" text-anchor="middle">ATS</text>'
        '</g>'
    )


def ups(x: float, y: float, color: str = INK) -> str:
    w, h = 52, 40
    return (
        f'<g data-symbol="ups" {_stroke(color)}>'
        f'<rect x="{_n(x-w/2)}" y="{_n(y-h/2)}" width="{w}" height="{h}"/>'
        f'<line x1="{_n(x-22)}" y1="{_n(y+16)}" x2="{_n(x+22)}" y2="{_n(y-16)}"/>'
        f'<path d="M {_n(x-19)} {_n(y-7)} C {_n(x-14)} {_n(y-15)}, {_n(x-8)} {_n(y+1)}, {_n(x-3)} {_n(y-7)}"/>'
        f'<line x1="{_n(x+5)}" y1="{_n(y+8)}" x2="{_n(x+19)}" y2="{_n(y+8)}"/>'
        f'<line x1="{_n(x+5)}" y1="{_n(y+13)}" x2="{_n(x+19)}" y2="{_n(y+13)}"/>'
        f'<text x="{_n(x)}" y="{_n(y-25)}" class="sym-small" text-anchor="middle">UPS</text>'
        '</g>'
    )


def generator(x: float, y: float, color: str = INK) -> str:
    return (
        f'<g data-symbol="generator" {_stroke(color)}>'
        f'<circle cx="{_n(x)}" cy="{_n(y)}" r="23"/>'
        f'<text x="{_n(x)}" y="{_n(y-3)}" class="sym-main" text-anchor="middle">G</text>'
        f'<text x="{_n(x)}" y="{_n(y+12)}" class="sym-small" text-anchor="middle">3~</text>'
        '</g>'
    )


def ground(x: float, y: float, color: str = INK) -> str:
    return (
        f'<g data-symbol="ground" {_stroke(color, 1.7)}>'
        f'<line x1="{_n(x)}" y1="{_n(y)}" x2="{_n(x)}" y2="{_n(y+8)}"/>'
        f'<line x1="{_n(x-10)}" y1="{_n(y+8)}" x2="{_n(x+10)}" y2="{_n(y+8)}"/>'
        f'<line x1="{_n(x-7)}" y1="{_n(y+13)}" x2="{_n(x+7)}" y2="{_n(y+13)}"/>'
        f'<line x1="{_n(x-4)}" y1="{_n(y+18)}" x2="{_n(x+4)}" y2="{_n(y+18)}"/>'
        '</g>'
    )
