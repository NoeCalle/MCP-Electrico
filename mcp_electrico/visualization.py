"""Render de diagramas unifilares técnicos para el modelo OpenDSS activo.

NetworkX se usa para interpretar y ordenar la topología. El render final aplica
reglas de representación eléctrica: barras solo cuando corresponden a una
barra física, protecciones en cabecera, alimentadores ortogonales, simbología
consistente y etiquetas de ingeniería.
"""

from __future__ import annotations

from html import escape
from math import sqrt
from pathlib import Path
import re
from typing import Any

import networkx as nx
from opendssdirect import dss

from .core import listar_cargas_criticas
from . import visual_state
from . import visual_symbols as sym


PAGE_MARGIN = 38
HEADER_H = 72
NET_TOP = 105
TIER_H = 300
BRANCH_W = 215
LEGEND_W = 220


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


def _engineering_name(name: str) -> str:
    text = name.strip()
    text = re.sub(r"_(\d+)$", r"-\1", text)
    text = text.replace("_", " ")
    return text.upper()


def _format_voltage(kv: float) -> str:
    if kv <= 0:
        return "—"
    if kv < 1:
        return f"{kv * 1000:.0f} V"
    if abs(kv - round(kv)) < 1e-6:
        return f"{kv:.0f} kV"
    return f"{kv:.3g} kV"


def _connection_code(primary: str | None, secondary: str | None) -> str:
    def one(value: str | None) -> str:
        if value == "delta":
            return "Δ"
        if value == "wye":
            return "Y"
        return "?"

    return f"{one(primary)}/{one(secondary)}"


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
                "etiqueta": visual_state.get_load_label(nombre),
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

    snapshot = visual_state.snapshot()
    alternate_generators: set[str] = set()
    for feeder in snapshot["alimentadores"].values():
        alternate = feeder.get("fuente_alterna")
        if alternate:
            alternate_generators.add(alternate.split(".")[-1].lower())

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
        "alternate_generators": alternate_generators,
    }


def _is_physical_bus(
    bus: str,
    model: dict[str, Any],
    tree: nx.DiGraph,
    diagram_root: str,
) -> bool:
    cfg = visual_state.get_bus(bus)
    if cfg["rol"] == "barra":
        return True
    if cfg["rol"] == "conexion":
        return False
    if bus == diagram_root:
        return True

    children = list(tree.successors(bus)) if bus in tree else []
    loads = model["loads_by_bus"].get(bus, [])
    generators = [
        g
        for g in model["generators_by_bus"].get(bus, [])
        if g["nombre"].lower() not in model["alternate_generators"]
    ]

    if len(children) >= 2:
        return True
    if len(loads) + len(generators) >= 2:
        return True
    if children and (loads or generators):
        return True

    parents = list(tree.predecessors(bus)) if bus in tree else []
    if parents:
        incoming = model["connections"].get((parents[0], bus), {})
        if incoming.get("tipo") == "Transformador":
            return True
    return False


def _bus_label(bus: str) -> str:
    cfg = visual_state.get_bus(bus)
    return cfg["etiqueta"] or _engineering_name(bus)


def _load_label(load: dict[str, Any]) -> str:
    return load.get("etiqueta") or _engineering_name(str(load["nombre"]))


def _load_symbol_name(tipo_visual: str) -> str:
    return {
        "tablero": "panel",
        "motor": "motor",
        "carga": "load",
    }.get(tipo_visual, "panel")


def _child_sort_key(parent: str, child: str, connections: dict) -> tuple[str, str]:
    dato = connections.get((parent, child), {})
    annotation = visual_state.get_feeder(dato.get("full_name", ""))
    etiqueta = str(annotation.get("etiqueta") or "").strip()
    return (etiqueta or "~", _engineering_name(child))


def _voltage_color(energized: bool, vpu: float) -> str:
    if not energized:
        return sym.DEENERGIZED
    if 0.95 <= vpu <= 1.05:
        return sym.BLUE
    if 0.90 <= vpu <= 1.10:
        return sym.WARN
    return sym.OPEN


