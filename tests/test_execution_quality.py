"""Failure injection at solver boundaries and real end-to-end result gates."""
from copy import deepcopy
import asyncio
import json
from pathlib import Path

import pytest

from mcp_electrico import (execution_quality as quality, real_controlled_execution as controlled,
                           real_protection_execution as protection, real_project_dossier as dossier,
                           workspace_state, study_dispatch, engine_selection, motor_fault_thermal)

ROOT = Path(__file__).resolve().parents[1]


def manifest():
    return json.loads((ROOT/"examples/p10_reference_substation_stage5.json").read_text(encoding="utf8"))


@pytest.mark.parametrize("helper,scope", [
    ("_execute_power_flow", controlled.POWER_FLOW),
    ("_execute_voltage_drop", controlled.VOLTAGE_DROP),
    ("_execute_ampacity", controlled.AMPACITY),
    ("_execute_3ph", controlled.SC_3PH),
    ("_execute_1ph_ground", controlled.SC_1PH),
])
def test_invalid_scope_halts_pipeline_before_protection(monkeypatch, helper, scope):
    monkeypatch.setattr(controlled, helper, lambda *args: {"ok": False, "convergio": False})
    monkeypatch.setattr(protection, "_evaluate_device", lambda *args: pytest.fail("P5 consumed invalid study"))
    result = protection.ejecutar_protecciones(manifest())
    assert result["execution_status"] == protection.STATUS_BLOCKED_P8D1
    failure = result["p8d1_execution"]
    assert failure["execution_status"] == controlled.STATUS_FAILED_RESULT
    assert failure["failed_scope"] == scope and scope not in failure["executed_scopes"]
    assert not failure["resultados_validos"] and not result["protection_calculation_performed"]
    assert not workspace_state.status()["results_current"]
    assert not workspace_state.status()["studies"]["controlled_execution_failure"]["valid"]


def test_exception_is_structured_and_never_generates_a_dossier(monkeypatch, tmp_path):
    def failed():
        raise RuntimeError("controlled solver failure")
    monkeypatch.setattr(controlled, "_execute_power_flow", failed)
    result = dossier.generar_dossier(manifest(), str(tmp_path/"rejected"))
    assert result["status"] == dossier.STATUS_BLOCKED_EXECUTION
    failed = result["p8d2_execution"]["p8d1_execution"]
    assert failed["issues"][0]["code"] == "EXECUTION_EXCEPTION"
    assert not (tmp_path/"rejected").exists()


@pytest.mark.parametrize("change", ["missing_min", "wrong_bus", "wrong_case", "nan", "negative", "boolean", "duplicate", "missing_target"])
def test_both_fault_cases_and_exact_targets_required(change):
    m = manifest()
    buses = m["study_inputs"]["short_circuit_buses"]
    result = {"targets": [{"bus": bus, "result": {"scenarios": {
        case: {"ok": True, "bus": bus, "case": case, "results": {"ikss_ka": 5.}}
        for case in ("max", "min")}}} for bus in buses]}
    assert not quality.scope_issues(controlled.SC_3PH, result, m)
    pair = result["targets"][0]["result"]["scenarios"]
    if change == "missing_min": del pair["min"]
    elif change == "wrong_bus": pair["min"]["bus"] = "another_bus"
    elif change == "wrong_case": pair["min"]["case"] = "max"
    elif change in {"nan", "negative", "boolean"}:
        pair["min"]["results"]["ikss_ka"] = {"nan": float("nan"), "negative": -1, "boolean": True}[change]
    elif change == "duplicate": result["targets"].append(deepcopy(result["targets"][0]))
    else: result["targets"].pop()
    assert quality.scope_issues(controlled.SC_3PH, result, m)


def test_nonfinite_output_diagnostic_and_workspace_remain_json_safe(monkeypatch):
    def bad():
        result = {"convergio": True, "value": float("inf")}
        workspace_state.record_study("flow", result)
        return result
    monkeypatch.setattr(controlled, "_execute_power_flow", bad)
    result = controlled.ejecutar_controlado(manifest())
    assert result["execution_status"] == controlled.STATUS_FAILED_RESULT
    json.dumps(result, allow_nan=False)
    state = workspace_state.status()
    json.dumps(state, allow_nan=False)
    assert not state["studies"]["flow"]["valid"]


