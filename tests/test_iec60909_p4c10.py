from mcp_electrico import iec60909_conformance, iec60909_contract, p4_completion


def test_p4c10_review_is_complete_but_does_not_claim_full_standard_conformance():
    result = iec60909_conformance.evaluar_revision()
    review = result["review"]

    assert result["complete"] is True
    assert review["target_standard"] == "IEC_60909_0_2026"
    assert review["target_edition"] == "3.0"
    assert review["backend"] == "pandapower"
    assert review["backend_version"] == "3.5.4"
    assert review["status"] == "REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION"
    assert review["decision"] == "P4C10_REVIEW_COMPLETE_WITH_LIMITATIONS"
    assert review["full_conformance_claim"] is False
    assert review["full_text_bundled"] is False
    assert review["professional_emission"] is False


def test_p4c10_pins_primary_metadata_and_backend_sources_without_bundling_standard():
    result = iec60909_conformance.evaluar_revision()
    evidence = result["evidence"]

    assert evidence["iec_official_metadata"]["kind"] == "PRIMARY_METADATA"
    assert evidence["iec_official_metadata"]["url"] == "https://webstore.iec.ch/en/publication/68454"
    assert evidence["pandapower_calc_sc_v354"]["blob_sha"] == "e9f53a79d3ebe9eaacbd9989afadabaa7ed927df"
    assert evidence["pandapower_branch_model_v354"]["blob_sha"] == "73868de22e31f73d40749c30b14ab26f8e1b49bc"
    assert result["review"]["full_text_bundled"] is False


def test_p4c10_keeps_2026_clause6_and_non_p4_results_as_explicit_limitations():
    review = iec60909_conformance.evaluar_revision()["review"]
    findings = review["clause_findings"]

    assert review["edition_change_assessment"]["impact_on_p4_v1"] == "LIMITED_SCOPE_REVIEW_REQUIRED"
    assert findings["equipment_modelling_clause_6"]["status"] == "REVIEWED_WITH_LIMITATIONS"
    assert findings["initial_fault_types"]["status"] == "MATCHED_WITH_SCOPE_EXCLUSION"
    assert findings["breaking_and_steady_state"]["status"] == "OUTSIDE_P4_V1_RESULT_SCOPE"
    assert "two_phase_ground" in review["out_of_scope_faults"]
    assert "symmetrical breaking current Ib" in review["excluded_equipment_or_methods"]
    assert "steady-state short-circuit current Ik" in review["excluded_equipment_or_methods"]
    assert review["upgrade_to_full_verification_requires"]


def test_p4c10_contract_and_gate_preserve_limited_review_after_p4_closure():
    contract = iec60909_contract.obtener_contrato_p4()
    gate = p4_completion.evaluar_cierre_p4()
    criteria = {item["id"]: item for item in gate["criteria"]}

    assert contract["backend"]["target_edition_conformance"] == iec60909_conformance.REVIEW_STATUS
    assert contract["backend"]["target_edition_conformance"] != iec60909_conformance.FULL_VERIFICATION_STATUS
    assert contract["backend"]["full_conformance_claim"] is False
    assert criteria["P4C10"]["status"] == "DONE"
    assert criteria["P4C12"]["status"] == "DONE"
    assert gate["phase_status"] == "READY_WITH_LIMITATIONS"
    assert gate["ready_for_next_phase"] is True
    assert gate["professional_emission"] is False
