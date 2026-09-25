from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from mcp_electrico import (
    real_integrated_readiness,
    real_pilot_intake,
    real_protection_execution,
    real_protection_materializer,
    workspace_state,
)


def _manifest() -> dict:
    path = Path(__file__).resolve().parents[1] / "examples" / "p10_reference_substation_stage5.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _devices_by_id(result: dict) -> dict[str, dict]:
    return {str(item["device_id"]).lower(): item for item in result["device_results"]}


def test_p10f_reference_intake_accepts_explicit_p5_data():
    result = real_pilot_intake.evaluar_admision(_manifest())

    assert result["intake_status"] == "READY_TO_BUILD_MODEL"
    assert result["ready_to_build_model"] is True
    assert result["issues"] == []
    assert "PROTECTION_TCC" in result["requested_scope"]
    assert result["study_input_readiness"]["PROTECTION_TCC"]["status"] == "INPUTS_PRESENT"
    assert result["electrical_calculation_performed"] is False
    assert result["automatic_defaults"] is False
    assert result["automatic_dispatch"] is False
    assert result["professional_emission"] is False


def test_p10f_reference_materializes_devices_and_tcc_without_evaluation():
    result = real_protection_materializer.materializar_protecciones(_manifest())

    assert result["protection_materializer_status"] == "P5_TCC_MATERIALIZED_NOT_EXECUTED"
    assert result["p5_materialized"] is True
    assert result["issues"] == []
    assert result["electrical_calculation_performed"] is False
    assert result["protection_calculation_performed"] is False
    assert result["tcc_evaluation_performed"] is False

    p5 = result["p5"]
    assert len(p5["devices"]) == 2
    assert len(p5["datasets"]) == 2
    assert len(p5["readiness"]) == 2
    assert all(item["breaking_capacity_ready"] is True for item in p5["readiness"])
    assert all(item["tcc_data_ready"] is True for item in p5["readiness"])
    assert all(item["p3_binding"]["status"] == "MATCH" for item in p5["readiness"])
    assert all(item["curve_time_semantics"] == "TOTAL_CLEARING_TIME" for item in p5["readiness"])

    assert result["automatic_defaults"] is False
    assert result["automatic_dispatch"] is False
    assert result["crosscheck"] is False
    assert result["professional_emission"] is False


def test_p10f_reference_readiness_is_green_without_p5_execution():
    result = real_integrated_readiness.evaluar_readiness_integral(_manifest())

    assert result["readiness_status"] == "READY_FOR_CONTROLLED_EXECUTION"
    assert result["materialization_layer"] == "P8C4B"
    assert result["materialization_ok"] is True
    assert result["blocked_scopes"] == []
    assert result["all_requested_ready"] is True

    p5 = result["scope_readiness"]["PROTECTION_TCC"]
    assert p5["status"] == "READY"
    assert p5["backend"] == "P5"
    assert len(p5["checks"]) == 2
    assert all(check["ready"] is True for check in p5["checks"])
    assert all(check["breaking_capacity_ready"] is True for check in p5["checks"])
    assert all(check["tcc_data_ready"] is True for check in p5["checks"])
    assert all(check["p3_binding"]["status"] == "MATCH" for check in p5["checks"])
    assert p5["tcc_evaluation_performed"] is False

    assert result["protection_calculation_performed"] is False
    assert result["workspace_studies_after_readiness"] == []
    assert result["automatic_dispatch"] is False
    assert result["crosscheck"] is False
    assert result["professional_emission"] is False


