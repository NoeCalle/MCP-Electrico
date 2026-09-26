from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from mcp_electrico import core, motor_starting_profiles, workspace_state


ROOT = Path(__file__).resolve().parents[1]


def _manifest() -> dict:
    return json.loads(
        (ROOT / "examples" / "p13_motor_starting_stage1.json").read_text(encoding="utf-8")
    )


def _profile_package() -> dict:
    return json.loads(
        (ROOT / "examples" / "p13_motor_starting_profile_stage2.json").read_text(
            encoding="utf-8"
        )
    )


def _seed_parent() -> tuple[str, list[str], dict]:
    core.crear_circuito(
        "p13c_parent_guard",
        4.16,
        frecuencia=60,
        bus_fuente="parent_source",
    )
    core.agregar_carga(
        "parent_guard_load",
        "parent_source",
        30.0,
        6.0,
        fases=3,
        kv=4.16,
    )
    workspace_state.reset_for_circuit("p13c_parent_guard_seed")
    from opendssdirect import dss

    return (
        str(dss.Circuit.Name() or ""),
        sorted(str(item) for item in dss.Circuit.AllElementNames()),
        deepcopy(workspace_state.status()),
    )


def _parent_snapshot() -> tuple[str, list[str], dict]:
    from opendssdirect import dss

    return (
        str(dss.Circuit.Name() or ""),
        sorted(str(item) for item in dss.Circuit.AllElementNames()),
        deepcopy(workspace_state.status()),
    )


def test_p13c_contract_is_cross_industry_static_and_non_interpolating():
    contract = motor_starting_profiles.obtener_contrato_p13c()

    assert contract["schema"] == "MCP_ELECTRICO_P13C_MOTOR_STARTING_PROFILE_CONTRACT_V1"
    assert contract["industry_scope"] == "CROSS_INDUSTRY"
    assert contract["profile_semantics"] == "DECLARED_STATIC_OPERATING_POINTS_ORDERED_BY_TIME"
    assert contract["current_basis"] == "SUPPLY_LINE_RMS_AT_RATED_VOLTAGE"
    assert contract["power_factor_basis"] == "FUNDAMENTAL_DISPLACEMENT"
    assert contract["point_isolation"] == "FRESH_OPENDSS_NEW_CONTEXT_PER_POINT"
    assert contract["elapsed_time_used_by_solver"] is False
    assert contract["interpolation"] is False
    assert contract["dynamic_integration"] is False
    assert contract["automatic_profile_generation"] is False
    assert contract["automatic_starting_current_derivation"] is False
    assert contract["automatic_defaults"] is False
    assert contract["professional_emission"] is False


def test_p13c_profile_fixture_is_ready_without_electrical_calculation():
    result = motor_starting_profiles.validar_perfiles(_manifest(), _profile_package())

    assert result["validation_status"] == "READY_FOR_STATIC_STARTING_PROFILE"
    assert result["ready_for_execution"] is True
    assert result["issues"] == []
    assert result["electrical_calculation_performed"] is False
    assert result["motor_starting_calculation_performed"] is False
    assert result["elapsed_time_used_by_solver"] is False
    assert result["dynamic_integration_performed"] is False

    profile = result["profiles"][0]
    assert profile["id"] == "PROFILE-M01"
    assert profile["study_id"] == "START-M01"
    assert profile["current_basis"] == "SUPPLY_LINE_RMS_AT_RATED_VOLTAGE"
    assert profile["power_factor_basis"] == "FUNDAMENTAL_DISPLACEMENT"
    assert [point["elapsed_time_s"] for point in profile["points"]] == [0.0, 0.5, 1.5, 3.0]


def test_p13c_requires_explicit_profile_bases():
    package = _profile_package()
    package["profiles"][0]["current_basis"] = None
    package["profiles"][0]["power_factor_basis"] = "TRUE_PF_WITH_HARMONICS"

    result = motor_starting_profiles.validar_perfiles(_manifest(), package)

    assert result["validation_status"] == "BLOCKED_STARTING_PROFILE_INPUTS"
    codes = {issue["code"] for issue in result["issues"]}
    assert "P13C013" in codes
    assert "P13C014" in codes


def test_p13c_first_point_must_match_p13a_initial_starting_data():
    package = _profile_package()
    package["profiles"][0]["points"][0]["starting_current_a"] = 1200.0

    result = motor_starting_profiles.validar_perfiles(_manifest(), package)

    assert result["validation_status"] == "BLOCKED_STARTING_PROFILE_INPUTS"
    assert result["ready_for_execution"] is False
    assert any(issue["code"] == "P13C026" for issue in result["issues"])
    assert result["automatic_starting_current_derivation"] is False


