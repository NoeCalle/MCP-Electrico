"""Motor numérico P4 para cortocircuito trifásico IEC 60909.

Alcance actual:
- IEC 60909 objetivo: IEC 60909-0:2026;
- backend candidato: pandapower 3.5.x;
- falla: trifásica (3ph) únicamente;
- escenarios: max/min;
- Ik'', Sk'' y, opcionalmente, ip/Ith;
- datos P2 de secuencia positiva;
- sin emisión profesional;
- sin afirmar todavía conformidad de edición 2026.

Para cálculo mínimo con líneas se exige `endtemp_degree` explícita por línea.
Para ip/Ith se exigen `topology` y `tk_s` explícitos. No se introduce un valor
oculto para ninguno de estos parámetros.
"""

from __future__ import annotations

from math import isfinite, sqrt
from typing import Any

import pandapower as pp
from pandapower.shortcircuit import calc_sc

from . import iec60909_contract, pandapower_engine, professional_data

CAPABILITIES = {
    "positive_sequence_adapter": True,
    "three_phase_max_min": True,
    "peak_thermal": True,
    "two_phase": False,
    "single_phase_ground": False,
    "two_phase_ground": False,
}

SUPPORTED_DUTY_TOPOLOGIES = {"radial", "meshed"}
SUPPORTED_KAPPA_METHODS = {"C"}


def _issue(code: str, message: str, element: str | None = None) -> dict[str, Any]:
    return {"code": code, "message": message, "element": element}


def _normalize_case(case: str) -> str:
    value = str(case or "").strip().lower()
    aliases = {
        "max": "max", "maximum": "max", "maximo": "max", "máximo": "max",
        "min": "min", "minimum": "min", "minimo": "min", "mínimo": "min",
    }
    if value not in aliases:
        raise ValueError("P4SC001: case debe ser 'max' o 'min'.")
    return aliases[value]


