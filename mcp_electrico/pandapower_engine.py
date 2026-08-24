"""Puente experimental hacia pandapower.

Esta primera integración NO implementa cross-check ni selección automática de
motor. Lee el modelo eléctrico activo de OpenDSS como fuente de topología y
datos, construye una red pandapower independiente y resuelve únicamente un
alcance deliberadamente pequeño y explícito.

Alcance v1:
- sistema trifásico balanceado;
- un solo nivel de tensión;
- fuente ideal en ``sourcebus``;
- elementos Line + Load;
- flujo de potencia AC balanceado.

Fuera de alcance v1:
- transformadores;
- generadores/motores;
- redes desbalanceadas;
- secuencia cero;
- cortocircuito IEC 60909;
- protecciones;
- cross-check OpenDSS vs pandapower.
"""

from __future__ import annotations

from math import sqrt
from typing import Any

import pandapower as pp
from opendssdirect import dss

from . import visual_state


ENGINE_NAME = "pandapower"
MATURITY = "EXPERIMENTAL"
SCOPE = "balanced_three_phase_single_voltage_line_load"
_INTERNAL_FALLBACK_MAX_I_KA = 1_000.0


def _bus_name(raw: str) -> str:
    return str(raw).split(".")[0]


def _active_element_is_open(full_name: str) -> bool:
    if not dss.Circuit.SetActiveElement(full_name):
        return False
    try:
        return bool(dss.CktElement.IsOpen(1, 0))
    except Exception:
        return False


def _collect_active_model() -> dict[str, Any]:
    """Extrae únicamente los datos necesarios para el puente v1.

    La extracción no ejecuta ``Solve`` y no consume resultados de flujo de
    OpenDSS. OpenDSS actúa aquí como almacén del modelo actualmente editado.
    """
    circuit_name = str(dss.Circuit.Name() or "")
    if not circuit_name:
        return {
            "circuit": "",
            "buses": [],
            "lines": [],
            "loads": [],
            "transformers": [],
            "generators": [],
        }

    buses: list[dict[str, Any]] = []
    for name in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(name)
        kv_base_ln = float(dss.Bus.kVBase())
        buses.append(
            {
                "name": name,
                "kv_base_ln": kv_base_ln,
                "vn_kv_ll": kv_base_ln * sqrt(3.0) if kv_base_ln > 0 else None,
                "nodes": [int(n) for n in dss.Bus.Nodes()],
            }
        )

    lines: list[dict[str, Any]] = []
    for name in dss.Lines.AllNames():
        dss.Lines.Name(name)
        full = f"Line.{name}"
        visual = visual_state.get_feeder(full)
        try:
            c1_nf_km = float(dss.Lines.C1())
        except Exception:
            c1_nf_km = 0.0
        lines.append(
            {
                "id": full,
                "name": name,
                "bus1": _bus_name(dss.Lines.Bus1()),
                "bus2": _bus_name(dss.Lines.Bus2()),
                "length_km": float(dss.Lines.Length()),
                "phases": int(dss.Lines.Phases()),
                "r1_ohm_km": float(dss.Lines.R1()),
                "x1_ohm_km": float(dss.Lines.X1()),
                "c1_nf_km": c1_nf_km,
                "open": _active_element_is_open(full),
                "rating_a": visual.get("corriente_nominal_a"),
            }
        )

    loads: list[dict[str, Any]] = []
    for name in dss.Loads.AllNames():
        dss.Loads.Name(name)
        buses_raw = dss.CktElement.BusNames()
        loads.append(
            {
                "id": f"Load.{name}",
                "name": name,
                "bus": _bus_name(buses_raw[0]) if buses_raw else "",
                "phases": int(dss.Loads.Phases()),
                "kw": float(dss.Loads.kW()),
                "kvar": float(dss.Loads.kvar()),
            }
        )

    return {
        "circuit": circuit_name,
        "buses": buses,
        "lines": lines,
        "loads": loads,
        "transformers": [str(x) for x in dss.Transformers.AllNames()],
        "generators": [str(x) for x in dss.Generators.AllNames()],
    }