def test_p13c_times_must_be_strictly_increasing():
    package = _profile_package()
    package["profiles"][0]["points"][2]["elapsed_time_s"] = 0.5

    result = motor_starting_profiles.validar_perfiles(_manifest(), package)

    assert result["validation_status"] == "BLOCKED_STARTING_PROFILE_INPUTS"
    assert any(issue["code"] == "P13C020" for issue in result["issues"])


def test_p13c_executes_each_declared_point_in_fresh_isolated_context():
    parent = _seed_parent()

    result = motor_starting_profiles.ejecutar_perfiles(_manifest(), _profile_package())

    assert result["schema"] == "MCP_ELECTRICO_P13C_MOTOR_STARTING_PROFILE_EXECUTION_V1"
    assert result["execution_status"] == "STATIC_STARTING_PROFILE_COMPLETED"
    assert result["profile_count"] == 1
    assert result["isolation_mode"] == "OPENDSS_NEW_CONTEXT"
    assert result["point_isolation"] == "FRESH_OPENDSS_NEW_CONTEXT_PER_POINT"
    assert result["parent_context_mutated"] is False
    assert result["parent_workspace_mutated"] is False
    assert _parent_snapshot() == parent
    assert result["elapsed_time_used_by_solver"] is False
    assert result["interpolation_performed"] is False
    assert result["dynamic_integration_performed"] is False
    assert result["torque_calculation_performed"] is False
    assert result["automatic_profile_generation"] is False
    assert result["automatic_starting_current_derivation"] is False
    assert result["professional_emission"] is False

    profile = result["results"][0]
    assert profile["ok"] is True
    assert profile["status"] in {"PASS", "FAIL"}
    assert profile["engine"] == "OpenDSS"
    assert profile["method"] == "DECLARED_STATIC_PROFILE_POINTS"
    assert profile["current_basis"] == "SUPPLY_LINE_RMS_AT_RATED_VOLTAGE"
    assert profile["power_factor_basis"] == "FUNDAMENTAL_DISPLACEMENT"
    assert profile["pre_start_converged"] is True
    assert profile["running_load_disabled"] == "Load.m01_run"
    assert len(profile["points"]) == 4
    assert all(point["ok"] is True for point in profile["points"])
    assert all(point["isolated_context_per_point"] is True for point in profile["points"])
    assert all(point["elapsed_time_used_by_solver"] is False for point in profile["points"])
    assert all(len(point["voltage_pu_by_phase"]) == 3 for point in profile["points"])

    first = profile["points"][0]
    last = profile["points"][-1]
    assert first["id"] == "T0"
    assert last["id"] == "T3"
    assert last["starting_current_a"] < first["starting_current_a"]
    assert last["minimum_voltage_pu"] > first["minimum_voltage_pu"]
    assert profile["worst_point"]["id"] == "T0"


def test_p13c_elapsed_time_is_ordering_metadata_not_solver_input():
    base_package = _profile_package()
    altered = deepcopy(base_package)
    altered["profiles"][0]["points"][1]["elapsed_time_s"] = 0.2
    altered["profiles"][0]["points"][2]["elapsed_time_s"] = 10.0
    altered["profiles"][0]["points"][3]["elapsed_time_s"] = 100.0

    first = motor_starting_profiles.ejecutar_perfiles(_manifest(), base_package)
    second = motor_starting_profiles.ejecutar_perfiles(_manifest(), altered)

    assert first["execution_status"] == second["execution_status"] == "STATIC_STARTING_PROFILE_COMPLETED"
    a = first["results"][0]
    b = second["results"][0]
    assert [point["minimum_voltage_pu"] for point in a["points"]] == [
        point["minimum_voltage_pu"] for point in b["points"]
    ]
    assert a["worst_point"]["id"] == b["worst_point"]["id"] == "T0"
    assert first["elapsed_time_used_by_solver"] is False
    assert second["elapsed_time_used_by_solver"] is False


def test_p13c_profile_execution_is_repeatable():
    first = motor_starting_profiles.ejecutar_perfiles(_manifest(), _profile_package())
    second = motor_starting_profiles.ejecutar_perfiles(
        deepcopy(_manifest()),
        deepcopy(_profile_package()),
    )

    assert first["execution_status"] == second["execution_status"] == "STATIC_STARTING_PROFILE_COMPLETED"
    first_profile = first["results"][0]
    second_profile = second["results"][0]
    assert [item["minimum_voltage_pu"] for item in first_profile["points"]] == [
        item["minimum_voltage_pu"] for item in second_profile["points"]
    ]
    assert first_profile["worst_point"]["id"] == second_profile["worst_point"]["id"]


def test_p13c_rejects_profile_package_from_another_project():
    package = _profile_package()
    package["project_id"] = "OTHER-PROJECT"

    result = motor_starting_profiles.validar_perfiles(_manifest(), package)

    assert result["validation_status"] == "BLOCKED_STARTING_PROFILE_INPUTS"
    assert any(issue["code"] == "P13C003" for issue in result["issues"])
