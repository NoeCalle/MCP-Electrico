from copy import deepcopy
import json
from math import pi
from pathlib import Path

import pytest

from mcp_electrico import core, motor_dynamics_intake as intake, motor_dynamics_qualification as qualification, motor_starting_tools, workspace_state

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    manifest = json.loads((ROOT / "examples/p13_motor_starting_multi_stage3.json").read_text(encoding="utf-8"))
    package = json.loads((ROOT / "examples/p13_motor_dynamics_reference.json").read_text(encoding="utf-8"))
    return manifest, package


def check(package):
    return intake.evaluar_admision_dinamica(inputs()[0], package)


def test_complete_inputs_prepare_qualification_and_never_enable_execution():
    manifest, package = inputs()
    original = deepcopy((manifest, package))
    result = intake.evaluar_admision_dinamica(manifest, package)
    assert result["issues"] == []
    assert result["admission_status"] == "READY_FOR_DYNAMIC_BACKEND_QUALIFICATION"
    assert result["data_ready"] is True
    assert result["ready_for_execution"] is False
    assert result["backend_implemented"] is True
    assert result["selected_backend"] == "MCP_BALANCED_RMS_RK4_V1"
    assert result["dynamic_integration_performed"] is False
    assert result["electrical_calculation_performed"] is False
    assert result["model_mutation_performed"] is False
    assert result["automatic_defaults"] is False
    assert result["professional_emission"] is False
    assert result["derived_kinematic_values"][0]["synchronous_speed_rad_s"] == pytest.approx(60 * pi)
    assert (manifest, package) == original


@pytest.mark.parametrize("group,field", [
    ("electrical", "rotor_resistance_ohm"), ("electrical", "magnetizing_inductance_h"),
    ("electrical", "pole_pairs"), ("electrical", "stator_temperature_k"),
    ("electrical", "parameter_basis"), ("electrical", "source_reference"),
    ("electrical", "saturation_model"), ("mechanical", "load_inertia_kg_m2"),
    ("mechanical", "motor_inertia_kg_m2"), ("mechanical", "inertia_basis"),
    ("mechanical", "viscous_damping_nm_s_per_rad"), ("initial_state", "speed_rad_s"),
])
def test_missing_physics_is_blocked_without_defaults(group, field):
    _, package = inputs()
    del package["motors"][0][group][field]
    result = check(package)
    assert result["data_ready"] is False
    assert result["accepted_package"] is None
    assert any(item["path"].endswith(f".{group}.{field}") for item in result["issues"])


@pytest.mark.parametrize("value", [True, "0.07", -1, 0, float("nan"), float("inf"), float("-inf"), 10**1000])
def test_resistance_must_be_positive_finite_si_number(value):
    _, package = inputs()
    package["motors"][0]["electrical"]["stator_resistance_ohm"] = value
    assert check(package)["data_ready"] is False


@pytest.mark.parametrize("value", [True, 2.0, 0, -2, 65, 10**1000])
def test_pole_pairs_have_explicit_integer_domain(value):
    _, package = inputs()
    package["motors"][0]["electrical"]["pole_pairs"] = value
    assert check(package)["data_ready"] is False


@pytest.mark.parametrize("change", ["unordered", "not_zero", "short_domain", "negative_torque", "missing_units"])
def test_curve_cannot_hide_order_domain_or_unit_errors(change):
    _, package = inputs()
    curve = package["motors"][0]["mechanical"]["load_curve"]
    if change == "unordered":
        curve[1]["speed_rad_s"] = 200
    elif change == "not_zero":
        curve[0]["speed_rad_s"] = 1
    elif change == "short_domain":
        curve[-1]["speed_rad_s"] = 120
    elif change == "negative_torque":
        curve[0]["torque_nm"] = -1
    else:
        curve[0]["speed_rpm"] = curve[0].pop("speed_rad_s")
    assert check(package)["data_ready"] is False


@pytest.mark.parametrize("step,limit", [(0, 10000), (0.003, 10000), (1e-320, 10000), (0.001, 9999), (0.001, True), (0.001, 200001)])
def test_grid_is_explicit_bounded_and_integral(step, limit):
    _, package = inputs()
    package["simulation"]["time_step_s"] = step
    package["simulation"]["maximum_steps"] = limit
    assert check(package)["data_ready"] is False


def test_manifest_binding_rejects_changed_project_data():
    manifest, package = inputs()
    manifest["base_model"]["source"]["scc_max_mva"] += 1
    result = intake.evaluar_admision_dinamica(manifest, package)
    assert any(item["code"] == "P13F012" for item in result["issues"])


