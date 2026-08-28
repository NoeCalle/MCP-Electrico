"""P4-v1.1B — falla bifásica a tierra sobre el modelo activo.

Pandapower 3.5.4 no ofrece ``fault=2ph_ground``. Este módulo lo usa únicamente
para construir el modelo IEC 60909 ya trazable y obtener las impedancias
Thevenin Z1/Z0 de la barra. La falla b-c-tierra franca se resuelve después con
el solver MCP auditado de componentes simétricas.

Alcance operativo deliberado:
- falla b-c-tierra franca, Zf = 0;
- red simétrica pasiva soportada por P4, con Z2 = Z1 explícito;
- Z0 explícita/proyectable de fuente, líneas y transformadores;
- escenarios MAX/MIN; MIN mantiene endtemp_degree explícita por línea;
- sin generadores, motores, convertidores ni modelos asimétricos;
- sin promoción normativa de Ik'', Sk'', ip o Ith 2F-T;
- professional_emission = false.
"""

from __future__ import annotations

from copy import deepcopy
from math import sqrt
from typing import Any

import pandapower as pp

from . import (
    iec60909,
    iec60909_contract,
    iec60909_single_phase_ground,
    iec60909_two_phase_ground_foundation,
    pandapower_engine,
)

SCHEMA = "MCP_ELECTRICO_IEC60909_2PH_GROUND_OPERATIONAL_V1"


def _issue(code: str, message: str, element: str | None = None) -> dict[str, Any]:
    return {"code": code, "message": message, "element": element}


def _value(row, name: str) -> float | None:
    raw = row.get(name)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if value == value else None


def _find_bus(net, bus: str) -> int | None:
    target = str(bus or "").strip()
    if target.lower().startswith("bus."):
        target = target[4:]
    matches = [
        int(idx)
        for idx, row in net.bus.iterrows()
        if str(row["name"]).lower() == target.lower()
    ]
    return matches[0] if matches else None