def _normalize_duty_request(
    calcular_ip_ith: bool,
    topology: str | None,
    tk_s: float | None,
    kappa_method: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not calcular_ip_ith:
        return {
            "requested": False,
            "topology": None,
            "tk_s": None,
            "kappa_method": None,
        }, []

    issues: list[dict[str, Any]] = []
    topology_value = str(topology or "").strip().lower()
    if topology_value not in SUPPORTED_DUTY_TOPOLOGIES:
        issues.append(_issue(
            "P4SC301",
            "ip/Ith exige topology explícita 'radial' o 'meshed'; no se acepta 'auto'.",
        ))

    try:
        tk_value = float(tk_s) if tk_s is not None else float("nan")
    except (TypeError, ValueError):
        tk_value = float("nan")
    if not isfinite(tk_value) or tk_value <= 0:
        issues.append(_issue("P4SC302", "ip/Ith exige tk_s finito y > 0 s."))

    kappa_value = str(kappa_method or "").strip().upper()
    if kappa_value not in SUPPORTED_KAPPA_METHODS:
        issues.append(_issue(
            "P4SC303",
            "P4C05 v1 admite únicamente kappa_method='C'; otros métodos requieren validación separada.",
        ))

    return {
        "requested": True,
        "topology": topology_value or None,
        "tk_s": tk_value if isfinite(tk_value) else None,
        "kappa_method": kappa_value or None,
    }, issues


def _source_projection(case: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    source = professional_data.obtener_red_equivalente()
    if not source:
        return None, [_issue("P4SC101", "Falta red equivalente P2.")]

    scenario = (source.get("scenarios") or {}).get(case)
    if not scenario:
        return None, [_issue("P4SC102", f"Falta escenario P2 '{case}'.")]

    scc = float(scenario.get("scc3_mva") or 0)
    x_r = float(scenario.get("x_r") or 0)
    if scc <= 0 or x_r <= 0:
        return None, [_issue("P4SC103", f"Escenario {case} requiere Scc3>0 y X/R>0.")]

    provenance = source.get("provenance") or {}
    ref_key = "scc_max_mva" if case == "max" else "scc_min_mva"
    ref = (provenance.get(ref_key) or {}).get("reference")
    if not ref:
        return None, [_issue("P4SC104", f"Escenario {case} no tiene procedencia P2 de Scc3.")]

    rx = 1.0 / x_r
    return {
        "case": case,
        "kv_ll": float(source.get("kv_ll") or 0),
        "scc3_mva": scc,
        "x_r": x_r,
        "r_x_pandapower": rx,
        "mapping": "rx = 1 / (X/R)",
        "reference": ref,
    }, []


def _line_temperature_map(
    model: dict[str, Any],
    case: str,
    line_endtemp_degree_c: dict[str, float] | None,
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    if case != "min" or not model.get("lines"):
        return {}, []

    supplied = {
        str(k).strip().lower(): float(v)
        for k, v in (line_endtemp_degree_c or {}).items()
    }
    normalized: dict[str, float] = {}
    issues: list[dict[str, Any]] = []
    for line in model["lines"]:
        full = str(line["id"])
        candidates = {
            full.lower(),
            str(line["name"]).lower(),
            f"line.{line['name']}".lower(),
        }
        value = next((supplied[key] for key in candidates if key in supplied), None)
        if value is None:
            issues.append(_issue(
                "P4SC201",
                "Cálculo mínimo exige endtemp_degree explícita por línea; no se asume temperatura final.",
                full,
            ))
            continue
        if not isfinite(value) or value < 20.0:
            issues.append(_issue(
                "P4SC202",
                "endtemp_degree debe ser finita y >=20 °C.",
                full,
            ))
            continue
        normalized[full.lower()] = float(value)
    return normalized, issues


def evaluar_preparacion_3ph(
    case: str,
    bus: str,
    line_endtemp_degree_c: dict[str, float] | None = None,
    calcular_ip_ith: bool = False,
    topology: str | None = None,
    tk_s: float | None = None,
    kappa_method: str = "C",
) -> dict[str, Any]:
    try:
        normalized_case = _normalize_case(case)
    except ValueError as exc:
        return {"ready": False, "issues": [_issue("P4SC001", str(exc))]}

    compatibility = pandapower_engine.evaluar_compatibilidad()
    issues: list[dict[str, Any]] = []
    if not compatibility.get("compatible"):
        issues.extend(compatibility.get("issues") or [])

    model = pandapower_engine._collect_active_model()
    names = {str(item.get("name") or "").lower() for item in model.get("buses", [])}
    if str(bus or "").strip().lower() not in names:
        issues.append(_issue("P4SC002", f"Bus de falla no encontrado: {bus}"))

    source_projection, source_issues = _source_projection(normalized_case)
    issues.extend(source_issues)
    temperatures, temperature_issues = _line_temperature_map(
        model, normalized_case, line_endtemp_degree_c
    )
    issues.extend(temperature_issues)

    duty, duty_issues = _normalize_duty_request(
        calcular_ip_ith, topology, tk_s, kappa_method
    )
    issues.extend(duty_issues)

    return {
        "ready": not issues,
        "case": normalized_case,
        "bus": str(bus),
        "issues": issues,
        "source_projection": source_projection,
        "line_endtemp_degree_c": temperatures,
        "duty": duty,
        "pandapower_compatibility": compatibility,
    }


def _set_source_short_circuit(net, projection: dict[str, Any]) -> None:
    idx = net.ext_grid.index[0]
    case = projection["case"]
    net.ext_grid.at[idx, f"s_sc_{case}_mva"] = projection["scc3_mva"]
    net.ext_grid.at[idx, f"rx_{case}"] = projection["r_x_pandapower"]


def _set_min_line_temperatures(
    net,
    line_meta: dict[int, dict[str, Any]],
    temperatures: dict[str, float],
) -> None:
    for idx, meta in line_meta.items():
        key = str(meta["id"]).lower()
        net.line.at[idx, "endtemp_degree"] = temperatures[key]


def ejecutar_3ph(
    case: str,
    bus: str,
    line_endtemp_degree_c: dict[str, float] | None = None,
    calcular_ip_ith: bool = False,
    topology: str | None = None,
    tk_s: float | None = None,
    kappa_method: str = "C",
) -> dict[str, Any]:
    prep = evaluar_preparacion_3ph(
        case,
        bus,
        line_endtemp_degree_c,
        calcular_ip_ith=calcular_ip_ith,
        topology=topology,
        tk_s=tk_s,
        kappa_method=kappa_method,
    )
    contract = iec60909_contract.obtener_contrato_p4()
    if not prep["ready"]:
        return {
            "schema": "MCP_ELECTRICO_IEC60909_3PH_V1",
            "ok": False,
            "study": "iec60909",
            "fault": "3ph",
            "case": prep.get("case"),
            "bus": str(bus),
            "issues": prep["issues"],
            "requested_duty": prep.get("duty"),
            "engine": contract["backend"],
            "target_standard": contract["target_standard"],
            "professional_emission": False,
        }

    model = pandapower_engine._collect_active_model()
    net, line_meta, _trafo_meta = pandapower_engine._build_net(model)
    _set_source_short_circuit(net, prep["source_projection"])
    if prep["case"] == "min":
        _set_min_line_temperatures(net, line_meta, prep["line_endtemp_degree_c"])

    bus_idx = next(
        int(idx)
        for idx, row in net.bus.iterrows()
        if str(row["name"]).lower() == str(bus).strip().lower()
    )

    duty = prep["duty"]
    calc_kwargs: dict[str, Any] = {
        "bus": bus_idx,
        "fault": "3ph",
        "case": prep["case"],
        "ip": bool(duty["requested"]),
        "ith": bool(duty["requested"]),
        "branch_results": False,
        "check_connectivity": True,
        "use_pre_fault_voltage": False,
    }
    if duty["requested"]:
        calc_kwargs.update({
            "topology": duty["topology"],
            "tk_s": duty["tk_s"],
            "kappa_method": duty["kappa_method"],
        })

    try:
        calc_sc(net, **calc_kwargs)
    except Exception as exc:
        return {
            "schema": "MCP_ELECTRICO_IEC60909_3PH_V1",
            "ok": False,
            "study": "iec60909",
            "fault": "3ph",
            "case": prep["case"],
            "bus": str(bus),
            "issues": [_issue("P4SC900", f"{type(exc).__name__}: {exc}")],
            "requested_duty": duty,
            "engine": contract["backend"],
            "target_standard": contract["target_standard"],
            "professional_emission": False,
        }

    row = net.res_bus_sc.loc[bus_idx]
    ikss_ka = float(row["ikss_ka"])
    vn_kv = float(net.bus.at[bus_idx, "vn_kv"])
    skss_mva = sqrt(3.0) * vn_kv * ikss_ka
    backend_skss = float(row["skss_mw"])
    skss_abs_error = abs(skss_mva - backend_skss)

    results: dict[str, float] = {
        "ikss_ka": ikss_ka,
        "skss_mva": skss_mva,
        "rk_ohm": float(row["rk_ohm"]),
        "xk_ohm": float(row["xk_ohm"]),
    }
    if duty["requested"]:
        results["ip_ka"] = float(row["ip_ka"])
        results["ith_ka"] = float(row["ith_ka"])

    return {
        "schema": "MCP_ELECTRICO_IEC60909_3PH_V1",
        "ok": True,
        "study": "iec60909",
        "fault": "3ph",
        "case": prep["case"],
        "bus": str(net.bus.at[bus_idx, "name"]),
        "vn_kv": vn_kv,
        "results": results,
        "backend_raw": {
            "skss_field": "skss_mw",
            "skss_value": backend_skss,
            "skss_vs_mcp_abs_error": skss_abs_error,
        },
        "input_projection": {
            "source": prep["source_projection"],
            "line_endtemp_degree_c": prep["line_endtemp_degree_c"],
            "duty": duty,
        },
        "engine": {
            **contract["backend"],
            "engine_version_runtime": pp.__version__,
        },
        "target_standard": contract["target_standard"],
        "maturity": "EXPERIMENTAL_P4",
        "professional_emission": False,
        "limitations": [
            "Solo falla trifásica 3F en el alcance numérico actual.",
            "La conformidad específica con IEC 60909-0:2026 permanece sin verificar.",
            "Ib e Ik todavía no se calculan.",
            "ip/Ith P4C05 se limitan a kappa_method C y requieren topology/tk_s explícitos.",
        ],
    }
