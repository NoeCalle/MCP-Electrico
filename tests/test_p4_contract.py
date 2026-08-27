from mcp_electrico import iec60909_contract, p4_completion


def test_p4_contract_targets_current_2026_edition_and_preserves_engine_policy():
    contract = iec60909_contract.obtener_contrato_p4()

    assert contract["target_standard"]["id"] == "IEC_60909_0_2026"
    assert contract["target_standard"]["edition"] == "3.0"
    assert contract["target_standard"]["publication_date"] == "2026-07-23"
    assert contract["target_standard"]["status"] == "CURRENT"
    assert contract["backend"]["engine"] == "pandapower"
    assert contract["backend"]["automatic_dispatch"] is False
    assert contract["backend"]["crosscheck"] is False
    assert contract["backend"]["target_edition_conformance"] == "UNVERIFIED_AGAINST_TARGET_EDITION"
    assert contract["professional_emission"] is False


def test_p4_fault_scope_is_fail_closed_for_two_phase_ground_and_zero_sequence():
    scope = iec60909_contract.obtener_contrato_p4()["fault_scope"]

    assert scope["three_phase"]["pandapower_fault"] == "3ph"
    assert scope["three_phase"]["p4_v1_candidate"] is True
    assert scope["single_phase_ground"]["status"] == "BLOCKED_BY_ZERO_SEQUENCE_VALIDATION"
    assert "zero" in scope["single_phase_ground"]["sequence_requirements"]
    assert scope["two_phase_ground"]["pandapower_fault"] is None
    assert scope["two_phase_ground"]["backend_api_supported"] is False
    assert scope["two_phase_ground"]["p4_v1_candidate"] is False


def test_p4_source_mapping_makes_x_over_r_to_r_over_x_conversion_explicit():
    mapping = iec60909_contract.obtener_contrato_p4()["source_mapping"]

    assert mapping["p2_x_r_max"] == "ext_grid.rx_max = 1 / X_R_max"
    assert mapping["p2_x_r_min"] == "ext_grid.rx_min = 1 / X_R_min"
    assert "P2 almacena X/R" in mapping["note"]


def test_p4_result_contract_does_not_invent_ib_or_ik():
    results = iec60909_contract.obtener_contrato_p4()["result_contract"]

    assert results["ikss_ka"]["iec_symbol"] == "Ik''"
    assert results["ip_ka"]["iec_symbol"] == "ip"
    assert results["ith_ka"]["iec_symbol"] == "Ith"
    assert results["ib_ka"]["pandapower_field"] is None
    assert results["ib_ka"]["status"] == "PENDING_P4_STRATEGY"
    assert results["ik_ka"]["pandapower_field"] is None
    assert results["ik_ka"]["status"] == "PENDING_P4_STRATEGY"


def test_p4_gate_starts_with_only_foundation_contract_done():
    gate = p4_completion.evaluar_cierre_p4()
    states = {item["id"]: item["status"] for item in gate["criteria"]}

    assert gate["phase"] == "P4"
    assert gate["phase_status"] == "NOT_READY"
    assert gate["ready_for_next_phase"] is False
    assert gate["next_phase"] is None
    assert gate["professional_emission"] is False
    assert states["P4C01"] == "DONE"
    assert states["P4C02"] == "DONE"
    for cid in [f"P4C{i:02d}" for i in range(3, 13)]:
        assert states[cid] == "PENDING"