class _Mapper:
    def __init__(self, orientation: str, canonical_width: float, canonical_height: float):
        self.orientation = orientation
        self.canonical_width = canonical_width
        self.canonical_height = canonical_height
        if orientation == "vertical":
            self.width = canonical_width
            self.height = canonical_height
        else:
            self.width = PAGE_MARGIN + (canonical_height - 82) + 90
            self.height = HEADER_H + 70 + (canonical_width - PAGE_MARGIN) + 55

    def p(self, x: float, y: float) -> tuple[float, float]:
        if self.orientation == "vertical":
            return x, y
        return PAGE_MARGIN + (y - 82), HEADER_H + 70 + (x - PAGE_MARGIN)

    def wire(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: str = sym.INK,
        width: float = 1.7,
        dash: str = "",
    ) -> str:
        ax, ay = self.p(x1, y1)
        bx, by = self.p(x2, y2)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        return (
            f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" '
            f'stroke="{color}" stroke-width="{width}" fill="none" '
            f'stroke-linecap="round"{dash_attr}/>'
        )

    def label(
        self,
        x: float,
        y: float,
        lines: list[str],
        anchor: str = "start",
        cls: str = "label",
    ) -> str:
        px, py = self.p(x, y)
        tspans = []
        for i, line in enumerate(lines):
            dy = 0 if i == 0 else 14
            tspans.append(
                f'<tspan x="{px:.1f}" dy="{dy}">{escape(str(line))}</tspan>'
            )
        return (
            f'<text x="{px:.1f}" y="{py:.1f}" text-anchor="{anchor}" '
            f'class="{cls}">{"".join(tspans)}</text>'
        )

    def source(self, x: float, y: float, color: str = sym.INK) -> str:
        px, py = self.p(x, y)
        return sym.source(px, py, color)

    def protection(
        self,
        x: float,
        y: float,
        kind: str,
        opened: bool,
        color: str,
    ) -> str:
        px, py = self.p(x, y)
        return sym.protection(px, py, kind, opened, color)

    def transformer(self, x: float, y: float, color: str) -> str:
        px, py = self.p(x, y)
        return sym.transformer(px, py, color, self.orientation)

    def busbar(
        self,
        x1: float,
        x2: float,
        y: float,
        color: str,
        width: float,
    ) -> str:
        if self.orientation == "vertical":
            return sym.busbar(x1, x2, y, color, width)
        px, py1 = self.p(x1, y)
        _, py2 = self.p(x2, y)
        return sym.busbar_vertical(px, py1, py2, color, width)

    def symbol(self, name: str, x: float, y: float, color: str) -> str:
        px, py = self.p(x, y)
        return getattr(sym, name)(px, py, color)

    def junction(self, x: float, y: float, color: str) -> str:
        px, py = self.p(x, y)
        return sym.junction(px, py, color)


def _feeder_detail(annotation: dict, fallback_name: str, mode: str) -> list[str]:
    lines: list[str] = []
    protection = annotation.get("proteccion") or "breaker"
    current = annotation.get("corriente_nominal_a")
    breaking = annotation.get("capacidad_ruptura_ka")
    if protection != "breaker" or current or breaking:
        text = protection.upper() if protection != "breaker" else "CB"
        if current:
            text += f" {current:g} A"
        if breaking:
            text += f" · {breaking:g} kA"
        lines.append(text)
    conductor = annotation.get("conductor") or ""
    if conductor:
        lines.append(conductor)
    if mode == "diagnostico":
        lines.append(fallback_name)
    return lines


