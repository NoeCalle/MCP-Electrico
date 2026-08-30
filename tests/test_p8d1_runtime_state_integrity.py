from __future__ import annotations

import pytest

from mcp_electrico import (
    ampacity,
    core,
    iec60909,
    iec60909_single_phase_ground,
    real_integrated_readiness,
    studies,
)


def _manifest() -> dict:
    return {
        "project": {
            "id": "REAL-SE-P8D1-RUNTIME-001",
            "name": "P8D1 runtime state integrity",
            "source_reference": "SLD + expediente aprobado REV-A",
        },
        "requested_scope": [
            "POWER_FLOW",
            "VOLTAGE_DROP",
            "AMPACITY",
            "IEC60909_3PH_MAX_MIN",
            "IEC60909_1PH_GROUND_MAX_MIN",
        ],
        "source": {
            "bus": "red_mt",
            "kv_ll": 22.9,
            "frequency_hz": 60.0,
            "pu": 1.0,
            "angle_deg": 0.0,
            "scc_max_mva": 350.0,
            "x_r_max": 10.0,
            "scc_min_mva": 180.0,
            "x_r_min": 6.0,
            "source_reference": "Utility study REV-A",
        },
        "topology": {
            "buses": ["red_mt", "tgbt", "load_bus"],
            "transformers": [{
                "id": "Transformer.tr01",
                "bus_hv": "red_mt",
                "bus_lv": "tgbt",
                "kva": 1000.0,
                "kv_hv": 22.9,
                "kv_lv": 0.48,
                "uk_percent": 6.0,
                "vector_group": "Dyn11",
                "x_r": 10.0,
                "no_load_loss_kw": 1.8,
                "i0_percent": 0.6,
                "tap_side": "hv",
                "tap_neutral": 0,
                "tap_min": -2,
                "tap_max": 2,
                "tap_step_percent": 2.5,
                "tap_pos": 0,
                "source_reference": "Transformer nameplate REV-A",
            }],
            "lines": [{
                "id": "Line.feeder",
                "bus1": "tgbt",
                "bus2": "load_bus",
                "phases": 3,
                "length_km": 0.05,
                "r1_ohm_km": 0.12,
                "x1_ohm_km": 0.08,
                "c1_nf_km": 0.0,
                "endtemp_min_c": 90.0,
                "source_reference": "Cable schedule REV-A",
            }],
            "loads": [{
                "id": "Load.load1",
                "bus": "load_bus",
                "phases": 3,
                "kv": 0.48,
                "kw": 250.0,
                "kvar": 80.0,
                "connection": "wye",
                "model": 1,
                "source_reference": "Load list REV-A",
            }],
        },
        "zero_sequence": {
            "source": {
                "r0_max_ohm": 0.15,
                "x0_max_ohm": 0.45,
                "r0_min_ohm": 0.25,
                "x0_min_ohm": 0.80,
                "source_reference": "Utility Z0 study REV-A",
            },
            "lines": [{
                "id": "Line.feeder",
                "r0_ohm_km": 0.36,
                "x0_ohm_km": 0.15,
                "c0_nf_km": 100.0,
                "source_reference": "Cable Z0 calculation REV-A",
            }],
            "transformers": [{
                "id": "Transformer.tr01",
                "uk0_percent": 5.5,
                "ur0_percent": 0.6,
                "magnetizing_z0_ratio_percent": 100.0,
                "magnetizing_r_over_x": 0.0,
                "leakage_share_hv": 0.5,
                "neutral_side": "lv",
                "neutral_mode": "solid",
                "source_reference": "Transformer Z0 test REV-A",
            }],
        },
        "ampacity": [{
            "element_id": "Line.feeder",
            "conductor_code": "PROJECT-CABLE-01",
            "conductor_description": "PROJECT-CABLE-01 · feeder aprobado",
            "base_ampacity_a": 500.0,
            "norm_id": "IEC_60364_5_52_2009_A1_2024",
            "ib_a": 350.0,
            "ib_reference": "Load list + feeder sizing REV-A",
            "in_a": 400.0,
            "in_reference": "Protection schedule REV-A",
            "installation_reference": "Installation detail REV-A",
            "ampacity_reference": "Approved cable ampacity calculation REV-A",
            "base_conditions_confirmed": True,
            "factors": [],
        }],
        "study_inputs": {
            "voltage_drop_limit_pct": 5.0,
            "short_circuit_buses": ["load_bus"],
        },
    }


