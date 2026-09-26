from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from mcp_electrico import operating_scenarios, workspace_state


def _manifest() -> dict:
    path = Path(__file__).resolve().parents[1] / "examples" / "p10_reference_substation_stage1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _package() -> dict:
    path = Path(__file__).resolve().parents[1] / "examples" / "p12c_explicit_load_state_reference.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_p12c_contract_accepts_explicit_load_state_actions():
    result = operating_scenarios.validar_paquete(_manifest(), _package())

    assert result["validation_status"] == "READY_FOR_SCENARIO_EXECUTION"
    assert result["ready_for_execution"] is True
    assert result["issues"] == []
    assert result["automatic_load_shedding"] is False
    assert result["electrical_calculation_performed"] is False
    assert result["model_mutation_performed"] is False
    assert result["professional_emission"] is False


def test_p12c_rejects_unknown_load_without_executing():
    package = _package()
    package["scenarios"][0]["actions"][0]["element_id"] = "Load.unknown"

    result = operating_scenarios.validar_paquete(_manifest(), package)

    assert result["validation_status"] == "BLOCKED_SCENARIO_INPUTS"
    assert result["ready_for_execution"] is False
    assert any(item["code"] == "P12C002" for item in result["issues"])
    assert result["electrical_calculation_performed"] is False


def test_p12c_manual_shedding_and_critical_load_off_are_distinguished():
    result = operating_scenarios.ejecutar_paquete(_manifest(), _package())

    assert result["execution_status"] == "SCENARIO_SET_EXECUTION_COMPLETED"
    assert result["summary"] == {
        "total": 2,
        "executed": 2,
        "pass": 1,
        "fail": 1,
        "blocked_or_error": 0,
    }
    assert result["model_restored_after_each_scenario"] is True
    assert result["automatic_load_shedding"] is False
    assert result["professional_emission"] is False

    by_id = {item["scenario_id"]: item for item in result["scenario_results"]}

    shed = by_id["SCN_MANUAL_SHED_NONCRITICAL_LOAD"]
    assert shed["scenario_status"] == "PASS"
    assert shed["action_results"][0]["action"] == "DISABLE_LOAD"
    assert shed["action_results"][0]["element_id"] == "Load.mv_process"
    assert shed["action_results"][0]["effective_enabled_state"] is False
    critical = shed["service"]["critical_load_checks"][0]
    assert critical["load_id"] == "Load.lv_services"
    assert critical["load_enabled"] is True
    assert critical["service_ok"] is True
    assert shed["model_restored"] is True

    critical_off = by_id["SCN_EXPLICIT_CRITICAL_LOAD_OFF"]
    assert critical_off["scenario_status"] == "FAIL"
    assert critical_off["action_results"][0]["effective_enabled_state"] is False
    check = critical_off["service"]["critical_load_checks"][0]
    assert check["load_id"] == "Load.lv_services"
    assert check["load_enabled"] is False
    assert check["service_ok"] is False
    assert critical_off["model_restored"] is True

    assert workspace_state.status()["studies"] == {}


def test_p12c_explicit_load_state_is_repeatable():
    first = operating_scenarios.ejecutar_paquete(_manifest(), _package())
    second = operating_scenarios.ejecutar_paquete(deepcopy(_manifest()), deepcopy(_package()))

    assert first["summary"] == second["summary"]
    first_by_id = {item["scenario_id"]: item for item in first["scenario_results"]}
    second_by_id = {item["scenario_id"]: item for item in second["scenario_results"]}

    for sid in first_by_id:
        assert first_by_id[sid]["scenario_status"] == second_by_id[sid]["scenario_status"]
        assert first_by_id[sid]["service"] == second_by_id[sid]["service"]
        assert first_by_id[sid]["model_restored"] is True
        assert second_by_id[sid]["model_restored"] is True
