"""Puente explícito hacia pandapower, ampliado por P2.

No implementa cross-check ni selección automática de motor. Lee el modelo
activo y los metadatos profesionales P2, construye una red pandapower nueva en
memoria y la resuelve independientemente.

Alcance P2 v1:
- sistema trifásico balanceado;
- líneas y cargas trifásicas;
- transformadores de dos devanados únicamente si tienen ficha P2 suficiente;
- varios niveles de tensión solo cuando son resolubles mediante esos
  transformadores;
- flujo AC balanceado.

No se sustituyen datos pandapower obligatorios por cero o valores típicos. Un
transformador sin pérdidas en vacío o i0 explícitos se rechaza con PP012.
"""

from __future__ import annotations

from math import sqrt
from typing import Any

import pandapower as pp
from opendssdirect import dss

from . import professional_data, visual_state


ENGINE_NAME = "pandapower"
MATURITY = "EXPERIMENTAL"
SCOPE = "balanced_three_phase_line_load_p2_transformer_optional"
_INTERNAL_FALLBACK_MAX_I_KA = 1_000.0


def _bus_name(raw: str) -> str:
    return str(raw).split(".")[0]


def _active_source_bus() -> str:
    """Lee la barra efectiva de Vsource.source sin asumir el nombre sourcebus."""
    try:
        dss("? Vsource.source.bus1")
        raw = str(dss.Text.Result() or "").strip()
        return _bus_name(raw).strip()
    except Exception:
        return ""


def _active_element_is_open(full_name: str) -> bool:
    if not dss.Circuit.SetActiveElement(full_name):
        return False
    try:
        return bool(dss.CktElement.IsOpen(1, 0))
    except Exception:
        return False


def _collect_active_model() -> dict[str, Any]:
    """Extrae entradas sin ejecutar ``Solve`` ni leer resultados de OpenDSS.

    La tensión nominal se resuelve con precedencia explícita P2: fuente y
    transformadores profesionales, propagación por líneas, y solo después
    ``dss.Bus.kVBase()`` como fallback. Así un kVBase implícito/stale de OpenDSS
    no puede sobrescribir un nivel LV declarado por un transformador P2.
    """
    circuit_name = str(dss.Circuit.Name() or "")
    if not circuit_name:
        return {
            "circuit": "", "buses": [], "lines": [], "loads": [],
            "transformers": [], "generators": [], "source": None,
            "source_bus": "", "active_source_bus": "",
        }

    p2 = professional_data.snapshot()
    p2_transformers = {
        str(item["id"]).lower(): item for item in p2.get("transformers", [])
    }
    source = p2.get("source")
    active_source_bus = _active_source_bus()
    declared_source_bus = str((source or {}).get("bus") or "").strip()
    source_bus = declared_source_bus or active_source_bus

    buses: list[dict[str, Any]] = []
    voltage_by_bus: dict[str, float] = {}
    dss_voltage_by_bus: dict[str, float] = {}
    for name in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(name)
        kv_base_ln = float(dss.Bus.kVBase())
        vn = kv_base_ln * sqrt(3.0) if kv_base_ln > 0 else None
        buses.append(
            {
                "name": name,
                "kv_base_ln": kv_base_ln,
                "vn_kv_ll": vn,
                "nodes": [int(n) for n in dss.Bus.Nodes()],
            }
        )
        if vn:
            dss_voltage_by_bus[name.lower()] = vn

    if source and source_bus:
        voltage_by_bus[source_bus.lower()] = float(source["kv_ll"])

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

    transformers: list[dict[str, Any]] = []
    for name in dss.Transformers.AllNames():
        full = f"Transformer.{name}"
        record = p2_transformers.get(full.lower())
        transformers.append(
            {
                "id": full,
                "name": name,
                "professional": record,
                "open": _active_element_is_open(full),
            }
        )
        if record:
            voltage_by_bus[str(record["buses"]["hv"]).lower()] = float(record["rating"]["kv_hv"])
            voltage_by_bus[str(record["buses"]["lv"]).lower()] = float(record["rating"]["kv_lv"])

    # Propaga primero los niveles nominales explícitos P2 a través de líneas.
    for _ in range(max(1, len(lines) + 1)):
        changed = False
        for line in lines:
            b1, b2 = line["bus1"].lower(), line["bus2"].lower()
            if b1 in voltage_by_bus and b2 not in voltage_by_bus:
                voltage_by_bus[b2] = voltage_by_bus[b1]
                changed = True
            elif b2 in voltage_by_bus and b1 not in voltage_by_bus:
                voltage_by_bus[b1] = voltage_by_bus[b2]
                changed = True
        if not changed:
            break

    # OpenDSS se usa únicamente como fallback para barras no resueltas por P2.
    for name, vn in dss_voltage_by_bus.items():
        voltage_by_bus.setdefault(name, float(vn))

    for bus in buses:
        resolved = voltage_by_bus.get(str(bus["name"]).lower())
        if resolved:
            bus["vn_kv_ll"] = float(resolved)
            bus["kv_base_ln"] = float(resolved) / sqrt(3.0)

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
        "transformers": transformers,
        "generators": [str(x) for x in dss.Generators.AllNames()],
        "source": source,
        "source_bus": source_bus,
        "active_source_bus": active_source_bus,
    }


