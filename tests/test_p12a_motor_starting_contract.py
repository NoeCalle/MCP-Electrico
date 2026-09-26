from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from mcp_electrico import motor_starting_contract


def _fixture() -> dict:
    path = Path(__file__).resolve().parents[1] / "examples" / "p12a_motor_starting_reference.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_p12a_reference_fixture_is_ready_without_calculation_or_mutation():
    result = motor_starting_contract.evaluar_admision(_fixture())

    assert result["schema"] == "MCP_ELECTRICO_P12A_MOTOR_STARTING_INPUT_V1"
    assert result["admission_status"] == "READY_FOR_MOTOR_STARTING_MODEL"
    assert result["ready_for_motor_starting_model"] is True
    assert result["requested_studies"] == [
        "STARTING_VOLTAGE_DIP",
        "ACCELERATION_TIME",
    ]
    assert result["issue_count"] == 0
    assert result["issues"] == []
    assert result["electrical_calculation_performed"] is False
    assert result["dynamic_simulation_performed"] is False
    assert result["model_mutation_performed"] is False
    assert result["automatic_defaults"] is False
    assert result["automatic_dispatch"] is False
    assert result["professional_emission"] is False

    motor = result["motors"][0]
    assert motor["id"] == "MTR-01"
    assert motor["motor_type"] == "INDUCTION_SQUIRREL_CAGE"
    assert motor["starter_type"] == "DOL"


def test_p12a_dol_blocks_when_locked_rotor_current_is_missing():
    payload = _fixture()
    payload["motors"][0]["starter"].pop("locked_rotor_current_ratio")

    result = motor_starting_contract.evaluar_admision(payload)

    assert result["admission_status"] == "BLOCKED_MISSING_MOTOR_STARTING_INPUTS"
    assert result["ready_for_motor_starting_model"] is False
    assert any(
        issue["code"] == "P12A_S010"
        and issue["path"] == "motors[0].starter.locked_rotor_current_ratio"
        for issue in result["issues"]
    )
    assert result["electrical_calculation_performed"] is False
    assert result["dynamic_simulation_performed"] is False


def test_p12a_voltage_dip_only_does_not_require_mechanical_inertia():
    payload = _fixture()
    payload["requested_studies"] = ["STARTING_VOLTAGE_DIP"]
    payload["motors"][0].pop("mechanical")

    result = motor_starting_contract.evaluar_admision(payload)

    assert result["admission_status"] == "READY_FOR_MOTOR_STARTING_MODEL"
    assert result["issues"] == []


def test_p12a_acceleration_time_requires_explicit_mechanical_data():
    payload = _fixture()
    payload["motors"][0].pop("mechanical")

    result = motor_starting_contract.evaluar_admision(payload)

    assert result["admission_status"] == "BLOCKED_MISSING_MOTOR_STARTING_INPUTS"
    assert any(issue["code"] == "P12A_M001" for issue in result["issues"])


def test_p12a_vfd_has_its_own_input_contract_and_is_not_treated_as_reduced_dol():
    payload = _fixture()
    payload["requested_studies"] = ["STARTING_VOLTAGE_DIP"]
    payload["motors"][0].pop("mechanical")
    payload["motors"][0]["starter"] = {
        "type": "VFD",
        "drive_rating_kw": 315.0,
        "input_current_limit_a": 450.0,
        "input_power_factor": 0.96,
        "control_mode": "VECTOR",
    }

    result = motor_starting_contract.evaluar_admision(payload)

    assert result["admission_status"] == "READY_FOR_MOTOR_STARTING_MODEL"
    assert result["motors"][0]["starter_type"] == "VFD"

    broken = deepcopy(payload)
    broken["motors"][0]["starter"].pop("drive_rating_kw")
    blocked = motor_starting_contract.evaluar_admision(broken)
    assert blocked["admission_status"] == "BLOCKED_MISSING_MOTOR_STARTING_INPUTS"
    assert any(
        issue["code"] == "P12A_S040"
        and issue["path"] == "motors[0].starter.drive_rating_kw"
        for issue in blocked["issues"]
    )


def test_p12a_soft_starter_requires_current_limit_ramp_and_input_pf():
    payload = _fixture()
    payload["requested_studies"] = ["STARTING_VOLTAGE_DIP"]
    payload["motors"][0].pop("mechanical")
    payload["motors"][0]["starter"] = {
        "type": "SOFT_STARTER",
        "current_limit_pu": 3.5,
        "ramp_time_s": 8.0,
        "input_power_factor": 0.85,
    }

    result = motor_starting_contract.evaluar_admision(payload)
    assert result["admission_status"] == "READY_FOR_MOTOR_STARTING_MODEL"

    payload["motors"][0]["starter"]["ramp_time_s"] = None
    blocked = motor_starting_contract.evaluar_admision(payload)
    assert any(issue["code"] == "P12A_S031" for issue in blocked["issues"])


def test_p12a_star_delta_requires_explicit_transition():
    payload = _fixture()
    payload["requested_studies"] = ["STARTING_VOLTAGE_DIP"]
    payload["motors"][0].pop("mechanical")
    payload["motors"][0]["starter"] = {
        "type": "STAR_DELTA",
        "locked_rotor_current_ratio_delta": 6.0,
        "starting_power_factor": 0.25,
        "transition": "OPEN",
    }

    result = motor_starting_contract.evaluar_admision(payload)
    assert result["admission_status"] == "READY_FOR_MOTOR_STARTING_MODEL"

    payload["motors"][0]["starter"]["transition"] = "UNKNOWN"
    blocked = motor_starting_contract.evaluar_admision(payload)
    assert any(issue["code"] == "P12A_S022" for issue in blocked["issues"])


def test_p12a_explicit_torque_points_must_be_monotonic_and_nonnegative():
    payload = _fixture()
    payload["motors"][0]["mechanical"] = {
        "motor_inertia_kg_m2": 4.0,
        "load_inertia_kg_m2": 12.0,
        "load_torque_model": "EXPLICIT_POINTS",
        "load_torque_points": [
            {"speed_pu": 0.0, "torque_pu": 0.3},
            {"speed_pu": 0.5, "torque_pu": 0.7},
            {"speed_pu": 1.0, "torque_pu": 1.0},
        ],
    }

    ready = motor_starting_contract.evaluar_admision(payload)
    assert ready["admission_status"] == "READY_FOR_MOTOR_STARTING_MODEL"

    payload["motors"][0]["mechanical"]["load_torque_points"][2]["speed_pu"] = 0.4
    blocked = motor_starting_contract.evaluar_admision(payload)
    assert any(issue["code"] == "P12A_M008" for issue in blocked["issues"])


def test_p12a_rejects_unsupported_single_phase_or_motor_type_without_approximation():
    payload = _fixture()
    payload["motors"][0]["phases"] = 1
    payload["motors"][0]["motor_type"] = "SYNCHRONOUS"

    result = motor_starting_contract.evaluar_admision(payload)

    assert result["admission_status"] == "BLOCKED_MISSING_MOTOR_STARTING_INPUTS"
    codes = {issue["code"] for issue in result["issues"]}
    assert "P12A_035" in codes
    assert "P12A_039" in codes
    assert result["automatic_defaults"] is False
