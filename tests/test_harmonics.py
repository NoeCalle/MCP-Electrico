from copy import deepcopy
import hashlib
import json
from math import hypot, sqrt
from pathlib import Path

import pytest
from opendssdirect import dss
from mcp_electrico import harmonics as h
from scripts.harmonics_reference import analytical, native_script, reference_package

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("frequency", [50, 60])
@pytest.mark.parametrize("connection", ["wye", "delta"])
@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("series", [0, 50, 100])
def test_independent_analytical_and_native_references(frequency, connection, enabled, series, tmp_path):
    package = reference_package(frequency, connection, enabled, series)
    result = h.execute(package, tmp_path/"study")
    assert result["status"] == "HARMONICS_COMPLETED", result
    assert result["results_valid"] and not result["parent_model_mutated"]
    expected_fund = analytical(package, 1)["voltage_v"]
    assert result["fundamental"]["buses"][1]["voltage_ln_v"] == pytest.approx([expected_fund]*3, abs=2e-6)
    native = dss.NewContext()
    native.Basic.AllowChangeDir(False)
    native(native_script(package))
    native("Set Mode=Harmonic")
    for row in result["harmonics"]:
        order = row["order"]
        expected = analytical(package, order)
        assert row["buses"][1]["voltage_ln_v"] == pytest.approx([expected["voltage_v"]]*3, abs=2e-6)
        assert row["elements"][0]["terminal_phase_currents_a"][0] == pytest.approx([expected["line_current_a"]]*3, abs=2e-5)
        native(f"Set Harmonics=[{order}]")
        native.Solution.Solve()
        native.Circuit.SetActiveBus("loadbus")
        volts = [hypot(a,b) for a,b in zip(native.Bus.Voltages()[::2], native.Bus.Voltages()[1::2])]
        assert row["buses"][1]["voltage_ln_v"] == pytest.approx(volts[:3], abs=2e-6)
    for point in result["scans"][0]["points"]:
        expected = analytical(package, point["order"])
        assert point["z_ohm"] == pytest.approx(expected["z_ohm"], abs=2e-7)
        assert point["r_ohm"] == pytest.approx(expected["r_ohm"], abs=2e-7)
        assert point["x_ohm"] == pytest.approx(expected["x_ohm"], abs=2e-7)
    expected_thd = 100*sqrt(sum(analytical(package,k)["voltage_v"]**2 for k in package["orders"]))/expected_fund
    assert result["voltage_thd"][1]["voltage_thd_percent"] == pytest.approx([expected_thd]*3, abs=2e-6)
    hashes = json.loads((tmp_path/"study/Integrity.json").read_text())["files_sha256"]
    for name, digest in hashes.items():
        assert hashlib.sha256((tmp_path/"study"/name).read_bytes()).hexdigest() == digest


def test_transformer_fixture_criteria_failure_does_not_invalidate_calculation(tmp_path):
    package = json.loads((ROOT/"examples/harmonics_stage1.json").read_text())
    package["criteria"]["maximum_voltage_thd_percent"] = .01
    result = h.execute(package, tmp_path/"transformer")
    assert result["results_valid"], result
    assert result["criteria"] == {"evaluated": True, "passed": False,
                                  "source_reference": package["criteria"]["source_reference"]}
    assert any(e["id"].lower() == "transformer.t1" for e in result["harmonics"][0]["elements"])
    assert result["scans"][0]["sampled_local_peaks"]
    assert h.execute(package, tmp_path/"transformer")["status"] == "BLOCKED_OUTPUT_DIRECTORY"


def test_transformer_native_input_independent_of_adapter_translation(tmp_path):
    package = json.loads((ROOT/"examples/harmonics_stage1.json").read_text())
    result = h.execute(package, tmp_path/"transformer-native")
    assert result["results_valid"], result
    native = dss.NewContext()
    native.Basic.AllowChangeDir(False)
    native((ROOT/"examples/harmonics_transformer_native.dss").read_text())
    native("Set Mode=Harmonic")
    for row in result["harmonics"]:
        native(f"Set Harmonics=[{row['order']}]")
        native.Solution.Solve()
        for bus in row["buses"]:
            native.Circuit.SetActiveBus(bus["bus"])
            raw = native.Bus.Voltages()
            expected = [hypot(a,b) for a,b in zip(raw[::2], raw[1::2])][:3]
            assert bus["voltage_ln_v"] == pytest.approx(expected, abs=2e-6)
        for item in row["elements"]:
            if item["id"].lower().startswith("capacitor."):
                continue  # Explicitly different native/reference object names.
            native.Circuit.SetActiveElement(item["id"])
            raw = native.CktElement.Currents()
            currents = [hypot(a,b) for a,b in zip(raw[::2],raw[1::2])]
            n = native.CktElement.NumConductors()
            for i, values in enumerate(item["terminal_phase_currents_a"]):
                assert values == pytest.approx(currents[i*n:i*n+3], abs=2e-5)


