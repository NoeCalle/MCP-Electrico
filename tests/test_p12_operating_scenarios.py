from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from mcp_electrico import operating_scenarios, workspace_state


def _manifest() -> dict:
    path = Path(__file__).resolve().parents[1] / "examples" / "p10_reference_substation_stage1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _package() -> dict:
    path = Path(__file__).resolve().parents[1] / "examples" / "p12_operating_scenarios_reference.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_p12_contract_is_multiindustry_and_fail_closed():
    result = operating_scenarios.validar_paquete(_manifest(), _package())

    assert result["schema"] == "MCP_ELECTRICO_P12_OPERATING_SCENARIOS_V1"
    assert result["validation_status"] == "READY_FOR_SCENARIO_EXECUTION"
    assert result["ready_for_execution"] is True
    assert result["scenario_count"] == 2
    assert result["issues"] == []
    assert result["electrical_calculation_performed"] is False
    assert result["model_mutation_performed"] is False
    assert result["automatic_contingency_selection"] is False
    assert result["automatic_switching"] is False
    assert result["automatic_load_shedding"] is False
    assert result["professional_emission"] is False


def test_p12_rejects_unknown_or_ambiguous_switching_inputs():
    package = _package()
    scenario = package["scenarios"][0]
    scenario["actions"].append({
        "action": "CLOSE_ELEMENT",
        "element_id": "Line.mv_feeder",
        "source_reference": "duplicate action",
    })
    scenario["actions"].append({
        "action": "OPEN_ELEMENT",
        "element_id": "Line.does_not_exist",
        "source_reference": "unknown element",
    })

    result = operating_scenarios.validar_paquete(_manifest(), package)

    assert result["validation_status"] == "BLOCKED_SCENARIO_INPUTS"
    assert result["ready_for_execution"] is False
    codes = {item["code"] for item in result["issues"]}
    assert "P12A016" in codes
    assert "P12A015" in codes
    assert result["electrical_calculation_performed"] is False


def test_p12_executes_explicit_scenarios_and_restores_base_model():
    result = operating_scenarios.ejecutar_paquete(_manifest(), _package())

    assert result["execution_status"] == "SCENARIO_SET_EXECUTION_COMPLETED"
    assert result["summary"]["total"] == 2
    assert result["summary"]["executed"] == 2
    assert result["summary"]["pass"] == 1
    assert result["summary"]["fail"] == 1
    assert result["summary"]["blocked_or_error"] == 0
    assert result["scenario_independence"] == "REBUILD_BASE_BEFORE_EACH_SCENARIO"
    assert result["model_restored_after_each_scenario"] is True
    assert result["electrical_calculation_performed"] is True
    assert result["automatic_contingency_selection"] is False
    assert result["automatic_switching"] is False
    assert result["automatic_load_shedding"] is False
    assert result["professional_emission"] is False

    by_id = {item["scenario_id"]: item for item in result["scenario_results"]}

    preserved = by_id["SCN_BRANCH_OUTAGE_SERVICE_PRESERVED"]
    assert preserved["execution_status"] == "SCENARIO_EXECUTED"
    assert preserved["scenario_status"] == "PASS"
    assert preserved["service"]["powerflow_converged"] is True
    assert preserved["service"]["all_critical_loads_ok"] is True
    assert preserved["action_results"][0]["element_id"] == "Line.mv_feeder"
    assert preserved["action_results"][0]["effective_open_state"] is True
    assert preserved["model_restored"] is True
    assert preserved["model_revision_unchanged"] is True

    failed = by_id["SCN_ESSENTIAL_TRANSFORMER_OUTAGE"]
    assert failed["execution_status"] == "SCENARIO_EXECUTED"
    assert failed["scenario_status"] == "FAIL"
    assert failed["service"]["all_critical_loads_ok"] is False
    check = failed["service"]["critical_load_checks"][0]
    assert check["load_id"] == "Load.lv_services"
    assert check["service_ok"] is False
    assert failed["model_restored"] is True
    assert failed["model_revision_unchanged"] is True

    assert workspace_state.status()["studies"] == {}


def test_p12_scenarios_are_repeatable():
    manifest = _manifest()
    package = _package()

    first = operating_scenarios.ejecutar_paquete(manifest, package)
    second = operating_scenarios.ejecutar_paquete(deepcopy(manifest), deepcopy(package))

    assert first["summary"] == second["summary"]

    first_by_id = {item["scenario_id"]: item for item in first["scenario_results"]}
    second_by_id = {item["scenario_id"]: item for item in second["scenario_results"]}
    assert first_by_id.keys() == second_by_id.keys()

    for sid in first_by_id:
        assert first_by_id[sid]["scenario_status"] == second_by_id[sid]["scenario_status"]
        assert first_by_id[sid]["service"] == second_by_id[sid]["service"]
        assert first_by_id[sid]["model_restored"] is True
        assert second_by_id[sid]["model_restored"] is True
