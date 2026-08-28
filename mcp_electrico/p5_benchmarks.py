"""Benchmarks deterministas P5 para el gate de uso interno.

La suite usa únicamente TEST_DATA y un circuito sintético reproducible. Está
pensada para CI/QA del producto, no como curva de fabricante ni como evidencia
de conformidad normativa integral.
"""

from __future__ import annotations

from copy import deepcopy
from math import isclose, sqrt
from typing import Any

from . import (
    core,
    protection_checks,
    protection_clearing_time,
    protection_coordination,
    protection_curves,
    protection_data,
)

SUITE_ID = "MCP_ELECTRICO_P5G_BENCHMARK_SUITE_V1"
BENCHMARK_IDS = (
    "P5G_B01_TCC_BAND_LOGLOG",
    "P5G_B02_TCC_NO_EXTRAPOLATION",
    "P5G_B03_CLEARING_TIME_BAND",
    "P5G_B04_TEMPORAL_COORDINATION",
    "P5G_B05_BREAKING_CAPACITY",
    "P5G_B06_CONDUCTOR_THERMAL",
)


def _passed(actual: float, expected: float, tolerance: float = 1e-10) -> bool:
    return isclose(float(actual), float(expected), rel_tol=tolerance, abs_tol=tolerance)


def _item(
    benchmark_id: str,
    passed: bool,
    actual: Any,
    reference: Any,
    note: str,
) -> dict[str, Any]:
    return {
        "id": benchmark_id,
        "status": "PASS" if passed else "FAIL",
        "pass": bool(passed),
        "actual": deepcopy(actual),
        "reference": deepcopy(reference),
        "note": note,
    }


def _build_case() -> float:
    core.crear_circuito("p5g_benchmark", 0.48)
    protection_data.reset()
    protection_curves.reset()

    core.agregar_linea(
        "f_up", "sourcebus", "bus1", 0.02,
        fases=3, r1_ohm_km=0.20, x1_ohm_km=0.08,
    )
    core.agregar_linea(
        "f_down", "bus1", "bus2", 0.03,
        fases=3, r1_ohm_km=0.20, x1_ohm_km=0.08,
    )

    for name, element, curve_id in (
        ("qf_up", "Line.f_up", "CURVE-P5G-UP"),
        ("qf_down", "Line.f_down", "CURVE-P5G-DOWN"),
    ):
        protection_data.definir_dispositivo(
            nombre=name,
            tipo="circuit_breaker",
            elemento_protegido=element,
            in_a=250.0,
            ue_kv=0.48,
            norma_referencia="TEST_DATA benchmark P5G",
            icu_ka=36.0,
            ics_ka=27.0,
            fuente_referencia="P5G synthetic benchmark device",
        )
        protection_data.vincular_curva(
            name,
            curva_id=curve_id,
            tipo_curva="TEST_CURVE",
            fuente_referencia="P5G synthetic benchmark curve",
            revision="1",
        )

    protection_curves.registrar_dataset(
        dataset_id="P5G-DS-DOWN",
        curve_id="CURVE-P5G-DOWN",
        shape="BAND",
        time_semantics="TOTAL_CLEARING_TIME",
        segments=[{
            "id": "inverse",
            "points": [
                {"current_a": 100.0, "time_min_s": 8.0, "time_max_s": 12.0},
                {"current_a": 1000.0, "time_min_s": 0.08, "time_max_s": 0.12},
            ],
        }],
        source_type="TEST_DATA",
        source_reference="P5G analytic band down: t proportional I^-2",
    )
    protection_curves.registrar_dataset(
        dataset_id="P5G-DS-UP",
        curve_id="CURVE-P5G-UP",
        shape="BAND",
        time_semantics="TOTAL_CLEARING_TIME",
        segments=[{
            "id": "inverse",
            "points": [
                {"current_a": 100.0, "time_min_s": 16.0, "time_max_s": 20.0},
                {"current_a": 1000.0, "time_min_s": 0.16, "time_max_s": 0.20},
            ],
        }],
        source_type="TEST_DATA",
        source_reference="P5G analytic band up: t proportional I^-2",
    )
    protection_curves.vincular_dataset_dispositivo("qf_down", "P5G-DS-DOWN")
    protection_curves.vincular_dataset_dispositivo("qf_up", "P5G-DS-UP")
    return sqrt(100.0 * 1000.0)


