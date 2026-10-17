"""Published inputs, explicit boundaries, no mutation on invalid data."""
import pytest
from opendssdirect import dss
import server
from mcp_electrico import core, power_flow_boundaries as bounds, real_model_materializer as builder, runtime_safety
from scripts.published_feeder_reference import load_case, manifest, reference, compare, disconnected_loads


@pytest.mark.parametrize("case,count,branches,power",[("case33bw",33,32,3715),("case69",69,68,3802.1)])
def test_published_fact_inventories(case,count,branches,power):
    facts=load_case(case)
    assert len(facts["bus"])==count
    assert sum(int(row[10]) for row in facts["branch"])==branches
    assert sum(row[2] for row in facts["bus"])==pytest.approx(power,abs=.05)


@pytest.mark.parametrize("case",["case33bw","case69"])
@pytest.mark.parametrize("factor",[.5,1.,1.25])
def test_public_model_matches_independent_newton(case,factor):
    pytest.importorskip("pypower")
    facts=load_case(case)
    inputs=manifest(facts,factor)
    built=builder.materializar_modelo(inputs)
    assert built["materializer_status"]=="MODEL_BUILT_NOT_EXECUTED",built
    assert not built["source_p2_materialized"]
    checks=compare(server.ejecutar_flujo_potencia(),server.analizar_flujo_operacion(),
                   server.analizar_caida_tension(),reference(facts,factor))
    assert checks["passed"],checks


@pytest.mark.parametrize("field,value",[
    ("model","Thevenin"),("base_mva",0),("base_mva",float("nan")),
    ("r_pu",0),("x_pu",float("inf")),("r_pu",True),("r_pu",.1),
    ("tolerance",0),("max_iterations",1.5),("max_iterations",False),("source_reference","")])
def test_bad_boundary_rejected_before_mutation(field,value):
    core.crear_circuito("preserve_me",.48)
    inputs=manifest(load_case("case33bw"))
    inputs["source"]["power_flow_boundary"][field]=value
    assert bounds.validate(inputs)
    result=builder.materializar_modelo(inputs)
    assert result["materializer_status"]=="BLOCKED_BY_MATERIALIZER_PREFLIGHT"
    assert dss.Circuit.Name()=="preserve_me"


@pytest.mark.parametrize("low,high",[(None,1.5),(.5,None),(1.2,1.1),(0,1.5),(True,1.5),(.5,float("nan"))])
def test_bad_load_range_rejected(low,high):
    inputs=manifest(load_case("case33bw"))
    inputs["topology"]["loads"][0].update(vminpu=low,vmaxpu=high)
    assert bounds.validate(inputs)


def test_pf_source_is_not_a_fault_equivalent_and_does_not_linger():
    inputs=manifest(load_case("case33bw"))
    assert builder.materializar_modelo(inputs)["materializer_status"]=="MODEL_BUILT_NOT_EXECUTED"
    assert runtime_safety.evaluar_faultstudy_opendss()["status"]=="BLOCKED_PF_ONLY_SOURCE"
    with pytest.raises(ValueError,match="PFBND_FAULT001"):
        core.ejecutar_cortocircuito("n2")
    core.crear_circuito("fresh",.48)
    assert runtime_safety.evaluar_faultstudy_opendss()["status"]=="LEGACY_EXPERIMENTAL"


@pytest.mark.parametrize("scope",["IEC60909_3PH_MAX_MIN","AMPACITY","PROTECTION_TCC"])
def test_pf_boundary_cannot_claim_other_scope(scope):
    inputs=manifest(load_case("case33bw"))
    inputs["requested_scope"].append(scope)
    assert any(item["path"]=="requested_scope" for item in bounds.validate(inputs))


def test_pf_boundary_cannot_also_claim_utility_scc():
    inputs=manifest(load_case("case33bw"))
    inputs["source"]["scc_max_mva"]=1000.
    assert bounds.validate(inputs)


def test_load_voltage_interval_is_actually_applied():
    inputs=manifest(load_case("case33bw"))
    assert builder.materializar_modelo(inputs)["materializer_status"]=="MODEL_BUILT_NOT_EXECUTED"
    dss("? Load.c2.vminpu")
    assert float(dss.Text.Result())==.5


def test_topology_oracle_known_cuts():
    facts=load_case("case33bw")
    assert len(disconnected_loads(facts,0))==32
    assert disconnected_loads(facts,16)==["c18"]
    assert disconnected_loads(facts,32)==[]
