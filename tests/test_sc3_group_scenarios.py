"""Independent impedance checks and review binding for scoped initial SC3."""
import math
import pytest
from opendssdirect import dss
from mcp_electrico import core, professional_data as p2, sc_machines as machines, iec60909, short_circuit_precheck as review

def build(with_min=False):
    core.crear_circuito("explicit_group_sc3", .4, frecuencia=50, bus_fuente="grid")
    p2.reset();machines.reset()
    core.agregar_linea("feeder","grid","target",.02,fases=3,r1_ohm_km=.2,x1_ohm_km=.1)
    core.agregar_carga("group","target",20.,10.,fases=3,kv=.4)
    p2.definir_red_equivalente(kv_ll=.4,scc_max_mva=100.,x_r_max=10.,
        scc_min_mva=50. if with_min else None,x_r_min=10. if with_min else None,
        fuente_referencia="Synthetic independent impedance benchmark",bus_fuente="grid")
    return machines.definir_grupo_equivalente("Load.group",.5,.4,5.,15.,
        "Synthetic equivalent: rated Sn/Z, no individual mechanical ratings")

def acceptance(pre):
    return {"model_sha256":pre["model_sha256"],"uso_previsto":pre["supported_scope"],
        "calidad_datos":"SUPUESTOS_APROBADOS","referencia_revision":"Synthetic automated validation only",
        "supuestos_aprobados":["All model inputs are explicit synthetic test data."],
        "exclusiones_revisadas":[x["id"] for x in pre["items_to_review"]]}

@pytest.mark.parametrize("tolerance,cmax",[(6,1.05),(10,1.1)])
def test_equivalent_group_current_matches_independent_complex_impedances(tolerance,cmax):
    sheet=build()
    result=iec60909.ejecutar_3ph("max","target",lv_tol_percent=tolerance)
    assert result["ok"],result
    zgmag=cmax*.4**2/100
    zg=complex(zgmag/math.sqrt(101),zgmag*10/math.sqrt(101))
    zm=.4**2/.5*complex(.05,.15)
    expected=cmax*.4/math.sqrt(3)*abs(1/(zg+complex(.004,.002))+1/zm)
    assert result["results"]["ikss_ka"]==pytest.approx(expected,rel=2e-6)
    assert result["input_projection"]["lv_tol_percent"]==tolerance
    assert sheet["individual_motor_nameplate"] is False
    assert "pn_mech_mw" not in sheet
    # Operating demand cannot silently modify the explicit nominal equivalent.
    dss("Edit Load.group kW=900 kvar=800")
    changed=iec60909.ejecutar_3ph("max","target",lv_tol_percent=tolerance)
    assert changed["results"]["ikss_ka"]==pytest.approx(expected,rel=2e-6)

def test_max_only_can_run_without_inventing_minimum_source_and_default_pair_blocks():
    build()
    pair=review.evaluar("target")
    assert not pair["numerical_ready"]
    pre=review.evaluar("target",caso="max",lv_tol_percent=6)
    assert pre["numerical_ready"],pre
    absent=review.ejecutar_revisado("target",caso="max",lv_tol_percent=6)
    assert absent["electrical_calculation_executed"] is False
    result=review.ejecutar_revisado("target",caso="max",lv_tol_percent=6,revision_modelo=acceptance(pre))
    assert result["ok"],result
    assert set(result["scenarios"])=={"max"}
    assert result["omitted_cases"]==["min"]
    assert result["max_min_pair_complete"] is False
    assert result["protection_validation_supported"] is False

@pytest.mark.parametrize("change",[{"lv_tol_percent":10},{"caso":"max_min"}])
def test_case_and_voltage_factor_are_bound_to_model_review(change):
    build(with_min=True)
    original=review.evaluar("target",caso="max",lv_tol_percent=6)
    args={"caso":"max","lv_tol_percent":6,**change}
    result=review.ejecutar_revisado("target",revision_modelo=acceptance(original),**args)
    assert result["electrical_calculation_executed"] is False
    assert any(i["code"]=="SCREV003" for i in result["issues"])

@pytest.mark.parametrize("invalid",[0,5,7,True,float("nan"),float("inf"),"6",None])
def test_invalid_lv_options_are_rejected_without_solver(monkeypatch,invalid):
    build()
    def forbidden(*args,**kwargs): raise AssertionError("solver must not run")
    monkeypatch.setattr(iec60909,"calc_sc",forbidden)
    result=iec60909.ejecutar_3ph("max","target",lv_tol_percent=invalid)
    assert result["ok"] is False
    assert any(i["code"]=="P4SC305" for i in result["issues"])

def test_group_cannot_bypass_thermal_machine_decay_gate():
    build()
    result=iec60909.ejecutar_3ph("max","target",calcular_ip_ith=True,topology="radial",tk_s=.2)
    assert not result["ok"]
    assert any(i["code"]=="SCM106" for i in result["issues"])

def test_minimum_excludes_declared_group_and_keeps_explicit_temperature_requirement():
    build(with_min=True)
    assert not iec60909.ejecutar_3ph("min","target")["ok"]
    with_group=iec60909.ejecutar_3ph("min","target",line_endtemp_degree_c={"Line.feeder":80.},lv_tol_percent=6)
    assert with_group["ok"],with_group
    machines.clasificar_carga("Load.group","ESTATICA","Explicit no contribution for comparison")
    static=iec60909.ejecutar_3ph("min","target",line_endtemp_degree_c={"Line.feeder":80.},lv_tol_percent=6)
    assert static["results"]["ikss_ka"]==pytest.approx(with_group["results"]["ikss_ka"],rel=1e-12)

@pytest.mark.parametrize("fields",[{"sn_mva":0},{"vn_kv":0},{"r_percent":-1},{"x_percent":0},{"x_percent":101},{"sn_mva":True}])
def test_invalid_group_data_are_rejected(fields):
    build()
    args={"elemento_carga":"Load.group","sn_mva":.5,"vn_kv":.4,"r_percent":5.,"x_percent":15.,
        "referencia":"Explicit synthetic equivalent",**fields}
    with pytest.raises(ValueError):machines.definir_grupo_equivalente(**args)