def _line_r1() -> float:
    assert core.dss.Lines.Name("feeder") > 0
    return float(core.dss.Lines.R1())


def _assert_r1(stage: str, expected: float) -> None:
    actual = _line_r1()
    assert actual == pytest.approx(expected, rel=0.0, abs=1e-12), (
        f"OpenDSS R1 mutated after {stage}: expected {expected!r}, got {actual!r}"
    )


def _prepare() -> float:
    readiness = real_integrated_readiness.evaluar_readiness_integral(_manifest())
    assert readiness["readiness_status"] == "READY_FOR_CONTROLLED_EXECUTION"
    baseline = _line_r1()
    _assert_r1("P8C5 readiness", baseline)
    return baseline


def _run_power_flow(baseline: float) -> None:
    studies.analizar_flujo_operacion()
    _assert_r1("P1 power flow", baseline)


def _run_voltage_drop(baseline: float) -> None:
    _run_power_flow(baseline)
    studies.analizar_caida_tension(5.0)
    _assert_r1("P1 voltage drop", baseline)


def _run_ampacity(baseline: float) -> None:
    _run_voltage_drop(baseline)
    ampacity.evaluar_todos()
    _assert_r1("P3 ampacity", baseline)


def _run_3ph_max(baseline: float) -> None:
    _run_ampacity(baseline)
    result = iec60909.ejecutar_3ph("max", "load_bus")
    assert result["ok"] is True
    _assert_r1("P4 3ph MAX", baseline)


def _run_3ph_min(baseline: float) -> None:
    _run_3ph_max(baseline)
    result = iec60909.ejecutar_3ph(
        "min",
        "load_bus",
        line_endtemp_degree_c={"Line.feeder": 90.0},
    )
    assert result["ok"] is True
    _assert_r1("P4 3ph MIN", baseline)


def _run_1ph_max(baseline: float) -> None:
    _run_3ph_min(baseline)
    result = iec60909_single_phase_ground.ejecutar_1ph_ground("load_bus", "max")
    assert result["ok"] is True
    _assert_r1("P4 1ph-ground MAX", baseline)


def _run_1ph_min(baseline: float) -> None:
    _run_1ph_max(baseline)
    result = iec60909_single_phase_ground.ejecutar_1ph_ground(
        "load_bus",
        "min",
        line_endtemp_degree_c={"Line.feeder": 90.0},
    )
    assert result["ok"] is True
    _assert_r1("P4 1ph-ground MIN", baseline)


def test_runtime_r1_00_readiness_baseline():
    _prepare()


def test_runtime_r1_10_after_p1_power_flow():
    baseline = _prepare()
    _run_power_flow(baseline)


def test_runtime_r1_20_after_p1_voltage_drop():
    baseline = _prepare()
    _run_voltage_drop(baseline)


def test_runtime_r1_30_after_p3_ampacity():
    baseline = _prepare()
    _run_ampacity(baseline)


def test_runtime_r1_40_after_p4_3ph_max():
    baseline = _prepare()
    _run_3ph_max(baseline)


def test_runtime_r1_50_after_p4_3ph_min():
    baseline = _prepare()
    _run_3ph_min(baseline)


def test_runtime_r1_60_after_p4_1ph_ground_max():
    baseline = _prepare()
    _run_1ph_max(baseline)


def test_runtime_r1_70_after_p4_1ph_ground_min():
    baseline = _prepare()
    _run_1ph_min(baseline)
