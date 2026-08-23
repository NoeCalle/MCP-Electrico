"""Render de diagramas unifilares técnicos para el modelo OpenDSS activo.

NetworkX se usa únicamente para ordenar la topología. El dibujo final sigue
reglas de unifilar: fuente, barras, alimentadores ortogonales, interruptores y
símbolos eléctricos consistentes.
"""

from __future__ import annotations

from html import escape
from math import sqrt
from pathlib import Path
from typing import Any

import networkx as nx
import opendssdirect as dss

from .core import listar_cargas_criticas
from . import visual_state
from . import visual_symbols as sym


PAGE_MARGIN = 38
HEADER_H = 76
SOURCE_H = 126
TIER_H = 270
BRANCH_W = 190
LEGEND_W = 250


def _bus_sin_nodos(bus: str) -> str:
    return bus.split(".")[0]


def _estado_abierto() -> bool:
    return bool(dss.CktElement.IsOpen(1, 0))


def _bus_info(bus: str) -> dict[str, Any]:
    dss.Circuit.SetActiveBus(bus)
    mags = [float(v) for v in dss.Bus.puVmagAngle()[0::2]]
    kv_ln = float(dss.Bus.kVBase())
    nodes = list(dss.Bus.Nodes())
    kv_nom = kv_ln * sqrt(3) if len(nodes) >= 2 else kv_ln
    return {
        "kv_base_ln": kv_ln,
        "kv_nominal": kv_nom,
        "vpu": sum(mags) / len(mags) if mags else 0.0,
        "nodes": nodes,
    }


def _transformer_info(nombre: str) -> dict[str, Any]:
    result = {
        "kva": None,
        "kv_primario": None,
        "kv_secundario": None,
        "conexion_primario": None,
        "conexion_secundario": None,
    }
    try:
        dss.Transformers.Name(nombre)
        dss.Transformers.Wdg(1)
        result["kva"] = float(dss.Transformers.kVA())
        result["kv_primario"] = float(dss.Transformers.kV())
        result["conexion_primario"] = (
            "delta" if bool(dss.Transformers.IsDelta()) else "wye"
        )
        dss.Transformers.Wdg(2)
        result["kv_secundario"] = float(dss.Transformers.kV())
        result["conexion_secundario"] = (
            "delta" if bool(dss.Transformers.IsDelta()) else "wye"
        )
    except Exception:
        pass
    return result


def _generator_info(nombre: str) -> dict[str, float | None]:
    result: dict[str, float | None] = {"kw": None, "kv": None}
    try:
        dss.Generators.Name(nombre)
        result["kw"] = float(dss.Generators.kW())
        result["kv"] = float(dss.Generators.kV())
    except Exception:
        pass
    return result


def _label_lines(x: float, y: float, lines: list[str], anchor: str = "start", cls: str = "label") -> str:
    tspans = []
    for i, line in enumerate(lines):
        dy = 0 if i == 0 else 15
        tspans.append(
            f'<tspan x="{x:.1f}" dy="{dy}">{escape(str(line))}</tspan>'
        )
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" class="{cls}">'
        + "".join(tspans)
        + "</text>"
    )


def _wire(x1: float, y1: float, x2: float, y2: float, color: str = sym.INK, width: float = 2.0, dash: str = "") -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{color}" stroke-width="{width}" fill="none"{dash_attr}/>'
    )


def _voltage_color(energizado: bool, vpu: float) -> str:
    if not energizado:
        return sym.DEENERGIZED
    if 0.95 <= vpu <= 1.05:
        return sym.BLUE
    if 0.90 <= vpu <= 1.10:
        return sym.WARN
    return sym.OPEN


