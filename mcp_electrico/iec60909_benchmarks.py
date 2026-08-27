"""Benchmarks independientes para el primer alcance P4 3F.

La referencia no usa pandapower ni OpenDSS para obtener el valor esperado.
Implementa directamente un circuito equivalente positivo de fuente + línea para
la falla trifásica mediante fuente de tensión equivalente.

Este benchmark valida P4B, pero NO cierra por sí solo P4C09: faltan benchmarks
para los demás alcances que P4-v1 finalmente admita.
"""

from __future__ import annotations

from math import hypot, sqrt
from typing import Any

from . import core, iec60909, professional_data, visual_state

SCHEMA = "MCP_ELECTRICO_P4_3PH_BENCHMARK_V1"

# Caso deliberadamente simple y auditable. Para el escenario min se fija
# endtemp=20 °C, por lo que el factor de corrección resistiva de la línea es 1.
CASE = {
    "id": "P4-3PH-RADIAL-22K9-LINE-01",
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
    "skss_mva_abs": 0.10,
    "rk_ohm_abs": 0.001,
    "xk_ohm_abs": 0.001,
}

REFERENCE_BASIS = {
    "method": "independent_positive_sequence_equivalent_voltage_source",
    "depends_on_pandapower": False,
    "depends_on_opendss": False,
    "equations": [
        "|ZQ| = c * Un^2 / Ssc",
        "R/X = 1 / (X/R)",
        "XQ = |ZQ| / sqrt(1 + (R/X)^2)",
        "RQ = (R/X) * XQ",
        "Zk = ZQ + Zline",
        "Ik'' = c * Un / (sqrt(3) * |Zk|)",
        "Sk'' = sqrt(3) * Un * Ik''",
    ],
    "voltage_factor_scope": "22.9 kV (>1 kV): cmax=1.10, cmin=1.00",
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
    ikss = (c * un / sqrt(3.0)) / zk
    skss = sqrt(3.0) * un * ikss

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
        "ikss_ka": ikss,
        "skss_mva": skss,
    }


def _prepare_model() -> None:
    core.crear_circuito("p4_benchmark_3ph", float(CASE["vn_kv"]))
    visual_state.reset()
    professional_data.reset()
    professional_data.definir_red_equivalente(
        kv_ll=float(CASE["vn_kv"]),
        scc_max_mva=float(CASE["source"]["max"]["scc_mva"]),
        x_r_max=float(CASE["source"]["max"]["x_r"]),
        scc_min_mva=float(CASE["source"]["min"]["scc_mva"]),
        x_r_min=float(CASE["source"]["min"]["x_r"]),
        fuente_referencia="P4 benchmark independiente: datos de entrada versionados",
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
    checks = {
        "ikss_ka": {
            "actual": float(values["ikss_ka"]),
            "reference": reference["ikss_ka"],
            "abs_error": abs(float(values["ikss_ka"]) - reference["ikss_ka"]),
            "tolerance": TOLERANCES["ikss_ka_abs"],
        },
        "skss_mva": {
            "actual": float(values["skss_mva"]),
            "reference": reference["skss_mva"],
            "abs_error": abs(float(values["skss_mva"]) - reference["skss_mva"]),
            "tolerance": TOLERANCES["skss_mva_abs"],
        },
        "rk_ohm": {
            "actual": float(values["rk_ohm"]),
            "reference": reference["rk_ohm"],
            "abs_error": abs(float(values["rk_ohm"]) - reference["rk_ohm"]),
            "tolerance": TOLERANCES["rk_ohm_abs"],
        },
        "xk_ohm": {
            "actual": float(values["xk_ohm"]),
            "reference": reference["xk_ohm"],
            "abs_error": abs(float(values["xk_ohm"]) - reference["xk_ohm"]),
            "tolerance": TOLERANCES["xk_ohm_abs"],
        },
    }
    for item in checks.values():
        item["pass"] = item["abs_error"] <= item["tolerance"]
    return {"pass": all(item["pass"] for item in checks.values()), "metrics": checks}


def run_case(case_name: str) -> dict[str, Any]:
    if case_name not in {"max", "min"}:
        raise ValueError("Benchmark P4 3F solo admite max/min.")
    _prepare_model()
    temperature = None
    if case_name == "min":
        temperature = {"Line.f1": float(CASE["line"]["endtemp_degree_c_min"])}
    actual = iec60909.ejecutar_3ph(case_name, str(CASE["fault_bus"]), temperature)
    if not actual.get("ok"):
        return {
            "case": case_name,
            "pass": False,
            "reference": solve_reference(case_name),
            "actual": actual,
            "comparison": None,
        }
    reference = solve_reference(case_name)
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
        "coverage": {"three_phase_max": True, "three_phase_min": True},
        "reference_basis": REFERENCE_BASIS,
        "tolerances": TOLERANCES,
        "cases": cases,
        "p4c09_complete": False,
        "professional_emission": False,
        "note": "P4C09A valida únicamente el alcance 3F max/min de P4B; P4C09 global permanece pendiente.",
    }