def _transformer_ready(record: dict[str, Any] | None) -> tuple[bool, str | None]:
    if not record:
        return False, "No existe ficha profesional P2."
    losses = record.get("losses", {})
    if losses.get("no_load_loss_kw") is None or losses.get("i0_percent") is None:
        return False, "Pandapower requiere pfe_kw e i0_percent explícitos; no se sustituyen por cero."
    sc = record.get("short_circuit", {})
    if sc.get("uk_percent") is None or sc.get("r_percent_total") is None:
        return False, "Faltan uk_percent o la componente resistiva trazable."
    return True, None


def evaluar_compatibilidad() -> dict[str, Any]:
    """Comprueba si el modelo entra exactamente en el alcance pandapower P2 v1."""
    model = _collect_active_model()
    issues: list[dict[str, str]] = []

    if not model["circuit"]:
        issues.append({"code": "PP001", "message": "No existe un circuito activo."})

    bus_names = {str(b["name"]).lower() for b in model["buses"]}
    source_bus = str(model.get("source_bus") or "").strip()
    active_source_bus = str(model.get("active_source_bus") or "").strip()
    if not source_bus:
        issues.append({"code": "PP002", "message": "No se pudo resolver la barra efectiva de Vsource.source."})
    elif source_bus.lower() not in bus_names:
        issues.append({"code": "PP002", "message": f"La barra fuente {source_bus!r} no existe en el modelo activo."})
    declared = str((model.get("source") or {}).get("bus") or "").strip()
    if declared and active_source_bus and declared.lower() != active_source_bus.lower():
        issues.append({
            "code": "PP003",
            "message": f"La barra P2 declarada {declared!r} no coincide con Vsource.source={active_source_bus!r}.",
        })

    if model["generators"]:
        issues.append({"code": "PP011", "message": "Esta versión todavía no traduce generadores ni motores."})

    for transformer in model["transformers"]:
        record = transformer.get("professional")
        if record is None:
            issues.append(
                {
                    "code": "PP010",
                    "message": f"{transformer['id']} no tiene ficha profesional P2; no se adivinan %Z, pérdidas ni grupo vectorial.",
                }
            )
            continue
        ready, reason = _transformer_ready(record)
        if not ready:
            issues.append({"code": "PP012", "message": f"{transformer['id']}: {reason}"})

    for line in model["lines"]:
        if line["phases"] != 3:
            issues.append({"code": "PP020", "message": f"{line['id']} tiene {line['phases']} fases; solo se admiten líneas trifásicas balanceadas."})
        if line["length_km"] <= 0:
            issues.append({"code": "PP021", "message": f"{line['id']} tiene longitud no positiva."})

    for load in model["loads"]:
        if load["phases"] != 3:
            issues.append({"code": "PP030", "message": f"{load['id']} tiene {load['phases']} fases; solo se admiten cargas trifásicas balanceadas."})

    unresolved = [str(b["name"]) for b in model["buses"] if not b.get("vn_kv_ll")]
    if unresolved:
        issues.append({"code": "PP041", "message": "No se pudo resolver la tensión nominal de: " + ", ".join(unresolved)})

    valid_levels = {round(float(b["vn_kv_ll"]), 6) for b in model["buses"] if b.get("vn_kv_ll")}
    if len(valid_levels) > 1 and not model["transformers"]:
        issues.append({"code": "PP040", "message": "Hay varios niveles nominales sin transformador P2 que los relacione."})

    return {
        "engine": ENGINE_NAME,
        "engine_version": pp.__version__,
        "maturity": MATURITY,
        "scope": SCOPE,
        "compatible": not issues,
        "issues": issues,
        "model_summary": {
            "circuit": model["circuit"],
            "source_bus": source_bus or None,
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
        idx = pp.create_bus(net, vn_kv=float(bus["vn_kv_ll"]), name=str(bus["name"]))
        bus_map[str(bus["name"]).lower()] = int(idx)

    source_bus = str(model.get("source_bus") or "").strip()
    source_idx = bus_map[source_bus.lower()]
    pp.create_ext_grid(net, bus=source_idx, vm_pu=1.0, va_degree=0.0, name=source_bus)

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
        line_meta[int(idx)] = {"id": line["id"], "rating_a": float(rating_a) if rating_valid else None}

    trafo_meta: dict[int, dict[str, Any]] = {}
    for transformer in model["transformers"]:
        p = transformer["professional"]
        sc = p["short_circuit"]
        losses = p["losses"]
        vg = p["vector_group"]
        tap = p["tap"]
        kwargs: dict[str, Any] = {}
        if tap.get("enabled"):
            kwargs.update(
                tap_side=tap["side"],
                tap_neutral=tap["neutral"],
                tap_min=tap["min"],
                tap_max=tap["max"],
                tap_step_percent=tap["step_percent"],
                tap_pos=tap["position"],
                tap_changer_type="Ratio",
            )
        idx = pp.create_transformer_from_parameters(
            net,
            hv_bus=bus_map[str(p["buses"]["hv"]).lower()],
            lv_bus=bus_map[str(p["buses"]["lv"]).lower()],
            sn_mva=float(p["rating"]["kva"]) / 1000.0,
            vn_hv_kv=float(p["rating"]["kv_hv"]),
            vn_lv_kv=float(p["rating"]["kv_lv"]),
            vkr_percent=float(sc["r_percent_total"]),
            vk_percent=float(sc["uk_percent"]),
            pfe_kw=float(losses["no_load_loss_kw"]),
            i0_percent=float(losses["i0_percent"]),
            shift_degree=float(vg["shift_degree"]),
            vector_group=str(vg["vector_group_pandapower"]),
            name=str(transformer["name"]),
            in_service=not bool(transformer["open"]),
            **kwargs,
        )
        trafo_meta[int(idx)] = {"id": transformer["id"]}

    for load in model["loads"]:
        pp.create_load(
            net,
            bus=bus_map[str(load["bus"]).lower()],
            p_mw=float(load["kw"]) / 1000.0,
            q_mvar=float(load["kvar"]) / 1000.0,
            name=str(load["name"]),
            type="wye",
        )

    return net, line_meta, trafo_meta


def ejecutar_flujo() -> dict[str, Any]:
    """Ejecuta flujo AC balanceado pandapower sin comparar contra OpenDSS."""
    model = _collect_active_model()
    compatibility = evaluar_compatibilidad()
    if not compatibility["compatible"]:
        return {
            **compatibility,
            "ok": False,
            "convergio": False,
            "resultados": None,
            "nota": "Modelo fuera del alcance explícito de pandapower; no se aplicaron aproximaciones silenciosas.",
        }

    net, line_meta, trafo_meta = _build_net(model)
    try:
        pp.runpp(net, algorithm="nr", calculate_voltage_angles=True, init="auto", check_connectivity=True)
    except Exception as exc:
        return {**compatibility, "ok": False, "convergio": False, "resultados": None, "error": f"{type(exc).__name__}: {exc}"}

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
                "cargabilidad_pct": round(float(res["loading_percent"]), 3) if rating_a is not None else None,
            }
        )

    transformers = []
    for idx, row in net.trafo.iterrows():
        res = net.res_trafo.loc[idx]
        meta = trafo_meta[int(idx)]
        transformers.append(
            {
                "id": meta["id"],
                "name": str(row["name"]),
                "loading_percent": round(float(res["loading_percent"]), 3),
                "p_hv_kw": round(float(res["p_hv_mw"]) * 1000.0, 6),
                "p_lv_kw": round(float(res["p_lv_mw"]) * 1000.0, 6),
                "q_hv_kvar": round(float(res["q_hv_mvar"]) * 1000.0, 6),
                "q_lv_kvar": round(float(res["q_lv_mvar"]) * 1000.0, 6),
            }
        )

    line_loss_kw = float(net.res_line["pl_mw"].sum()) * 1000.0 if len(net.res_line) else 0.0
    trafo_loss_kw = float(net.res_trafo["pl_mw"].sum()) * 1000.0 if len(net.res_trafo) else 0.0
    line_loss_kvar = float(net.res_line["ql_mvar"].sum()) * 1000.0 if len(net.res_line) else 0.0
    trafo_loss_kvar = float(net.res_trafo["ql_mvar"].sum()) * 1000.0 if len(net.res_trafo) else 0.0

    return {
        **compatibility,
        "ok": True,
        "convergio": bool(net.converged),
        "resultados": {
            "buses": buses,
            "lines": lines,
            "transformers": transformers,
            "resumen": {
                "perdidas_totales_kw": round(line_loss_kw + trafo_loss_kw, 6),
                "perdidas_totales_kvar": round(line_loss_kvar + trafo_loss_kvar, 6),
            },
        },
        "assumptions": [
            f"Flujo AC trifásico balanceado; la barra fuente {model['source_bus']} se representa como ext_grid a 1.0 pu.",
            "La Scc P2 se conserva para estudios que la requieran y no altera este flujo ideal.",
            "La topología y parámetros se leen del modelo activo; no se consumen resultados de flujo OpenDSS.",
            "La cargabilidad de línea solo se expone cuando existe corriente_nominal_a explícita.",
        ],
        "nota": "Pandapower permanece EXPERIMENTAL; P2 amplía compatibilidad, no su madurez de validación.",
    }