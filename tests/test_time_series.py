from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path

import pytest
from opendssdirect import dss
from mcp_electrico import time_series as ts
from scripts.time_series_reference import analytical, native_script, reference_package

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("mode", ["daily", "yearly"])
@pytest.mark.parametrize("frequency", [50, 60])
@pytest.mark.parametrize("model", [1, 2])
@pytest.mark.parametrize("step", [.25, 1])
def test_native_and_independent_pq_z_energy_references(mode, frequency, model, step, tmp_path):
    package = reference_package(mode, frequency, model, step, days=2)
    result = ts.execute(package, tmp_path/"series")
    assert result["results_valid"], result
    native = dss.NewContext()
    native.Basic.AllowChangeDir(False)
    native(native_script(package))
    expected_energy = 0
    shape = package["load_profiles"][0]
    for i, row in enumerate(result["results"]):
        idx = i % len(shape["p_multipliers"])
        expected = analytical(shape["p_multipliers"][idx], shape["q_multipliers"][idx], model)
        assert row["interval_end_hour"] == pytest.approx((i+1)*step, abs=1e-8)
        assert row["loads"][0]["profile_index"] == idx
        assert row["source"]["p_kw"] == pytest.approx(expected["source_kw"], abs=2e-6)
        assert row["source"]["q_kvar"] == pytest.approx(expected["source_kvar"], abs=2e-6)
        assert row["actual_load_kw"] == pytest.approx(expected["load_kw"], abs=2e-6)
        assert row["network_losses_kw"] == pytest.approx(expected["network_losses_kw"], abs=2e-6)
        assert row["buses"][1]["minimum_pu"] == pytest.approx(expected["voltage_pu"], abs=2e-7)
        assert row["lines"][0]["maximum_phase_current_a"] == pytest.approx(expected["current_a"], abs=2e-5)
        native.Solution.Solve()
        native_p = -native.Circuit.TotalPower()[0]
        assert row["source"]["p_kw"] == pytest.approx(native_p, abs=2e-6)
        assert native.Solution.DblHour() == pytest.approx(row["interval_end_hour"], abs=1e-8)
        expected_energy += expected["source_kw"]*step
    assert result["summary"]["source_energy_kwh"] == pytest.approx(expected_energy, abs=2e-5)
    assert abs(result["summary"]["active_energy_balance_residual_kwh"]) < 1e-5
    with (tmp_path/"series/Series.csv").open(encoding="utf8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == package["timeline"]["steps"]
    integrity = json.loads((tmp_path/"series/Integrity.json").read_text())
    for name, digest in integrity["files_sha256"].items():
        assert hashlib.sha256((tmp_path/"series"/name).read_bytes()).hexdigest() == digest


def test_yearly_full_8760_hours_without_implicit_annual_extrapolation(tmp_path):
    package = reference_package("yearly", model=1)
    package["timeline"]["steps"] = 8760
    profile = package["load_profiles"][0]
    profile["p_multipliers"] = [0.5]*8759+[1.5]
    profile["q_multipliers"] = [0.4]*8760
    result = ts.execute(package, tmp_path/"annual")
    assert result["results_valid"], result
    summary = result["summary"]
    assert summary["duration_hours"] == 8760
    assert summary["peak_source_interval_end_hour"] == 8760
    expected = analytical(.5,.4,1)["source_kw"]*8759+analytical(1.5,.4,1)["source_kw"]
    assert summary["source_energy_kwh"] == pytest.approx(expected, abs=.001)


@pytest.mark.parametrize("path,value", [
    (["timeline","mode"], "snapshot"), (["timeline","start_hour"], 1),
    (["timeline","step_hours"], 5), (["timeline","steps"], True),
    (["timeline","steps"], 0), (["timeline","steps"], 35137),
    (["timeline","energy_integration"], "automatic"),
    (["load_profiles"], []), (["load_profiles",0,"q_multipliers"], None),
    (["load_profiles",0,"p_multipliers"], [1]),
    (["load_profiles",0,"p_multipliers",0], -1),
    (["load_profiles",0,"p_multipliers",0], float("nan")),
    (["load_profiles",0,"load_id"], "Load.absent"),
    (["base_model","source","frequency_hz"], 400),
    (["criteria","voltage_max_pu"], .1), (["options","max_iterations"], 0),
    (["base_model"], []), (["options"], []),
    (["base_model","topology","lines"], 5),
])
def test_invalid_inputs_are_blocked_without_native_build_or_output(path, value, tmp_path, monkeypatch):
    package = reference_package()
    target = package
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    def forbidden(*args):
        raise AssertionError("invalid input reached the solver")
    monkeypatch.setattr(ts, "_build", forbidden)
    result = ts.execute(package, tmp_path/"blocked")
    assert result["status"] == "BLOCKED_TIME_SERIES_INPUTS"
    assert not result["readiness"]["electrical_calculation_performed"]
    assert not (tmp_path/"blocked").exists()


def test_no_wrap_without_explicit_daily_repetition_and_no_yearly_wrap(tmp_path):
    daily = reference_package(days=2)
    daily["timeline"]["repeat_daily_profile"] = False
    assert not ts.validate(daily)["ready_for_execution"]
    yearly = reference_package("yearly")
    yearly["timeline"]["repeat_daily_profile"] = True
    assert not ts.validate(yearly)["ready_for_execution"]
    yearly["timeline"]["repeat_daily_profile"] = False
    yearly["timeline"]["steps"] = 48
    assert not ts.validate(yearly)["ready_for_execution"]


def test_multiple_loads_transformer_and_criterion_failure(tmp_path):
    package = json.loads((ROOT/"examples/time_series_stage1.json").read_text())
    package["criteria"]["maximum_line_loading_pct"] = 1
    result = ts.execute(package, tmp_path/"transformer")
    assert result["results_valid"], result
    assert not result["summary"]["criteria_passed"]
    assert result["summary"]["violating_steps"]
    for i, row in enumerate(result["results"]):
        assert len(row["loads"]) == 2
        for item in row["loads"]:
            original = next(v for v in package["base_model"]["topology"]["loads"] if v["id"] == item["id"])
            assert item["actual_kw"] == pytest.approx(original["kw"]*item["p_multiplier"], abs=1e-5)
            assert item["actual_kvar"] == pytest.approx(original["kvar"]*item["q_multiplier"], abs=1e-5)
    assert ts.execute(package, tmp_path/"transformer")["status"] == "BLOCKED_OUTPUT_DIRECTORY"


def test_parent_state_preserved_and_incomplete_series_has_no_total_energy(tmp_path, monkeypatch):
    dss("Clear\nNew Circuit.parent basekv=12.47\nNew Load.keep bus1=sourcebus kv=12.47 kw=20 kvar=5\nSolve")
    parent = deepcopy(ts.rc.network._parent_signature())
    assert ts.execute(reference_package(), tmp_path/"good")["results_valid"]
    assert parent == ts.rc.network._parent_signature()
    original = ts.rc._measure
    calls = []
    def fail_second(engine, package, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            return {"results_valid": False, "converged": False, "overload_evaluation": "NOT_EVALUABLE"}
        return original(engine, package, **kwargs)
    monkeypatch.setattr(ts.rc, "_measure", fail_second)
    bad = ts.execute(reference_package(), tmp_path/"bad")
    assert not bad["results_valid"] and bad["status"] == "TIME_SERIES_INVALID"
    assert len(bad["results"]) == 2 and bad["completed_valid_steps"] == 1
    assert bad["summary"] == {"evaluated": False}
    assert parent == ts.rc.network._parent_signature()


def test_one_point_profile_and_single_yearly_interval(tmp_path):
    for mode in ("daily", "yearly"):
        package = reference_package(mode, step_hours=24)
        result = ts.execute(package, tmp_path/mode)
        assert result["results_valid"], result
        assert len(result["results"]) == 1
        assert result["summary"]["duration_hours"] == 24


def test_short_yearly_horizon_and_native_nonconvergence(tmp_path):
    package = reference_package("yearly")
    package["timeline"]["steps"] = 3
    package["load_profiles"][0]["p_multipliers"] = [0.1, 0.4, 1.2]
    package["load_profiles"][0]["q_multipliers"] = [0.3, 0.8, 0.5]
    result = ts.execute(package, tmp_path/"three-hours")
    assert result["summary"]["duration_hours"] == 3
    assert result["results"][0]["loads"][0]["actual_kw"] == pytest.approx(10, abs=1e-6)
    assert result["results"][-1]["loads"][0]["actual_kw"] == pytest.approx(120, abs=1e-6)
    package["base_model"]["source"]["scc_max_mva"] = .2
    package["options"]["max_iterations"] = 1
    bad = ts.execute(package, tmp_path/"nonconvergent")
    assert not bad["results_valid"]
    assert not bad["summary"]["evaluated"]
    assert not bad["results"][0]["converged"]
    assert bad["results"][0]["criteria"] == {"evaluated": False, "passed": False}


def test_selector_needs_a_validated_explicit_profile_package():
    from mcp_electrico import engine_selection
    route = engine_selection.seleccionar_motor_estudio("series_temporales")
    assert route["selected_engine"] == "opendss"
    assert route["readiness"]["overall_status"] == "MISSING_DATA"
    assert not route["executable"]
