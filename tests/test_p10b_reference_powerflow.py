from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from mcp_electrico import (
    real_controlled_execution,
    real_integrated_readiness,
    real_model_materializer,
    real_pilot_intake,
    workspace_state,
)


def _manifest() -> dict:
    path = Path(__file__).resolve().parents[1] / "examples" / "p10_reference_substation_stage1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_p10b_reference_intake_is_ready_without_p3_p4_p5():
    manifest = _manifest()
    result = real_pilot_intake.evaluar_admision(manifest)

    assert result["intake_status"] == "READY_TO_BUILD_MODEL"
    assert result["ready_to_build_model"] is True
    assert result["requested_scope"] == ["POWER_FLOW", "VOLTAGE_DROP"]
    assert result["issues"] == []
    assert result["electrical_calculation_performed"] is False
    assert result["model_mutation_performed"] is False
    assert result["automatic_defaults"] is False
    assert result["automatic_dispatch"] is False
    assert result["professional_emission"] is False


def test_p10b_reference_materializes_positive_sequence_without_retained_defaults():
    result = real_model_materializer.materializar_modelo(_manifest())

    assert result["materializer_status"] == "MODEL_BUILT_NOT_EXECUTED"
    assert result["model_mutation_performed"] is True
    assert result["electrical_calculation_performed"] is False
    assert result["source_p2_materialized"] is True
    assert result["engine_defaults_retained_count"] == 0
    assert result["engine_defaults_retained"] == []

    evidence = result["evidence"]
    assert evidence["source_bus"].lower() == "source_22k9"
    assert set(name.lower() for name in evidence["transformers"]) == {
        "transformer.t1_main",
        "transformer.t2_aux",
    }
    assert set(name.lower() for name in evidence["lines"]) == {
        "line.mv_feeder",
        "line.lv_feeder",
    }
    assert set(name.lower() for name in evidence["loads"]) == {
        "load.mv_process",
        "load.lv_services",
    }


def test_p10b_reference_readiness_is_green_without_execution():
    result = real_integrated_readiness.evaluar_readiness_integral(_manifest())

    assert result["readiness_status"] == "READY_FOR_CONTROLLED_EXECUTION"
    assert result["materialization_layer"] == "P8C3B"
    assert result["materialization_ok"] is True
    assert result["ready_scopes"] == ["POWER_FLOW", "VOLTAGE_DROP"]
    assert result["blocked_scopes"] == []
    assert result["all_requested_ready"] is True

    assert result["scope_readiness"]["POWER_FLOW"]["status"] == "READY"
    assert result["scope_readiness"]["POWER_FLOW"]["backend"] == "OpenDSS"
    assert result["scope_readiness"]["VOLTAGE_DROP"]["status"] == "READY"
    assert result["scope_readiness"]["VOLTAGE_DROP"]["backend"] == "OpenDSS"
    assert result["scope_readiness"]["VOLTAGE_DROP"]["limit_pct"] == 5.0

    assert result["electrical_calculation_performed"] is False
    assert result["workspace_studies_after_readiness"] == []
    assert result["automatic_defaults"] is False
    assert result["automatic_dispatch"] is False
    assert result["professional_emission"] is False


def test_p10b_reference_executes_only_power_flow_and_voltage_drop():
    result = real_controlled_execution.ejecutar_controlado(_manifest())

    assert result["execution_status"] == "CONTROLLED_EXECUTION_COMPLETED"
    assert result["executed_scopes"] == ["POWER_FLOW", "VOLTAGE_DROP"]
    assert result["pending_scopes"] == []
    assert result["next_gate"] == "P8E_WORKSPACE_AND_DOSSIER"

    power = result["results"]["POWER_FLOW"]
    voltage = result["results"]["VOLTAGE_DROP"]

    assert power["powerflow"]["convergio"] is True
    assert power["convergio"] is True
    assert len(power["alimentadores"]) == 2

    assert voltage["convergio"] is True
    assert voltage["criterio"]["limite_pct"] == 5.0
    assert voltage["criterio"]["normativo_universal"] is False
    assert voltage["resumen"]["alimentadores_evaluados"] == 2
    assert voltage["resumen"]["vpu_min_sistema"] is not None
    assert 0.85 < voltage["resumen"]["vpu_min_sistema"] < 1.10

    assert result["electrical_calculation_performed"] is True
    assert result["ampacity_calculation_performed"] is False
    assert result["short_circuit_calculation_performed"] is False
    assert result["protection_calculation_performed"] is False
    assert result["automatic_dispatch"] is False
    assert result["automatic_fault_binding"] is False
    assert result["crosscheck"] is False
    assert result["professional_emission"] is False

    studies = workspace_state.status()["studies"]
    assert "powerflow" in studies
    assert "flow" in studies
    assert "voltage_drop" in studies
    assert "ampacity" not in studies
    assert not any(name.startswith("iec60909") for name in studies)
    assert not any(name.startswith("protection_") for name in studies)


def test_p10b_reference_execution_is_repeatable():
    manifest = _manifest()
    first = real_controlled_execution.ejecutar_controlado(manifest)
    second = real_controlled_execution.ejecutar_controlado(deepcopy(manifest))

    assert first["execution_status"] == second["execution_status"] == "CONTROLLED_EXECUTION_COMPLETED"
    assert first["executed_scopes"] == second["executed_scopes"]
    assert first["model_revision"] == second["model_revision"]
    assert first["results"]["POWER_FLOW"]["powerflow"]["convergio"] is True
    assert second["results"]["POWER_FLOW"]["powerflow"]["convergio"] is True
    assert first["results"]["VOLTAGE_DROP"]["resumen"] == second["results"]["VOLTAGE_DROP"]["resumen"]