def ejecutar_benchmarks_p5g() -> dict[str, Any]:
    """Ejecuta la suite integral P5G en un caso sintético reproducible."""
    current = _build_case()
    results: list[dict[str, Any]] = []

    down_curve = protection_curves.evaluar_dispositivo("qf_down", current)
    curve_values = down_curve.get("values") or {}
    curve_ok = (
        down_curve.get("status") == "RESOLVED_INTERPOLATED"
        and _passed(curve_values.get("time_min_s"), 0.8)
        and _passed(curve_values.get("time_max_s"), 1.2)
        and down_curve.get("extrapolated") is False
        and down_curve.get("cross_segment_interpolation") is False
    )
    results.append(_item(
        BENCHMARK_IDS[0],
        curve_ok,
        {
            "status": down_curve.get("status"),
            "time_min_s": curve_values.get("time_min_s"),
            "time_max_s": curve_values.get("time_max_s"),
        },
        {"time_min_s": 0.8, "time_max_s": 1.2},
        "Referencia analítica independiente para banda t ∝ I^-2 en la media geométrica de corriente.",
    ))

    outside = protection_curves.evaluar_dispositivo("qf_down", 50.0)
    outside_ok = (
        outside.get("status") == "OUT_OF_DOMAIN"
        and outside.get("values") is None
        and outside.get("extrapolated") is False
    )
    results.append(_item(
        BENCHMARK_IDS[1],
        outside_ok,
        {"status": outside.get("status"), "values": outside.get("values")},
        {"status": "OUT_OF_DOMAIN", "values": None},
        "P5B debe fallar cerrado fuera del dominio y nunca extrapolar.",
    ))

    clearing = protection_clearing_time.evaluar_tiempo_despeje("qf_down", current)
    ctime = clearing.get("clearing_time") or {}
    clearing_ok = (
        clearing.get("status") == "CLEARING_TIME_READY"
        and clearing.get("time_semantics") == "TOTAL_CLEARING_TIME"
        and _passed(ctime.get("time_min_s"), 0.8)
        and _passed(ctime.get("time_max_s"), 1.2)
        and _passed(ctime.get("conservative_time_s"), 1.2)
        and clearing.get("p4_tk_s_consumed") is False
    )
    results.append(_item(
        BENCHMARK_IDS[2],
        clearing_ok,
        {
            "status": clearing.get("status"),
            "time_min_s": ctime.get("time_min_s"),
            "time_max_s": ctime.get("time_max_s"),
            "conservative_time_s": ctime.get("conservative_time_s"),
        },
        {"time_min_s": 0.8, "time_max_s": 1.2, "conservative_time_s": 1.2},
        "P5D conserva banda y usa time_max_s como campo conservador sin consumir tk_s P4.",
    ))

    coordination = protection_coordination.evaluar_coordinacion_temporal(
        dispositivo_downstream="qf_down",
        corriente_downstream_a=current,
        dispositivo_upstream="qf_up",
        corriente_upstream_a=current,
        margen_minimo_s=0.3,
        fuente_relacion="P5G synthetic radial relationship",
        fuente_corrientes="P5G same benchmark current declared explicitly for both devices",
    )
    coordination_ok = (
        coordination.get("status") == "PASS"
        and _passed(coordination.get("conservative_margin_s"), 0.4)
        and coordination.get("claims", {}).get("selectivity") == "NOT_EVALUATED"
        and coordination.get("claims", {}).get("backup") == "NOT_EVALUATED"
        and coordination.get("domain_scan_performed") is False
    )
    results.append(_item(
        BENCHMARK_IDS[3],
        coordination_ok,
        {
            "status": coordination.get("status"),
            "conservative_margin_s": coordination.get("conservative_margin_s"),
            "claims": coordination.get("claims"),
        },
        {"conservative_margin_s": 0.4, "selectivity": "NOT_EVALUATED"},
        "Referencia: upstream_min 1.6 s - downstream_max 1.2 s = 0.4 s.",
    ))

    breaking = protection_checks.evaluar_capacidad_corte(
        dispositivo="qf_down",
        corriente_falla_ka=25.0,
        tension_operacion_kv=0.48,
        fuente_corriente="P5G explicit synthetic fault current",
        tipo_falla="3F",
        escenario="max",
    )
    breaking_ok = (
        breaking.get("status") == "PASS"
        and (breaking.get("rating_used") or {}).get("type") == "Icu"
        and _passed(breaking.get("margin_ka"), 11.0)
        and breaking.get("full_standard_compliance_claim") is False
    )
    results.append(_item(
        BENCHMARK_IDS[4],
        breaking_ok,
        {
            "status": breaking.get("status"),
            "rating_used": breaking.get("rating_used"),
            "margin_ka": breaking.get("margin_ka"),
        },
        {"rating_type": "Icu", "margin_ka": 11.0},
        "Referencia aritmética: Icu 36 kA - falla 25 kA = 11 kA.",
    ))

    thermal_time = float(ctime.get("conservative_time_s") or 0.0)
    thermal = protection_checks.evaluar_soportabilidad_termica_conductor(
        elemento="Line.f_down",
        corriente_falla_ka=8.0,
        tiempo_despeje_s=thermal_time,
        seccion_mm2=70.0,
        k_a_sqrt_s_per_mm2=143.0,
        fuente_k="P5G explicit benchmark coefficient",
        fuente_tiempo="P5G P5D conservative_time_s",
        fuente_seccion="P5G explicit benchmark section",
    )
    thermal_results = thermal.get("results") or {}
    reference_actual = (8000.0 ** 2) * 1.2
    reference_limit = (143.0 * 70.0) ** 2
    reference_ratio = reference_actual / reference_limit
    thermal_ok = (
        thermal.get("status") == "PASS"
        and _passed(thermal_results.get("actual_i2t_a2s"), reference_actual, 1e-9)
        and _passed(thermal_results.get("limit_k2s2_a2s"), reference_limit, 1e-9)
        and _passed(thermal_results.get("utilization_ratio"), reference_ratio, 1e-9)
        and thermal.get("policies", {}).get("p4_tk_s_consumed") is False
    )
    results.append(_item(
        BENCHMARK_IDS[5],
        thermal_ok,
        {
            "status": thermal.get("status"),
            "actual_i2t_a2s": thermal_results.get("actual_i2t_a2s"),
            "limit_k2s2_a2s": thermal_results.get("limit_k2s2_a2s"),
            "utilization_ratio": thermal_results.get("utilization_ratio"),
        },
        {
            "actual_i2t_a2s": reference_actual,
            "limit_k2s2_a2s": reference_limit,
            "utilization_ratio": reference_ratio,
        },
        "Referencia independiente por sustitución directa en I²t y k²S².",
    ))

    failed = sum(1 for item in results if not item["pass"])
    return {
        "schema": "MCP_ELECTRICO_P5G_BENCHMARK_REPORT_V1",
        "suite_id": SUITE_ID,
        "benchmark_ids": list(BENCHMARK_IDS),
        "case": {
            "kind": "SYNTHETIC_REPRODUCIBLE_TEST_DATA",
            "curve_source_type": "TEST_DATA",
            "manufacturer_claim": False,
            "normative_compliance_claim": False,
        },
        "benchmarks": results,
        "passed": len(results) - failed,
        "failed": failed,
        "pass": failed == 0 and len(results) == len(BENCHMARK_IDS),
        "professional_emission": False,
    }
