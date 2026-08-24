"""Benchmarks independientes para flujo de potencia y caída de tensión.

La referencia NO usa resultados de OpenDSS. Resuelve un sistema balanceado
de dos barras por fase con carga PQ constante mediante iteración compleja:

    I = conj(S_phase / V_r)
    V_r = V_s - Z_line * I

OpenDSS se usa únicamente como sistema bajo prueba. Los casos están limitados
a redes radiales trifásicas balanceadas, fuente casi ideal, una línea sin
capacitancia shunt y carga PQ conectada al extremo receptor.
"""

from __future__ import annotations

from copy import deepcopy
from math import sqrt
from typing import Any

from opendssdirect import dss

from . import core, studies, visual_state


TOLERANCES: dict[str, float] = {
    # Declaradas antes de ejecutar la comparación y deliberadamente mayores
    # que el redondeo público actual (Vpu 4 decimales, I 3, pérdidas 3).
    "vpu_abs": 2.0e-4,
    "current_a_abs": 0.15,
    "current_rel_pct": 0.30,
    "loss_kw_abs": 0.005,
    "loss_kvar_abs": 0.005,
    "drop_pct_abs": 0.020,
}


BENCHMARK_CASES: tuple[dict[str, Any], ...] = (
    {
        "id": "bt_radial_pq",
        "description": "BT 480 V, línea corta, carga PQ balanceada",
        "source_kv_ll": 0.48,
        "length_km": 0.050,
        "r_ohm_km": 0.200,
        "x_ohm_km": 0.080,
        "load_kw": 30.0,
        "load_kvar": 10.0,
    },
    {
        "id": "bt_radial_heavy",
        "description": "BT 480 V, caída apreciable, carga PQ balanceada",
        "source_kv_ll": 0.48,
        "length_km": 0.100,
        "r_ohm_km": 0.300,
        "x_ohm_km": 0.100,
        "load_kw": 80.0,
        "load_kvar": 40.0,
    },
    {
        "id": "mt_radial_pq",
        "description": "MT 22.9 kV, alimentador radial balanceado",
        "source_kv_ll": 22.9,
        "length_km": 1.000,
        "r_ohm_km": 0.3422,
        "x_ohm_km": 0.1619,
        "load_kw": 1000.0,
        "load_kvar": 300.0,
    },
)


def _relative_error_pct(actual: float, reference: float) -> float | None:
    if abs(reference) < 1e-12:
        return None
    return abs(actual - reference) / abs(reference) * 100.0


def solve_balanced_two_bus_reference(case: dict[str, Any]) -> dict[str, float]:
    """Resuelve independientemente el caso balanceado de dos barras.

    La fuente se considera ideal. La impedancia es serie por fase y no existe
    admitancia shunt. La carga es PQ trifásica balanceada y constante.
    """
    v_ll = float(case["source_kv_ll"]) * 1000.0
    v_s = complex(v_ll / sqrt(3.0), 0.0)
    z = complex(float(case["r_ohm_km"]), float(case["x_ohm_km"])) * float(
        case["length_km"]
    )
    s_phase = complex(float(case["load_kw"]), float(case["load_kvar"])) * 1000.0 / 3.0

    v_r = v_s
    current = 0j
    if abs(s_phase) > 0:
        for _ in range(200):
            current = (s_phase / v_r).conjugate()
            new_v = v_s - z * current
            if abs(new_v - v_r) <= 1e-10 * max(1.0, abs(v_s)):
                v_r = new_v
                current = (s_phase / v_r).conjugate()
                break
            v_r = new_v
        else:
            raise RuntimeError(f"La referencia independiente no convergió: {case['id']}")

    i_mag = abs(current)
    r_total = float(case["r_ohm_km"]) * float(case["length_km"])
    x_total = float(case["x_ohm_km"]) * float(case["length_km"])
    vpu = abs(v_r) / abs(v_s)
    return {
        "vpu_receiving": vpu,
        "current_a": i_mag,
        "loss_kw": 3.0 * i_mag**2 * r_total / 1000.0,
        "loss_kvar": 3.0 * i_mag**2 * x_total / 1000.0,
        "drop_pct": (1.0 - vpu) * 100.0,
    }


