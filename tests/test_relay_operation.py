from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pandas as pd
import pandapower as pp
from pandapower.protection.protection_devices.ocrelay import OCRelay
import pytest
from opendssdirect import dss

from mcp_electrico import relay_operation as ro
from scripts.relay_operation_reference import expected_time, reference_package

KINDS = [("DTOC", "standard_inverse")]+[(k,c) for k in ("IDMT", "IDTOC") for c in ro.CURVES]


@pytest.mark.parametrize("kind,curve", KINDS)
@pytest.mark.parametrize("scenario", ["sc", "pp"])
@pytest.mark.parametrize("breaker", [None, .05])
def test_independent_operation_boundary_and_clearing_references(kind, curve, scenario, breaker, tmp_path):
    package = reference_package(kind,curve,scenario,breaker)
    result = ro.execute(package, tmp_path/"study")
    assert result["results_valid"], result
    assert result["criteria"] == {"evaluated": True, "passed": True}
    for case, inputs in zip(result["results"], package["cases"]):
        row = case["relays"][0]
        current = inputs["currents"]["R1"]["primary_rms_a"]
        expected = expected_time(kind,curve,current)
        assert row["trip_command"] == (expected is not None)
        assert row["native_switch_closed_after_command"] == (expected is None)
        assert row["relay_operating_time_s"] == pytest.approx(expected, rel=1e-9, abs=1e-9)
        if expected is None:
            assert row["total_clearing_time_s"] is None and row["native_nontrip_time"] == "POSITIVE_INFINITY"
        elif breaker is None:
            assert row["total_clearing_time_s"] is None
            assert row["clearing_time_status"] == "NOT_EVALUABLE_BREAKER_DELAY_MISSING"
        else:
            assert row["total_clearing_time_s"] == pytest.approx(expected+breaker, rel=1e-9, abs=1e-9)
    assert not result["network_short_circuit_calculated"] and not result["network_recalculated_after_trip"]
    data = json.loads((tmp_path/"study/Results.json").read_text())
    assert data["results_valid"]
    integrity = json.loads((tmp_path/"study/Integrity.json").read_text())
    for name,digest in integrity["files_sha256"].items():
        assert hashlib.sha256((tmp_path/"study"/name).read_bytes()).hexdigest() == digest


def native_constructor_network():
    net = pp.create_empty_network(sn_mva=10)
    a = pp.create_bus(net,vn_kv=13.8,geodata=(0,0))
    b = pp.create_bus(net,vn_kv=13.8,geodata=(1,0))
    pp.create_ext_grid(net,a,s_sc_max_mva=200,s_sc_min_mva=150,rx_max=.1,rx_min=.1)
    line = pp.create_line_from_parameters(net,a,b,1,r_ohm_per_km=.1,x_ohm_per_km=.2,c_nf_per_km=0,max_i_ka=.5)
    pp.create_switch(net,a,line,et="l",closed=True,type="CB")
    return net


@pytest.mark.parametrize("curve", ro.CURVES)
def test_native_idmt_constructor_and_serialization_parity(curve):
    net = native_constructor_network()
    native = OCRelay(net,0,"IDMT",pd.DataFrame({"switch_id":[0],"tms":[.1],"t_grade":[.05]}),
                     pickup_current_manual=pd.DataFrame({"switch_id":[0],"I_s":[.1]}),curve_type=curve)
    explicit = ro._native_relay(reference_package("IDMT",curve)["relays"][0],0)
    assert (explicit.k,explicit.alpha,explicit.I_s,explicit.tms,explicit.t_grade) == (
        native.k,native.alpha,native.I_s,native.tms,native.t_grade)
    for current in (0,100,101,1000):
        net.res_switch_sc = pd.DataFrame({"ikss_ka":[current/1000]})
        native.reset_device()
        expected = native.protection_function(net,"sc")
        actual = ro._point(explicit,current,"sc")
        assert actual["trip_command"] == bool(expected["trip_melt"])
        if actual["trip_command"]:
            assert actual["relay_operating_time_s"] == expected["trip_melt_time_s"]
    restored = OCRelay.from_json(explicit.to_json())
    assert ro._point(restored,500,"sc") == ro._point(explicit,500,"sc")


def test_pinned_native_dtoc_constructor_issue_is_not_used_by_adapter():
    net = native_constructor_network()
    native = OCRelay(net,0,"DTOC",pd.DataFrame({"switch_id":[0],"t_gg":[.02],"t_g":[.4]}),
                     pickup_current_manual=pd.DataFrame({"switch_id":[0],"I_g":[.5],"I_gg":[1.0]}))
    # Documents the installed vendor issue; no vendor mutation or local curve replacement.
    assert native.I_g == native.I_gg == .5
    relay = ro._native_relay(reference_package("DTOC")["relays"][0],0)
    assert relay.I_g == .5 and relay.I_gg == 1.0
    assert ro._point(relay,750,"sc")["relay_operating_time_s"] == .4
    assert ro._point(relay,1500,"sc")["relay_operating_time_s"] == .02


