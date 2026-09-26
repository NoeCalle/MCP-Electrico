from __future__ import annotations

import json
from copy import deepcopy
from math import sqrt
from pathlib import Path

import pytest

from mcp_electrico import core, motor_starting_static, workspace_state


def _manifest() -> dict:
    path = Path(__file__).resolve().parents[1] / "examples" / "p13_motor_starting_stage1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _seed_parent() -> tuple[str, list[str], dict]:
    core.crear_circuito(
        "p13b_parent_guard",
        4.16,
        frecuencia=60,
        bus_fuente="parent_source",
    )
    core.agregar_carga(
        "parent_guard_load",
        "parent_source",
        25.0,
        5.0,
        fases=3,
        kv=4.16,
    )
    workspace_state.reset_for_circuit("p13b_parent_guard_seed")
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


def test_p13b_readiness_builds_isolated_model_without_solve_or_parent_mutation():
    parent = _seed_parent()

    result = motor_starting_static.evaluar_readiness(_manifest())

    assert result["schema"] == "MCP_ELECTRICO_P13B_MOTOR_STARTING_READINESS_V1"
    assert result["readiness_status"] == "READY_FOR_STATIC_MOTOR_STARTING"
    assert result["ready_for_execution"] is True
    assert result["issues"] == []
    assert result["industry_scope"] == "CROSS_INDUSTRY"
    assert result["engine"] == "OpenDSS"
    assert result["isolation_mode"] == "OPENDSS_NEW_CONTEXT"
    assert result["method"] == "EQUIVALENT_STARTING_IMPEDANCE"

    base = result["base_model"]
    assert base["materializer_status"] == "ISOLATED_MODEL_BUILT_NOT_EXECUTED"
    assert base["engine_defaults_retained_count"] == 0
    assert base["solve_performed"] is False
    assert base["isolation_mode"] == "OPENDSS_NEW_CONTEXT"

    assert result["parent_context_mutated"] is False
    assert _parent_snapshot() == parent
    assert result["electrical_calculation_performed"] is False
    assert result["motor_starting_calculation_performed"] is False
    assert result["dynamic_acceleration_calculation_performed"] is False
    assert result["torque_calculation_performed"] is False
    assert result["automatic_starting_current_derivation"] is False
    assert result["professional_emission"] is False


def test_p13b_blocks_if_base_network_would_retain_relevant_engine_default():
    manifest = _manifest()
    manifest["base_model"]["topology"]["lines"][0]["c1_nf_km"] = None

    result = motor_starting_static.evaluar_readiness(manifest)

    assert result["readiness_status"] == "BLOCKED_BY_BASE_ENGINE_DEFAULTS"
    assert result["ready_for_execution"] is False
    assert any(
        issue["path"] == "base_model.topology.lines[0].c1_nf_km"
        for issue in result["issues"]
    )
    assert result["electrical_calculation_performed"] is False
    assert result["parent_context_mutated"] is False


def test_p13b_executes_static_start_in_fresh_isolated_context():
    parent = _seed_parent()

    result = motor_starting_static.ejecutar_estudios(_manifest())

    assert result["schema"] == "MCP_ELECTRICO_P13B_MOTOR_STARTING_STATIC_V1"
    assert result["execution_status"] == "STATIC_MOTOR_STARTING_COMPLETED"
    assert result["study_count"] == 1
    assert result["isolation_mode"] == "OPENDSS_NEW_CONTEXT"
    assert result["parent_context_mutated_by_starting_execution"] is False
    assert result["parent_workspace_mutated_by_starting_execution"] is False
    assert _parent_snapshot() == parent

    study = result["results"][0]
    assert study["ok"] is True
    assert study["status"] in {"PASS", "FAIL"}
    assert study["pre_start_motor_state"] == "OFF"
    assert study["running_load_disabled"] == "Load.m01_run"
    assert study["pre_start_converged"] is True
    assert study["starting_converged"] is True
    assert len(study["pre_start_voltage_pu_by_phase"]) == 3
    assert len(study["starting_voltage_pu_by_phase"]) == 3
    assert study["pre_start_min_voltage_pu"] > 0
    assert study["starting_min_voltage_pu"] > 0
    assert study["starting_min_voltage_pu"] < study["pre_start_min_voltage_pu"]
    assert study["voltage_dip_pu"] > 0
    assert study["voltage_dip_pct"] > 0

    expected_s = sqrt(3.0) * 0.48 * 1250.0
    expected_p = expected_s * 0.25
    assert study["starting_demand"]["apparent_kva_at_rated_voltage"] == pytest.approx(expected_s)
    assert study["starting_demand"]["active_kw_at_rated_voltage"] == pytest.approx(expected_p)

    model = study["equivalent_load_model"]
    assert model["opendss_load_model"] == 2
    assert model["semantics"] == (
        "CONSTANT_IMPEDANCE_EQUIVALENT_FROM_EXPLICIT_SUPPLY_LINE_RMS_CURRENT_"
        "AND_FUNDAMENTAL_DISPLACEMENT_PF"
    )
    assert study["starting_current_basis"] == "SUPPLY_LINE_RMS_AT_RATED_VOLTAGE"
    assert study["starting_power_factor_basis"] == "FUNDAMENTAL_DISPLACEMENT"
    assert study["criterion"]["universal_normative_claim"] is False

    assert result["motor_starting_calculation_performed"] is True
    assert result["dynamic_acceleration_calculation_performed"] is False
    assert result["torque_calculation_performed"] is False
    assert result["automatic_starting_current_derivation"] is False
    assert result["automatic_dispatch"] is False
    assert result["crosscheck"] is False
    assert result["professional_emission"] is False


def test_p13b_starting_method_label_does_not_generate_network_parameters():
    dol = _manifest()
    alt = deepcopy(dol)
    alt["motors"][0]["starting_method"] = "VFD"

    dol_result = motor_starting_static.ejecutar_estudios(dol)
    alt_result = motor_starting_static.ejecutar_estudios(alt)

    assert dol_result["execution_status"] == "STATIC_MOTOR_STARTING_COMPLETED"
    assert alt_result["execution_status"] == "STATIC_MOTOR_STARTING_COMPLETED"

    dol_study = dol_result["results"][0]
    alt_study = alt_result["results"][0]
    assert dol_study["starting_method_metadata"] == "DOL"
    assert alt_study["starting_method_metadata"] == "VFD"
    assert dol_study["starting_demand"] == alt_study["starting_demand"]
    assert dol_study["starting_min_voltage_pu"] == pytest.approx(
        alt_study["starting_min_voltage_pu"], rel=1e-12, abs=1e-12
    )


def test_p13b_lower_explicit_start_current_reduces_voltage_dip():
    high = _manifest()
    low = deepcopy(high)
    low["motors"][0]["starting_current_a"] = 800.0
    low["motors"][0]["starting_data_reference"] = (
        "CONTROLLED_REFERENCE_DATA - reduced explicit starting current"
    )

    high_result = motor_starting_static.ejecutar_estudios(high)["results"][0]
    low_result = motor_starting_static.ejecutar_estudios(low)["results"][0]

    assert high_result["ok"] is True
    assert low_result["ok"] is True
    assert low_result["starting_min_voltage_pu"] > high_result["starting_min_voltage_pu"]
    assert low_result["voltage_dip_pct"] < high_result["voltage_dip_pct"]