def test_real_breaking_capacity_fail_is_valid_calculation_with_failed_design(tmp_path):
    m = manifest()
    m["protection"]["devices"][0]["icu_ka"] = .001
    m["protection"]["devices"][0]["ics_ka"] = .001
    m["protection"]["devices"][0]["breaking_capacity_ka"] = .001
    result = dossier.generar_dossier(m, str(tmp_path/"failed-design"))
    assert result["status"] == dossier.STATUS_READY, result
    assessment = result["design_assessment"]
    assert assessment["calculation_valid"]
    assert assessment["status"] == "DECLARED_CHECKS_FAILED"
    assert any(c["status"] == "FAIL" for c in assessment["checks"])
    assert not assessment["installation_validation_closed"]
    saved = json.loads(Path(result["design_checks_path"]).read_text(encoding="utf8"))
    assert saved == assessment
    assert assessment["manifest_sha256"] == result["manifest_sha256"]
    assert assessment["model_revision"] == result["model_revision"]


@pytest.mark.parametrize("component,status", [("breaking_capacity", "NOT_APPLICABLE_VOLTAGE"),
                                               ("thermal_check", "SECTION_MISMATCH"),
                                               ("breaking_capacity", "PASS")])
def test_incomplete_requested_check_cannot_be_completed(monkeypatch, component, status):
    native = protection._evaluate_device
    def incomplete(binding, fault):
        result = native(binding, fault)
        if component == "thermal_check":
            result["binding"]["thermal_check"] = {"explicit_request": True}
        result[component] = {"status": status}
        if status == "PASS":
            result[component]["invalid_value"] = float("nan")
        return result
    monkeypatch.setattr(protection, "_evaluate_device", incomplete)
    result = protection.ejecutar_protecciones(manifest())
    assert result["execution_status"] == protection.STATUS_PARTIAL
    assert result["design_assessment"]["status"] == "NOT_EVALUABLE"
    assert not result["workspace_study_recorded"]
    assert not result["resultados_validos"]
    assert result["issues"]
    json.dumps(result, allow_nan=False)


def test_valid_calculation_may_fail_voltage_drop_and_ampacity_criteria():
    m = manifest()
    m["study_inputs"]["voltage_drop_limit_pct"] = .00001
    for item in m["ampacity"]:
        item["ib_a"] = 1e6
    result = controlled.ejecutar_controlado(m)
    assert result["execution_status"] == controlled.STATUS_COMPLETED_P5_PENDING, result
    assert result["resultados_validos"]
    assert result["results"][controlled.AMPACITY]["status"] == "NO_CUMPLE"
    assert any(r["estado_criterio"] == "EXCEDE" for r in result["results"][controlled.VOLTAGE_DROP]["alimentadores"])


def test_workspace_does_not_promote_failed_or_unconfirmed_solution():
    workspace_state.reset_for_circuit()
    workspace_state.record_study("failed_sc", {"ok": False})
    workspace_state.record_study("failed_design", {"status": "FAIL"})
    assert not workspace_state.status()["studies"]["failed_sc"]["valid"]
    assert workspace_state.status()["studies"]["failed_design"]["valid"]
    workspace_state.record_solution({"results": {}})
    assert not workspace_state.status()["results_current"]
    assert not workspace_state.status()["studies"]["powerflow"]["valid"]


def test_fault_motor_route_uses_one_executor_and_preserves_data_gate(tmp_path, monkeypatch):
    import server
    monkeypatch.setattr(motor_fault_thermal, "runtime", lambda: {"ready": False})
    package = json.loads((ROOT/"examples/qualification/motor_terminal_fault_emt.json").read_text(encoding="utf8"))
    package["machine"]["rotor_resistance_ohm"] = None
    result = asyncio.run(study_dispatch.execute(server.mcp, "falla_terminal_motor", {
        "paquete_estudio": package, "directorio_salida": str(tmp_path/"blocked")}))
    assert result["execution_tool"] == "ejecutar_falla_terminal_motor_modelica"
    assert result["selected_engine"] == "openmodelica+msl" and not result["fallback"]
    assert result["result"]["status"] == "BLOCKED_MOTOR_FAULT_READINESS"
    assert not (tmp_path/"blocked").exists()
    selected = engine_selection.seleccionar_motor_estudio("falla_terminal_motor")
    assert not selected["executable"] and not selected["readiness"]["data_evaluated"]
