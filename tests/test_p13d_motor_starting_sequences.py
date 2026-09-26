from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from mcp_electrico import motor_starting_sequences


ROOT = Path(__file__).resolve().parents[1]


def _manifest() -> dict:
    return json.loads(
        (ROOT / "examples" / "p13_motor_starting_multi_stage3.json").read_text(encoding="utf-8")
    )


def _profiles() -> dict:
    return json.loads(
        (ROOT / "examples" / "p13_motor_starting_multi_profiles_stage3.json").read_text(encoding="utf-8")
    )


def _sequence() -> dict:
    return json.loads(
        (ROOT / "examples" / "p13_motor_starting_sequence_stage3.json").read_text(encoding="utf-8")
    )


def test_p13d_contract_is_cross_industry_explicit_and_static():
    contract = motor_starting_sequences.obtener_contrato_p13d()

    assert contract["schema"] == "MCP_ELECTRICO_P13D_MOTOR_SEQUENCE_CONTRACT_V1"
    assert contract["industry_scope"] == "CROSS_INDUSTRY"
    assert contract["allowed_motor_states"] == ["OFF", "RUNNING", "STARTING_PROFILE_POINT"]
    assert contract["step_semantics"] == "INDEPENDENT_STATIC_STATE_REBUILT_FROM_BASE_MODEL"
    assert contract["minimum_motors_per_sequence"] == 2
    assert contract["interpolation"] is False
    assert contract["dynamic_integration"] is False
    assert contract["automatic_motor_selection"] is False
    assert contract["automatic_start_order"] is False
    assert contract["professional_emission"] is False


def test_p13d_sequence_fixture_is_ready_without_calculation():
    result = motor_starting_sequences.validar_secuencias(
        _manifest(),
        _profiles(),
        _sequence(),
    )

    assert result["validation_status"] == "READY_FOR_STATIC_MOTOR_SEQUENCE"
    assert result["ready_for_execution"] is True
    assert result["issues"] == []
    assert result["electrical_calculation_performed"] is False
    assert result["motor_starting_calculation_performed"] is False
    assert result["dynamic_integration_performed"] is False

    sequence = result["sequences"][0]
    assert sequence["motor_ids"] == ["Motor.m01", "Motor.m02"]
    assert [step["elapsed_time_s"] for step in sequence["steps"]] == [0.0, 1.5, 3.0, 5.0]
    assert [state["state"] for state in sequence["steps"][1]["motor_states"]] == [
        "STARTING_PROFILE_POINT",
        "STARTING_PROFILE_POINT",
    ]


def test_p13d_requires_exactly_one_state_for_each_sequence_motor():
    package = _sequence()
    package["sequences"][0]["steps"][1]["motor_states"].pop()

    result = motor_starting_sequences.validar_secuencias(
        _manifest(),
        _profiles(),
        package,
    )

    assert result["validation_status"] == "BLOCKED_MOTOR_SEQUENCE_INPUTS"
    assert any(issue["code"] == "P13D032" for issue in result["issues"])


def test_p13d_starting_profile_must_belong_to_declared_motor():
    package = _sequence()
    state = package["sequences"][0]["steps"][0]["motor_states"][0]
    state["profile_id"] = "PROFILE-M02"
    state["point_id"] = "M02-T0"

    result = motor_starting_sequences.validar_secuencias(
        _manifest(),
        _profiles(),
        package,
    )

    assert result["validation_status"] == "BLOCKED_MOTOR_SEQUENCE_INPUTS"
    assert any(issue["code"] == "P13D029" for issue in result["issues"])


def test_p13d_executes_staggered_and_overlapping_states_in_isolated_contexts():
    result = motor_starting_sequences.ejecutar_secuencias(
        _manifest(),
        _profiles(),
        _sequence(),
    )

    assert result["schema"] == "MCP_ELECTRICO_P13D_MOTOR_SEQUENCE_EXECUTION_V1"
    assert result["execution_status"] == "STATIC_MOTOR_SEQUENCE_COMPLETED"
    assert result["sequence_count"] == 1
    assert result["parent_context_mutated"] is False
    assert result["parent_workspace_mutated"] is False
    assert result["static_state_rebuild_per_step"] is True
    assert result["interpolation_performed"] is False
    assert result["dynamic_integration_performed"] is False
    assert result["torque_calculation_performed"] is False
    assert result["automatic_motor_selection"] is False
    assert result["automatic_start_order"] is False
    assert result["professional_emission"] is False

    sequence = result["results"][0]
    assert sequence["ok"] is True
    assert sequence["status"] in {"PASS", "FAIL"}
    assert sequence["static_state_rebuild_per_step"] is True
    assert len(sequence["steps"]) == 4

    s0, s1, s2, s3 = sequence["steps"]
    assert s0["status"] in {"PASS", "FAIL"}
    assert s1["status"] in {"PASS", "FAIL"}
    assert len(s1["criterion_evaluations"]) == 2
    assert len(s2["criterion_evaluations"]) == 1
    assert s3["status"] == "OBSERVED"
    assert s3["criterion_status"] == "NOT_APPLICABLE"

    s1_states = {item["motor_id"]: item["state"] for item in s1["applied_states"]}
    assert s1_states == {
        "Motor.m01": "STARTING_PROFILE_POINT",
        "Motor.m02": "STARTING_PROFILE_POINT",
    }
    assert s3["minimum_participant_voltage_pu"] > 0
    assert sequence["worst_starting_criterion"] is not None
    assert sequence["worst_starting_criterion"]["motor_id"] in {"Motor.m01", "Motor.m02"}


def test_p13d_each_step_is_rebuilt_and_results_are_repeatable():
    first = motor_starting_sequences.ejecutar_secuencias(
        _manifest(),
        _profiles(),
        _sequence(),
    )
    second = motor_starting_sequences.ejecutar_secuencias(
        deepcopy(_manifest()),
        deepcopy(_profiles()),
        deepcopy(_sequence()),
    )

    assert first["execution_status"] == second["execution_status"] == "STATIC_MOTOR_SEQUENCE_COMPLETED"
    first_steps = first["results"][0]["steps"]
    second_steps = second["results"][0]["steps"]
    assert [item["status"] for item in first_steps] == [item["status"] for item in second_steps]
    assert [item["minimum_participant_voltage_pu"] for item in first_steps] == [
        item["minimum_participant_voltage_pu"] for item in second_steps
    ]
    assert first["results"][0]["worst_starting_criterion"] == second["results"][0]["worst_starting_criterion"]


def test_p13d_does_not_infer_a_start_order():
    package = _sequence()
    package["sequences"][0]["steps"] = list(reversed(package["sequences"][0]["steps"]))

    result = motor_starting_sequences.validar_secuencias(
        _manifest(),
        _profiles(),
        package,
    )

    assert result["validation_status"] == "BLOCKED_MOTOR_SEQUENCE_INPUTS"
    codes = {issue["code"] for issue in result["issues"]}
    assert "P13D020" in codes or "P13D021" in codes
    assert result["automatic_start_order"] is False