@pytest.mark.parametrize("path,value", [
    (["current_time_model"], "TRANSIENT"), (["relays"], []),
    (["relays",0,"type"], "DIRECTIONAL"),
    (["relays",0,"settings","curve_type"], "manufacturer_curve"),
    (["relays",0,"settings","pickup_primary_a"], 0),
    (["relays",0,"settings","time_multiplier"], True),
    (["relays",0,"settings","additive_delay_s"], -1),
    (["relays",0,"breaker","clearing_delay_s"], float("nan")),
    (["cases"], []), (["cases",0,"scenario"], "dynamic"),
    (["cases",0,"currents","R1","primary_rms_a"], -1),
    (["cases",0,"currents","R1","primary_rms_a"], float("inf")),
    (["cases",0,"currents","R1","source_reference"], ""),
    (["cases",0,"expectations","R1","trip"], 1),
    (["cases",0,"expectations","R1","maximum_relay_time_s"], .1),
    (["cases",0,"currents"], {}), (["relays",0,"settings"], []),
])
def test_unsupported_or_missing_inputs_block_before_native_evaluation(path,value,tmp_path,monkeypatch):
    package = reference_package()
    target = package
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    def forbidden(*args):
        raise AssertionError("invalid data reached native relay")
    monkeypatch.setattr(ro,"_native_relay",forbidden)
    result = ro.execute(package,tmp_path/"blocked")
    assert result["status"] == "BLOCKED_RELAY_OPERATION_INPUTS"
    assert not result["readiness"]["electrical_calculation_performed"]
    assert not (tmp_path/"blocked").exists()


def test_unknown_breaker_delay_and_failed_project_criterion_are_not_numerical_failure(tmp_path):
    package = reference_package(breaker_delay=None)
    package["cases"] = [package["cases"][-1]]
    package["cases"][0]["expectations"]["R1"]["maximum_total_clearing_time_s"] = 1
    result = ro.execute(package,tmp_path/"missing-breaker")
    assert result["results_valid"]
    assert result["criteria"] == {"evaluated": False,"passed": False}
    row = result["results"][0]["relays"][0]
    assert row["relay_operating_time_s"] is not None and row["total_clearing_time_s"] is None
    package = reference_package()
    package["cases"] = [package["cases"][-1]]
    package["cases"][0]["expectations"]["R1"]["maximum_relay_time_s"] = 0
    result = ro.execute(package,tmp_path/"deadline-failed")
    assert result["results_valid"] and not result["criteria"]["passed"] and result["criteria"]["evaluated"]


def test_parent_state_and_reset_between_trip_and_nontrip(tmp_path,monkeypatch):
    dss("Clear\nNew Circuit.keep basekv=12.47\nNew Load.keep bus1=sourcebus kv=12.47 kw=10 kvar=2\nSolve")
    before = deepcopy(ro.network._parent_signature())
    package = reference_package()
    package["cases"] = [package["cases"][-1],package["cases"][0]]
    result = ro.execute(package,tmp_path/"parent")
    assert result["results_valid"]
    assert [c["relays"][0]["trip_command"] for c in result["results"]] == [True,False]
    assert before == ro.network._parent_signature()
    assert ro.execute(package,tmp_path/"parent")["status"] == "BLOCKED_OUTPUT_DIRECTORY"
    monkeypatch.setattr(ro.pp,"__version__","unqualified")
    failed = ro.execute(package,tmp_path/"engine-changed")
    assert failed["status"] == "RELAY_OPERATION_INVALID" and not failed["results_valid"]
    assert "UNQUALIFIED" in failed["error"]


def test_multiple_relays_current_binding_and_stage_order(tmp_path):
    package = reference_package("DTOC")
    second = deepcopy(package["relays"][0])
    second["id"] = "R2"
    package["relays"].append(second)
    for case in package["cases"]:
        case["currents"]["R2"] = {"primary_rms_a":0,"source_reference":"OTHER_EXPLICIT_BRANCH"}
        case["expectations"]["R2"] = {"trip":False,"maximum_relay_time_s":None,
            "maximum_total_clearing_time_s":None,"source_reference":"NO_CURRENT_IN_OTHER_BRANCH"}
    result = ro.execute(package,tmp_path/"two")
    assert result["results_valid"] and result["criteria"]["passed"]
    assert all(not c["relays"][1]["trip_command"] for c in result["results"])
    second["settings"]["high_set_primary_a"] = 400
    assert not ro.validate(package)["ready_for_execution"]