def test_decimal_grid_roundoff_does_not_exceed_an_exact_declared_limit():
    _, package = inputs()
    package["simulation"].update(duration_s=0.003, time_step_s=0.0003, maximum_steps=10)
    package["studies"][0]["maximum_acceleration_time_s"] = 0.002
    assert check(package)["data_ready"] is True


def test_vfd_is_not_admitted_using_dol_equations():
    manifest, package = inputs()
    manifest["motors"][0]["starting_method"] = "VFD"
    package["manifest_sha256"] = intake.manifest_sha256(manifest)
    result = intake.evaluar_admision_dinamica(manifest, package)
    assert any(item["code"] == "P13F033" for item in result["issues"])


@pytest.mark.parametrize("change,code", [
    ("frequency", "P13F035"), ("moving", "P13F042"), ("duplicate_motor", "P13F031"),
    ("unknown_motor", "P13F032"), ("unknown_study", "P13F052"), ("no_study", "P13F055"),
    ("target", "P13F053"), ("deadline", "P13F054"), ("forged_backend", "P13F003"),
])
def test_references_scope_and_project_criteria_are_enforced(change, code):
    _, package = inputs()
    if change == "frequency": package["motors"][0]["electrical"]["frequency_hz"] = 50
    elif change == "moving": package["motors"][0]["initial_state"]["speed_rad_s"] = 10
    elif change == "duplicate_motor": package["motors"].append(deepcopy(package["motors"][0]))
    elif change == "unknown_motor": package["motors"][0]["motor_id"] = "Motor.missing"
    elif change == "unknown_study": package["studies"][0]["motor_id"] = "Motor.missing"
    elif change == "no_study": package["studies"] = []
    elif change == "target": package["studies"][0]["target_speed_fraction"] = 1
    elif change == "deadline": package["studies"][0]["maximum_acceleration_time_s"] = 11
    else: package["selected_backend"] = "qualified"
    assert any(item["code"] == code for item in check(package)["issues"])


@pytest.mark.parametrize("manifest,package", [(None, None), ({"project": []}, {}), ({"x": float("nan")}, {}), ({}, {"motors": [None], "simulation": [], "studies": [5]})])
def test_malformed_inputs_produce_blocked_report(manifest, package):
    result = intake.evaluar_admision_dinamica(manifest, package)
    assert result["data_ready"] is False
    assert result["ready_for_execution"] is False


def test_analytical_oracles_declare_energy_and_unverified_backend():
    plan = qualification.obtener_plan_validacion()
    constant, damped = plan["analytical_oracles"]
    one_second = next(row for row in constant["expected"] if row["time_s"] == 1)
    assert one_second == {"time_s": 1, "speed_rad_s": 6, "angle_rad": 3, "kinetic_energy_j": 180}
    # Net torque work equals kinetic energy in the no-loss analytical case.
    assert one_second["kinetic_energy_j"] == (80 - 20) * one_second["angle_rad"]
    assert damped["expected"][0]["speed_rad_s"] == 0
    assert all(0 <= row["speed_rad_s"] < 20 for row in damped["expected"])
    assert plan["numerical_integration_performed"] is False
    assert plan["backend_benchmarks_run"] is True
    assert plan["selected_backend"] == "MCP_BALANCED_RMS_RK4_V1"
    assert len(plan["required_qualification_cases"]) == 5


def test_read_only_mcp_preparation_preserves_parent_workspace():
    from opendssdirect import dss
    core.crear_circuito("p13f_parent", 4.16, frecuencia=60, bus_fuente="parent_bus")
    core.agregar_carga("parent_load", "parent_bus", 40, 8, fases=3, kv=4.16)
    workspace_state.reset_for_circuit("p13f_parent")
    before = (dss.Circuit.Name(), list(dss.Circuit.AllElementNames()), workspace_state.status())
    class Registry:
        def __init__(self): self.tools = {}
        def tool(self):
            def register(fn): self.tools[fn.__name__] = fn; return fn
            return register
    registry = Registry()
    motor_starting_tools.register(registry)
    manifest, package = inputs()
    result = registry.tools["validar_datos_dinamica_motores"](manifest, package)
    assert result["data_ready"] is True
    assert registry.tools["obtener_contrato_dinamica_motores"]()["ready_for_execution"] is False
    assert registry.tools["obtener_plan_validacion_dinamica_motores"]()["ready_for_execution"] is False
    assert registry.tools["obtener_contrato_ejecucion_dinamica_motores"]()["electrical_flux_transients"] is False
    assert (dss.Circuit.Name(), list(dss.Circuit.AllElementNames()), workspace_state.status()) == before
