"""External design inputs and documented discrepancies; no whole-project claim."""
from copy import deepcopy
import pytest
from mcp_electrico import conductor_library, protection_checks
from scripts.lupech_cable_reference import load_facts, reference, arguments, compare

FACTS = load_facts()


@pytest.fixture(autouse=True)
def isolate_catalog(monkeypatch):
    # These published conductors have no P2 assignment; preserve caller state.
    monkeypatch.setattr(conductor_library,"obtener_asignacion",lambda element:None)


@pytest.mark.parametrize("row",FACTS["cases"],ids=lambda r:r["id"])
def test_published_minimum_sections_match_at_printed_precision(row):
    expected = reference(FACTS,row)
    assert abs(expected["published_minimum_difference_mm2"]) <= .005
    assert expected["status"] == row["expected_status"]


@pytest.mark.parametrize("row",FACTS["cases"],ids=lambda r:r["id"])
def test_real_design_checks_and_synthetic_boundaries(row):
    expected = reference(FACTS,row)
    result = protection_checks.evaluar_soportabilidad_termica_conductor(**arguments(FACTS,row))
    assert compare(result,expected)["comparison_passed"]
    for factor,status in ((.999,"FAIL"),(1.001,"PASS")):
        control = deepcopy(row)
        control["section_mm2"] = expected["minimum_section_mm2"]*factor
        result = protection_checks.evaluar_soportabilidad_termica_conductor(**arguments(FACTS,control))
        assert result["status"] == status
        assert compare(result,reference(FACTS,control))["comparison_passed"]


def test_parallel_runs_cannot_hide_the_published_outgoing_discrepancy():
    row = next(r for r in FACTS["cases"] if r["id"] == "33kv_outgoing")
    args = arguments(FACTS,row)
    assert row["parallel_runs"] == 3 and args["seccion_mm2"] == 300
    result = protection_checks.evaluar_soportabilidad_termica_conductor(**args)
    assert result["status"] == "FAIL"
    assert result["results"]["utilization_ratio"] == pytest.approx(2.0119712288)
    assert result["results"]["max_permissible_clearing_time_s_at_input_current"] == pytest.approx(.497025)


@pytest.mark.parametrize("key,code",[("fuente_k","P5C206"),("fuente_tiempo","P5C207"),("fuente_seccion","P5C209")])
def test_source_provenance_is_required(key,code):
    args = arguments(FACTS,FACTS["cases"][0]); args[key] = ""
    with pytest.raises(ValueError,match=code):
        protection_checks.evaluar_soportabilidad_termica_conductor(**args)


def test_case_is_a_published_design_not_a_field_validated_complete_network():
    assert len(FACTS["cases"]) == 7
    assert len(FACTS["source_pdf_sha256"]) == 64
    assert not FACTS["complete_real_project_qualified"] and not FACTS["full_standard_compliance_claim"]
    assert all(r["page"] in (159,160,161) for r in FACTS["cases"])
    assert "published cable design criterion" in FACTS["current_origin"]
