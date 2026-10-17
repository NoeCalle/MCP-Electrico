"""Real-source audit, honest admission and numerical diagnostic integration."""
from copy import deepcopy
import pytest
from opendssdirect import dss
import server
from mcp_electrico import core, real_model_materializer as builder, real_pilot_intake
from scripts.unam_industrial_reference import load_facts, audit, manifest, reference, compare_translation, compare_published, VARIANTS


def test_source_inventory_and_provenance():
    f = load_facts()
    assert len(f["etap_voltages_pct"]) == 14
    assert len(f["lines"]) == 8 and len(f["transformers"]) == 4 and len(f["loads"]) == 5
    assert sum(row["kw"] for row in f["loads"]) == pytest.approx(4292.9)
    assert f["source_pdf_sha256"] == "c0a2c846f924c908cdee7ba1eee5b2583f6c57d6d38d6c3559155e39d3d9e20e"


def test_audit_preserves_all_source_conflicts_and_does_not_promote_case():
    result = audit(load_facts())
    assert result["status"] == "BLOCKED_FULL_REFERENCE_QUALIFICATION"
    assert not result["can_claim_complete_reference"] and not result["can_claim_etap_parity"]
    ids = {row["id"] for row in result["findings"]}
    assert {"LENGTH_CP09","LENGTH_CP10","LENGTH_CP11","SE01_REACTANCE","NEW_TRANSFORMER_LOSS_INPUTS","TABLE613_ZERO_SEQUENCE_LABEL","LV_IMPEDANCE_BASE"} <= ids
    assert result["missing"] and "NOT_IEC60909" in result["short_circuit_comparison"]


def test_wrong_zero_sequence_label_is_reconciled_without_source_projection():
    result = audit(load_facts())
    row = next(r for r in result["findings"] if r["id"] == "TABLE613_ZERO_SEQUENCE_LABEL")
    assert row["recomputed_z0_plus_2z1"] == pytest.approx(row["table_labeled_z0"],abs=1e-9)
    base = next(r for r in result["findings"] if r["id"] == "LV_IMPEDANCE_BASE")
    assert base["voltage_base_ratio_squared"] == pytest.approx(2500)
    assert base["cp09_correct_local_r_pu"] == pytest.approx(2500*base["cp09_using_23kv_base_r_pu"])


def test_unresolved_original_inputs_block_before_mutation():
    core.crear_circuito("preserve_unam_parent",.48)
    data = manifest(load_facts(),diagnostic=False)
    admission = real_pilot_intake.evaluar_admision(data)
    assert not admission["ready_to_build_model"]
    assert builder.materializar_modelo(data)["materializer_status"] == "BLOCKED_BY_P8B_INTAKE"
    assert dss.Circuit.Name() == "preserve_unam_parent"


@pytest.mark.parametrize("variant",VARIANTS)
def test_diagnostic_manifest_discloses_conventions_and_no_fictitious_breaker(variant):
    data = manifest(load_facts(),variant)
    assert len(data["topology"]["buses"]) == 13
    assert "bus_09" not in data["topology"]["buses"]
    assert len(data["topology"]["lines"]) == 8
    assert data["qualification_status"] == "DIAGNOSTIC_ONLY"
    assert not data["source_reference_admitted"]
    assert data["qualification_conventions"]["clock"]
    assert all(t["no_load_loss_kw"] == 0 and t["i0_percent"] == 0 for t in data["topology"]["transformers"])
    assert "scc_max_mva" not in data["source"]


@pytest.mark.parametrize("variant",VARIANTS)
def test_diagnostic_translation_matches_independent_newton(variant):
    pytest.importorskip("pypower")
    f = load_facts()
    built = builder.materializar_modelo(manifest(f,variant))
    assert built["materializer_status"] == "MODEL_BUILT_NOT_EXECUTED", built
    flow = server.ejecutar_flujo_potencia()
    comparison = compare_translation(flow,server.analizar_flujo_operacion(),reference(f,variant))
    assert comparison["translation_passed"], comparison
    assert not comparison["complete_real_project_qualified"] and not comparison["etap_parity_qualified"]
    difference = compare_published(flow,f)
    assert difference["status"] == "DIAGNOSTIC_NOT_ACCEPTANCE"
    assert not difference["can_claim_etap_parity"]


def test_source_is_not_calibrated_to_the_etap_answer():
    f = load_facts()
    data = manifest(f)
    changed = deepcopy(f)
    changed["etap_voltages_pct"] = {b:80. for b in f["etap_voltages_pct"]}
    changed["etap_source_power"] = {"kw":100000.,"kvar":100000.}
    assert manifest(changed) == data