def test_superposition_and_harmonic_phase_sequence(tmp_path):
    import cmath
    package = reference_package()
    package["scan"]["buses"] = []
    package["scan"]["orders"] = []
    first = h.execute(package, tmp_path/"sequence")
    for row in first["harmonics"][:2]:
        phase = [complex(*p) for p in row["buses"][1]["voltage_phasors_v"]]
        expected = cmath.exp(-2j*cmath.pi*row["order"]/3)
        assert phase[1]/phase[0] == pytest.approx(expected, abs=2e-8)
    package["base_model"]["topology"]["loads"].append(deepcopy(package["base_model"]["topology"]["loads"][0]))
    package["base_model"]["topology"]["loads"][1]["id"] = "Load.cancel"
    second = deepcopy(package["load_harmonics"][0])
    second["load_id"] = "Load.cancel"
    for point in second["spectrum"]:
        point["angle_deg"] += 180
    package["load_harmonics"].append(second)
    result = h.execute(package, tmp_path/"cancel")
    assert result["results_valid"], result
    assert max(result["voltage_thd"][1]["voltage_thd_percent"]) < 1e-8


@pytest.mark.parametrize("path,value", [
    (["orders"], [3,5]), (["orders"], [5,5]), (["orders"], [5.5]),
    (["orders"], [True]), (["orders"], []), (["orders"], [[5]]),
    (["load_harmonics"], []), (["load_harmonics",0,"series_rl_percent"], None),
    (["load_harmonics",0,"spectrum",0,"percent"], float("nan")),
    (["load_harmonics",0,"spectrum",0,"order"], 13),
    (["scan","orders"], [4,3,2]), (["scan","sequence"], "zero"),
    (["scan","orders"], [1,2,3]), (["scan","buses"], ["absent"]),
    (["options","neglect_load_y"], True), (["options","frequency_model"], "invented"),
    (["base_model","topology","loads",0,"kw"], 0),
    (["base_model","topology","loads",0,"kvar"], -10),
    (["banks",0,"kv_ll"], 13.8), (["banks",0,"bus"], {}),
    (["base_model"], []), (["criteria"], {}),
    (["base_model","source","frequency_hz"], 400),
])
def test_reject_invalid_or_unsupported_without_solving_or_writing(path, value, tmp_path, monkeypatch):
    package = reference_package()
    obj = package
    for key in path[:-1]:
        obj = obj[key]
    obj[path[-1]] = value
    def forbidden(*args, **kwargs):
        raise AssertionError("invalid input reached the solver")
    monkeypatch.setattr(h, "_build", forbidden)
    result = h.execute(package, tmp_path/"blocked")
    assert result["status"] == "BLOCKED_HARMONICS_INPUTS"
    assert not result["readiness"]["electrical_calculation_performed"]
    assert not (tmp_path/"blocked").exists()


def test_clean_spectra_zero_thd_and_scan_independent_of_emission(tmp_path):
    package = reference_package()
    emitted = h.execute(package, tmp_path/"emitted")
    package["load_harmonics"][0]["spectrum"] = []
    clean = h.execute(package, tmp_path/"clean")
    assert clean["results_valid"], clean
    assert max(clean["voltage_thd"][1]["voltage_thd_percent"]) < 1e-10
    assert clean["scans"] == emitted["scans"]


def test_parent_state_preserved_and_runtime_failure_is_not_a_passing_study(tmp_path, monkeypatch):
    dss("Clear\nNew Circuit.keep basekv=12.47\nNew Load.keep bus1=sourcebus kv=12.47 kw=30 kvar=5\nSolve")
    before = deepcopy(h.rc.network._parent_signature())
    good = h.execute(reference_package(), tmp_path/"good")
    assert good["results_valid"], good
    assert h.rc.network._parent_signature() == before
    def broken(*args, **kwargs):
        raise RuntimeError("engine failure test")
    monkeypatch.setattr(h, "_solve_order", broken)
    bad = h.execute(reference_package(), tmp_path/"failed")
    assert bad["status"] == "HARMONICS_INVALID" and not bad["results_valid"]
    assert bad["criteria"] == {"evaluated": False, "passed": False}
    assert "engine failure test" in bad["error"]
    assert (tmp_path/"failed/Results.json").is_file()
    assert h.rc.network._parent_signature() == before


def test_peaks_are_sampled_and_no_scan_is_explicitly_allowed(tmp_path):
    package = reference_package()
    result = h.execute(package, tmp_path/"peaks")
    assert result["scans"][0]["sampled_local_peaks"], result
    points = result["scans"][0]["points"]
    for peak in result["scans"][0]["sampled_local_peaks"]:
        index = points.index(peak)
        assert points[index-1]["z_ohm"] < peak["z_ohm"] > points[index+1]["z_ohm"]
    package["scan"]["buses"] = []
    package["scan"]["orders"] = []
    assert h.execute(package, tmp_path/"no-scan")["scans"] == []


def test_selector_describes_package_gate_and_qualification():
    from mcp_electrico import engine_selection, module_qualification, validation_status
    route = engine_selection.seleccionar_motor_estudio("armonicos")
    assert route["selected_engine"] == "opendss"
    assert route["readiness"]["overall_status"] == "MISSING_DATA"
    assert not route["executable"]
    assert module_qualification.get("harmonics")["verification_status"] == "VERIFIED_IN_SCOPE"
    assert validation_status.get_module_status("harmonics")["status"] == "VALIDATED_WITH_LIMITATIONS"
