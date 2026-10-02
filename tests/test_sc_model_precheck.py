"""Regression: missing review must stop execution before the numerical solver."""
from copy import deepcopy

import pytest
from opendssdirect import dss

import server
from mcp_electrico import (core, iec60909_suite, pandapower_engine,
                          professional_data, short_circuit_precheck as gate,
                          visual_state, workspace_p4_view, workspace_state)


@pytest.fixture
def model():
    core.crear_circuito("review_gate", 13.8)
    visual_state.reset()
    professional_data.reset()
    workspace_state.reset_for_circuit("test")
    professional_data.definir_red_equivalente(
        13.8, 500., 10., 250., 5., fuente_referencia="Synthetic regression inputs",
    )
    core.agregar_linea("link", "sourcebus", "b1", .001, fases=3,
                      r1_ohm_km=.001, x1_ohm_km=.001)
    core.agregar_carga("aggregate", "b1", 100., 25., fases=3, kv=13.8)
    return {"Line.link": 20.}


def review(p):
    return {
        "model_sha256": p["model_sha256"],
        "uso_previsto": "APORTE_FUENTES_EQUIVALENTES",
        "calidad_datos": "SUPUESTOS_APROBADOS",
        "referencia_revision": "Synthetic test fixture: explicit review of source-only scope.",
        "supuestos_aprobados": ["Synthetic source500/250MVA, link R=X1e-6ohm, Load100/25kW/kvar; temperature20°C."],
        "exclusiones_revisadas": [i["id"] for i in p["items_to_review"]],
    }


