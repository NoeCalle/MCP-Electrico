"""Motor numérico P4C06 para cortocircuito bifásico IEC 60909.

Alcance P4C06 v1:
- falla fase-fase sin tierra (2ph);
- escenarios max/min;
- Ik'' y, opcionalmente, ip/Ith;
- misma proyección P2 de secuencia positiva usada por P4 3F;
- red simétrica pasiva sin generadores/motores en el alcance pandapower vigente;
- política explícita Z2 = Z1 dentro de ese alcance restringido;
- sin emisión profesional y sin afirmar conformidad IEC 60909-0:2026.

La igualdad Z2=Z1 NO se presenta como regla universal. Es una política explícita
limitada al modelo simétrico pasivo actualmente aceptado por MCP Eléctrico.
"""

from __future__ import annotations

from typing import Any

import pandapower as pp
from pandapower.shortcircuit import calc_sc

from . import iec60909, iec60909_contract, pandapower_engine

SCHEMA = "MCP_ELECTRICO_IEC60909_2PH_V1"
NEGATIVE_SEQUENCE_POLICY = {
    "id": "P4C06_Z2_EQUALS_Z1_SYMMETRIC_PASSIVE_SCOPE",
    "z2_relation": "Z2 = Z1",
    "explicit": True,
    "scope": "red simétrica pasiva aceptada por pandapower_engine; sin generadores ni motores",
    "universal_assumption": False,
}


def evaluar_preparacion_2ph(
    case: str,
    bus: str,
    line_endtemp_degree_c: dict[str, float] | None = None,
    calcular_ip_ith: bool = False,
    topology: str | None = None,
    tk_s: float | None = None,
    kappa_method: str = "C",
) -> dict[str, Any]:
    try:
        normalized_case = iec60909._normalize_case(case)
    except ValueError as exc:
        return {"ready": False, "issues": [iec60909._issue("P4SC001", str(exc))]}

    compatibility = pandapower_engine.evaluar_compatibilidad()
    issues: list[dict[str, Any]] = []
    if not compatibility.get("compatible"):
        issues.extend(compatibility.get("issues") or [])

    model = pandapower_engine._collect_active_model()
    names = {str(item.get("name") or "").lower() for item in model.get("buses", [])}
    if str(bus or "").strip().lower() not in names:
        issues.append(iec60909._issue("P4SC002", f"Bus de falla no encontrado: {bus}"))

    source_projection, source_issues = iec60909._source_projection(normalized_case)
    issues.extend(source_issues)
    temperatures, temperature_issues = iec60909._line_temperature_map(
        model, normalized_case, line_endtemp_degree_c
    )
    issues.extend(temperature_issues)

    duty, duty_issues = iec60909._normalize_duty_request(
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
        "negative_sequence_policy": dict(NEGATIVE_SEQUENCE_POLICY),
        "pandapower_compatibility": compatibility,
    }


def ejecutar_2ph(
    case: str,
    bus: str,
    line_endtemp_degree_c: dict[str, float] | None = None,
    calcular_ip_ith: bool = False,
    topology: str | None = None,
    tk_s: float | None = None,
    kappa_method: str = "C",
) -> dict[str, Any]:
    prep = evaluar_preparacion_2ph(
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
            "schema": SCHEMA,
            "ok": False,
            "study": "iec60909",
            "fault": "2ph",
            "case": prep.get("case"),
            "bus": str(bus),
            "issues": prep["issues"],
            "requested_duty": prep.get("duty"),
            "negative_sequence_policy": prep.get("negative_sequence_policy"),
            "engine": contract["backend"],
            "target_standard": contract["target_standard"],
            "professional_emission": False,
        }

    model = pandapower_engine._collect_active_model()
    net, line_meta, _trafo_meta = pandapower_engine._build_net(model)
    iec60909._set_source_short_circuit(net, prep["source_projection"])
    if prep["case"] == "min":
        iec60909._set_min_line_temperatures(net, line_meta, prep["line_endtemp_degree_c"])

    bus_idx = next(
        int(idx)
        for idx, row in net.bus.iterrows()
        if str(row["name"]).lower() == str(bus).strip().lower()
    )

    duty = prep["duty"]
    calc_kwargs: dict[str, Any] = {
        "bus": bus_idx,
        "fault": "2ph",
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
            "schema": SCHEMA,
            "ok": False,
            "study": "iec60909",
            "fault": "2ph",
            "case": prep["case"],
            "bus": str(bus),
            "issues": [iec60909._issue("P4SC920", f"{type(exc).__name__}: {exc}")],
            "requested_duty": duty,
            "negative_sequence_policy": prep["negative_sequence_policy"],
            "engine": contract["backend"],
            "target_standard": contract["target_standard"],
            "professional_emission": False,
        }

    row = net.res_bus_sc.loc[bus_idx]
    results: dict[str, float] = {
        "ikss_ka": float(row["ikss_ka"]),
        "rk_ohm": float(row["rk_ohm"]),
        "xk_ohm": float(row["xk_ohm"]),
    }
    if duty["requested"]:
        results["ip_ka"] = float(row["ip_ka"])
        results["ith_ka"] = float(row["ith_ka"])

    backend_skss = float(row["skss_mw"]) if "skss_mw" in row.index else None

    return {
        "schema": SCHEMA,
        "ok": True,
        "study": "iec60909",
        "fault": "2ph",
        "case": prep["case"],
        "bus": str(net.bus.at[bus_idx, "name"]),
        "vn_kv": float(net.bus.at[bus_idx, "vn_kv"]),
        "results": results,
        "backend_raw": {
            "skss_field": "skss_mw" if backend_skss is not None else None,
            "skss_value": backend_skss,
            "note": "P4C06 no promueve skss_mw a Sk'' normalizado para 2F; el gate se basa en Ik'' y Zk.",
        },
        "input_projection": {
            "source": prep["source_projection"],
            "line_endtemp_degree_c": prep["line_endtemp_degree_c"],
            "duty": duty,
            "negative_sequence_policy": prep["negative_sequence_policy"],
        },
        "engine": {
            **contract["backend"],
            "engine_version_runtime": pp.__version__,
        },
        "target_standard": contract["target_standard"],
        "maturity": "EXPERIMENTAL_P4",
        "professional_emission": False,
        "limitations": [
            "Solo falla bifásica fase-fase sin tierra en este payload.",
            "Z2=Z1 se declara únicamente para el alcance de red simétrica pasiva P4C06 v1.",
            "La conformidad específica con IEC 60909-0:2026 permanece sin verificar.",
            "Sk'' no se normaliza ni usa como criterio de aceptación 2F en P4C06.",
            "ip/Ith se limitan a kappa_method C y requieren topology/tk_s explícitos.",
        ],
    }
