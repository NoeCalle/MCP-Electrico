"""Thermal integral: analytic waveforms, malformed traces and execution gates."""
from copy import deepcopy
import csv
import json
from math import exp, pi, sin
from pathlib import Path

import pytest

from mcp_electrico import motor_fault_thermal as fault

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def package(monkeypatch):
    monkeypatch.setattr(fault.runtime_adapter, "runtime", lambda: {"ready": False})
    return json.loads((ROOT/"examples/qualification/motor_terminal_fault_emt.json").read_text(encoding="utf8"))


def trace(path, times, function, integral, speed):
    with path.open("w", newline="", encoding="utf8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time", "ia", "ib", "ic", "qa", "qb", "qc", "speed"])
        for t in times:
            writer.writerow([t, function(t), -function(t), 0, integral(t), integral(t), 0, speed])


def test_complete_inputs_never_execute_without_runtime(package, tmp_path):
    original = deepcopy(package)
    assert fault.validate(package)["data_ready"]
    assert not fault.validate(package)["ready_for_execution"]
    assert fault.execute(package, tmp_path/"NoRuntime")["results"] is None
    assert not (tmp_path/"NoRuntime").exists() and package == original


@pytest.mark.parametrize("value", [None, [], {}, True, "bad"])
def test_malformed_package_has_structured_blockers(value, package):
    assert not fault.validate(value)["data_ready"]


@pytest.mark.parametrize("value", [None, True, 0, -1, "0.1", float("nan"), float("inf")])
def test_no_default_machine_resistance(package, value):
    package["machine"]["rotor_resistance_ohm"] = value
    assert not fault.validate(package)["data_ready"]


@pytest.mark.parametrize("field,value", [
    ("frequency_hz", 40), ("end_time_s", 1), ("end_time_s", 11),
    ("fault_time_s", .001), ("output_step_s", .001),
    ("maximum_internal_step_s", .001), ("solver_tolerance", .01),
    ("verification_relative_tolerance", .1), ("timeout_s", 601),
    ("shaft_speed_rad_s", 999), ("switch_resistance_ohm", 2),
])
def test_unsupported_boundaries_rejected(package, field, value):
    package[field] = value
    assert not fault.validate(package)["data_ready"]


def test_no_scope_expansion_by_extra_fields(package):
    package["connection"] = "delta"
    assert not fault.validate(package)["data_ready"]


def test_exact_linear_current_integral_and_per_phase_maximum(package, tmp_path):
    package.update(fault_time_s=1., end_time_s=2.)
    path = tmp_path/"linear.csv"
    # i=2t: integral from 1 to 2 is 28/3, known independently.
    trace(path, [0., 1., 2.], lambda t: 2*t,
          lambda t: 0 if t < 1 else 4*(t**3-1)/3, package["shaft_speed_rad_s"])
    r = fault.summarize_trace(path, package, 1.)
    assert r["joule_integral_a2s_by_phase"] == pytest.approx([28/3, 28/3, 0])
    assert r["maximum_phase_equivalent_rms_a"] == pytest.approx((28/3)**.5)
    assert max(r["integral_crosscheck_relative_errors"]) < 1e-14


def test_decaying_current_energy_is_not_initial_rms_squared_times_duration(package, tmp_path):
    package.update(fault_time_s=.1, end_time_s=.3)
    dt = .00002
    path = tmp_path/"decay.csv"
    # Postfault current 100 exp(-(t-.1)/.03), including its full offset.
    def current(t): return 100*exp(-(t-.1)/.03) if t >= .1 else 100
    def integral(t): return 150*(1-exp(-2*(t-.1)/.03)) if t >= .1 else 0
    trace(path, [k*dt for k in range(15001)], current, integral, package["shaft_speed_rad_s"])
    r = fault.summarize_trace(path, package, dt)
    assert r["joule_integral_a2s_by_phase"][0] == pytest.approx(integral(.3), rel=1e-6)
    assert r["joule_integral_a2s_by_phase"][0] < .1*100**2*.2


def test_sinusoidal_energy_uses_instantaneous_square_not_mean_current(package, tmp_path):
    package.update(fault_time_s=.02, end_time_s=.04)
    dt = .00001
    def integral(t):
        return 0 if t < .02 else 50*(t-.02)-100*(sin(200*pi*t)-sin(200*pi*.02))/(400*pi)
    path = tmp_path/"sine.csv"
    trace(path, [k*dt for k in range(4001)], lambda t: 10*sin(100*pi*t), integral, package["shaft_speed_rad_s"])
    r = fault.summarize_trace(path, package, dt)
    assert r["joule_integral_a2s_by_phase"] == pytest.approx([1., 1., 0], rel=3e-6)


@pytest.mark.parametrize("times", [[0., .5, .4, 1.2], [0., .1], [.1, .2, 1.2], [0., .2, 1.2]])
def test_incomplete_unordered_and_gapped_traces_block(package, tmp_path, times):
    path = tmp_path/"bad.csv"
    trace(path, times, lambda t: 0., lambda t: 0., package["shaft_speed_rad_s"])
    with pytest.raises(ValueError):
        fault.summarize_trace(path, package, package["output_step_s"])


def test_nonfinite_trace_is_never_a_result(package, tmp_path):
    path = tmp_path/"nan.csv"
    trace(path, [0., .6, 1.2], lambda t: float("nan"), lambda t: 0., package["shaft_speed_rad_s"])
    with pytest.raises(ValueError, match="NONFINITE"):
        fault.summarize_trace(path, package, 1.)


def test_model_uses_msl_components_and_no_custom_machine_equations(package):
    model = fault.build_model(package)
    assert "IM_SquirrelCage motor" in model and "Sources.Speed drive" in model
    assert "motor.is=zeros(3)" in model and "terminalConnection=\"Y\"" in model
    assert "Continuous.Integrator" in model and "each Goff=0" in model
    assert "der(" not in model and "reinit(" not in model
    assert not fault.contract()["iec60909_conformance_claim"]


@pytest.mark.parametrize("version", ["OpenModelica 1.27.1", "OpenModelica v1.27.1", "OpenModelica v1.27.1 (64-bit)"])
def test_official_release_version_spellings(version):
    assert fault.supported_compiler_version(version)


@pytest.mark.parametrize("version", ["OpenModelica 1.27.10", "OpenModelica 1.27.1-dev", "OpenModelica 1.26.0", "unverified runtime"])
def test_other_compiler_versions_do_not_pass(version):
    assert not fault.supported_compiler_version(version)
