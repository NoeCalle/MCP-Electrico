"""Benchmark independiente P4C07 para falla monofásica a tierra.

La referencia usa componentes simétricas y no toma el valor esperado de
pandapower ni de OpenDSS:

    If = 3 * E / (Z1 + Z2 + Z0)
       = sqrt(3) * c * Un / (2*Z1 + Z0)

dentro del alcance pasivo simétrico P4C07, con Z2=Z1 explícita.
"""

from __future__ import annotations

from math import hypot, sqrt
from typing import Any

from . import (
    core,
    iec60909_single_phase_ground,
    professional_data,
    visual_state,
    zero_sequence,
)

SCHEMA = "MCP_ELECTRICO_P4_1PH_GROUND_BENCHMARK_V1"
CASE = {
    "id": "P4-1PH-GROUND-RADIAL-22K9-LINE-01",
    "vn_kv": 22.9,
    "source": {
        "max": {
            "scc_mva": 500.0,
            "x_r": 10.0,
            "c": 1.10,
            "r0_ohm": 0.10,
            "x0_ohm": 0.35,
        },
        "min": {
            "scc_mva": 250.0,
            "x_r": 5.0,
            "c": 1.00,
            "r0_ohm": 0.20,
            "x0_ohm": 0.70,
        },
    },
    "line": {
        "name": "f1",
        "length_km": 0.25,
        "r1_ohm_per_km": 0.18,
        "x1_ohm_per_km": 0.09,
        "r0_ohm_per_km": 0.55,
        "x0_ohm_per_km": 0.22,
        "c0_nf_per_km": 0.0,
        "endtemp_degree_c_min": 20.0,
    },
    "fault_bus": "bus1",
}

TOLERANCES = {
    "ikss_ka_abs": 0.003,
    "rk_ohm_abs": 0.001,
    "xk_ohm_abs": 0.001,
    "rk0_ohm_abs": 0.001,
    "xk0_ohm_abs": 0.001,
}

REFERENCE_BASIS = {
    "method": "independent_symmetrical_components_single_phase_ground",
    "depends_on_pandapower": False,
    "depends_on_opendss": False,
    "negative_sequence_policy": "Z2 = Z1 only for the symmetric-passive P4C07 scope",
    "equations": [
        "|Z1_source| = c * Un^2 / Ssc",
        "R1/X1 = 1 / (X/R)",
        "Z1 = Z1_source + Z1_line",
        "Z2 = Z1",
        "Z0 = Z0_source(explicit) + Z0_line(explicit)",
        "Ik''_1F-T = sqrt(3) * c * Un / |2*Z1 + Z0|",
    ],
    "line_minimum_temperature": "20 °C explícitos; K_L=1 para R1 y R0 en este benchmark",
    "line_zero_capacitance": "C0=0 nF/km explícito en el fixture para aislar el contraste de impedancias serie",
}


def solve_reference(case_name: str) -> dict[str, float]:
    scenario = CASE["source"][case_name]
    line = CASE["line"]
    un = float(CASE["vn_kv"])
    c = float(scenario["c"])
    scc = float(scenario["scc_mva"])
    x_r = float(scenario["x_r"])

    r_x = 1.0 / x_r
    z1_source = c * un**2 / scc
    x1_source = z1_source / sqrt(1.0 + r_x**2)
    r1_source = r_x * x1_source

    length = float(line["length_km"])
    r1_line = float(line["r1_ohm_per_km"]) * length
    x1_line = float(line["x1_ohm_per_km"]) * length
    r0_line = float(line["r0_ohm_per_km"]) * length
    x0_line = float(line["x0_ohm_per_km"]) * length

    r1 = r1_source + r1_line
    x1 = x1_source + x1_line
    r0 = float(scenario["r0_ohm"]) + r0_line
    x0 = float(scenario["x0_ohm"]) + x0_line

    denominator_r = 2.0 * r1 + r0
    denominator_x = 2.0 * x1 + x0
    denominator = hypot(denominator_r, denominator_x)
    ikss = sqrt(3.0) * c * un / denominator

    return {
        "r_x_source": r_x,
        "r1_source_ohm": r1_source,
        "x1_source_ohm": x1_source,
        "rk_ohm": r1,
        "xk_ohm": x1,
        "rk0_ohm": r0,
        "xk0_ohm": x0,
        "denominator_ohm": denominator,
        "ikss_ka": ikss,
    }