def _legend(x: float, y: float) -> str:
    rows = [
        (sym.source(x + 25, y + 34), "Fuente / Red"),
        (sym.breaker(x + 25, y + 76), "Interruptor"),
        (sym.fuse(x + 25, y + 116), "Fusible"),
        (sym.isolator(x + 25, y + 156), "Seccionador"),
        (sym.transformer(x + 25, y + 202), "Transformador"),
        (sym.busbar(x + 7, x + 43, y + 244, width=4.5), "Barra"),
        (sym.panel(x + 25, y + 288), "Tablero"),
        (sym.motor(x + 25, y + 334), "Motor"),
        (sym.ats(x + 25, y + 382), "ATS"),
        (sym.ups(x + 25, y + 430), "UPS"),
        (sym.generator(x + 25, y + 478), "Grupo electrógeno"),
    ]
    out = [
        '<g data-panel="legend">',
        f'<rect x="{x:.1f}" y="{y:.1f}" width="198" height="510" rx="5" '
        f'fill="#fff" stroke="#d1d5db" stroke-width="1"/>',
        f'<text x="{x+99:.1f}" y="{y+20:.1f}" text-anchor="middle" '
        f'class="legend-title">SIMBOLOGÍA</text>',
    ]
    text_y = [38, 80, 120, 160, 206, 248, 292, 338, 386, 434, 482]
    for (symbol_svg, label), ty in zip(rows, text_y):
        out.append(symbol_svg)
        out.append(
            f'<text x="{x+55:.1f}" y="{y+ty:.1f}" class="legend-text">'
            f'{escape(label)}</text>'
        )
    return "".join(out) + "</g>"


def _rules_panel(x: float, y: float) -> str:
    rules = [
        "Flujo jerárquico",
        "Barras solo donde son físicas",
        "Protección en cabecera",
        "Derivaciones ortogonales",
        "Datos técnicos selectivos",
    ]
    out = [
        '<g data-panel="rules">',
        f'<rect x="{x:.1f}" y="{y:.1f}" width="198" height="150" rx="5" '
        f'fill="#fff" stroke="#d1d5db" stroke-width="1"/>',
        f'<text x="{x+99:.1f}" y="{y+20:.1f}" text-anchor="middle" '
        f'class="legend-title">REGLAS</text>',
    ]
    for i, rule in enumerate(rules):
        yy = y + 45 + i * 20
        out.append(
            f'<text x="{x+14:.1f}" y="{yy:.1f}" class="rule-text">'
            f'• {escape(rule)}</text>'
        )
    return "".join(out) + "</g>"


