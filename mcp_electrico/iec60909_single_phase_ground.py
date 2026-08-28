"""P4C07 — falla monofásica a tierra IEC 60909 con secuencia cero explícita."""

from __future__ import annotations

from copy import deepcopy
from math import sqrt
from typing import Any

import pandapower as pp

from . import iec60909, iec60909_contract, pandapower_engine, professional_data, zero_sequence

SCHEMA = "MCP_ELECTRICO_IEC60909_1PH_GROUND_V1"
NEGATIVE_SEQUENCE_POLICY = {
    "id": "P4C07_Z2_EQUALS_Z1_SYMMETRIC_PASSIVE_SCOPE",
    "relation": "Z2 = Z1",
    "explicit": True,
    "scope": "red simétrica pasiva soportada actualmente por el puente pandapower P4",
    "universal_assumption": False,
    "note": (
        "La igualdad Z2=Z1 se limita al alcance pasivo simétrico actual; no se extiende "
        "a generadores, motores ni modelos asimétricos."
    ),
}


def _voltage_factor(vn_kv: float, case: str, lv_tol_percent: int = 10) -> float:
    case_norm = iec60909._normalize_case(case)
    vn = float(vn_kv)
    if vn <= 0:
        raise ValueError("P4C07V001: vn_kv debe ser positivo.")
    if vn < 1.0:
        if lv_tol_percent == 10:
            return 1.1 if case_norm == "max" else 0.9
        if lv_tol_percent == 6:
            return 1.05 if case_norm == "max" else 0.95
        raise ValueError("P4C07V002: lv_tol_percent debe ser 6 o 10 para redes BT.")
    return 1.1 if case_norm == "max" else 1.0


def _source_zero_projection(case: str, lv_tol_percent: int = 10) -> dict[str, Any]:
    case_norm = iec60909._normalize_case(case)
    positive = iec60909._source_projection(case_norm)
    source = professional_data.obtener_red_equivalente()
    z0 = zero_sequence.obtener_fuente()
    if not source:
        raise ValueError("P4C07S001: falta red equivalente P2.")
    values = (z0 or {}).get("scenarios", {}).get(case_norm)
    if not values:
        raise ValueError(f"P4C07S002: falta Z0 explícita de fuente para escenario {case_norm}.")

    vn_kv = float(source.get("kv_ll") or 0.0)
    c = _voltage_factor(vn_kv, case_norm, lv_tol_percent)
    rx = float(positive["r_x_pandapower"])
    z1_ohm = c * vn_kv * vn_kv / float(positive["scc3_mva"])
    x1_ohm = z1_ohm / sqrt(1.0 + rx * rx)
    r1_ohm = rx * x1_ohm

    r0 = float(values.get("r0_ohm") or 0.0)
    x0 = float(values.get("x0_ohm") or 0.0)
    if r0 < 0 or x0 <= 0:
        raise ValueError(
            "P4C07S003: la proyección pandapower requiere R0>=0 y X0>0 explícitos; "
            "no se aproxima un X0 nulo."
        )

    return {
        **positive,
        "vn_kv": vn_kv,
        "voltage_factor_c": c,
        "lv_tol_percent": int(lv_tol_percent),
        "z1_backend_ohm": z1_ohm,
        "r1_backend_ohm": r1_ohm,
        "x1_backend_ohm": x1_ohm,
        "r0_ohm": r0,
        "x0_ohm": x0,
        "r0x0": r0 / x0,
        "x0x": x0 / x1_ohm,
        "mapping": {
            "r0x0": "R0 / X0",
            "x0x": "X0 / X1_backend",
            "preserves_absolute_z0": True,
        },
    }


def _apply_source_zero_sequence(net, projection: dict[str, Any]) -> None:
    if len(net.ext_grid) != 1:
        raise ValueError("P4C07S010: el alcance P4C07 v1 requiere una única ext_grid.")
    idx = net.ext_grid.index[0]
    case = str(projection["case"])
    net.ext_grid.at[idx, f"r0x0_{case}"] = float(projection["r0x0"])
    net.ext_grid.at[idx, f"x0x_{case}"] = float(projection["x0x"])


