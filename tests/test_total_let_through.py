import pytest
from mcp_electrico import core, protection_data, conductor_library, protection_let_through as energy
from scripts.abb_let_through_reference import load_facts, arguments, compare


@pytest.fixture
def setup_case(monkeypatch):
    core.crear_circuito("abb_point_container",.4)
    protection_data.reset()
    monkeypatch.setattr(conductor_library,"obtener_asignacion",lambda element:None)
    protection_data.definir_dispositivo("abb_cb1","circuit_breaker","Bus.sourcebus",160,.4,
        fabricante="ABB",modelo="T1N160 In160",norma_referencia="ABB declared device data, not full standard review",
        icu_ka=36,fuente_referencia="ABB handbook printed p.74")
    return arguments(load_facts())


def test_published_manufacturer_point_and_capacity(setup_case):
    result = energy.evaluar_energia_pasante_conductor(**setup_case)
    assert compare(result)["comparison_passed"]
    assert result["results"]["total_let_through_i2t_a2s"] == 750000
    assert result["results"]["limit_k2s2_a2s"] == 33062500
    assert result["breaking_capacity_check"]["margin_ka"] == 6
    assert result["unit_conversion"]["multiplier"] == 1000000
    published = load_facts()["published_cable_capacity_ka2s"]
    assert abs(result["results"]["limit_k2s2_a2s"]/1000000-published) <= .05


def test_explicit_equivalent_units(setup_case):
    setup_case["punto_energia"].update(value=750000,unit="A2s")
    assert compare(energy.evaluar_energia_pasante_conductor(**setup_case))["comparison_passed"]


@pytest.mark.parametrize("semantics",["PRE_ARCING_I2T","MELTING_I2T","TRIP_TIME","",None])
def test_only_total_integral_can_protect_cable(setup_case,semantics):
    setup_case["punto_energia"]["semantics"] = semantics
    result = energy.evaluar_energia_pasante_conductor(**setup_case)
    assert result["status"] == "ENERGY_SEMANTICS_NOT_TOTAL"
    assert not result["thermal_calculation_performed"]


@pytest.mark.parametrize("key,value,status",[
    ("unit","J","ENERGY_UNIT_NOT_SUPPORTED"),("unit","kA2","ENERGY_UNIT_NOT_SUPPORTED"),
    ("current_ka",29,"ENERGY_REFERENCE_POINT_MISMATCH"),("current_ka",31,"ENERGY_REFERENCE_POINT_MISMATCH"),
    ("voltage_kv",.415,"ENERGY_REFERENCE_POINT_MISMATCH"),
    ("model","T1N160 In125","ENERGY_DEVICE_IDENTITY_MISMATCH"),
    ("manufacturer","Another maker","ENERGY_DEVICE_IDENTITY_MISMATCH"),
    ("model","","DEVICE_IDENTITY_INCOMPLETE")])
def test_exact_point_and_identity_are_required(setup_case,key,value,status):
    setup_case["punto_energia"][key] = value
    result = energy.evaluar_energia_pasante_conductor(**setup_case)
    assert result["status"] == status and not result["thermal_calculation_performed"]


@pytest.mark.parametrize("key,code",[("fuente_corriente","P5C305"),("fuente_k","P5C306"),("fuente_seccion","P5C307")])
def test_sources_are_required(setup_case,key,code):
    setup_case[key] = ""
    with pytest.raises(ValueError,match=code):
        energy.evaluar_energia_pasante_conductor(**setup_case)


def test_energy_source_is_required(setup_case):
    setup_case["punto_energia"]["source_reference"] = ""
    with pytest.raises(ValueError,match="P5C309"):
        energy.evaluar_energia_pasante_conductor(**setup_case)


@pytest.mark.parametrize("value",[0,-1,float("nan"),float("inf")])
def test_invalid_energy_values(setup_case,value):
    setup_case["punto_energia"]["value"] = value
    with pytest.raises(ValueError,match="P5C310"):
        energy.evaluar_energia_pasante_conductor(**setup_case)


def test_no_device_or_different_protected_element(setup_case):
    setup_case["dispositivo"] = "absent"
    assert energy.evaluar_energia_pasante_conductor(**setup_case)["status"] == "DEVICE_NOT_FOUND"
    setup_case["dispositivo"] = "abb_cb1"; setup_case["elemento"] = "Line.other"
    assert energy.evaluar_energia_pasante_conductor(**setup_case)["status"] == "PROTECTED_ELEMENT_MISMATCH"


def test_bad_cut_rating_blocks_even_with_good_energy(setup_case):
    protection_data.reset()
    protection_data.definir_dispositivo("abb_cb1","circuit_breaker","Bus.sourcebus",160,.4,
        fabricante="ABB",modelo="T1N160 In160",norma_referencia="synthetic insufficient Icu control",
        icu_ka=20,fuente_referencia="synthetic negative control")
    result = energy.evaluar_energia_pasante_conductor(**setup_case)
    assert result["status"] == "BREAKING_CAPACITY_NOT_PASSED"
    assert result["breaking_capacity_check"]["status"] == "FAIL"
    assert not result["thermal_calculation_performed"]


def test_registered_conductor_section_is_not_substituted(setup_case,monkeypatch):
    monkeypatch.setattr(conductor_library,"obtener_asignacion",lambda e:{"producto":{"seccion_mm2":35}})
    result = energy.evaluar_energia_pasante_conductor(**setup_case)
    assert result["status"] == "SECTION_MISMATCH"
    assert not result["thermal_calculation_performed"]


def test_whitespace_cannot_bypass_the_registered_conductor(setup_case,monkeypatch):
    setup_case["elemento"] = "  Bus.sourcebus  "
    monkeypatch.setattr(conductor_library,"obtener_asignacion",
        lambda e:{"producto":{"seccion_mm2":35}} if e == "Bus.sourcebus" else None)
    result = energy.evaluar_energia_pasante_conductor(**setup_case)
    assert result["status"] == "SECTION_MISMATCH"
    assert not result["thermal_calculation_performed"]


def test_cut_rating_at_another_voltage_is_not_reused(setup_case):
    protection_data.reset()
    protection_data.definir_dispositivo("abb_cb1","circuit_breaker","Bus.sourcebus",160,.69,
        fabricante="ABB",modelo="T1N160 In160",norma_referencia="synthetic other voltage",
        icu_ka=36,fuente_referencia="synthetic negative control")
    result = energy.evaluar_energia_pasante_conductor(**setup_case)
    assert result["status"] == "BREAKING_RATING_VOLTAGE_MISMATCH"
    assert not result["thermal_calculation_performed"]


@pytest.mark.parametrize("factor,status",[(.999,"FAIL"),(1.001,"PASS")])
def test_boundary_sensitivity_not_published_cases(setup_case,factor,status):
    setup_case["seccion_mm2"] = (750000**.5/115)*factor
    result = energy.evaluar_energia_pasante_conductor(**setup_case)
    assert result["status"] == status
    assert result["clearing_time"] is None


def test_numerical_overflow_is_not_emitted(setup_case):
    setup_case["k_a_sqrt_s_per_mm2"] = 1e200
    with pytest.raises(ValueError,match="P5C313"):
        energy.evaluar_energia_pasante_conductor(**setup_case)