def evaluar_compatibilidad() -> dict[str, Any]:
    """Comprueba si el modelo activo entra exactamente en el alcance v1."""
    model = _collect_active_model()
    issues: list[dict[str, str]] = []

    if not model["circuit"]:
        issues.append({"code": "PP001", "message": "No existe un circuito activo."})

    bus_names = {str(b["name"]).lower() for b in model["buses"]}
    if "sourcebus" not in bus_names:
        issues.append(
            {
                "code": "PP002",
                "message": "Pandapower v1 requiere una barra fuente llamada sourcebus.",
            }
        )

    if model["transformers"]:
        issues.append(
            {
                "code": "PP010",
                "message": "Pandapower v1 todavía no traduce transformadores; se incorporarán con datos profesionales de P2.",
            }
        )

    if model["generators"]:
        issues.append(
            {
                "code": "PP011",
                "message": "Pandapower v1 todavía no traduce generadores ni motores.",
            }
        )

    for line in model["lines"]:
        if line["phases"] != 3:
            issues.append(
                {
                    "code": "PP020",
                    "message": f"{line['id']} tiene {line['phases']} fases; v1 solo admite líneas trifásicas balanceadas.",
                }
            )
        if line["length_km"] <= 0:
            issues.append(
                {
                    "code": "PP021",
                    "message": f"{line['id']} tiene longitud no positiva.",
                }
            )

    for load in model["loads"]:
        if load["phases"] != 3:
            issues.append(
                {
                    "code": "PP030",
                    "message": f"{load['id']} tiene {load['phases']} fases; v1 solo admite cargas trifásicas balanceadas.",
                }
            )

    valid_levels = [float(b["vn_kv_ll"]) for b in model["buses"] if b["vn_kv_ll"]]
    rounded_levels = {round(v, 6) for v in valid_levels}
    if len(rounded_levels) > 1:
        issues.append(
            {
                "code": "PP040",
                "message": "Pandapower v1 solo admite un nivel nominal de tensión por modelo.",
            }
        )
    if not valid_levels and model["circuit"]:
        issues.append(
            {
                "code": "PP041",
                "message": "No se pudo determinar la tensión nominal de las barras.",
            }
        )

    return {
        "engine": ENGINE_NAME,
        "engine_version": pp.__version__,
        "maturity": MATURITY,
        "scope": SCOPE,
        "compatible": not issues,
        "issues": issues,
        "model_summary": {
            "circuit": model["circuit"],
            "buses": len(model["buses"]),
            "lines": len(model["lines"]),
            "loads": len(model["loads"]),
            "transformers": len(model["transformers"]),
            "generators": len(model["generators"]),
        },
    }


def _build_net(model: dict[str, Any]):
    net = pp.create_empty_network(sn_mva=100.0, name=model["circuit"])
    bus_map: dict[str, int] = {}

    for bus in model["buses"]:
        idx = pp.create_bus(
            net,
            vn_kv=float(bus["vn_kv_ll"]),
            name=str(bus["name"]),
        )
        bus_map[str(bus["name"]).lower()] = int(idx)

    source_idx = bus_map["sourcebus"]
    pp.create_ext_grid(net, bus=source_idx, vm_pu=1.0, va_degree=0.0, name="sourcebus")

    line_meta: dict[int, dict[str, Any]] = {}
    for line in model["lines"]:
        rating_a = line.get("rating_a")
        rating_valid = rating_a is not None and float(rating_a) > 0
        max_i_ka = float(rating_a) / 1000.0 if rating_valid else _INTERNAL_FALLBACK_MAX_I_KA
        idx = pp.create_line_from_parameters(
            net,
            from_bus=bus_map[str(line["bus1"]).lower()],
            to_bus=bus_map[str(line["bus2"]).lower()],
            length_km=float(line["length_km"]),
            r_ohm_per_km=float(line["r1_ohm_km"]),
            x_ohm_per_km=float(line["x1_ohm_km"]),
            c_nf_per_km=float(line["c1_nf_km"]),
            max_i_ka=max_i_ka,
            name=str(line["name"]),
            in_service=not bool(line["open"]),
        )
        line_meta[int(idx)] = {
            "id": line["id"],
            "rating_a": float(rating_a) if rating_valid else None,
        }

    for load in model["loads"]:
        pp.create_load(
            net,
            bus=bus_map[str(load["bus"]).lower()],
            p_mw=float(load["kw"]) / 1000.0,
            q_mvar=float(load["kvar"]) / 1000.0,
            name=str(load["name"]),
            type="wye",
        )

    return net, line_meta


