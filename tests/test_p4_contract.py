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


def test_p4_fault_scope_has_explicit_sequence_policies_and_keeps_2ph_ground_blocked():
    scope = iec60909_contract.obtener_contrato_p4()["fault_scope"]

    assert scope["three_phase"]["pandapower_fault"] == "3ph"
    assert scope["three_phase"]["p4_v1_candidate"] is True

    two_phase = scope["two_phase"]
    assert two_phase["pandapower_fault"] == "2ph"
    assert two_phase["backend_api_supported"] is True
    assert two_phase["status"] == "FOUNDATION_READY"
    assert two_phase["sequence_requirements"] == ["positive", "negative"]
    policy = two_phase["negative_sequence_policy"]
    assert policy["relation"] == "Z2 = Z1"
    assert policy["explicit"] is True
    assert policy["universal_assumption"] is False

    one_phase = scope["single_phase_ground"]
    assert one_phase["pandapower_fault"] == "1ph"
    assert one_phase["backend_api_supported"] is True
    assert one_phase["status"] == "FOUNDATION_READY"
    assert one_phase["sequence_requirements"] == ["positive", "negative", "zero"]
    assert one_phase["negative_sequence_policy"]["relation"] == "Z2 = Z1"
    assert one_phase["negative_sequence_policy"]["explicit"] is True
    assert one_phase["negative_sequence_policy"]["universal_assumption"] is False
    assert "C0 no se inventa" in one_phase["zero_sequence_policy"]["lines"]
    assert one_phase["result_scope"]["ikss"] is True
    assert one_phase["result_scope"]["skss_normalized"] is False
    assert one_phase["result_scope"]["ip_ith"] is False

    assert scope["two_phase_ground"]["pandapower_fault"] is None
    assert scope["two_phase_ground"]["backend_api_supported"] is False
    assert scope["two_phase_ground"]["p4_v1_candidate"] is False


def test_p4_source_mapping_makes_positive_and_zero_sequence_conversions_explicit():
    mapping = iec60909_contract.obtener_contrato_p4()["source_mapping"]

    assert mapping["p2_x_r_max"] == "ext_grid.rx_max = 1 / X_R_max"
    assert mapping["p2_x_r_min"] == "ext_grid.rx_min = 1 / X_R_min"
    assert mapping["p2_zero_sequence"]["r0x0"] == "R0 / X0"
    assert mapping["p2_zero_sequence"]["x0x"] == "X0 / X1_backend"
    assert "preservando R0/X0 absolutos" in mapping["p2_zero_sequence"]["note"]
    assert "P2 almacena X/R" in mapping["note"]


def test_p4_result_contract_does_not_invent_ib_ik_or_promote_non_3ph_skss():
    results = iec60909_contract.obtener_contrato_p4()["result_contract"]

    assert results["ikss_ka"]["iec_symbol"] == "Ik''"
    assert results["ip_ka"]["iec_symbol"] == "ip"
    assert results["ith_ka"]["iec_symbol"] == "Ith"
    assert results["skss_mva"]["scope"] == "3ph_normalized_only_in_current_p4"
    assert "1F-T" in results["skss_mva"]["note"]
    assert "1F-T" in results["ip_ka"]["note"]
    assert "1F-T" in results["ith_ka"]["note"]
    assert results["ib_ka"]["pandapower_field"] is None
    assert results["ib_ka"]["status"] == "PENDING_P4_STRATEGY"
    assert results["ik_ka"]["pandapower_field"] is None
    assert results["ik_ka"]["status"] == "PENDING_P4_STRATEGY"


def test_p4_gate_recognizes_p4c07_without_closing_phase():
    gate = p4_completion.evaluar_cierre_p4()
    states = {item["id"]: item["status"] for item in gate["criteria"]}

    assert gate["phase"] == "P4"
    assert gate["phase_status"] == "NOT_READY"
    assert gate["ready_for_next_phase"] is False
    assert gate["next_phase"] is None
    assert gate["professional_emission"] is False

    for cid in ("P4C01", "P4C02", "P4C03", "P4C04", "P4C05", "P4C06", "P4C07"):
        assert states[cid] == "DONE"
    for cid in [f"P4C{i:02d}" for i in range(8, 13)]:
        assert states[cid] == "PENDING"