def _apply_line_zero_sequence(net) -> list[dict[str, Any]]:
    applied: list[dict[str, Any]] = []
    by_name = {str(row["name"]).lower(): idx for idx, row in net.line.iterrows()}
    for record in zero_sequence.snapshot().get("lines", []):
        element = str(record.get("element") or "")
        name = element.split(".", 1)[-1].lower()
        if name not in by_name:
            raise ValueError(f"P4C07L001: línea Z0 {element} no existe en la red pandapower proyectada.")
        c0 = record.get("c0_nf_km")
        if c0 is None:
            raise ValueError(f"P4C07L002: {element} requiere c0_nf_km explícita para 1F-T IEC 60909.")
        idx = by_name[name]
        net.line.at[idx, "r0_ohm_per_km"] = float(record["r0_ohm_km"])
        net.line.at[idx, "x0_ohm_per_km"] = float(record["x0_ohm_km"])
        net.line.at[idx, "c0_nf_per_km"] = float(c0)
        applied.append(
            {
                "element": element,
                "r0_ohm_per_km": float(record["r0_ohm_km"]),
                "x0_ohm_per_km": float(record["x0_ohm_km"]),
                "c0_nf_per_km": float(c0),
            }
        )

    if len(applied) != len(net.line):
        known = {item["element"].split(".", 1)[-1].lower() for item in applied}
        missing = [
            str(row["name"])
            for _, row in net.line.iterrows()
            if str(row["name"]).lower() not in known
        ]
        if missing:
            raise ValueError("P4C07L003: líneas sin ficha Z0 explícita: " + ", ".join(sorted(missing)))
    return applied


def _effective_vector_group(p2: dict[str, Any], z0: dict[str, Any]) -> str:
    vg = p2.get("vector_group", {})
    hv = "D" if vg.get("hv_connection") == "delta" else "Y"
    lv = "d" if vg.get("lv_connection") == "delta" else "y"
    neutral = z0.get("neutral", {})
    side = neutral.get("side")
    mode = neutral.get("mode")
    grounded = mode in {"solid", "impedance"}
    if grounded and side == "hv" and hv == "Y":
        hv = "YN"
    if grounded and side == "lv" and lv == "y":
        lv = "yn"
    return f"{hv}{lv}"


def _apply_transformer_zero_sequence(net) -> list[dict[str, Any]]:
    applied: list[dict[str, Any]] = []
    if len(net.trafo) == 0:
        return applied
    by_name = {str(row["name"]).lower(): idx for idx, row in net.trafo.iterrows()}
    z0_by_name = {
        str(item.get("element") or "").split(".", 1)[-1].lower(): item
        for item in zero_sequence.snapshot().get("transformers", [])
    }
    for name, idx in by_name.items():
        record = z0_by_name.get(name)
        if not record:
            raise ValueError(f"P4C07T001: Transformer.{name} no tiene ficha Z0 explícita.")
        p2 = professional_data.obtener_transformador(f"Transformer.{name}")
        if not p2:
            raise ValueError(f"P4C07T002: Transformer.{name} no tiene ficha P2 positiva.")
        projection = record.get("projection", {}).get("pandapower", {})
        required = ("vk0_percent", "vkr0_percent", "mag0_percent", "mag0_rx", "si0_hv_partial")
        missing = [key for key in required if projection.get(key) is None]
        if missing:
            raise ValueError(
                f"P4C07T003: Transformer.{name} Z0 incompleto para pandapower: {', '.join(missing)}."
            )
        for key in required:
            net.trafo.at[idx, key] = float(projection[key])
        vector_group = _effective_vector_group(p2, record)
        net.trafo.at[idx, "vector_group"] = vector_group

        neutral = record.get("neutral", {})
        mode = neutral.get("mode")
        if mode in {"solid", "impedance"}:
            net.trafo.at[idx, "rn_ohm"] = float(projection.get("rn_ohm") or 0.0)
            net.trafo.at[idx, "xn_ohm"] = float(projection.get("xn_ohm") or 0.0)
        else:
            net.trafo.at[idx, "rn_ohm"] = 0.0
            net.trafo.at[idx, "xn_ohm"] = 0.0

        applied.append(
            {
                "element": f"Transformer.{name}",
                "vector_group_effective": vector_group,
                "neutral": deepcopy(neutral),
                "pandapower": {key: float(projection[key]) for key in required}
                | {
                    "rn_ohm": float(net.trafo.at[idx, "rn_ohm"]),
                    "xn_ohm": float(net.trafo.at[idx, "xn_ohm"]),
                },
            }
        )
    return applied


def _apply_zero_sequence(net, case: str, lv_tol_percent: int = 10) -> dict[str, Any]:
    source = _source_zero_projection(case, lv_tol_percent)
    _apply_source_zero_sequence(net, source)
    lines = _apply_line_zero_sequence(net)
    transformers = _apply_transformer_zero_sequence(net)
    return {"source": source, "lines": lines, "transformers": transformers}