def ejecutar_2ph_ground(
    bus: str,
    case: str = "max",
    *,
    line_endtemp_degree_c: dict[str, float] | None = None,
    lv_tol_percent: int = 10,
) -> dict[str, Any]:
    """Ejecuta 2F-T franca MAX/MIN sobre Z1/Z0 del modelo P4.

    ``ikss_ka`` se expone como valor numérico operativo igual a la mayor
    corriente RMS de las dos fases en falla. ``ikss_contractual`` permanece
    False hasta cerrar la revisión normativa registrada en
    ``docs/VALIDACIONES_PENDIENTES.md``.
    """
    case_norm = iec60909._normalize_case(case)
    compatibility = pandapower_engine.evaluar_compatibilidad()
    base = {
        "schema": SCHEMA,
        "study": "IEC60909_SHORT_CIRCUIT_OPERATIONAL_EXTENSION",
        "fault": "2PH_GROUND",
        "fault_type": "two_phase_ground",
        "case": case_norm,
        "engine": "mcp_sequence_solver",
        "sequence_impedance_backend": "pandapower",
        "target_standard": deepcopy(iec60909_contract.TARGET_STANDARD),
        "target_edition_conformance": iec60909_contract.BACKEND[
            "target_edition_conformance"
        ],
        "maturity": "USABLE_WITH_DECLARED_SCOPE",
        "professional_emission": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "limitations": [
            "Falla 2F-T franca b-c-tierra, Zf=0.",
            "Z2=Z1 solo para la red simétrica pasiva soportada; no es un supuesto universal.",
            "Pandapower se usa para Z1/Z0; no existe ni se simula un token pandapower 2ph_ground.",
            "La magnitud ikss_ka es un valor operativo de corriente de fase máxima y todavía no una promoción contractual IEC.",
            "Sk'', ip e Ith 2F-T permanecen fail-closed.",
            "Validación contra IEC 60909-0:2026 completa y caso externo permanecen pendientes.",
        ],
    }
    if not compatibility.get("compatible"):
        return {
            **base,
            "ok": False,
            "status": "NOT_COMPATIBLE",
            "issues": deepcopy(compatibility.get("issues", [])),
        }

    model = pandapower_engine._collect_active_model()
    if not model.get("source"):
        return {
            **base,
            "ok": False,
            "status": "MISSING_SOURCE_DATA",
            "issues": [_issue("P4V11B001", "Falta red equivalente P2.")],
        }

    source_projection, source_issues = iec60909._source_projection(case_norm)
    if source_issues or not source_projection:
        return {
            **base,
            "ok": False,
            "status": "MISSING_SOURCE_DATA",
            "issues": deepcopy(source_issues),
        }

    temperatures, temperature_issues = iec60909._line_temperature_map(
        model, case_norm, line_endtemp_degree_c
    )
    if temperature_issues:
        return {
            **base,
            "ok": False,
            "status": "MISSING_LINE_TEMPERATURE",
            "issues": deepcopy(temperature_issues),
            "inputs": {"source_projection": source_projection},
        }

    try:
        net, line_meta, _trafo_meta = pandapower_engine._build_net(model)
        iec60909._set_source_short_circuit(net, source_projection)
        if case_norm == "min":
            iec60909._set_min_line_temperatures(net, line_meta, temperatures)
        zero_projection = iec60909_single_phase_ground._apply_zero_sequence(
            net, case_norm, int(lv_tol_percent)
        )
    except (ValueError, KeyError) as exc:
        return {
            **base,
            "ok": False,
            "status": "PREPARATION_BLOCKED",
            "issues": [_issue("P4V11B002", str(exc))],
        }

    pp_bus = _find_bus(net, bus)
    if pp_bus is None:
        return {
            **base,
            "ok": False,
            "status": "BUS_NOT_FOUND",
            "issues": [_issue("P4V11B003", f"Bus no encontrado: {bus}")],
            "inputs": {
                "source_projection": source_projection,
                "zero_sequence_projection": zero_projection,
                "line_temperature_projection": temperatures,
            },
        }

    try:
        # Se usa la ruta 1ph exclusivamente para obtener Z1/Z0 equivalentes
        # que pandapower deja en res_bus_sc. Su corriente 1F-T NO se reutiliza.
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
            "status": "SEQUENCE_IMPEDANCE_EXTRACTION_ERROR",
            "issues": [_issue("P4V11B004", f"{type(exc).__name__}: {exc}")],
            "inputs": {
                "source_projection": source_projection,
                "zero_sequence_projection": zero_projection,
                "line_temperature_projection": temperatures,
            },
        }

    row = net.res_bus_sc.loc[pp_bus]
    r1 = _value(row, "rk_ohm")
    x1 = _value(row, "xk_ohm")
    r0 = _value(row, "rk0_ohm")
    x0 = _value(row, "xk0_ohm")
    if None in (r1, x1, r0, x0):
        return {
            **base,
            "ok": False,
            "status": "SEQUENCE_IMPEDANCE_NOT_AVAILABLE",
            "issues": [
                _issue(
                    "P4V11B005",
                    "El backend no devolvió Rk/Xk/Rk0/Xk0 completos en la barra.",
                )
            ],
        }

    vn_kv = float(net.bus.at[pp_bus, "vn_kv"])
    c = iec60909_single_phase_ground._voltage_factor(
        vn_kv, case_norm, int(lv_tol_percent)
    )
    e1_v = c * vn_kv * 1000.0 / sqrt(3.0)

    try:
        solved = iec60909_two_phase_ground_foundation.resolver_2ph_ground_bolted(
            e1_v=e1_v,
            r1_ohm=float(r1),
            x1_ohm=float(x1),
            r0_ohm=float(r0),
            x0_ohm=float(x0),
        )
    except ValueError as exc:
        return {
            **base,
            "ok": False,
            "status": "FOUNDATION_BLOCKED",
            "issues": [_issue("P4V11B006", str(exc))],
        }

    phases = solved["phase_currents_a"]
    sequences = solved["sequence_currents_a"]
    max_phase_ka = float(phases["max_faulted_phase_current_a"]) / 1000.0
    return {
        **base,
        "ok": True,
        "status": "CALCULATED_USABLE_WITH_DECLARED_SCOPE",
        "bus": str(net.bus.at[pp_bus, "name"]),
        "inputs": {
            "source_projection": source_projection,
            "zero_sequence_projection": zero_projection,
            "line_temperature_projection": temperatures,
            "lv_tol_percent": int(lv_tol_percent),
            "vn_kv": vn_kv,
            "voltage_factor_c": c,
            "e1_v": e1_v,
            "sequence_thevenin": {
                "r1_ohm": float(r1),
                "x1_ohm": float(x1),
                "r2_ohm": float(r1),
                "x2_ohm": float(x1),
                "r0_ohm": float(r0),
                "x0_ohm": float(x0),
                "z2_relation": "Z2 = Z1",
            },
            "sequence_impedance_extraction": {
                "backend": "pandapower",
                "backend_fault_used_only_for_impedance_extraction": "1ph",
                "backend_fault_current_consumed": False,
            },
        },
        "results": {
            "ikss_ka": max_phase_ka,
            "ib_ka": float(phases["ib"]["magnitude"]) / 1000.0,
            "ic_ka": float(phases["ic"]["magnitude"]) / 1000.0,
            "ground_current_ka": float(phases["ground_sum"]["magnitude"]) / 1000.0,
            "i0_ka": float(sequences["i0"]["magnitude"]) / 1000.0,
            "i1_ka": float(sequences["i1"]["magnitude"]) / 1000.0,
            "i2_ka": float(sequences["i2"]["magnitude"]) / 1000.0,
            "rk_ohm": float(r1),
            "xk_ohm": float(x1),
            "rk0_ohm": float(r0),
            "xk0_ohm": float(x0),
            "skss_mva": None,
            "ip_ka": None,
            "ith_ka": None,
        },
        "foundation": solved,
        "result_promotion": {
            "ikss_contractual": False,
            "skss_contractual": False,
            "ip_ith": False,
            "operational_current_field": "results.ikss_ka",
            "operational_current_semantics": "max_faulted_phase_rms_current",
            "pending_validation_ids": ["VP-IEC-01", "VP-2FT-01", "VP-2FT-02", "VP-2FT-03"],
        },
        "pandapower_version": getattr(pp, "__version__", None),
    }
