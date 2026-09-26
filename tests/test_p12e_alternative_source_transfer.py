from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from mcp_electrico import operating_scenarios, workspace_state


def _manifest() -> dict:
    path = Path(__file__).resolve().parents[1] / "examples" / "p10_reference_substation_stage1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _package() -> dict:
    path = Path(__file__).resolve().parents[1] / "examples" / "p12e_alternative_source_transfer_reference.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_p12e_contract_accepts_explicit_break_before_make_transfer():
    result = operating_scenarios.validar_paquete(_manifest(), _package())

    assert result["validation_status"] == "READY_FOR_SCENARIO_EXECUTION"
    assert result["ready_for_execution"] is True
    assert result["issues"] == []
    assert result["electrical_calculation_performed"] is False
    assert result["model_mutation_performed"] is False
    assert result["automatic_source_selection"] is False
    assert result["automatic_transfer"] is False
    assert result["professional_emission"] is False

    contract = operating_scenarios.obtener_contrato()
    assert "ENABLE_ALT_SOURCE" in contract["allowed_actions"]
    assert contract["transfer_policy"] == "EXPLICIT_BREAK_BEFORE_MAKE_ONLY"
    assert contract["automatic_source_selection"] is False
    assert contract["automatic_transfer"] is False
    assert contract["closed_transition_transfer"] is False


def test_p12e_requires_explicit_positive_sequence_source_strength():
    package = _package()
    package["alternative_sources"][0]["scc_mva"] = None
    package["alternative_sources"][0]["x_r"] = None

    result = operating_scenarios.validar_paquete(_manifest(), package)

    assert result["validation_status"] == "BLOCKED_SCENARIO_INPUTS"
    paths = {item["path"] for item in result["issues"]}
    assert "alternative_sources[0].scc_mva" in paths
    assert "alternative_sources[0].x_r" in paths
    assert result["electrical_calculation_performed"] is False


def test_p12e_rejects_enable_before_required_isolation():
    package = _package()
    actions = package["scenarios"][0]["actions"]
    package["scenarios"][0]["actions"] = [actions[1], actions[0]]

    result = operating_scenarios.validar_paquete(_manifest(), package)

    assert result["validation_status"] == "BLOCKED_SCENARIO_INPUTS"
    assert any(item["code"] == "P12E021" for item in result["issues"])
    assert result["model_mutation_performed"] is False


def test_p12e_rejects_undeclared_alternative_source():
    package = _package()
    package["scenarios"][0]["actions"][1]["element_id"] = "Vsource.unknown"

    result = operating_scenarios.validar_paquete(_manifest(), package)

    assert result["validation_status"] == "BLOCKED_SCENARIO_INPUTS"
    assert any(item["code"] in {"P12E020", "P12E022"} for item in result["issues"])


def test_p12e_executes_backup_transfer_and_restores_base_model():
    result = operating_scenarios.ejecutar_paquete(_manifest(), _package())

    assert result["execution_status"] == "SCENARIO_SET_EXECUTION_COMPLETED"
    assert result["summary"] == {
        "total": 1,
        "executed": 1,
        "pass": 1,
        "fail": 0,
        "blocked_or_error": 0,
    }
    assert result["model_restored_after_each_scenario"] is True
    assert result["automatic_source_selection"] is False
    assert result["automatic_transfer"] is False
    assert result["professional_emission"] is False

    scenario = result["scenario_results"][0]
    assert scenario["execution_status"] == "SCENARIO_EXECUTED"
    assert scenario["scenario_status"] == "PASS"
    assert scenario["model_restored"] is True
    assert scenario["restored_powerflow_converged"] is True
    assert scenario["model_revision_unchanged"] is True

    assert len(scenario["alternative_sources_materialized"]) == 1
    alt = scenario["alternative_sources_materialized"][0]
    assert alt["id"] == "Vsource.backup_480"
    assert alt["source_type"] == "THEVENIN_VSOURCE_EQUIVALENT"
    assert alt["initial_enabled"] is False
    assert alt["zero_sequence_modeled"] is False
    assert alt["positive_sequence_equivalent"]["r1_ohm"] > 0
    assert alt["positive_sequence_equivalent"]["x1_ohm"] > 0

    actions = scenario["action_results"]
    assert actions[0]["action"] == "OPEN_ELEMENT"
    assert actions[0]["element_id"] == "Transformer.t2_aux"
    assert actions[0]["effective_open_state"] is True
    assert actions[1]["action"] == "ENABLE_ALT_SOURCE"
    assert actions[1]["element_id"] == "Vsource.backup_480"
    assert actions[1]["effective_enabled_state"] is True
    assert actions[1]["break_before_make_contract"] is True

    check = scenario["service"]["critical_load_checks"][0]
    assert check["load_id"] == "Load.lv_services"
    assert check["load_enabled"] is True
    assert check["service_ok"] is True
    assert min(check["voltage_pu"]) >= 0.9

    assert workspace_state.status()["studies"] == {}


def test_p12e_transfer_is_repeatable():
    first = operating_scenarios.ejecutar_paquete(_manifest(), _package())
    second = operating_scenarios.ejecutar_paquete(deepcopy(_manifest()), deepcopy(_package()))

    assert first["summary"] == second["summary"]
    first_scenario = first["scenario_results"][0]
    second_scenario = second["scenario_results"][0]
    assert first_scenario["scenario_status"] == second_scenario["scenario_status"] == "PASS"
    assert first_scenario["service"] == second_scenario["service"]
    assert first_scenario["model_restored"] is True
    assert second_scenario["model_restored"] is True
