"""Single-executor dispatch, native gates and actual engine integration."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from opendssdirect import dss

import server
from mcp_electrico import core, modelica_motor_adapter, study_dispatch as dispatch, workspace_state

ROOT = Path(__file__).resolve().parents[1]


def run(study, params=None, **kwargs):
    return asyncio.run(dispatch.execute(server.mcp, study, params, **kwargs))


@pytest.fixture(autouse=True)
def empty_model():
    dss("Clear")
    workspace_state.reset_for_circuit()
    yield
    dss("Clear")


def circuit():
    core.crear_circuito("dispatch", .48)
    core.agregar_linea("f1", "sourcebus", "load", .05, fases=3, r1_ohm_km=.2, x1_ohm_km=.08)
    core.agregar_carga("c1", "load", 30, 10, fases=3, kv=.48)


def test_contract_uses_registered_public_schemas():
    result = asyncio.run(dispatch.contract(server.mcp))
    assert not result["unavailable_tools"]
    assert not result["fallback"] and not result["crosscheck"]
    schema = result["parameter_schemas"]["ejecutar_dinamica_modelica"]
    assert set(schema["required"]) == {"paquete_estudio", "directorio_salida"}
    result["routes"].clear()
    assert dispatch.routes()["routes"]


@pytest.mark.parametrize("study,kwargs,status", [
    ("magia", {}, "UNKNOWN_STUDY"),
    ("arc_flash", {}, "BLOCKED_DISPATCH_ROUTE"),
    ("dinamica_variador", {}, "BLOCKED_DISPATCH_ROUTE"),
    ("estabilidad_transitoria", {}, "BLOCKED_DISPATCH_ROUTE"),
    ("cortocircuito", {}, "BLOCKED_DISPATCH_ROUTE"),
    ("iec60909", {}, "BLOCKED_FAULT_TYPE"),
    ("iec60909", {"tipo_falla": "two_phase_ground"}, "BLOCKED_FAULT_TYPE"),
    ("flujo", {"tipo_falla": "three_phase"}, "BLOCKED_FAULT_TYPE"),
    ("flujo", {"norma": "IEC 60909"}, "BLOCKED_STANDARD"),
    ("cortocircuito", {"norma": "IEEE"}, "BLOCKED_STANDARD"),
    ("flujo", {}, "BLOCKED_ACTIVE_MODEL"),
])
def test_blocked_routing_never_calls_an_executor(study, kwargs, status, monkeypatch):
    async def forbidden(*args, **kw):
        pytest.fail("blocked request invoked an executor")
    monkeypatch.setattr(server.mcp, "call_tool", forbidden)
    result = run(study, **kwargs)
    assert result["status"] == status
    assert not result["executor_invoked"] and not result["fallback"]


@pytest.mark.parametrize("params", [{"motor": "pandapower"}, {"limite_pct": "3"},
                                    {"limite_pct": None}, {"limite_pct": True},
                                    {"limite_pct": float("nan")}, {"limite_pct": float("inf")}])
def test_unknown_and_wrongly_typed_parameters_cannot_be_ignored(params):
    circuit()
    result = run("caida_tension", params)
    assert result["status"] == "BLOCKED_PARAMETERS"
    assert not result["executor_invoked"]


def test_package_fields_required_before_invocation(tmp_path):
    for params in ({}, {"paquete_estudio": {}}, {"directorio_salida": str(tmp_path/"missing")}):
        result = run("armonicos", params)
        assert result["status"] == "BLOCKED_PARAMETERS"
        assert not result["executor_invoked"]
    assert not (tmp_path/"missing").exists()


def test_actual_flow_matches_public_executor_and_records_workspace(monkeypatch):
    circuit()
    calls = []
    native_call = server.mcp.call_tool
    async def tracked(name, args):
        calls.append(name)
        return await native_call(name, args)
    monkeypatch.setattr(server.mcp, "call_tool", tracked)
    result = run("flujo")
    assert calls == ["ejecutar_flujo_potencia"]
    assert result["selected_engine"] == "opendss"
    assert result["result"]["convergio"]
    assert result["result"] == server.ejecutar_flujo_potencia()
    assert "flow" in workspace_state.status()["studies"]


def test_actual_voltage_drop_preserves_explicit_criterion():
    circuit()
    result = run("caída tensión", {"limite_pct": 1.0})
    assert result["executor_invoked"]
    assert result["result"] == server.analizar_caida_tension(1.0)


@pytest.mark.parametrize("study,filename", [
    ("armonicos", "harmonics_stage1.json"),
    ("series_temporales", "time_series_stage1.json"),
    ("actuacion_reles", "relay_operation_stage1.json"),
    ("compensacion_reactiva", "reactive_compensation_stage1.json"),
])
def test_actual_package_executors_keep_results_and_parent_model(study, filename, tmp_path):
    circuit()
    parent = dss.Circuit.Name(), dss.Circuit.AllElementNames()
    package = json.loads((ROOT/"examples"/filename).read_text())
    original = deepcopy(package)
    result = run(study, {"paquete_estudio": package, "directorio_salida": str(tmp_path/"study")})
    assert result["status"] == "EXECUTOR_RETURNED", result
    saved = json.loads((tmp_path/"study"/"Results.json").read_text())
    assert "COMPLETED" in result["result"]["status"]
    assert result["result"]["status"] == saved["status"]
    assert not result["result"]["parent_model_mutated"]
    assert parent == (dss.Circuit.Name(), dss.Circuit.AllElementNames())
    assert package == original


@pytest.mark.parametrize("study", ["armonicos", "series_temporales", "actuacion_reles", "compensacion_reactiva"])
def test_native_package_validation_blocks_before_output_creation(study, tmp_path):
    result = run(study, {"paquete_estudio": {}, "directorio_salida": str(tmp_path/"invalid")})
    assert result["executor_invoked"]
    assert result["result"]["status"].startswith("BLOCKED_")
    assert not (tmp_path/"invalid").exists()


@pytest.mark.parametrize("study,filename", [
    ("dinamica_arranque_directo", "msl_motor_dol.json"),
    ("dinamica_simultanea", "msl_motor_two.json"),
    ("dinamica_scr", "msl_motor_two_scr.json"),
])
def test_modelica_keeps_runtime_gate_without_active_unifilar(study, filename, tmp_path, monkeypatch):
    monkeypatch.setattr(modelica_motor_adapter, "runtime", lambda: {"ready": False, "reason": "test runtime absent"})
    package = json.loads((ROOT/"examples"/filename).read_text())
    result = run(study, {"paquete_estudio": package, "directorio_salida": str(tmp_path/"absent")})
    assert result["executor_invoked"]
    assert result["selected_engine"] == "openmodelica+msl"
    assert result["result"]["status"] == "BLOCKED_MODELICA_READINESS"
    assert not (tmp_path/"absent").exists()


@pytest.mark.parametrize("study,filename", [
    ("dinamica_scr", "msl_motor_dol.json"),
    ("dinamica_arranque_directo", "msl_motor_scr.json"),
    ("dinamica_simultanea", "msl_motor_dol.json"),
])
def test_motor_package_must_match_requested_study(study, filename, tmp_path):
    package = json.loads((ROOT/"examples"/filename).read_text())
    result = run(study, {"paquete_estudio": package, "directorio_salida": str(tmp_path/"wrong")})
    assert result["status"] == "BLOCKED_MOTOR_STUDY" and not result["executor_invoked"]
    assert not (tmp_path/"wrong").exists()


@pytest.mark.parametrize("fault,expected", list(dispatch.FAULT_ROUTES.items()))
def test_iec_selects_exactly_the_requested_public_route(fault, expected, monkeypatch):
    circuit()
    calls = []
    async def tracked(name, args):
        calls.append((name, args))
        return {"status": "BLOCKED_NATIVE_GATE", "professional_emission": False}
    monkeypatch.setattr(server.mcp, "call_tool", tracked)
    result = run("cortocircuito", {"bus_falla": "load"}, norma="IEC 60909", tipo_falla=fault)
    assert calls == [(expected, {"bus_falla": "load"})]
    assert result["selected_engine"] == "pandapower"
    assert result["result"]["status"] == "BLOCKED_NATIVE_GATE"


def test_actual_three_phase_cannot_bypass_model_review():
    circuit()
    result = run("iec60909", {"bus_falla": "load"}, tipo_falla="three_phase")
    assert result["executor_invoked"] and result["status"] == "EXECUTOR_RETURNED"
    assert result["result"]["execution_status"] == "BLOQUEADO_ANTES_DEL_CALCULO"
    assert not result["result"]["electrical_calculation_executed"]


def test_actual_ampacity_keeps_missing_data_visible():
    circuit()
    result = run("ampacidad", {"nombre_elemento": "Line.f1"})
    assert result["selected_engine"] == "mcp"
    assert result["result"]["status"] == "DATOS_INSUFICIENTES"


def test_actual_scenarios_restore_declared_manifest_base():
    circuit()
    manifest = json.loads((ROOT/"examples/p10_reference_substation_stage1.json").read_text())
    package = json.loads((ROOT/"examples/p12_operating_scenarios_reference.json").read_text())
    result = run("N-1", {"manifest": manifest, "paquete_escenarios": package})
    assert result["status"] == "EXECUTOR_RETURNED"
    assert result["selected_engine"] == "opendss"
    assert result["result"]["execution_status"] == "SCENARIO_SET_EXECUTION_COMPLETED", result
    assert result["result"]["model_restored_after_each_scenario"]
    assert result["result"]["summary"]["executed"] == 2
    assert result["result"]["summary"]["fail"] == 1
    assert all(item["explicit_actions_only"] for item in result["result"]["scenario_results"])
    assert dss.Circuit.Name() != "dispatch"


def test_scenario_selector_remains_read_only_and_requires_package():
    from mcp_electrico import engine_selection
    result = engine_selection.seleccionar_motor_estudio("N-1")
    assert result["selected_engine"] == "opendss"
    assert not result["executable"] and not result["automatic_dispatch"]
    assert result["readiness"]["data_status"] == "MISSING_DATA"


@pytest.mark.parametrize("response,expected", [
    ([SimpleNamespace(type="text", text='{"status":"NATIVE"}')], "EXECUTOR_RETURNED"),
    (([], {"status": "NATIVE"}), "EXECUTOR_RETURNED"),
    ([SimpleNamespace(type="text", text="not JSON")], "EXECUTOR_RESPONSE_UNAVAILABLE"),
])
def test_sdk_response_formats_do_not_trigger_a_second_run(response, expected, monkeypatch):
    circuit()
    calls = []
    async def fake(name, args):
        calls.append(name)
        return response
    monkeypatch.setattr(server.mcp, "call_tool", fake)
    result = run("flujo")
    assert result["status"] == expected
    assert calls == ["ejecutar_flujo_potencia"]


def test_executor_failure_does_not_fall_back(monkeypatch):
    circuit()
    calls = []
    async def fail(name, args):
        calls.append(name)
        raise RuntimeError("engine failure")
    monkeypatch.setattr(server.mcp, "call_tool", fail)
    result = run("flujo")
    assert result["status"] == "EXECUTOR_ERROR"
    assert calls == ["ejecutar_flujo_potencia"] and not result["fallback"]