def test_p10f_reference_executes_explicit_fault_bindings_and_tcc():
    result = real_protection_execution.ejecutar_protecciones(_manifest())

    assert result["execution_status"] == "PROTECTION_EXECUTION_COMPLETED"
    assert result["issues"] == []
    assert result["protection_calculation_performed"] is True
    assert result["tcc_evaluation_performed"] is True
    assert result["p4_results_reused"] is True
    assert result["p4_recalculation_inside_p5"] is False
    assert result["automatic_dispatch"] is False
    assert result["automatic_fault_binding"] is False
    assert result["crosscheck"] is False
    assert result["professional_emission"] is False
    assert result["next_gate"] == "P8E_WORKSPACE_AND_DOSSIER"

    devices = _devices_by_id(result)
    assert set(devices) == {"protection.qf_mv", "protection.qf_lv"}

    mv = devices["protection.qf_mv"]
    assert mv["protected_element"] == "Line.mv_feeder"
    assert mv["fault_binding_explicit"] is True
    assert mv["fault_provenance"]["fault_bus"] == "mv_load_bus"
    assert mv["fault_provenance"]["fault_type"] == "3ph"
    assert mv["fault_provenance"]["case"] == "max"
    assert mv["fault_provenance"]["automatic_target_selection"] is False
    assert mv["fault_provenance"]["fault_current_ka"] > 0
    assert mv["breaking_capacity"]["status"] == "PASS"
    assert mv["breaking_capacity"]["rating_used"]["type"] == "Icu"
    assert mv["breaking_capacity"]["rating_used"]["value_ka"] == pytest.approx(25.0)
    assert mv["clearing_time"]["status"] == "CLEARING_TIME_READY"
    assert mv["clearing_time"]["clearing_time"]["conservative_time_s"] > 0
    assert mv["thermal_check"]["status"] == "NOT_REQUESTED"

    lv = devices["protection.qf_lv"]
    assert lv["protected_element"] == "Line.lv_feeder"
    assert lv["fault_binding_explicit"] is True
    assert lv["fault_provenance"]["fault_bus"] == "lv_load_bus"
    assert lv["fault_provenance"]["fault_type"] == "3ph"
    assert lv["fault_provenance"]["case"] == "max"
    assert lv["fault_provenance"]["automatic_target_selection"] is False
    assert lv["fault_provenance"]["fault_current_ka"] > 0
    assert lv["breaking_capacity"]["status"] == "PASS"
    assert lv["breaking_capacity"]["rating_used"]["type"] == "Icu"
    assert lv["breaking_capacity"]["rating_used"]["value_ka"] == pytest.approx(50.0)
    assert lv["clearing_time"]["status"] == "CLEARING_TIME_READY"
    assert lv["clearing_time"]["clearing_time"]["conservative_time_s"] > 0
    assert lv["thermal_check"]["status"] == "NOT_REQUESTED"

    studies = workspace_state.status()["studies"]
    assert "protection_tcc" in studies
    assert studies["protection_tcc"]["valid"] is True
    assert studies["protection_tcc"]["model_revision"] == result["model_revision"]


def test_p10f_reference_protection_is_repeatable():
    manifest = _manifest()
    first = real_protection_execution.ejecutar_protecciones(manifest)
    second = real_protection_execution.ejecutar_protecciones(deepcopy(manifest))

    assert first["execution_status"] == second["execution_status"] == "PROTECTION_EXECUTION_COMPLETED"
    assert first["model_revision"] == second["model_revision"]

    first_devices = _devices_by_id(first)
    second_devices = _devices_by_id(second)
    assert first_devices.keys() == second_devices.keys()

    for device_id in first_devices:
        a = first_devices[device_id]
        b = second_devices[device_id]
        assert a["fault_provenance"]["fault_current_ka"] == pytest.approx(
            b["fault_provenance"]["fault_current_ka"], rel=1e-12, abs=1e-12
        )
        assert a["breaking_capacity"]["status"] == b["breaking_capacity"]["status"] == "PASS"
        assert a["clearing_time"]["status"] == b["clearing_time"]["status"] == "CLEARING_TIME_READY"
        assert a["clearing_time"]["clearing_time"]["conservative_time_s"] == pytest.approx(
            b["clearing_time"]["clearing_time"]["conservative_time_s"], rel=1e-12, abs=1e-12
        )