def test_precheck_shows_unknown_machine_and_virtual_link_without_solving(model, monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("A read-only precheck called the electrical solver")
    monkeypatch.setattr(iec60909_suite, "ejecutar_3ph_max_min", fail)
    before = workspace_state.status()
    p = server.evaluar_preparacion_cortocircuito_3ph("b1", model)
    assert workspace_state.status() == before
    assert p["numerical_ready"] is True
    assert p["physical_completeness_verified"] is False
    assert p["input_inventory"]["near_ideal_links_to_confirm"] == ["Line.link"]
    assert p["input_inventory"]["loads_without_motor_fault_model"][0]["id"] == "Load.aggregate"
    assert "APORTE_MOTORES" in [i["id"] for i in p["items_to_review"]]


def test_public_tool_blocks_missing_review_without_solver_or_currents(model, monkeypatch):
    monkeypatch.setattr(iec60909_suite, "ejecutar_3ph_max_min",
                        lambda *a, **k: pytest.fail("Solver ran without review"))
    result = server.ejecutar_cortocircuito_iec60909_3ph("b1", model)
    assert result["ok"] is False
    assert result["electrical_calculation_executed"] is False
    assert result["execution_status"] == "BLOQUEADO_ANTES_DEL_CALCULO"
    assert "scenarios" not in result and "results" not in result
    assert "SCREV002" in [i["code"] for i in result["issues"]]
    assert workspace_state.status()["studies"]["iec60909_3ph"]["valid"] is False


@pytest.mark.parametrize("mutation", ["source", "load", "switch"])
def test_changed_inputs_invalidate_review(model, monkeypatch, mutation):
    p = gate.evaluar("b1", model)
    r = review(p)
    if mutation == "source":
        professional_data.definir_red_equivalente(13.8, 600., 10., 250., 5., fuente_referencia="Changed source")
    elif mutation == "load":
        dss("edit Load.aggregate kw=200")
    else:
        dss("open Line.link term=1")
    monkeypatch.setattr(iec60909_suite, "ejecutar_3ph_max_min",
                        lambda *a, **k: pytest.fail("Solver ran with stale approval"))
    result = gate.ejecutar_revisado("b1", model, revision_modelo=r)
    assert result["electrical_calculation_executed"] is False
    assert "SCREV003" in [i["code"] for i in result["issues"]]


@pytest.mark.parametrize("field,value,code", [
    ("uso_previsto", "COMPROBAR_PROTECCIONES", "SCREV004"),
    ("calidad_datos", [], "SCREV005"),
    ("referencia_revision", "  ", "SCREV006"),
    ("exclusiones_revisadas", ["ORIGEN_DATOS"], "SCREV007"),
    ("supuestos_aprobados", [], "SCREV008"),
])
def test_ambiguous_or_wrong_scope_review_blocks(model, monkeypatch, field, value, code):
    p = gate.evaluar("b1", model)
    r = review(p);r[field] = value
    monkeypatch.setattr(iec60909_suite, "ejecutar_3ph_max_min",
                        lambda *a, **k: pytest.fail("Solver ran with invalid review"))
    result = gate.ejecutar_revisado("b1", model, revision_modelo=r)
    assert code in [i["code"] for i in result["issues"]]
    assert not result["electrical_calculation_executed"]


def test_numerical_missing_temperature_not_overridden_by_review(model, monkeypatch):
    p = gate.evaluar("b1")
    monkeypatch.setattr(iec60909_suite, "ejecutar_3ph_max_min",
                        lambda *a, **k: pytest.fail("Solver ran with missing MIN data"))
    result = gate.ejecutar_revisado("b1", revision_modelo=review(p))
    assert not result["ok"] and not result["electrical_calculation_executed"]
    assert any(i["code"] == "P4SC201" for i in p["numeric_readiness"]["min"]["issues"])


def test_changed_study_temperature_invalidates_review(model, monkeypatch):
    p = gate.evaluar("b1", model)
    monkeypatch.setattr(iec60909_suite, "ejecutar_3ph_max_min",
                        lambda *a, **k: pytest.fail("Solver ran with unreviewed temperature"))
    result = gate.ejecutar_revisado("b1", {"Line.link": 90.}, revision_modelo=review(p))
    assert not result["electrical_calculation_executed"]
    assert "SCREV003" in [i["code"] for i in result["issues"]]


def test_changed_clearing_time_invalidates_review(model, monkeypatch):
    p = gate.evaluar("b1", model, True, "radial", .2)
    monkeypatch.setattr(iec60909_suite, "ejecutar_3ph_max_min",
                        lambda *a, **k: pytest.fail("Solver ran with unreviewed clearing time"))
    result = gate.ejecutar_revisado("b1", model, True, "radial", .5, revision_modelo=review(p))
    assert not result["electrical_calculation_executed"]
    assert "SCREV003" in [i["code"] for i in result["issues"]]


def test_explicit_untranslated_induction_machine_is_not_silently_omitted(model):
    dss("new IndMach012.motor bus1=b1 phases=3 kv=13.8 kva=200")
    p = gate.evaluar("b1", model)
    assert p["numerical_ready"] is False
    assert p["input_inventory"]["untranslated_fault_sources"] == ["IndMach012.motor"]


def test_reviewed_numeric_results_stay_partial_and_visible_in_workspace(model):
    p = gate.evaluar("b1", model)
    r = review(p)
    result = server.ejecutar_cortocircuito_iec60909_3ph("b1", model, revision_modelo=r)
    assert result["ok"] is True
    assert result["result_scope"] == "APORTE_FUENTES_EQUIVALENTES"
    assert result["physical_completeness_verified"] is False
    assert result["protection_validation_supported"] is False
    assert result["model_review"] == r
    assert all(result["scenarios"][k]["results"]["ikss_ka"] > 0 for k in ("max", "min"))
    assert result["scenarios"]["max"]["engine"]["engine_version_runtime"] == "3.5.4"
    block = workspace_p4_view._study_block("iec60909_3ph", result)
    assert "APORTE PARCIAL" in block and "NO VALIDA PROTECCIONES" in block
    assert "Estado <strong class=\"p4-ok\">COMPLETO" not in block
    cloned = deepcopy(r);cloned["supuestos_aprobados"].append("Mutated later")
    assert result["model_review"] == r


@pytest.mark.parametrize("frequency", [50., 60.])
def test_adapter_preserves_actual_system_frequency(model, frequency):
    dss(f"set frequency={frequency}")
    m = pandapower_engine._collect_active_model()
    net, _, _ = pandapower_engine._build_net(m)
    assert net.f_hz == frequency