def _prepare_model() -> None:
    core.crear_circuito("p4_benchmark_1ph_ground", float(CASE["vn_kv"]))
    visual_state.reset()
    professional_data.reset()
    zero_sequence.reset()

    professional_data.definir_red_equivalente(
        kv_ll=float(CASE["vn_kv"]),
        scc_max_mva=float(CASE["source"]["max"]["scc_mva"]),
        x_r_max=float(CASE["source"]["max"]["x_r"]),
        scc_min_mva=float(CASE["source"]["min"]["scc_mva"]),
        x_r_min=float(CASE["source"]["min"]["x_r"]),
        fuente_referencia="P4C07 benchmark independiente 1F-T: entrada versionada",
    )
    zero_sequence.definir_fuente(
        r0_max_ohm=float(CASE["source"]["max"]["r0_ohm"]),
        x0_max_ohm=float(CASE["source"]["max"]["x0_ohm"]),
        r0_min_ohm=float(CASE["source"]["min"]["r0_ohm"]),
        x0_min_ohm=float(CASE["source"]["min"]["x0_ohm"]),
        fuente_referencia="P4C07 benchmark Z0 fuente",
    )

    line = CASE["line"]
    core.agregar_linea(
        str(line["name"]),
        "sourcebus",
        str(CASE["fault_bus"]),
        float(line["length_km"]),
        fases=3,
        r1_ohm_km=float(line["r1_ohm_per_km"]),
        x1_ohm_km=float(line["x1_ohm_per_km"]),
    )
    zero_sequence.definir_linea(
        str(line["name"]),
        r0_ohm_km=float(line["r0_ohm_per_km"]),
        x0_ohm_km=float(line["x0_ohm_per_km"]),
        c0_nf_km=float(line["c0_nf_per_km"]),
        fuente_referencia="P4C07 benchmark Z0 línea",
    )


def _compare(actual: dict[str, Any], reference: dict[str, float]) -> dict[str, Any]:
    values = actual["results"]
    checks: dict[str, Any] = {}
    for metric, tolerance_key in (
        ("ikss_ka", "ikss_ka_abs"),
        ("rk_ohm", "rk_ohm_abs"),
        ("xk_ohm", "xk_ohm_abs"),
        ("rk0_ohm", "rk0_ohm_abs"),
        ("xk0_ohm", "xk0_ohm_abs"),
    ):
        actual_value = float(values[metric])
        checks[metric] = {
            "actual": actual_value,
            "reference": reference[metric],
            "abs_error": abs(actual_value - reference[metric]),
            "tolerance": TOLERANCES[tolerance_key],
        }
        checks[metric]["pass"] = checks[metric]["abs_error"] <= checks[metric]["tolerance"]
    return {"pass": all(item["pass"] for item in checks.values()), "metrics": checks}


def run_case(case_name: str) -> dict[str, Any]:
    if case_name not in {"max", "min"}:
        raise ValueError("Benchmark P4 1F-T solo admite max/min.")
    _prepare_model()
    temperature = None
    if case_name == "min":
        temperature = {"Line.f1": float(CASE["line"]["endtemp_degree_c_min"])}
    actual = iec60909_single_phase_ground.ejecutar_1ph_ground(
        str(CASE["fault_bus"]),
        case_name,
        line_endtemp_degree_c=temperature,
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
    passed = all(item["pass"] for item in cases)
    return {
        "schema": SCHEMA,
        "id": CASE["id"],
        "pass": passed,
        "coverage": {
            "single_phase_ground_max": True,
            "single_phase_ground_min": True,
            "source_zero_sequence": True,
            "line_zero_sequence": True,
            "transformer_zero_sequence": False,
        },
        "reference_basis": REFERENCE_BASIS,
        "tolerances": TOLERANCES,
        "cases": cases,
        "p4c07_foundation_complete": passed,
        "p4c09_complete": False,
        "professional_emission": False,
        "note": (
            "El benchmark independiente valida la cadena fuente+línea 1F-T MAX/MIN y Z2=Z1 "
            "solo en el alcance simétrico pasivo. La proyección de transformadores se cubre "
            "con tests de integración separados; P4C09 global permanece pendiente."
        ),
    }
