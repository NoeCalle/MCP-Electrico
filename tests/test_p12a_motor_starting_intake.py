from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from mcp_electrico import motor_starting_intake


def _manifest() -> dict:
    path = Path(__file__).resolve().parents[1] / "examples" / "p12_motor_starting_stage1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_p12a_generic_motor_fixture_is_ready_without_calculation():
    result = motor_starting_intake.evaluar_admision_motor(_manifest())

    assert result["schema"] == "MCP_ELECTRICO_P12A_MOTOR_STARTING_INTAKE_V1"
    assert result["intake_status"] == "READY_FOR_STATIC_MOTOR_STARTING_BUILD"
    assert result["ready_for_static_starting_build"] is True
    assert result["issues"] == []
    assert result["industry_scope"] == "CROSS_INDUSTRY"

    motor = result["motors"][0]
    assert motor["id"] == "Motor.m01"
    assert motor["starting_method"] == "DOL"
    assert motor["starting_current_a"] == 1250.0
    assert motor["starting_power_factor"] == 0.25
    assert motor["running_load_element_id"] == "Load.m01_run"

    study = result["studies"][0]
    assert study["study_type"] == "STATIC_MOTOR_STARTING_VOLTAGE_DIP"
    assert study["minimum_terminal_voltage_pu"] == 0.80

    assert result["electrical_calculation_performed"] is False
    assert result["model_mutation_performed"] is False
    assert result["automatic_starting_current_derivation"] is False
    assert result["automatic_defaults"] is False
    assert result["automatic_dispatch"] is False
    assert result["crosscheck"] is False
    assert result["professional_emission"] is False


def test_p12a_never_derives_starting_current_from_starting_method():
    manifest = _manifest()
    motor = manifest["motors"][0]
    motor["starting_method"] = "STAR_DELTA"
    motor["starting_current_a"] = None

    result = motor_starting_intake.evaluar_admision_motor(manifest)

    assert result["intake_status"] == "BLOCKED_MOTOR_STARTING_INPUTS"
    assert result["ready_for_static_starting_build"] is False
    assert any(
        issue["path"] == "motors[0].starting_current_a"
        for issue in result["issues"]
    )
    assert result["automatic_starting_current_derivation"] is False


def test_p12a_requires_explicit_running_load_replacement_semantics():
    manifest = _manifest()
    manifest["motors"][0]["running_load_element_id"] = None

    result = motor_starting_intake.evaluar_admision_motor(manifest)

    assert result["intake_status"] == "BLOCKED_MOTOR_STARTING_INPUTS"
    assert any(issue["code"] == "P12A032" for issue in result["issues"])


def test_p12a_rejects_running_load_on_different_bus():
    manifest = _manifest()
    manifest["base_model"]["topology"]["loads"][1]["bus"] = "bus_480"

    result = motor_starting_intake.evaluar_admision_motor(manifest)

    assert result["intake_status"] == "BLOCKED_MOTOR_STARTING_INPUTS"
    assert any(issue["code"] == "P12A034" for issue in result["issues"])


def test_p12a_rejects_unsupported_phase_count_and_invalid_pf():
    manifest = _manifest()
    manifest["motors"][0]["phases"] = 1
    manifest["motors"][0]["starting_power_factor"] = 1.2

    result = motor_starting_intake.evaluar_admision_motor(manifest)

    assert result["intake_status"] == "BLOCKED_MOTOR_STARTING_INPUTS"
    codes = {issue["code"] for issue in result["issues"]}
    assert "P12A026" in codes
    assert "P12A030" in codes


def test_p12a_propagates_invalid_base_model_without_mutation():
    manifest = _manifest()
    manifest["base_model"]["source"]["bus"] = None

    result = motor_starting_intake.evaluar_admision_motor(manifest)

    assert result["intake_status"] == "BLOCKED_MOTOR_STARTING_INPUTS"
    assert any(issue["code"] == "P12A011" for issue in result["issues"])
    assert result["base_model_admission"]["ready_to_build_model"] is False
    assert result["electrical_calculation_performed"] is False
    assert result["model_mutation_performed"] is False


def test_p12a_study_requires_explicit_project_voltage_criterion():
    manifest = _manifest()
    manifest["studies"][0]["minimum_terminal_voltage_pu"] = None

    result = motor_starting_intake.evaluar_admision_motor(manifest)

    assert result["intake_status"] == "BLOCKED_MOTOR_STARTING_INPUTS"
    assert any(
        issue["path"] == "studies[0].minimum_terminal_voltage_pu"
        for issue in result["issues"]
    )


def test_p12a_contract_is_cross_industry_and_static_only():
    contract = motor_starting_intake.obtener_contrato_p12a()

    assert contract["industry_scope"] == "CROSS_INDUSTRY"
    assert contract["supported_study_type"] == "STATIC_MOTOR_STARTING_VOLTAGE_DIP"
    assert "DOL" in contract["supported_starting_methods"]
    assert "VFD" in contract["supported_starting_methods"]
    assert contract["automatic_starting_current_derivation"] is False
    assert contract["professional_emission"] is False