def _svg_document(width: float, height: float, body: str, circuit_name: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" width="{width:.0f}" height="{height:.0f}" role="img" aria-label="Diagrama unifilar {escape(circuit_name)}">
<style>
text {{ font-family: Arial, Helvetica, sans-serif; fill:{sym.INK}; }}
.title {{ font-size:20px; font-weight:700; }}
.subtitle {{ font-size:9.5px; font-weight:600; letter-spacing:1px; fill:{sym.DIM}; }}
.bus-name {{ font-size:11px; font-weight:700; }}
.bus-state {{ font-size:9.5px; font-weight:600; }}
.label {{ font-size:10.5px; font-weight:600; }}
.label-strong {{ font-size:11px; font-weight:700; }}
.label-dim {{ font-size:9px; fill:{sym.DIM}; }}
.feeder-tag {{ font-size:10.5px; font-weight:700; }}
.status-open {{ font-size:9px; font-weight:700; fill:{sym.OPEN}; }}
.critical {{ font-size:8.5px; font-weight:700; fill:{sym.OPEN}; }}
.sym-main {{ font-size:13px; font-weight:700; }}
.sym-small {{ font-size:8px; font-weight:700; }}
.sym-protection {{ font-size:7.5px; font-weight:700; fill:{sym.DIM}; }}
.legend-title {{ font-size:11px; font-weight:700; }}
.legend-text {{ font-size:9px; }}
.rule-text {{ font-size:8.5px; fill:{sym.DIM}; }}
</style>
<rect width="100%" height="100%" fill="#ffffff"/>
{body}
</svg>"""


def generar_diagrama_unifilar(
    ruta_salida: str = "diagrama_red.html",
    mostrar_leyenda: bool = False,
    titulo: str | None = None,
    modo: str = "ingenieria",
    orientacion: str = "vertical",
    mostrar_marca: bool = False,
    mostrar_reglas: bool = False,
) -> dict[str, Any]:
    """Genera un unifilar técnico SVG/HTML.

    ``modo``:
    - ``ingenieria``: prioriza rótulos técnicos y omite nombres internos;
    - ``diagnostico``: añade nombres OpenDSS y valores pu.

    ``orientacion`` admite ``vertical`` y ``horizontal``. La disposición
    vertical es la referencia principal; la horizontal transpone la jerarquía
    para redes profundas.
    """
    mode = modo.strip().lower()
    if mode not in {"ingenieria", "diagnostico"}:
        raise ValueError("modo debe ser 'ingenieria' o 'diagnostico'.")
    orientation = orientacion.strip().lower()
    if orientation not in {"vertical", "horizontal"}:
        raise ValueError("orientacion debe ser 'vertical' u 'horizontal'.")

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

    root_children = list(tree.successors(root)) if root in tree else []
    hidden_root_edge: tuple[str, str] | None = None
    diagram_root = root
    if len(root_children) == 1 and not loads_by_bus.get(root):
        child = root_children[0]
        dato = connections.get((root, child), {})
        if dato.get("tipo") == "Transformador":
            hidden_root_edge = (root, child)
            diagram_root = child

    layout_graph = model["total"].copy()
    if hidden_root_edge and root in layout_graph:
        layout_graph.remove_node(root)
    layout_tree = nx.bfs_tree(layout_graph, diagram_root)

    physical = {
        bus: _is_physical_bus(bus, model, layout_tree, diagram_root)
        for bus in layout_tree.nodes
    }

    leaf_cursor = [PAGE_MARGIN + 75]
    pos_bus: dict[str, tuple[float, float]] = {}
    span_bus: dict[str, tuple[float, float]] = {}
    pos_load: dict[tuple[str, int], float] = {}
    pos_gen: dict[tuple[str, int], float] = {}

    base_y = 300 if hidden_root_edge else 225

    def layout(bus: str, depth: int) -> float:
        children = sorted(
            layout_tree.successors(bus),
            key=lambda c: _child_sort_key(bus, c, connections),
        )
        child_xs = [layout(child, depth + 1) for child in children]
        loads = sorted(loads_by_bus.get(bus, []), key=lambda x: x["nombre"])
        gens = sorted(
            [
                g for g in generators_by_bus.get(bus, [])
                if g["nombre"].lower() not in model["alternate_generators"]
            ],
            key=lambda x: x["nombre"],
        )

        own_xs: list[float] = []
        if physical.get(bus, False):
            for i, _ in enumerate(loads):
                x = leaf_cursor[0]
                leaf_cursor[0] += BRANCH_W
                pos_load[(bus, i)] = x
                own_xs.append(x)
            for i, _ in enumerate(gens):
                x = leaf_cursor[0]
                leaf_cursor[0] += BRANCH_W
                pos_gen[(bus, i)] = x
                own_xs.append(x)
        elif (loads or gens) and not children:
            x = leaf_cursor[0]
            leaf_cursor[0] += BRANCH_W
            for i, _ in enumerate(loads):
                pos_load[(bus, i)] = x
            for i, _ in enumerate(gens):
                pos_gen[(bus, i)] = x
            own_xs.append(x)

        xs = child_xs + own_xs
        if not xs:
            x = leaf_cursor[0]
            leaf_cursor[0] += BRANCH_W
            xs = [x]
        center = (min(xs) + max(xs)) / 2
        pos_bus[bus] = (center, base_y + depth * TIER_H)
        span_bus[bus] = (min(xs), max(xs))
        return center

    layout(diagram_root, 0)

    outside = [b for b in buses if b not in pos_bus and b != root]
    canonical_width = max(860, leaf_cursor[0] + PAGE_MARGIN)
    max_depth = max(
        (nx.shortest_path_length(layout_tree, diagram_root, b) for b in layout_tree.nodes),
        default=0,
    )
    canonical_height = max(690, base_y + max_depth * TIER_H + 190)
    mapper = _Mapper(orientation, canonical_width, canonical_height)

    legend_extra = LEGEND_W if mostrar_leyenda else 0
    canvas_width = mapper.width + legend_extra
    canvas_height = max(mapper.height, 690 if mostrar_leyenda else mapper.height)

    body: list[str] = []
    main_title = titulo or "DIAGRAMA UNIFILAR"
    body.append(
        f'<text x="{PAGE_MARGIN}" y="34" class="title">{escape(main_title)}</text>'
    )
    body.append(
        f'<line x1="{PAGE_MARGIN}" y1="48" x2="{min(mapper.width-28, PAGE_MARGIN+470):.1f}" '
        f'y2="48" stroke="{sym.INK}" stroke-width="1.2"/>'
    )
    if mostrar_marca:
        body.append(
            f'<text x="{PAGE_MARGIN}" y="64" class="subtitle">'
            f'MCP ELÉCTRICO · OPENDSS</text>'
        )

    sx = pos_bus[diagram_root][0]
    sy = NET_TOP
    source_nom = info_bus[root]["kv_nominal"]
    body.append(mapper.source(sx, sy))
    source_label_y = sy - 3 if orientation == "vertical" else sy + 34
    body.append(
        mapper.label(
            sx + 35 if orientation == "vertical" else sx,
            source_label_y,
            [f"RED {_format_voltage(source_nom)}"],
            cls="label-strong",
        )
    )

    used_alt_generators: set[str] = set()
    feeder_counter = [1]
    circuit_counter = [1]

    def next_tag(annotation: dict) -> str:
        if annotation.get("etiqueta"):
            return str(annotation["etiqueta"])
        tag = f"F-{feeder_counter[0]:02d}"
        feeder_counter[0] += 1
        return tag

    def render_transformer_label(x: float, y: float, dato: dict) -> None:
        lines = [_engineering_name(str(dato["nombre"]))]
        if dato.get("kva"):
            lines.append(f'{dato["kva"]:.0f} kVA')
        if dato.get("kv_primario") and dato.get("kv_secundario"):
            lines.append(
                f'{dato["kv_primario"]:g}/{dato["kv_secundario"]:g} kV'
            )
        lines.append(
            _connection_code(
                dato.get("conexion_primario"), dato.get("conexion_secundario")
            )
        )
        body.append(mapper.label(x + 38, y - 8, lines, cls="label"))

    if hidden_root_edge:
        dato = connections[hidden_root_edge]
        opened = bool(dato["abierta"])
        line_color = sym.OPEN if opened else sym.INK
        breaker_y = sy + 52
        trafo_y = sy + 112
        bus_y = pos_bus[diagram_root][1]
        body.append(mapper.wire(sx, sy + 20, sx, breaker_y - 13, line_color, 1.8))
        body.append(mapper.protection(sx, breaker_y, "breaker", opened, line_color))
        body.append(
            mapper.label(sx + 16, breaker_y - 4, ["CB-MT"], cls="label-dim")
        )
        if opened:
            body.append(
                mapper.label(sx + 18, breaker_y + 13, ["ABIERTO"], cls="status-open")
            )
        body.append(mapper.wire(sx, breaker_y + 13, sx, trafo_y - 16, line_color))
        body.append(mapper.transformer(sx, trafo_y, line_color))
        render_transformer_label(sx, trafo_y, dato)
        body.append(mapper.wire(sx, trafo_y + 16, sx, bus_y, line_color, 1.8))
    else:
        root_y = pos_bus[root][1]
        breaker_y = sy + 55
        body.append(mapper.wire(sx, sy + 20, sx, breaker_y - 13))
        body.append(mapper.protection(sx, breaker_y, "breaker", False, sym.INK))
        body.append(mapper.wire(sx, breaker_y + 13, sx, root_y))

    for bus in sorted(pos_bus, key=lambda b: (pos_bus[b][1], pos_bus[b][0])):
        if bus == root and hidden_root_edge:
            continue
        if not physical.get(bus, False):
            continue
        bx, by = pos_bus[bus]
        x_min, x_max = span_bus[bus]
        bar_left = min(x_min - 50, bx - 85)
        bar_right = max(x_max + 50, bx + 85)
        energized = bus in energized_buses
        bar_color = sym.INK if energized else sym.DEENERGIZED
        thickness = 6.0 if bus == diagram_root else 4.2
        body.append(mapper.busbar(bar_left, bar_right, by, bar_color, thickness))

        label = _bus_label(bus)
        if mode == "diagnostico":
            state = (
                f'{_format_voltage(info_bus[bus]["kv_nominal"])} · '
                f'{info_bus[bus]["vpu"]:.3f} pu'
                if energized
                else "SIN TENSIÓN"
            )
        else:
            state = (
                _format_voltage(info_bus[bus]["kv_nominal"])
                if energized
                else "SIN TENSIÓN"
            )
        vcolor = _voltage_color(energized, info_bus[bus]["vpu"])
        lx, ly = mapper.p(bar_right + 10, by - 6)
        body.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" class="bus-name">{escape(label)}</text>'
        )
        sx2, sy2 = mapper.p(bar_right + 10, by + 10)
        body.append(
            f'<text x="{sx2:.1f}" y="{sy2:.1f}" class="bus-state" '
            f'fill="{vcolor}">{escape(state)}</text>'
        )

    for bus in sorted(pos_bus, key=lambda b: (pos_bus[b][1], pos_bus[b][0])):
        if bus not in layout_tree:
            continue
        bx, by = pos_bus[bus]
        parent_bar = physical.get(bus, False)

        for child in sorted(
            layout_tree.successors(bus),
            key=lambda c: _child_sort_key(bus, c, connections),
        ):
            cx, cy = pos_bus[child]
            dato = connections[(bus, child)]
            annotation = visual_state.get_feeder(dato["full_name"])
            opened = bool(dato["abierta"])
            path_color = (
                sym.OPEN
                if opened
                else (sym.INK if child in energized_buses else sym.DEENERGIZED)
            )
            tag = next_tag(annotation)
            current_y = by

            if parent_bar:
                breaker_y = by + 42
                body.append(mapper.wire(cx, by, cx, breaker_y - 13, path_color))
                body.append(
                    mapper.protection(
                        cx,
                        breaker_y,
                        annotation.get("proteccion") or "breaker",
                        opened,
                        path_color,
                    )
                )
                body.append(
                    mapper.label(
                        cx - 15, breaker_y - 17, [tag], anchor="end", cls="feeder-tag"
                    )
                )
                detail = _feeder_detail(annotation, str(dato["nombre"]), mode)
                if detail:
                    body.append(
                        mapper.label(cx + 24, breaker_y - 10, detail, cls="label-dim")
                    )
                if opened:
                    body.append(
                        mapper.label(
                            cx + 18, breaker_y + 14, ["ABIERTO"], cls="status-open"
                        )
                    )
                current_y = breaker_y + 13
            else:
                if mode == "diagnostico":
                    body.append(mapper.junction(bx, by, path_color))

            if dato["tipo"] == "Transformador":
                tr_y = current_y + 55
                body.append(mapper.wire(cx, current_y, cx, tr_y - 16, path_color))
                body.append(mapper.transformer(cx, tr_y, path_color))
                render_transformer_label(cx, tr_y, dato)
                current_y = tr_y + 16

            devices = list(annotation.get("dispositivos") or [])
            for device in devices:
                if device == "ats":
                    ats_y = current_y + 70
                    alt = annotation.get("fuente_alterna")
                    if alt:
                        body.append(
                            mapper.wire(cx, current_y, cx, ats_y - 35, path_color)
                        )
                        body.append(
                            mapper.wire(cx, ats_y - 35, cx - 14, ats_y - 35, path_color)
                        )
                        body.append(
                            mapper.wire(
                                cx - 14, ats_y - 35, cx - 14, ats_y - 14, path_color
                            )
                        )
                    else:
                        body.append(
                            mapper.wire(cx, current_y, cx, ats_y - 21, path_color)
                        )
                    body.append(mapper.symbol("ats", cx, ats_y, path_color))

                    if alt:
                        gen = generator_index.get(str(alt).lower())
                        if gen:
                            gx, gy = cx + 105, ats_y - 35
                            body.append(mapper.symbol("generator", gx, gy, path_color))
                            body.append(mapper.symbol("ground", gx, gy + 23, path_color))
                            knee_x = cx + 58
                            body.append(
                                mapper.wire(gx - 22, gy, knee_x, gy, path_color)
                            )
                            body.append(
                                mapper.wire(
                                    knee_x, gy, knee_x, ats_y - 14, path_color
                                )
                            )
                            body.append(
                                mapper.wire(
                                    knee_x,
                                    ats_y - 14,
                                    cx + 14,
                                    ats_y - 14,
                                    path_color,
                                )
                            )
                            glines = [_engineering_name(str(gen["nombre"]))]
                            if gen.get("kw") is not None:
                                glines.append(f'{gen["kw"]:.0f} kW')
                            body.append(
                                mapper.label(gx + 30, gy - 4, glines, cls="label")
                            )
                            used_alt_generators.add(str(gen["nombre"]).lower())
                    current_y = ats_y + 21
                elif device == "ups":
                    ups_y = current_y + 58
                    body.append(mapper.wire(cx, current_y, cx, ups_y - 19, path_color))
                    body.append(mapper.symbol("ups", cx, ups_y, path_color))
                    current_y = ups_y + 19

            child_is_bar = physical.get(child, False)
            child_loads = sorted(loads_by_bus.get(child, []), key=lambda x: x["nombre"])
            child_gens = sorted(
                [
                    g for g in generators_by_bus.get(child, [])
                    if g["nombre"].lower() not in model["alternate_generators"]
                ],
                key=lambda x: x["nombre"],
            )

            if child_is_bar:
                body.append(mapper.wire(cx, current_y, cx, cy, path_color, 1.7))
            elif len(child_loads) == 1 and not child_gens and not list(layout_tree.successors(child)):
                target_y = cy - 24
                body.append(mapper.wire(cx, current_y, cx, target_y, path_color, 1.7))
            elif len(child_gens) == 1 and not child_loads and not list(layout_tree.successors(child)):
                target_y = cy - 24
                body.append(mapper.wire(cx, current_y, cx, target_y, path_color, 1.7))
            else:
                body.append(mapper.wire(cx, current_y, cx, cy, path_color, 1.7))
                if mode == "diagnostico" or len(list(layout_tree.successors(child))) > 1:
                    body.append(mapper.junction(cx, cy, path_color))

    for bus, (bx, by) in pos_bus.items():
        if physical.get(bus, False):
            continue
        energized = bus in energized_buses
        color = sym.INK if energized else sym.DEENERGIZED
        loads = sorted(loads_by_bus.get(bus, []), key=lambda x: x["nombre"])
        gens = sorted(
            [
                g for g in generators_by_bus.get(bus, [])
                if g["nombre"].lower() not in model["alternate_generators"]
            ],
            key=lambda x: x["nombre"],
        )
        if len(loads) == 1 and not gens and not list(layout_tree.successors(bus)):
            load = loads[0]
            body.append(mapper.symbol(_load_symbol_name(load["tipo_visual"]), bx, by, color))
            lines = [_load_label(load), f'{load["kw"]:.0f} kW']
            body.append(mapper.label(bx, by + 48, lines, anchor="middle", cls="label"))
            if load["critica"]:
                body.append(
                    mapper.label(
                        bx, by + 81, ["CARGA CRÍTICA"], anchor="middle", cls="critical"
                    )
                )
        elif len(gens) == 1 and not loads and not list(layout_tree.successors(bus)):
            gen = gens[0]
            if gen["nombre"].lower() not in used_alt_generators:
                body.append(mapper.symbol("generator", bx, by, color))
                body.append(mapper.symbol("ground", bx, by + 23, color))
                lines = [_engineering_name(str(gen["nombre"]))]
                if gen.get("kw") is not None:
                    lines.append(f'{gen["kw"]:.0f} kW')
                body.append(
                    mapper.label(bx, by + 56, lines, anchor="middle", cls="label")
                )

    for bus, (bx, by) in pos_bus.items():
        if not physical.get(bus, False):
            continue
        energized = bus in energized_buses
        color = sym.INK if energized else sym.DEENERGIZED
        loads = sorted(loads_by_bus.get(bus, []), key=lambda x: x["nombre"])
        for i, load in enumerate(loads):
            x = pos_load[(bus, i)]
            breaker_y = by + 42
            symbol_y = by + 116
            tag = f"C-{circuit_counter[0]:02d}"
            circuit_counter[0] += 1
            body.append(mapper.wire(x, by, x, breaker_y - 13, color))
            body.append(mapper.protection(x, breaker_y, "mccb", False, color))
            body.append(
                mapper.label(
                    x - 15, breaker_y - 17, [tag], anchor="end", cls="feeder-tag"
                )
            )
            body.append(mapper.wire(x, breaker_y + 13, x, symbol_y - 24, color))
            body.append(mapper.symbol(_load_symbol_name(load["tipo_visual"]), x, symbol_y, color))
            body.append(
                mapper.label(
                    x,
                    symbol_y + 48,
                    [_load_label(load), f'{load["kw"]:.0f} kW'],
                    anchor="middle",
                    cls="label",
                )
            )
            if load["critica"]:
                body.append(
                    mapper.label(
                        x,
                        symbol_y + 81,
                        ["CARGA CRÍTICA"],
                        anchor="middle",
                        cls="critical",
                    )
                )

        gens = sorted(
            [
                g for g in generators_by_bus.get(bus, [])
                if g["nombre"].lower() not in model["alternate_generators"]
            ],
            key=lambda x: x["nombre"],
        )
        for i, gen in enumerate(gens):
            if gen["nombre"].lower() in used_alt_generators:
                continue
            x = pos_gen[(bus, i)]
            breaker_y = by + 42
            symbol_y = by + 116
            body.append(mapper.wire(x, by, x, breaker_y - 13, color))
            body.append(mapper.protection(x, breaker_y, "breaker", False, color))
            body.append(mapper.wire(x, breaker_y + 13, x, symbol_y - 24, color))
            body.append(mapper.symbol("generator", x, symbol_y, color))
            body.append(mapper.symbol("ground", x, symbol_y + 23, color))
            lines = [_engineering_name(str(gen["nombre"]))]
            if gen.get("kw") is not None:
                lines.append(f'{gen["kw"]:.0f} kW')
            body.append(
                mapper.label(
                    x, symbol_y + 56, lines, anchor="middle", cls="label"
                )
            )

    if outside and mode == "diagnostico":
        body.append(
            f'<text x="{PAGE_MARGIN}" y="{canvas_height-24:.1f}" class="status-open">'
            f'Buses fuera del componente principal: {escape(", ".join(outside))}</text>'
        )

    if mostrar_leyenda:
        lx = mapper.width + 10
        body.append(_legend(lx, 18))
        if mostrar_reglas:
            body.append(_rules_panel(lx, 538))

    svg_text = _svg_document(
        canvas_width, canvas_height, "".join(body), dss.Circuit.Name()
    )

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
        html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>Unifilar — {escape(dss.Circuit.Name())}</title>
<style>html,body{{margin:0;background:#eef2f7}}.sheet{{max-width:{canvas_width:.0f}px;margin:24px auto;background:#fff;box-shadow:0 4px 24px #0002}}svg{{display:block;width:100%;height:auto}}</style>
</head><body><div class="sheet">{svg_text}</div></body></html>"""
        html_path.write_text(html, encoding="utf-8")

    barras = [b for b, value in physical.items() if value]
    ocultos = [b for b, value in physical.items() if not value]
    desconectados = sorted(set(buses) - set(energized_buses))
    is_radial = nx.is_tree(model["total"]) if model["total"].number_of_nodes() else True

    return {
        "archivo_generado": str(html_path or svg_path),
        "archivo_svg": str(svg_path),
        "archivo_html": str(html_path) if html_path else None,
        "buses_modelo": len(buses),
        "barras_fisicas_dibujadas": barras,
        "buses_logicos_no_dibujados_como_barra": ocultos,
        "buses_desconectados": desconectados,
        "cargas_dibujadas": len(dss.Loads.AllNames()),
        "generadores_dibujados": len(dss.Generators.AllNames()),
        "transformadores_dibujados": len(dss.Transformers.AllNames()),
        "topologia_radial_pura": is_radial,
        "modo": mode,
        "orientacion": orientation,
        "estilo": "unifilar_tecnico_svg_v2",
        "nota": (
            "ATS/UPS y metadatos de protección/conductor son anotaciones "
            "visuales; no modifican el cálculo OpenDSS."
        ),
    }
