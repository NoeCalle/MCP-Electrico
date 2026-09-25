from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from mcp_electrico import (
    real_controlled_execution,
    real_integrated_readiness,
    real_pilot_intake,
    workspace_state,
)


def _manifest() -> dict:
    path = Path(__file__).resolve().parents[1] / "examples" / "p10_reference_substation_stage3.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _one_phase_pairs(result: dict) -> dict[str, tuple[float, float]]:
    one = result["results"]["IEC60909_1PH_GROUND_MAX_MIN"]
    pairs: dict[str, tuple[float, float]] = {}
    for item in one["targets"]:
        pair = item["result"]
        pairs[item["bus"]] = (
            float(pair["max"]["results"]["ikss_ka"]),
            float(pair["min"]["results"]["ikss_ka"]),
        )
    return pairs


def test_p10d_reference_intake_accepts_explicit_zero_sequence():
    result = real_pilot_intake.evaluar_admision(_manifest())

    assert result["intake_status"] == "READY_TO_BUILD_MODEL"
    assert result["ready_to_build_model"] is True
    assert result["issues"] == []
    assert result["requested_scope"] == [
        "POWER_FLOW",
        "VOLTAGE_DROP",
        "IEC60909_3PH_MAX_MIN",
        "IEC60909_1PH_GROUND_MAX_MIN",
    ]
    assert result["electrical_calculation_performed"] is False
    assert result["automatic_defaults"] is False
    assert result["professional_emission"] is False


def test_p10d_reference_1ph_readiness_is_green_without_execution():
    result = real_integrated_readiness.evaluar_readiness_integral(_manifest())

    assert result["readiness_status"] == "READY_FOR_CONTROLLED_EXECUTION"
    assert result["materialization_layer"] == "P8C3B"
    assert result["materialization_ok"] is True
    assert result["blocked_scopes"] == []
    assert result["all_requested_ready"] is True

    one = result["scope_readiness"]["IEC60909_1PH_GROUND_MAX_MIN"]
    assert one["status"] == "READY"
    assert one["backend"] == "pandapower"
    assert one["fault"] == "1ph-ground"
    assert one["cases"] == ["max", "min"]
    assert one["target_buses"] == ["mv_load_bus", "lv_load_bus"]
    assert len(one["checks"]) == 4
    assert all(check["ready"] is True for check in one["checks"])
    assert one["projection_preflight_only"] is True
    assert one["short_circuit_calculation_performed"] is False

    materialization = result["materialization"]
    z0 = materialization["zero_sequence"]
    assert z0["source"]["status"] == "EXPLICIT"
    assert len(z0["lines"]) == 2
    assert len(z0["transformers"]) == 2

    assert result["electrical_calculation_performed"] is False
    assert result["short_circuit_calculation_performed"] is False
    assert result["workspace_studies_after_readiness"] == []
    assert result["automatic_dispatch"] is False
    assert result["crosscheck"] is False
    assert result["professional_emission"] is False


def test_p10d_reference_executes_1ph_ground_max_min_for_all_declared_buses():
    result = real_controlled_execution.ejecutar_controlado(_manifest())

    assert result["execution_status"] == "CONTROLLED_EXECUTION_COMPLETED"
    assert result["executed_scopes"] == [
        "POWER_FLOW",
        "VOLTAGE_DROP",
        "IEC60909_3PH_MAX_MIN",
        "IEC60909_1PH_GROUND_MAX_MIN",
    ]
    assert result["pending_scopes"] == []
    assert result["short_circuit_calculation_performed"] is True
    assert result["ampacity_calculation_performed"] is False
    assert result["protection_calculation_performed"] is False

    one = result["results"]["IEC60909_1PH_GROUND_MAX_MIN"]
    assert one["fault"] == "1ph-ground"
    assert one["target_count"] == 2
    assert one["automatic_target_selection"] is False
    assert [item["bus"] for item in one["targets"]] == ["mv_load_bus", "lv_load_bus"]

    for item in one["targets"]:
        assert item["result"]["max"]["ok"] is True
        assert item["result"]["min"]["ok"] is True
        assert item["result"]["max"]["status"] == "CALCULATED_EXPERIMENTAL"
        assert item["result"]["min"]["status"] == "CALCULATED_EXPERIMENTAL"

    pairs = _one_phase_pairs(result)
    for bus, (ikss_max, ikss_min) in pairs.items():
        assert bus in {"mv_load_bus", "lv_load_bus"}
        assert ikss_max > 0
        assert ikss_min > 0
        assert ikss_max > ikss_min

    assert result["automatic_dispatch"] is False
    assert result["automatic_fault_binding"] is False
    assert result["crosscheck"] is False
    assert result["professional_emission"] is False

    studies = workspace_state.status()["studies"]
    assert "iec60909_3ph_targets" in studies
    assert "iec60909_1ph_ground_targets" in studies
    assert "ampacity" not in studies
    assert not any(name.startswith("protection_") for name in studies)


def test_p10d_reference_1ph_results_are_repeatable():
    manifest = _manifest()
    first = real_controlled_execution.ejecutar_controlado(manifest)
    second = real_controlled_execution.ejecutar_controlado(deepcopy(manifest))

    assert first["execution_status"] == second["execution_status"] == "CONTROLLED_EXECUTION_COMPLETED"
    assert first["model_revision"] == second["model_revision"]

    first_pairs = _one_phase_pairs(first)
    second_pairs = _one_phase_pairs(second)
    assert first_pairs.keys() == second_pairs.keys()
    for bus in first_pairs:
        assert first_pairs[bus][0] == pytest.approx(second_pairs[bus][0], rel=1e-12, abs=1e-12)
        assert first_pairs[bus][1] == pytest.approx(second_pairs[bus][1], rel=1e-12, abs=1e-12)
