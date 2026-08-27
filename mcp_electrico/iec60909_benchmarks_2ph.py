"""Benchmark independiente P4C06 para falla bifásica fase-fase.

La referencia no usa pandapower ni OpenDSS para obtener el valor esperado.
Resuelve por componentes simétricas el caso P4C06 v1 con Z2=Z1 explícito:

    I1 = E / (Z1 + Z2)
    |I_2F| = sqrt(3) |I1| = c Un / |Z1 + Z2|

Con Z2=Z1 resulta |I_2F| = c Un / (2 |Z1|).
"""

from __future__ import annotations

from math import hypot, sqrt
from typing import Any

from . import core, iec60909_two_phase, professional_data, visual_state

SCHEMA = "MCP_ELECTRICO_P4_2PH_BENCHMARK_V1"
CASE = {
    "id": "P4-2PH-RADIAL-22K9-LINE-01",
    "vn_kv": 22.9,
    "source": {
        "max": {"scc_mva": 500.0, "x_r": 10.0, "c": 1.10},
        "min": {"scc_mva": 250.0, "x_r": 5.0, "c": 1.00},
    },
    "line": {
        "name": "f1",
        "length_km": 0.25,
        "r_ohm_per_km": 0.18,
        "x_ohm_per_km": 0.09,
        "endtemp_degree_c_min": 20.0,
    },
    "fault_bus": "bus1",
}

TOLERANCES = {
    "ikss_ka_abs": 0.002,
    "rk_ohm_abs": 0.001,
    "xk_ohm_abs": 0.001,
}

REFERENCE_BASIS = {
    "method": "independent_symmetrical_components_two_phase",
    "depends_on_pandapower": False,
    "depends_on_opendss": False,
    "negative_sequence_policy": "Z2 = Z1 for the explicit symmetric-passive P4C06 scope",
    "equations": [
        "|ZQ| = c * Un^2 / Ssc",
        "R/X = 1 / (X/R)",
        "Z1 = ZQ + Zline",
        "Z2 = Z1",
        "I1 = (c*Un/sqrt(3)) / (Z1 + Z2)",
        "Ik''_2F = sqrt(3) * |I1| = c*Un / (2*|Z1|)",
    ],
    "line_minimum_temperature": "20 °C explícitos; K_L=1 en este benchmark",
}


def solve_reference(case_name: str) -> dict[str, float]:
    scenario = CASE["source"][case_name]
    line = CASE["line"]
    un = float(CASE["vn_kv"])
    c = float(scenario["c"])
    scc = float(scenario["scc_mva"])
    x_r = float(scenario["x_r"])

    r_x = 1.0 / x_r
    zq = c * un**2 / scc
    xq = zq / sqrt(1.0 + r_x**2)
    rq = r_x * xq
    rline = float(line["r_ohm_per_km"]) * float(line["length_km"])
    xline = float(line["x_ohm_per_km"]) * float(line["length_km"])
    rk = rq + rline
    xk = xq + xline
    zk = hypot(rk, xk)
    ikss_2ph = c * un / (2.0 * zk)
    ikss_3ph_reference = (c * un / sqrt(3.0)) / zk

    return {
        "r_x_source": r_x,
        "zq_ohm": zq,
        "rq_ohm": rq,
        "xq_ohm": xq,
        "rline_ohm": rline,
        "xline_ohm": xline,
        "rk_ohm": rk,
        "xk_ohm": xk,
        "zk_ohm": zk,
        "ikss_ka": ikss_2ph,
        "ikss_3ph_reference_ka": ikss_3ph_reference,
        "ratio_2ph_to_3ph": ikss_2ph / ikss_3ph_reference,
    }


def _prepare_model() -> None:
    core.crear_circuito("p4_benchmark_2ph", float(CASE["vn_kv"]))
    visual_state.reset()
    professional_data.reset()
    professional_data.definir_red_equivalente(
        kv_ll=float(CASE["vn_kv"]),
        scc_max_mva=float(CASE["source"]["max"]["scc_mva"]),
        x_r_max=float(CASE["source"]["max"]["x_r"]),
        scc_min_mva=float(CASE["source"]["min"]["scc_mva"]),
        x_r_min=float(CASE["source"]["min"]["x_r"]),
        fuente_referencia="P4C06 benchmark independiente 2F: datos de entrada versionados",
    )
    line = CASE["line"]
    core.agregar_linea(
        str(line["name"]),
        "sourcebus",
        str(CASE["fault_bus"]),
        float(line["length_km"]),
        fases=3,
        r1_ohm_km=float(line["r_ohm_per_km"]),
        x1_ohm_km=float(line["x_ohm_per_km"]),
    )


def _compare(actual: dict[str, Any], reference: dict[str, float]) -> dict[str, Any]:
    values = actual["results"]
    checks = {}
    for metric, tolerance_key in (
        ("ikss_ka", "ikss_ka_abs"),
        ("rk_ohm", "rk_ohm_abs"),
        ("xk_ohm", "xk_ohm_abs"),
    ):
        checks[metric] = {
            "actual": float(values[metric]),
            "reference": reference[metric],
            "abs_error": abs(float(values[metric]) - reference[metric]),
            "tolerance": TOLERANCES[tolerance_key],
        }
        checks[metric]["pass"] = checks[metric]["abs_error"] <= checks[metric]["tolerance"]
    return {"pass": all(item["pass"] for item in checks.values()), "metrics": checks}


def run_case(case_name: str) -> dict[str, Any]:
    if case_name not in {"max", "min"}:
        raise ValueError("Benchmark P4 2F solo admite max/min.")
    _prepare_model()
    temperature = None
    if case_name == "min":
        temperature = {"Line.f1": float(CASE["line"]["endtemp_degree_c_min"])}
    actual = iec60909_two_phase.ejecutar_2ph(
        case_name, str(CASE["fault_bus"]), temperature
    )
    reference = solve_reference(case_name)
    if not actual.get("ok"):
        return {
            "case": case_name,
            "pass": False,
            "reference": reference,
            "actual": actual,
            "comparison": None,
        }
    comparison = _compare(actual, reference)
    return {
        "case": case_name,
        "pass": comparison["pass"],
        "reference": reference,
        "actual": actual,
        "comparison": comparison,
    }


def run_suite() -> dict[str, Any]:
    cases = [run_case("max"), run_case("min")]
    return {
        "schema": SCHEMA,
        "id": CASE["id"],
        "pass": all(item["pass"] for item in cases),
        "coverage": {"two_phase_max": True, "two_phase_min": True},
        "reference_basis": REFERENCE_BASIS,
        "tolerances": TOLERANCES,
        "cases": cases,
        "p4c06_complete": all(item["pass"] for item in cases),
        "p4c09_complete": False,
        "professional_emission": False,
        "note": "Este benchmark independiente cierra P4C06 2F max/min dentro del alcance Z2=Z1 declarado; P4C09 global permanece pendiente.",
    }