def _configure_benchmark_case(case: dict[str, Any]) -> None:
    core.crear_circuito(f"benchmark_{case['id']}", float(case["source_kv_ll"]), 60)
    visual_state.reset()

    # Fuente prácticamente ideal para que la referencia analítica solo necesite
    # modelar la impedancia serie declarada de la línea.
    dss("Edit Vsource.source MVAsc3=1000000000 MVAsc1=1000000000 X1R1=1 X0R0=1")

    core.agregar_linea(
        "feeder",
        "sourcebus",
        "loadbus",
        float(case["length_km"]),
        3,
        float(case["r_ohm_km"]),
        float(case["x_ohm_km"]),
    )
    # El benchmark declara explícitamente una línea serie sin capacitancia.
    dss("Edit Line.feeder C1=0 C0=0")
    core.agregar_carga(
        "load",
        "loadbus",
        float(case["load_kw"]),
        float(case["load_kvar"]),
        3,
        float(case["source_kv_ll"]),
    )


def _metric(
    actual: float,
    reference: float,
    abs_tolerance: float,
    rel_tolerance_pct: float | None = None,
) -> dict[str, Any]:
    abs_error = abs(actual - reference)
    rel_error = _relative_error_pct(actual, reference)
    passed = abs_error <= abs_tolerance
    if rel_tolerance_pct is not None and rel_error is not None:
        passed = passed or rel_error <= rel_tolerance_pct
    return {
        "actual": actual,
        "reference": reference,
        "abs_error": abs_error,
        "rel_error_pct": rel_error,
        "abs_tolerance": abs_tolerance,
        "rel_tolerance_pct": rel_tolerance_pct,
        "pass": passed,
    }


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    reference = solve_balanced_two_bus_reference(case)
    _configure_benchmark_case(case)

    result = studies.analizar_caida_tension(limite_pct=100.0)
    flow = result["flow"]
    pf = flow["powerflow"]
    feeder = next(x for x in flow["alimentadores"] if x["id"].lower() == "line.feeder")
    drop = next(x for x in result["alimentadores"] if x["id"].lower() == "line.feeder")
    load_bus = pf["voltajes_por_bus"]["loadbus"]

    actual = {
        "vpu_receiving": float(load_bus["voltajes_pu"][0]),
        "current_a": float(feeder["corriente_max_a"]),
        "loss_kw": float(pf["perdidas_totales_kw"]),
        "loss_kvar": float(pf["perdidas_totales_kvar"]),
        "drop_pct": float(drop["caida_evaluada_pct"]),
    }

    comparisons = {
        "vpu_receiving": _metric(
            actual["vpu_receiving"], reference["vpu_receiving"], TOLERANCES["vpu_abs"]
        ),
        "current_a": _metric(
            actual["current_a"],
            reference["current_a"],
            TOLERANCES["current_a_abs"],
            TOLERANCES["current_rel_pct"],
        ),
        "loss_kw": _metric(actual["loss_kw"], reference["loss_kw"], TOLERANCES["loss_kw_abs"]),
        "loss_kvar": _metric(
            actual["loss_kvar"], reference["loss_kvar"], TOLERANCES["loss_kvar_abs"]
        ),
        "drop_pct": _metric(
            actual["drop_pct"], reference["drop_pct"], TOLERANCES["drop_pct_abs"]
        ),
    }

    return {
        "id": case["id"],
        "description": case["description"],
        "inputs": deepcopy(case),
        "reference_method": "balanced_two_bus_constant_pq_independent_complex_iteration",
        "reference": reference,
        "actual": actual,
        "comparisons": comparisons,
        "pass": all(item["pass"] for item in comparisons.values()),
    }


def run_p1_benchmarks() -> dict[str, Any]:
    cases = [run_case(case) for case in BENCHMARK_CASES]
    return {
        "suite": "P1_power_flow_voltage_drop",
        "scope": "radial_balanced_three_phase_two_bus_constant_pq",
        "tolerances": deepcopy(TOLERANCES),
        "cases": cases,
        "summary": {
            "total": len(cases),
            "passed": sum(case["pass"] for case in cases),
            "failed": sum(not case["pass"] for case in cases),
            "pass": all(case["pass"] for case in cases),
        },
        "limitations": [
            "No cubre redes desbalanceadas ni multifásicas no simétricas",
            "No cubre transformadores, reguladores ni bancos de capacitores",
            "No sustituye todavía un benchmark IEEE/EPRI de alimentador completo",
            "La caída validada es la implementación actual por cada objeto Line",
        ],
    }