def _collect_model() -> dict[str, Any]:
    buses = list(dss.Circuit.AllBusNames())
    if not buses:
        return {"buses": []}

    info_bus = {bus: _bus_info(bus) for bus in buses}
    total = nx.Graph()
    energized = nx.Graph()
    total.add_nodes_from(buses)
    energized.add_nodes_from(buses)
    connections: dict[tuple[str, str], dict[str, Any]] = {}

    for nombre in dss.Lines.AllNames():
        dss.Lines.Name(nombre)
        b1 = _bus_sin_nodos(dss.Lines.Bus1())
        b2 = _bus_sin_nodos(dss.Lines.Bus2())
        abierta = _estado_abierto()
        total.add_edge(b1, b2)
        if not abierta:
            energized.add_edge(b1, b2)
        dato = {
            "tipo": "Línea",
            "nombre": nombre,
            "full_name": f"Line.{nombre}",
            "abierta": abierta,
        }
        connections[(b1, b2)] = connections[(b2, b1)] = dato

    for nombre in dss.Transformers.AllNames():
        dss.Transformers.Name(nombre)
        bs = dss.CktElement.BusNames()
        if len(bs) < 2:
            continue
        b1, b2 = _bus_sin_nodos(bs[0]), _bus_sin_nodos(bs[1])
        abierta = _estado_abierto()
        total.add_edge(b1, b2)
        if not abierta:
            energized.add_edge(b1, b2)
        dato = {
            "tipo": "Transformador",
            "nombre": nombre,
            "full_name": f"Transformer.{nombre}",
            "abierta": abierta,
            **_transformer_info(nombre),
        }
        connections[(b1, b2)] = connections[(b2, b1)] = dato

    root_candidates = [b for b in buses if "source" in b.lower()]
    root = root_candidates[0] if root_candidates else buses[0]
    energized_buses = (
        set(nx.node_connected_component(energized, root))
        if root in energized
        else {root}
    )

    component = set(nx.node_connected_component(total, root)) if root in total else {root}
    tree = nx.bfs_tree(total.subgraph(component).copy(), root)

    criticas = set(listar_cargas_criticas())
    loads_by_bus: dict[str, list[dict[str, Any]]] = {}
    for nombre in dss.Loads.AllNames():
        dss.Loads.Name(nombre)
        bs = dss.CktElement.BusNames()
        if not bs:
            continue
        bus = _bus_sin_nodos(bs[0])
        loads_by_bus.setdefault(bus, []).append(
            {
                "nombre": nombre,
                "kw": float(dss.Loads.kW()),
                "kvar": float(dss.Loads.kvar()),
                "critica": nombre in criticas,
                "tipo_visual": visual_state.get_load_type(nombre),
            }
        )

    generators_by_bus: dict[str, list[dict[str, Any]]] = {}
    generator_index: dict[str, dict[str, Any]] = {}
    for nombre in dss.Generators.AllNames():
        dss.Generators.Name(nombre)
        bs = dss.CktElement.BusNames()
        if not bs:
            continue
        bus = _bus_sin_nodos(bs[0])
        info = {"nombre": nombre, **_generator_info(nombre), "bus": bus}
        generators_by_bus.setdefault(bus, []).append(info)
        generator_index[nombre.lower()] = info
        generator_index[f"generator.{nombre}".lower()] = info

    return {
        "buses": buses,
        "info_bus": info_bus,
        "total": total,
        "energized": energized,
        "energized_buses": energized_buses,
        "connections": connections,
        "root": root,
        "tree": tree,
        "loads_by_bus": loads_by_bus,
        "generators_by_bus": generators_by_bus,
        "generator_index": generator_index,
        "criticas": criticas,
    }


def _legend(x: float, y: float) -> str:
    rows: list[tuple[str, str]] = [
        (sym.source(x + 28, y + 40), "Fuente / Red"),
        (sym.breaker(x + 28, y + 86), "Interruptor"),
        (sym.transformer(x + 28, y + 135), "Transformador"),
        (sym.busbar(x + 7, x + 49, y + 184), "Barra"),
        (sym.panel(x + 28, y + 230), "Tablero"),
        (sym.motor(x + 28, y + 282), "Motor"),
        (sym.ats(x + 28, y + 335), "ATS"),
        (sym.ups(x + 28, y + 390), "UPS"),
        (sym.generator(x + 28, y + 447), "Grupo electrógeno"),
        (sym.ground(x + 28, y + 487), "Tierra"),
    ]
    out = [
        f'<g data-panel="legend">',
        f'<rect x="{x:.1f}" y="{y:.1f}" width="220" height="548" rx="8" fill="#fff" stroke="{sym.BLUE}" stroke-width="1.4"/>',
        f'<text x="{x+110:.1f}" y="{y+22:.1f}" text-anchor="middle" class="legend-title">Simbología</text>',
    ]
    text_y = [44, 90, 140, 188, 235, 287, 340, 395, 452, 501]
    for i, ((symbol_svg, label), ty) in enumerate(zip(rows, text_y)):
        out.append(symbol_svg)
        out.append(f'<text x="{x+66:.1f}" y="{y+ty:.1f}" class="legend-text">{escape(label)}</text>')
        if i < len(rows) - 1:
            sep_y = y + (65 + i * 51)
            out.append(_wire(x + 8, sep_y, x + 212, sep_y, "#d1d5db", 0.8, "3,3"))
    return "".join(out) + "</g>"