def ejecutar_flujo() -> dict[str, Any]:
    """Ejecuta flujo AC balanceado con pandapower dentro del alcance v1.

    No ejecuta OpenDSS ``Solve`` y no compara ambos motores.
    """
    model = _collect_active_model()
    compatibility = evaluar_compatibilidad()
    if not compatibility["compatible"]:
        return {
            **compatibility,
            "ok": False,
            "convergio": False,
            "resultados": None,
            "nota": "Modelo fuera del alcance experimental de pandapower v1; no se aplicaron aproximaciones silenciosas.",
        }

    net, line_meta = _build_net(model)
    try:
        pp.runpp(
            net,
            algorithm="nr",
            calculate_voltage_angles=True,
            init="auto",
            check_connectivity=True,
        )
    except Exception as exc:
        return {
            **compatibility,
            "ok": False,
            "convergio": False,
            "resultados": None,
            "error": f"{type(exc).__name__}: {exc}",
        }

    buses = []
    for idx, row in net.bus.iterrows():
        res = net.res_bus.loc[idx]
        buses.append(
            {
                "bus": str(row["name"]),
                "vn_kv": round(float(row["vn_kv"]), 6),
                "vm_pu": round(float(res["vm_pu"]), 6),
                "va_degree": round(float(res["va_degree"]), 6),
            }
        )

    lines = []
    for idx, row in net.line.iterrows():
        res = net.res_line.loc[idx]
        meta = line_meta[int(idx)]
        rating_a = meta["rating_a"]
        lines.append(
            {
                "id": meta["id"],
                "name": str(row["name"]),
                "i_from_a": round(float(res["i_from_ka"]) * 1000.0, 3),
                "i_to_a": round(float(res["i_to_ka"]) * 1000.0, 3),
                "perdidas_kw": round(float(res["pl_mw"]) * 1000.0, 6),
                "perdidas_kvar": round(float(res["ql_mvar"]) * 1000.0, 6),
                "corriente_nominal_a": rating_a,
                "cargabilidad_pct": (
                    round(float(res["loading_percent"]), 3) if rating_a is not None else None
                ),
            }
        )

    return {
        **compatibility,
        "ok": True,
        "convergio": bool(net.converged),
        "resultados": {
            "buses": buses,
            "lines": lines,
            "resumen": {
                "perdidas_totales_kw": round(float(net.res_line["pl_mw"].sum()) * 1000.0, 6),
                "perdidas_totales_kvar": round(float(net.res_line["ql_mvar"].sum()) * 1000.0, 6),
            },
        },
        "assumptions": [
            "Fuente ideal en sourcebus con 1.0 pu y 0 grados.",
            "Flujo AC trifásico balanceado.",
            "La topología y parámetros de entrada se leen del modelo activo; no se consumen resultados de flujo OpenDSS.",
            "La cargabilidad solo se expone cuando existe corriente_nominal_a explícita; el valor interno de respaldo de max_i_ka no se reporta como rating.",
        ],
        "nota": "Pandapower v1 es experimental y no habilita por sí solo emisión profesional.",
    }