def ejecutar_1ph_ground(
    bus: str,
    case: str = "max",
    *,
    line_endtemp_degree_c: dict[str, float] | None = None,
    lv_tol_percent: int = 10,
) -> dict[str, Any]:
    """Ejecuta 1F-T MAX/MIN con Z0 explícita y sin emisión profesional."""

    case_norm = iec60909._normalize_case(case)
    compatibility = pandapower_engine.evaluar_compatibilidad()
    base = {
        "schema": SCHEMA,
        "study": "IEC60909_SHORT_CIRCUIT",
        "fault": "1PH_GROUND",
        "fault_type": "single_phase_ground",
        "case": case_norm,
        "engine": "pandapower",
        "target_standard": deepcopy(iec60909_contract.TARGET_STANDARD),
        "target_edition_conformance": iec60909_contract.BACKEND["target_edition_conformance"],
        "maturity": "EXPERIMENTAL_P4",
        "professional_emission": False,
        "negative_sequence_policy": deepcopy(NEGATIVE_SEQUENCE_POLICY),
        "limitations": [
            "P4C07 v1 usa la API 1ph de pandapower 3.5.x con Z0 explícita.",
            "ip/Ith no se promocionan para 1F-T: calc_sc 3.5.4 no los calcula en la ruta _calc_sc_1ph.",
            "Sk'' no se normaliza contractualmente para 1F-T en P4C07.",
            "La conformidad específica con IEC 60909-0:2026 permanece pendiente de P4C10.",
        ],
        "compatibility": compatibility,
    }
    if not compatibility.get("compatible"):
        return {
            **base,
            "ok": False,
            "status": "NOT_COMPATIBLE",
            "issues": deepcopy(compatibility.get("issues", [])),
        }

    model = pandapower_engine._collect_active_model()
    if not model.get("source_professional"):
        return {
            **base,
            "ok": False,
            "status": "MISSING_SOURCE_DATA",
            "issues": [{"code": "P4C07S001", "message": "Falta red equivalente P2."}],
        }

    net, bus_map = pandapower_engine._build_net(model)
    source_projection = iec60909._source_projection(case_norm)
    iec60909._set_source_short_circuit(net, source_projection)
    temperature_projection = iec60909._set_min_line_temperatures(
        net, case_norm, line_endtemp_degree_c
    )
    zero_projection = _apply_zero_sequence(net, case_norm, int(lv_tol_percent))

    target = str(bus).split(".")[0].lower()
    pp_bus = bus_map.get(target)
    if pp_bus is None:
        return {
            **base,
            "ok": False,
            "status": "BUS_NOT_FOUND",
            "issues": [{"code": "P4C07B001", "message": f"Bus no encontrado: {bus}"}],
            "inputs": {
                "source_projection": source_projection,
                "zero_sequence_projection": zero_projection,
                "line_temperature_projection": temperature_projection,
            },
        }

    try:
        pp.shortcircuit.calc_sc(
            net,
            bus=pp_bus,
            fault="1ph",
            case=case_norm,
            lv_tol_percent=int(lv_tol_percent),
            ip=False,
            ith=False,
        )
    except Exception as exc:
        return {
            **base,
            "ok": False,
            "status": "CALCULATION_ERROR",
            "issues": [{"code": "P4C07E001", "message": f"{type(exc).__name__}: {exc}"}],
            "inputs": {
                "source_projection": source_projection,
                "zero_sequence_projection": zero_projection,
                "line_temperature_projection": temperature_projection,
            },
        }

    row = net.res_bus_sc.loc[pp_bus]

    def value(name: str) -> float | None:
        raw = row.get(name)
        try:
            number = float(raw)
        except (TypeError, ValueError):
            return None
        return number if number == number else None

    return {
        **base,
        "ok": True,
        "status": "CALCULATED_EXPERIMENTAL",
        "bus": target,
        "inputs": {
            "source_projection": source_projection,
            "zero_sequence_projection": zero_projection,
            "line_temperature_projection": temperature_projection,
            "lv_tol_percent": int(lv_tol_percent),
        },
        "results": {
            "ikss_ka": value("ikss_ka"),
            "rk_ohm": value("rk_ohm"),
            "xk_ohm": value("xk_ohm"),
            "rk0_ohm": value("rk0_ohm"),
            "xk0_ohm": value("xk0_ohm"),
            "skss_mva": None,
            "ip_ka": None,
            "ith_ka": None,
        },
        "backend_raw": {
            "skss_mw": value("skss_mw"),
            "columns": [str(col) for col in net.res_bus_sc.columns],
        },
        "pandapower_version": getattr(pp, "__version__", None),
    }
