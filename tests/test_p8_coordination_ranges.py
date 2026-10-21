"""P8 ranges: admission, P4 reuse, design failures, reports and integrity."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from mcp_electrico import (
    dossier_integrity, protection_coordination_range, real_controlled_execution,
    real_coordination_execution as ranges, real_pilot_intake,
    real_project_dossier as dossier, real_protection_execution as protection,
    workspace_p8d2_view, workspace_state,
)

ROOT = Path(__file__).resolve().parents[1]


def manifest():
    return json.loads((ROOT / "examples/p10_reference_coordination_range.json").read_text(encoding="utf8"))


def request(m):
    return m["protection"]["coordination_ranges"][0]


def test_optional_absence_remains_not_requested_not_a_selectivity_pass():
    m = manifest()
    del m["protection"]["coordination_ranges"]
    result = protection.ejecutar_protecciones(m)
    assert result["execution_status"] == protection.STATUS_COMPLETED, result
    summary = result["coordination_ranges"]
    assert summary["status"] == "NOT_REQUESTED"
    assert summary["requested_count"] == 0 and not summary["calculation_performed"]
    assert not summary["selectivity_integral_evaluated"]
    assert not any(c["check"] == "temporal_coordination_range" for c in result["design_assessment"]["checks"])


@pytest.mark.parametrize("fault_type", ["3ph", "1ph-ground"])
def test_p4_bounds_reused_once_with_same_manifest_and_revision(fault_type, monkeypatch):
    m = manifest()
    for bound in request(m)["current_bounds"].values():
        bound["fault_type"] = fault_type
    counts = {"fault_3ph": 0, "fault_1ph": 0, "range": 0}
    def tracked(name, original):
        def wrapped(*args, **kwargs):
            counts[name] += 1
            return original(*args, **kwargs)
        return wrapped
    monkeypatch.setattr(real_controlled_execution, "_execute_3ph",
                        tracked("fault_3ph", real_controlled_execution._execute_3ph))
    monkeypatch.setattr(real_controlled_execution, "_execute_1ph_ground",
                        tracked("fault_1ph", real_controlled_execution._execute_1ph_ground))
    monkeypatch.setattr(protection_coordination_range, "evaluar_coordinacion_intervalo",
                        tracked("range", protection_coordination_range.evaluar_coordinacion_intervalo))
    result = protection.ejecutar_protecciones(m)
    assert result["execution_status"] == protection.STATUS_COMPLETED, result
    summary = result["coordination_ranges"]
    assert summary["status"] == "PASS"
    assert counts == {"fault_3ph": 1, "fault_1ph": 1, "range": 1}
    row = summary["ranges"][0]
    assert row["model_revision"] == result["model_revision"] == summary["model_revision"]
    assert row["manifest_sha256"] == result["manifest_sha256"] == summary["manifest_sha256"]
    for name, case in (("minimum", "min"), ("maximum", "max")):
        assert row["p4_provenance"][name]["case"] == case
        assert row["p4_provenance"][name]["fault_bus"] == "lv_load_bus"
        assert row["p4_provenance"][name]["fault_type"] == fault_type
        assert row["result"]["currents"]["downstream_" + ("min" if case == "min" else "max") + "_a"] == row["p4_provenance"][name]["fault_current_ka"] * 1000
    assert workspace_state.status()["studies"]["protection_tcc"]["valid"]


def invalidate(m, change):
    r = request(m)
    if change == "null": m["protection"]["coordination_ranges"] = None
    elif change == "not_object": m["protection"]["coordination_ranges"] = [42]
    elif change == "duplicate": m["protection"]["coordination_ranges"].append(deepcopy(r))
    elif change == "same_device": r["upstream_device_id"] = "Protection.qf_lv"
    elif change == "unknown_device": r["upstream_device_id"] = "absent"
    elif change == "bool_ratio": r["upstream_to_downstream_ratio"] = True
    elif change == "zero_ratio": r["upstream_to_downstream_ratio"] = 0
    elif change == "negative_margin": r["required_margin_s"] = -1
    elif change == "missing_source": r["currents_source_reference"] = " "
    elif change == "unknown_field": r["margen"] = .3
    elif change == "missing_scope": m["requested_scope"].remove("PROTECTION_TCC")
    elif change == "missing_p4_scope": m["requested_scope"].remove("IEC60909_3PH_MAX_MIN")
    elif change == "wrong_case": r["current_bounds"]["minimum"]["case"] = "max"
    elif change == "wrong_quantity": r["current_bounds"]["minimum"]["current_quantity"] = "ip_ka"
    elif change == "unknown_bus": r["current_bounds"]["minimum"]["fault_bus"] = "absent"
    elif change == "mixed_fault": r["current_bounds"]["minimum"]["fault_type"] = "1ph-ground"
    elif change == "mixed_bus": r["current_bounds"]["minimum"]["fault_bus"] = "mv_load_bus"
    elif change == "voltage": r["current_bounds"]["minimum"]["operating_voltage_kv"] = 0
    elif change == "invalid_fault_type": r["current_bounds"]["minimum"]["fault_type"] = []
    elif change == "bound_typo": r["current_bounds"]["minimum"]["typo"] = 1


@pytest.mark.parametrize("change", [
    "null", "not_object", "duplicate", "same_device", "unknown_device", "bool_ratio",
    "zero_ratio", "negative_margin", "missing_source", "unknown_field", "missing_scope",
    "missing_p4_scope", "wrong_case", "wrong_quantity", "unknown_bus", "mixed_fault",
    "mixed_bus", "voltage", "invalid_fault_type", "bound_typo",
])
def test_bad_request_blocked_at_admission_before_any_execution(change, monkeypatch, tmp_path):
    m = manifest()
    invalidate(m, change)
    assert not real_pilot_intake.evaluar_admision(m)["ready_to_build_model"]
    def forbidden(*args, **kwargs):
        pytest.fail("invalid range must not execute P8D1")
    monkeypatch.setattr(real_controlled_execution, "ejecutar_controlado", forbidden)
    result = dossier.generar_dossier(m, str(tmp_path / "blocked"))
    assert result["status"] == dossier.STATUS_BLOCKED_EXECUTION
    assert not result["p8d2_execution"]["electrical_calculation_performed"]
    assert not (tmp_path / "blocked").exists()


def test_real_temporal_fail_delivered_visibly_with_protected_trace(tmp_path):
    m = manifest()
    request(m)["required_margin_s"] = 100
    result = dossier.generar_dossier(m, str(tmp_path / "design-fail"))
    assert result["status"] == dossier.STATUS_READY, result
    assessment = result["design_assessment"]
    assert assessment["calculation_valid"] and assessment["status"] == "DECLARED_CHECKS_FAILED"
    assert any(c["scope"] == "TEMPORAL_COORDINATION_RANGE" and c["status"] == "FAIL"
               and c["element"] == "LV_SERIES_PAIR" for c in assessment["checks"])
    saved = json.loads(Path(result["coordination_ranges_path"]).read_text(encoding="utf8"))
    assert saved["status"] == "FAIL"
    assert saved["manifest_sha256"] == result["manifest_sha256"]
    assert saved["model_revision"] == result["model_revision"]
    assert not saved["selectivity_integral_evaluated"]
    for filename in ("workspace_v5.html", "project_report_p7c.html"):
        html = (tmp_path / "design-fail" / filename).read_text(encoding="utf8")
        assert 'data-module="mcp-coordination-ranges"' in html
        assert "LV_SERIES_PAIR" in html and "Peor margen" in html
        assert "No acredita selectividad integral" in html
    assert dossier_integrity.verificar_indice(result["integrity"]["index_path"])["ok"]
    Path(result["coordination_ranges_path"]).write_text("{}", encoding="utf8")
    assert not dossier_integrity.verificar_indice(result["integrity"]["index_path"])["ok"]


def test_internal_curve_gap_prevents_any_ready_dossier(tmp_path):
    m = manifest()
    baseline = protection.ejecutar_protecciones(m)
    assert baseline["execution_status"] == protection.STATUS_COMPLETED
    currents = baseline["coordination_ranges"]["ranges"][0]["result"]["currents"]
    low, high = currents["downstream_min_a"], currents["downstream_max_a"]
    a, b = low + .4 * (high - low), low + .6 * (high - low)
    def point(i):
        return {"current_a": i, "time_min_s": 3, "time_max_s": 4}
    m["protection"]["tcc_datasets"][-1]["segments"] = [
        {"id": "low", "points": [point(800), point(a)]},
        {"id": "high", "points": [point(b), point(120000)]},
    ]
    result = dossier.generar_dossier(m, str(tmp_path / "gap"))
    assert result["status"] == dossier.STATUS_BLOCKED_EXECUTION, result
    execution = result["p8d2_execution"]
    assert execution["coordination_ranges"]["status"] == "NOT_EVALUABLE"
    assert not execution["resultados_validos"] and not execution["workspace_study_recorded"]
    assert not (tmp_path / "gap").exists()


@pytest.mark.parametrize("failure", ["exception", "nan", "wrong_range", "wrong_pair", "wrong_criterion", "not_object"])
def test_invalid_envelope_never_promoted_or_delivered(failure, monkeypatch, tmp_path):
    native = protection_coordination_range.evaluar_coordinacion_intervalo
    def injected(*args, **kwargs):
        if failure == "exception":
            raise RuntimeError("injected failure")
        if failure == "not_object":
            return ["invalid result"]
        result = native(*args, **kwargs)
        if failure == "nan": result["worst_case"]["conservative_margin_s"] = float("nan")
        elif failure == "wrong_range": result["currents"]["downstream_min_a"] = 1
        elif failure == "wrong_pair": result["relationship"]["upstream_device"] = "absent"
        elif failure == "wrong_criterion": result["required_margin_s"] = 999
        return result
    monkeypatch.setattr(protection_coordination_range, "evaluar_coordinacion_intervalo", injected)
    result = dossier.generar_dossier(manifest(), str(tmp_path / "invalid"))
    assert result["status"] == dossier.STATUS_BLOCKED_EXECUTION
    assert not result["p8d2_execution"]["resultados_validos"]
    assert not (tmp_path / "invalid").exists()
    json.dumps(result, allow_nan=False)


def test_missing_p4_reference_never_invokes_the_curve_executor(monkeypatch):
    m = manifest()
    requests, issues = ranges.preflight(m)
    assert not issues
    def missing(execution, binding):
        return None, [{"code": "MISSING_P4", "message": "missing injected target"}]
    def forbidden(*args, **kwargs):
        pytest.fail("P5E must not run without valid P4 bounds")
    monkeypatch.setattr(protection_coordination_range, "evaluar_coordinacion_intervalo", forbidden)
    summary = ranges.evaluate(requests, {"model_revision": 12, "manifest_sha256": "explicit"}, missing)
    assert summary["status"] == "NOT_EVALUABLE"
    assert summary["executor_invocation_count"] == 0 and not summary["calculation_performed"]


def test_renderer_escapes_labels_and_absent_requests_do_not_show_pass():
    assert workspace_p8d2_view.coordination_section({"requested_count": 0}) == ""
    label = '<img src=x onerror="alert(1)">'
    summary = {"requested_count": 1, "ranges": [{
        "range_id": label, "request": {}, "result": {}, "result_usable": False}]}
    html = workspace_p8d2_view.coordination_section(summary)
    assert "<img" not in html and "&lt;img" in html
    assert "NOT_EVALUABLE" in html
