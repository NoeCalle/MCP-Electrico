"""Visualización de diagramas unifilares SVG para el modelo OpenDSS activo."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import networkx as nx
import opendssdirect as dss

from .core import listar_cargas_criticas


def _bus_sin_nodos(bus: str) -> str:
    return bus.split(".")[0]


def _estado_abierto() -> bool:
    return bool(dss.CktElement.IsOpen(1, 0))


def generar_diagrama_unifilar(ruta_salida: str = "diagrama_red.html") -> dict[str, Any]:
    """
    Genera un unifilar SVG.

    La topología completa se usa para el layout, mientras que un segundo grafo
    excluye elementos abiertos para determinar qué buses siguen conectados a
    la fuente. Así una contingencia activa se representa sin confundir
    "elemento dibujado" con "elemento energizando la red".
    """
    buses = dss.Circuit.AllBusNames()
    if not buses:
        return {"error": "El circuito no tiene buses definidos."}

    criticas = set(listar_cargas_criticas())
    info_bus: dict[str, dict[str, Any]] = {}
    for bus in buses:
        dss.Circuit.SetActiveBus(bus)
        mags = [float(v) for v in dss.Bus.puVmagAngle()[0::2]]
        info_bus[bus] = {
            "kvbase": float(dss.Bus.kVBase()),
            "vpu": sum(mags) / len(mags) if mags else 0.0,
        }

    grafo_total = nx.Graph()
    grafo_energizado = nx.Graph()
    grafo_total.add_nodes_from(buses)
    grafo_energizado.add_nodes_from(buses)

    conexiones: dict[tuple[str, str], dict[str, Any]] = {}

    for nombre in dss.Lines.AllNames():
        dss.Lines.Name(nombre)
        b1 = _bus_sin_nodos(dss.Lines.Bus1())
        b2 = _bus_sin_nodos(dss.Lines.Bus2())
        abierta = _estado_abierto()
        grafo_total.add_edge(b1, b2)
        if not abierta:
            grafo_energizado.add_edge(b1, b2)
        dato = {"tipo": "Línea", "nombre": nombre, "abierta": abierta}
        conexiones[(b1, b2)] = conexiones[(b2, b1)] = dato

    for nombre in dss.Transformers.AllNames():
        dss.Transformers.Name(nombre)
        bs = dss.CktElement.BusNames()
        if len(bs) < 2:
            continue
        b1, b2 = _bus_sin_nodos(bs[0]), _bus_sin_nodos(bs[1])
        abierta = _estado_abierto()
        grafo_total.add_edge(b1, b2)
        if not abierta:
            grafo_energizado.add_edge(b1, b2)
        dato = {"tipo": "Transformador", "nombre": nombre, "abierta": abierta}
        conexiones[(b1, b2)] = conexiones[(b2, b1)] = dato

    candidatos_fuente = [b for b in buses if "source" in b.lower()]
    raiz = candidatos_fuente[0] if candidatos_fuente else buses[0]

    if raiz in grafo_energizado:
        energizados = nx.node_connected_component(grafo_energizado, raiz)
    else:
        energizados = {raiz}

    # Layout principal: conserva también las conexiones abiertas para mostrar
    # exactamente dónde ocurrió la contingencia.
    componente_layout = (
        nx.node_connected_component(grafo_total, raiz)
        if raiz in grafo_total
        else {raiz}
    )
    subgrafo = grafo_total.subgraph(componente_layout).copy()
    arbol = nx.bfs_tree(subgrafo, raiz)

    hojas_por_bus: dict[str, list[dict[str, Any]]] = {}
    for nombre in dss.Loads.AllNames():
        dss.Loads.Name(nombre)
        busnames = dss.CktElement.BusNames()
        if not busnames:
            continue
        bus = _bus_sin_nodos(busnames[0])
        hojas_por_bus.setdefault(bus, []).append(
            {
                "tipo": "carga",
                "nombre": nombre,
                "kw": float(dss.Loads.kW()),
                "critica": nombre in criticas,
            }
        )

    for nombre in dss.Generators.AllNames():
        dss.Generators.Name(nombre)
        busnames = dss.CktElement.BusNames()
        if not busnames:
            continue
        bus = _bus_sin_nodos(busnames[0])
        hojas_por_bus.setdefault(bus, []).append(
            {
                "tipo": "generador",
                "nombre": nombre,
                "kw": float(dss.Generators.kW()),
            }
        )

    LEAF_W, TIER_H = 105, 175
    cursor = [70]
    pos_bus: dict[str, tuple[float, float]] = {}
    span_bus: dict[str, tuple[float, float]] = {}
    pos_hoja: dict[tuple[str, int], float] = {}

    def layout(bus: str, profundidad: int) -> float:
        hijos = list(arbol.successors(bus)) if bus in arbol else []
        xs = [layout(h, profundidad + 1) for h in hijos]
        for i, _ in enumerate(hojas_por_bus.get(bus, [])):
            x = cursor[0]
            cursor[0] += LEAF_W
            pos_hoja[(bus, i)] = x
            xs.append(x)
        if not xs:
            x = cursor[0]
            cursor[0] += LEAF_W
            xs = [x]
        xbus = sum(xs) / len(xs)
        pos_bus[bus] = (xbus, 70 + profundidad * TIER_H)
        span_bus[bus] = (min(xs), max(xs))
        return xbus

    layout(raiz, 0)

    # Componentes no conectados siquiera topológicamente a la fuente.
    fuera_layout = [b for b in buses if b not in pos_bus]
    for i, bus in enumerate(fuera_layout):
        x = cursor[0]
        cursor[0] += LEAF_W
        pos_bus[bus] = (x, 70 + i * 80)
        span_bus[bus] = (x, x)

    profundidad_max = max(
        (nx.shortest_path_length(arbol, raiz, b) for b in arbol.nodes),
        default=0,
    )
    ancho = max(cursor[0] + 80, 820)
    alto = 70 + profundidad_max * TIER_H + 280

    def color_bus(bus: str) -> str:
        if bus not in energizados:
            return "#e6584f"
        vpu = info_bus[bus]["vpu"]
        if 0.95 <= vpu <= 1.05:
            return "#4fd1a5"
        if 0.90 <= vpu <= 1.10:
            return "#e8c547"
        return "#e6584f"

    partes: list[str] = []

    for bus, (bx, by) in pos_bus.items():
        x0, x1 = span_bus[bus]
        x0, x1 = x0 - 35, x1 + 35
        color = color_bus(bus)
        energizado = bus in energizados
        if energizado:
            vtxt = f'{info_bus[bus]["vpu"]:.4f} pu'
        else:
            vtxt = "SIN CONEXIÓN A LA FUENTE"

        partes.append(
            f'<line x1="{x0:.0f}" y1="{by:.0f}" x2="{x1:.0f}" y2="{by:.0f}" '
            f'stroke="{color}" stroke-width="4" stroke-linecap="round"/>'
        )
        partes.append(
            f'<text x="{x0:.0f}" y="{by-14:.0f}" class="lbl-bus">{escape(bus)}</text>'
        )
        partes.append(
            f'<text x="{x0:.0f}" y="{by+18:.0f}" class="lbl-kv" fill="{color}">'
            f'{info_bus[bus]["kvbase"]:.3f} kV · {escape(vtxt)}</text>'
        )

        if bus in arbol:
            for hijo in arbol.successors(bus):
                hx, hy = pos_bus[hijo]
                dato = conexiones.get(
                    (bus, hijo),
                    {"tipo": "Línea", "nombre": "", "abierta": False},
                )
                abierta = bool(dato["abierta"])
                wire = "#e6584f" if abierta else "#5b6b8c"
                partes.append(
                    f'<line x1="{hx:.0f}" y1="{by:.0f}" x2="{hx:.0f}" '
                    f'y2="{by+30:.0f}" stroke="{wire}" stroke-width="1.8"/>'
                )
                if abierta:
                    partes.append(
                        f'<line x1="{hx-9:.0f}" y1="{by+30:.0f}" '
                        f'x2="{hx-2:.0f}" y2="{by+34:.0f}" '
                        f'stroke="#e6584f" stroke-width="2"/>'
                    )
                    partes.append(
                        f'<line x1="{hx+2:.0f}" y1="{by+36:.0f}" '
                        f'x2="{hx+9:.0f}" y2="{by+40:.0f}" '
                        f'stroke="#e6584f" stroke-width="2"/>'
                    )
                    partes.append(
                        f'<text x="{hx+16:.0f}" y="{by+40:.0f}" '
                        f'class="lbl-elem open">ABIERTO</text>'
                    )
                else:
                    partes.append(
                        f'<rect x="{hx-9:.0f}" y="{by+30:.0f}" width="18" '
                        f'height="10" fill="none" stroke="#c9d3e3" stroke-width="1.5"/>'
                    )

                if dato["tipo"] == "Transformador":
                    c1y, c2y = by + 62, by + 94
                    col = "#7a5a44" if abierta else "#c98a55"
                    partes.append(
                        f'<circle cx="{hx:.0f}" cy="{c1y:.0f}" r="20" '
                        f'fill="none" stroke="{col}" stroke-width="1.8"/>'
                    )
                    partes.append(
                        f'<circle cx="{hx:.0f}" cy="{c2y:.0f}" r="20" '
                        f'fill="none" stroke="{col}" stroke-width="1.8"/>'
                    )
                    partes.append(
                        f'<line x1="{hx:.0f}" y1="{c2y+20:.0f}" x2="{hx:.0f}" '
                        f'y2="{hy:.0f}" stroke="{wire}" stroke-width="1.8"/>'
                    )
                    partes.append(
                        f'<text x="{hx+28:.0f}" y="{c1y+4:.0f}" '
                        f'class="lbl-elem">{escape(str(dato["nombre"]))}</text>'
                    )
                else:
                    partes.append(
                        f'<line x1="{hx:.0f}" y1="{by+40:.0f}" x2="{hx:.0f}" '
                        f'y2="{hy:.0f}" stroke="{wire}" stroke-width="1.8"/>'
                    )
                    partes.append(
                        f'<text x="{hx+16:.0f}" y="{(by+hy)/2:.0f}" '
                        f'class="lbl-elem">{escape(str(dato["nombre"]))}</text>'
                    )

        for i, hoja in enumerate(hojas_por_bus.get(bus, [])):
            hx = pos_hoja.get((bus, i), bx)
            y0 = by + 32
            if hoja["tipo"] == "carga":
                critica = bool(hoja["critica"])
                col = "#e6584f" if critica else "#c98a55"
                partes.append(
                    f'<line x1="{hx:.0f}" y1="{by:.0f}" x2="{hx:.0f}" '
                    f'y2="{y0+30:.0f}" stroke="{col}" stroke-width="1.8"/>'
                )
                partes.append(
                    f'<polygon points="{hx-10:.0f},{y0+30:.0f} '
                    f'{hx+10:.0f},{y0+30:.0f} {hx:.0f},{y0+48:.0f}" '
                    f'fill="none" stroke="{col}" stroke-width="1.8"/>'
                )
                marca = " ⚠" if critica else ""
                partes.append(
                    f'<text x="{hx:.0f}" y="{y0+68:.0f}" text-anchor="middle" '
                    f'class="lbl-elem" fill="{col}">'
                    f'{escape(str(hoja["nombre"]))}</text>'
                )
                partes.append(
                    f'<text x="{hx:.0f}" y="{y0+81:.0f}" text-anchor="middle" '
                    f'class="lbl-elem" fill="{col}">{hoja["kw"]:.0f} kW{marca}</text>'
                )
            else:
                cy = y0 + 30
                partes.append(
                    f'<line x1="{hx:.0f}" y1="{by:.0f}" x2="{hx:.0f}" '
                    f'y2="{y0:.0f}" stroke="#4a9de8" stroke-width="1.8" '
                    f'stroke-dasharray="3,3"/>'
                )
                partes.append(
                    f'<circle cx="{hx:.0f}" cy="{cy:.0f}" r="20" fill="none" '
                    f'stroke="#4a9de8" stroke-width="1.8"/>'
                )
                partes.append(
                    f'<text x="{hx:.0f}" y="{cy+5:.0f}" text-anchor="middle" '
                    f'class="lbl-bus" fill="#4a9de8">G</text>'
                )
                partes.append(
                    f'<text x="{hx:.0f}" y="{cy+40:.0f}" text-anchor="middle" '
                    f'class="lbl-elem" fill="#4a9de8">'
                    f'{escape(str(hoja["nombre"]))} · {hoja["kw"]:.0f} kW</text>'
                )

    desconectados = sorted(set(buses) - set(energizados))
    perdidas_kw, _ = dss.Circuit.Losses()
    resumen = (
        f"Convergencia: {'SÍ' if dss.Solution.Converged() else 'NO'} · "
        f"Pérdidas: {float(perdidas_kw)/1000:.3f} kW · "
        f"{len(buses)} buses · {len(dss.Transformers.AllNames())} transformadores · "
        f"{len(dss.Loads.AllNames())} cargas ({len(criticas)} críticas) · "
        f"{len(dss.Generators.AllNames())} generadores"
    )

    es_radial = nx.is_tree(grafo_total) if grafo_total.number_of_nodes() > 0 else True
    if not es_radial:
        resumen += " · ⚠ topología no radial: el dibujo usa un árbol de expansión"

    svg = "\n      ".join(partes)
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Diagrama unifilar — {escape(dss.Circuit.Name())}</title>
<style>
:root {{ --bg:#0b1220; --panel:#121b2e; --border:#22314d; --ink:#e7ecf5;
--dim:#8fa0bd; --copper:#d97a3f; --mono:Consolas,monospace; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
font-family:-apple-system,sans-serif; padding:28px 22px; }}
.wrap {{ max-width:{ancho+40}px; margin:0 auto; }}
.eyebrow {{ font:11px var(--mono); letter-spacing:.12em; color:var(--copper);
text-transform:uppercase; margin-bottom:6px; }}
h1 {{ font-size:20px; margin:0 0 16px; }}
.panel {{ background:var(--panel); border:1px solid var(--border);
border-radius:10px; padding:20px; overflow-x:auto; }}
text {{ font-family:var(--mono); }}
.lbl-bus {{ font-size:12px; fill:var(--ink); font-weight:600; }}
.lbl-kv {{ font-size:10.5px; }}
.lbl-elem {{ font-size:9.5px; fill:var(--dim); }}
.open {{ fill:#e6584f; }}
.footer {{ margin-top:14px; font:11.5px var(--mono); color:var(--dim); }}
.legend {{ display:flex; gap:16px; flex-wrap:wrap; margin-top:12px;
font:10.5px var(--mono); color:var(--dim); }}
</style>
</head>
<body><div class="wrap">
<div class="eyebrow">MCP Eléctrico · OpenDSS · unifilar dinámico</div>
<h1>{escape(dss.Circuit.Name())}</h1>
<div class="panel">
<svg viewBox="0 0 {ancho:.0f} {alto:.0f}" width="{ancho:.0f}"
xmlns="http://www.w3.org/2000/svg">
      {svg}
</svg>
<div class="footer">{escape(resumen)}</div>
<div class="legend">
<span>— Barra</span><span>▭ Interruptor</span><span>◎◎ Transformador</span>
<span>▽ Carga</span><span style="color:#e6584f">▽ Crítica / desenergizada</span>
<span style="color:#4a9de8">◯G Generador</span>
</div>
</div></div></body></html>"""

    salida = Path(ruta_salida).expanduser()
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(html, encoding="utf-8")

    return {
        "archivo_generado": str(salida),
        "buses_dibujados": len(buses),
        "buses_desconectados": desconectados,
        "cargas_dibujadas": len(dss.Loads.AllNames()),
        "generadores_dibujados": len(dss.Generators.AllNames()),
        "transformadores_dibujados": len(dss.Transformers.AllNames()),
        "topologia_radial_pura": es_radial,
    }