def _rules_panel(x: float, y: float) -> str:
    rules = [
        "Flujo de energía vertical",
        "Una línea por alimentador",
        "Barras claramente visibles",
        "Símbolos eléctricos consistentes",
        "Etiquetado técnico básico",
    ]
    out = [
        f'<g data-panel="rules">',
        f'<rect x="{x:.1f}" y="{y:.1f}" width="220" height="184" rx="8" fill="#fff" stroke="{sym.BLUE}" stroke-width="1.4"/>',
        f'<text x="{x+110:.1f}" y="{y+22:.1f}" text-anchor="middle" class="legend-title">Reglas visuales</text>',
    ]
    for i, rule in enumerate(rules, 1):
        yy = y + 48 + (i - 1) * 27
        out.append(f'<circle cx="{x+20:.1f}" cy="{yy-4:.1f}" r="10" fill="{sym.BLUE}"/>')
        out.append(f'<text x="{x+20:.1f}" y="{yy:.1f}" text-anchor="middle" class="rule-num">{i}</text>')
        out.append(f'<text x="{x+39:.1f}" y="{yy:.1f}" class="rule-text">{escape(rule)}</text>')
    return "".join(out) + "</g>"


def _svg_document(width: float, height: float, body: str, circuit_name: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" width="{width:.0f}" height="{height:.0f}" role="img" aria-label="Diagrama unifilar {escape(circuit_name)}">
<style>
text {{ font-family: Arial, Helvetica, sans-serif; fill:{sym.INK}; }}
.title {{ font-size:22px; font-weight:700; fill:{sym.BLUE}; }}
.subtitle {{ font-size:11px; font-weight:600; letter-spacing:1.2px; fill:{sym.DIM}; }}
.bus-name {{ font-size:12px; font-weight:700; }}
.bus-state {{ font-size:10px; font-weight:600; }}
.label {{ font-size:11px; font-weight:600; }}
.label-dim {{ font-size:10px; fill:{sym.DIM}; }}
.feeder-tag {{ font-size:11px; font-weight:700; }}
.status-open {{ font-size:10px; font-weight:700; fill:{sym.OPEN}; }}
.critical {{ font-size:9px; font-weight:700; fill:{sym.OPEN}; }}
.sym-main {{ font-size:14px; font-weight:700; }}
.sym-small {{ font-size:9px; font-weight:600; }}
.sym-note {{ font-size:10px; font-weight:700; fill:{sym.DIM}; stroke:none; }}
.legend-title {{ font-size:13px; font-weight:700; fill:{sym.BLUE}; }}
.legend-text {{ font-size:10px; }}
.rule-num {{ font-size:9px; font-weight:700; fill:#fff; }}
.rule-text {{ font-size:9.5px; }}
</style>
<rect width="100%" height="100%" fill="#ffffff"/>
{body}
</svg>'''


def generar_diagrama_unifilar(
    ruta_salida: str = "diagrama_red.html",
    mostrar_leyenda: bool = True,
    titulo: str | None = None,
) -> dict[str, Any]:
    """Genera un unifilar técnico en SVG y, opcionalmente, un wrapper HTML.

    Reglas principales:
    - flujo vertical de fuente a cargas;
    - barras horizontales;
    - alimentadores ortogonales con interruptor en cabecera;
    - simbología diferenciada para transformadores, tableros, motores,
      generadores, ATS y UPS;
    - dispositivos ATS/UPS pueden anotarse visualmente sin alterar el cálculo
      OpenDSS mediante ``configurar_alimentador_unifilar``.
    """
    model = _collect_model()
    buses = model["buses"]
    if not buses:
        return {"error": "El circuito no tiene buses definidos."}

    info_bus = model["info_bus"]
    connections = model["connections"]
    tree: nx.DiGraph = model["tree"]
    root = model["root"]
    energized_buses: set[str] = model["energized_buses"]
    loads_by_bus = model["loads_by_bus"]
    generators_by_bus = model["generators_by_bus"]
    generator_index = model["generator_index"]

    # Si la fuente tiene un único transformador y ninguna carga local, se
    # representa como en un unifilar típico: RED -> CB -> TR -> barra BT,
    # sin dibujar una barra MT artificial entre medio.
    root_children = list(tree.successors(root)) if root in tree else []
    hidden_root_edge: tuple[str, str] | None = None
    diagram_root = root
    if len(root_children) == 1 and not loads_by_bus.get(root):
        child = root_children[0]
        dato = connections.get((root, child), {})
        if dato.get("tipo") == "Transformador":
            hidden_root_edge = (root, child)
            diagram_root = child

    # Árbol de layout re-enraizado en la barra que realmente se dibujará.
    # Cuando ocultamos la barra de fuente, retiramos sourcebus del grafo visual
    # para que no reaparezca aguas abajo del transformador.
    layout_graph = model["total"].copy()
    if hidden_root_edge and root in layout_graph:
        layout_graph.remove_node(root)
    layout_tree = nx.bfs_tree(layout_graph, diagram_root)

    leaf_cursor = [PAGE_MARGIN + 60]
    pos_bus: dict[str, tuple[float, float]] = {}
    span_bus: dict[str, tuple[float, float]] = {}
    pos_load: dict[tuple[str, int], float] = {}
    pos_gen: dict[tuple[str, int], float] = {}

    base_y = HEADER_H + SOURCE_H + (70 if hidden_root_edge else 30)

    def layout(bus: str, depth: int) -> float:
        child_xs = [layout(c, depth + 1) for c in sorted(layout_tree.successors(bus))]
        load_xs: list[float] = []
        for i, _ in enumerate(sorted(loads_by_bus.get(bus, []), key=lambda x: x["nombre"])):
            x = leaf_cursor[0]
            leaf_cursor[0] += BRANCH_W
            pos_load[(bus, i)] = x
            load_xs.append(x)
        gen_xs: list[float] = []
        for i, _ in enumerate(sorted(generators_by_bus.get(bus, []), key=lambda x: x["nombre"])):
            x = leaf_cursor[0]
            leaf_cursor[0] += BRANCH_W
            pos_gen[(bus, i)] = x
            gen_xs.append(x)
        xs = child_xs + load_xs + gen_xs
        if not xs:
            x = leaf_cursor[0]
            leaf_cursor[0] += BRANCH_W
            xs = [x]
        center = sum(xs) / len(xs)
        pos_bus[bus] = (center, base_y + depth * TIER_H)
        span_bus[bus] = (min(xs), max(xs))
        return center

    layout(diagram_root, 0)

    # Topología fuera del componente principal: se agrega en una columna de
    # aviso, sin fingir continuidad eléctrica.
    outside = [b for b in buses if b not in pos_bus and b != root]
    for i, bus in enumerate(outside):
        x = leaf_cursor[0]
        leaf_cursor[0] += BRANCH_W
        pos_bus[bus] = (x, base_y + i * 90)
        span_bus[bus] = (x, x)

    diagram_width = max(920, leaf_cursor[0] + PAGE_MARGIN)
    legend_extra = LEGEND_W if mostrar_leyenda else 0
    canvas_width = diagram_width + legend_extra
    max_depth = max((nx.shortest_path_length(layout_tree, diagram_root, b) for b in layout_tree.nodes), default=0)
    canvas_height = max(760, base_y + max_depth * TIER_H + 260)

    body: list[str] = []
    main_title = titulo or "Diagrama unifilar"
    body.append(f'<text x="{PAGE_MARGIN}" y="38" class="title">{escape(main_title)}</text>')
    body.append(_wire(PAGE_MARGIN, 52, min(diagram_width - 30, PAGE_MARGIN + 520), 52, sym.BLUE, 3.0))
    body.append(f'<text x="{PAGE_MARGIN}" y="69" class="subtitle">MCP ELÉCTRICO · OPENDSS · REPRESENTACIÓN TÉCNICA</text>')

    # Fuente.
    sx = pos_bus[diagram_root][0]
    sy = HEADER_H + 36
    source_nom = info_bus[root]["kv_nominal"]
    body.append(sym.source(sx, sy))
    body.append(_label_lines(sx + 38, sy - 4, [f"RED / FUENTE {source_nom:.3g} kV"], cls="label"))

    used_alt_generators: set[str] = set()
    feeder_counter = [1]
    circuit_counter = [1]

    def next_tag(annotation: dict) -> str:
        if annotation.get("etiqueta"):
            return str(annotation["etiqueta"])
        tag = f"F-{feeder_counter[0]:02d}"
        feeder_counter[0] += 1
        return tag

    # Tramo fuente -> primera barra, con transformador si se ocultó root.
    if hidden_root_edge:
        dato = connections[hidden_root_edge]
        open_state = bool(dato["abierta"])
        line_color = sym.OPEN if open_state else sym.INK
        breaker_y = sy + 58
        trafo_y = sy + 125
        bus_y = pos_bus[diagram_root][1]
        body.append(_wire(sx, sy + 22, sx, breaker_y - 12, line_color))
        body.append(sym.breaker(sx, breaker_y, open_state))
        if open_state:
            body.append(f'<text x="{sx+18:.1f}" y="{breaker_y+4:.1f}" class="status-open">ABIERTO</text>')
        body.append(_wire(sx, breaker_y + 12, sx, trafo_y - 31, line_color))
        body.append(
            sym.transformer(
                sx,
                trafo_y,
                line_color,
                dato.get("conexion_primario"),
                dato.get("conexion_secundario"),
            )
        )
        kv1, kv2, kva = dato.get("kv_primario"), dato.get("kv_secundario"), dato.get("kva")
        details = [str(dato["nombre"])]
        if kva:
            details.append(f"{kva:.0f} kVA")
        if kv1 and kv2:
            details.append(f"{kv1:g}/{kv2:g} kV")
        body.append(_label_lines(sx + 45, trafo_y - 10, details, cls="label"))
        body.append(_wire(sx, trafo_y + 31, sx, bus_y, line_color))
    else:
        root_y = pos_bus[root][1]
        breaker_y = sy + 60
        body.append(_wire(sx, sy + 22, sx, breaker_y - 12))
        body.append(sym.breaker(sx, breaker_y, False))
        body.append(_wire(sx, breaker_y + 12, sx, root_y))

    # Barras y derivaciones.
    for bus in sorted(pos_bus, key=lambda b: (pos_bus[b][1], pos_bus[b][0])):
        if bus == root and hidden_root_edge:
            continue
        bx, by = pos_bus[bus]
        x_min, x_max = span_bus[bus]
        bar_left = min(x_min - 58, bx - 90)
        bar_right = max(x_max + 58, bx + 90)
        energized = bus in energized_buses
        bar_color = sym.INK if energized else sym.DEENERGIZED
        body.append(sym.busbar(bar_left, bar_right, by, bar_color))
        vcolor = _voltage_color(energized, info_bus[bus]["vpu"])
        state = f'{info_bus[bus]["kv_nominal"]:.3f} kV · {info_bus[bus]["vpu"]:.3f} pu' if energized else "DESENERGIZADA"
        body.append(f'<text x="{bar_right+12:.1f}" y="{by-7:.1f}" class="bus-name">{escape(bus.upper())}</text>')
        body.append(f'<text x="{bar_right+12:.1f}" y="{by+10:.1f}" class="bus-state" fill="{vcolor}">{escape(state)}</text>')

        # Hacia buses hijos.
        if bus in layout_tree:
            for child in sorted(layout_tree.successors(bus), key=lambda c: pos_bus[c][0]):
                cx, cy = pos_bus[child]
                dato = connections[(bus, child)]
                annotation = visual_state.get_feeder(dato["full_name"])
                tag = next_tag(annotation)
                open_state = bool(dato["abierta"])
                path_color = sym.OPEN if open_state else (sym.INK if child in energized_buses else sym.DEENERGIZED)
                breaker_y = by + 48
                body.append(_wire(cx, by, cx, breaker_y - 12, path_color))
                body.append(sym.breaker(cx, breaker_y, open_state, path_color))
                body.append(f'<text x="{cx-18:.1f}" y="{breaker_y-18:.1f}" class="feeder-tag" text-anchor="end">{escape(tag)}</text>')
                if open_state:
                    body.append(f'<text x="{cx+18:.1f}" y="{breaker_y+4:.1f}" class="status-open">ABIERTO</text>')

                current_y = breaker_y + 12
                if dato["tipo"] == "Transformador":
                    tr_y = by + 120
                    body.append(_wire(cx, current_y, cx, tr_y - 31, path_color))
                    body.append(
                        sym.transformer(
                            cx,
                            tr_y,
                            path_color,
                            dato.get("conexion_primario"),
                            dato.get("conexion_secundario"),
                        )
                    )
                    details = [str(dato["nombre"])]
                    if dato.get("kva"):
                        details.append(f'{dato["kva"]:.0f} kVA')
                    if dato.get("kv_primario") and dato.get("kv_secundario"):
                        details.append(f'{dato["kv_primario"]:g}/{dato["kv_secundario"]:g} kV')
                    body.append(_label_lines(cx + 45, tr_y - 10, details, cls="label"))
                    current_y = tr_y + 31
                else:
                    devices = list(annotation.get("dispositivos") or [])
                    if devices:
                        available = max(90.0, cy - current_y - 45)
                        step = min(82.0, available / (len(devices) + 1))
                        for dev in devices:
                            dy = current_y + step
                            body.append(_wire(cx, current_y, cx, dy - 24, path_color))
                            if dev == "ats":
                                body.append(sym.ats(cx, dy, path_color))
                                alt = annotation.get("fuente_alterna")
                                if alt:
                                    gen = generator_index.get(str(alt).lower())
                                    if gen:
                                        gx = cx + 120
                                        body.append(_wire(gx - 23, dy, cx + 26, dy, path_color))
                                        body.append(sym.generator(gx, dy, path_color))
                                        body.append(sym.ground(gx, dy + 23, path_color))
                                        glines = [str(gen["nombre"])]
                                        if gen.get("kw") is not None:
                                            glines.append(f'{gen["kw"]:.0f} kW')
                                        body.append(_label_lines(gx + 36, dy - 4, glines, cls="label"))
                                        used_alt_generators.add(str(gen["nombre"]).lower())
                            elif dev == "ups":
                                body.append(sym.ups(cx, dy, path_color))
                            current_y = dy + 24
                    body.append(f'<text x="{cx+15:.1f}" y="{(current_y+cy)/2:.1f}" class="label-dim">{escape(str(dato["nombre"]))}</text>')
                body.append(_wire(cx, current_y, cx, cy, path_color))

        # Cargas terminales.
        loads = sorted(loads_by_bus.get(bus, []), key=lambda x: x["nombre"])
        for i, load in enumerate(loads):
            x = pos_load[(bus, i)]
            breaker_y = by + 48
            symbol_y = by + 128
            color = sym.INK if energized else sym.DEENERGIZED
            tag = f"C-{circuit_counter[0]:02d}"
            circuit_counter[0] += 1
            body.append(_wire(x, by, x, breaker_y - 12, color))
            body.append(sym.breaker(x, breaker_y, False, color))
            body.append(f'<text x="{x-18:.1f}" y="{breaker_y-18:.1f}" class="feeder-tag" text-anchor="end">{tag}</text>')
            body.append(_wire(x, breaker_y + 12, x, symbol_y - 25, color))
            tipo = load["tipo_visual"]
            if tipo == "motor":
                body.append(sym.motor(x, symbol_y, color))
            elif tipo == "carga":
                body.append(sym.load(x, symbol_y, color))
            else:
                body.append(sym.panel(x, symbol_y, color))
            lines = [str(load["nombre"]).upper(), f'{load["kw"]:.0f} kW']
            body.append(_label_lines(x, symbol_y + 52, lines, anchor="middle", cls="label"))
            if load["critica"]:
                body.append(f'<text x="{x:.1f}" y="{symbol_y+87:.1f}" text-anchor="middle" class="critical">CARGA CRÍTICA</text>')

        # Generadores que no se usaron como fuente alterna de un ATS.
        generators = sorted(generators_by_bus.get(bus, []), key=lambda x: x["nombre"])
        for i, gen in enumerate(generators):
            if str(gen["nombre"]).lower() in used_alt_generators:
                continue
            x = pos_gen[(bus, i)]
            breaker_y = by + 48
            symbol_y = by + 128
            color = sym.INK if energized else sym.DEENERGIZED
            body.append(_wire(x, by, x, breaker_y - 12, color))
            body.append(sym.breaker(x, breaker_y, False, color))
            body.append(_wire(x, breaker_y + 12, x, symbol_y - 23, color))
            body.append(sym.generator(x, symbol_y, color))
            body.append(sym.ground(x, symbol_y + 23, color))
            lines = [str(gen["nombre"]).upper()]
            if gen.get("kw") is not None:
                lines.append(f'{gen["kw"]:.0f} kW')
            body.append(_label_lines(x, symbol_y + 62, lines, anchor="middle", cls="label"))

    if outside:
        ox = diagram_width - 200
        oy = 100
        body.append(f'<text x="{ox:.1f}" y="{oy:.1f}" class="status-open">COMPONENTE SIN CONEXIÓN A LA FUENTE</text>')
        for i, bus in enumerate(outside):
            body.append(f'<text x="{ox:.1f}" y="{oy+20+i*16:.1f}" class="label-dim">• {escape(bus)}</text>')

    # Leyenda separada del dibujo para no contaminar el unifilar.
    if mostrar_leyenda:
        lx = diagram_width + 12
        body.append(_legend(lx, 18))
        body.append(_rules_panel(lx, 578))

    svg_text = _svg_document(canvas_width, canvas_height, "".join(body), dss.Circuit.Name())

    salida = Path(ruta_salida).expanduser()
    salida.parent.mkdir(parents=True, exist_ok=True)
    if salida.suffix.lower() == ".svg":
        svg_path = salida
        html_path = None
    else:
        html_path = salida if salida.suffix.lower() == ".html" else salida.with_suffix(".html")
        svg_path = html_path.with_suffix(".svg")

    svg_path.write_text(svg_text, encoding="utf-8")

    if html_path is not None:
        html = f'''<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>Unifilar — {escape(dss.Circuit.Name())}</title>
<style>html,body{{margin:0;background:#eef2f7}}.sheet{{max-width:{canvas_width:.0f}px;margin:24px auto;background:#fff;box-shadow:0 4px 24px #0002}}svg{{display:block;width:100%;height:auto}}</style>
</head><body><div class="sheet">{svg_text}</div></body></html>'''
        html_path.write_text(html, encoding="utf-8")

    desconectados = sorted(set(buses) - set(energized_buses))
    is_radial = nx.is_tree(model["total"]) if model["total"].number_of_nodes() else True
    return {
        "archivo_generado": str(html_path or svg_path),
        "archivo_svg": str(svg_path),
        "archivo_html": str(html_path) if html_path else None,
        "buses_dibujados": len(buses),
        "buses_desconectados": desconectados,
        "cargas_dibujadas": len(dss.Loads.AllNames()),
        "generadores_dibujados": len(dss.Generators.AllNames()),
        "transformadores_dibujados": len(dss.Transformers.AllNames()),
        "topologia_radial_pura": is_radial,
        "estilo": "unifilar_tecnico_svg_v1",
        "nota": "ATS/UPS configurados como anotaciones visuales no modifican el cálculo OpenDSS.",
    }
