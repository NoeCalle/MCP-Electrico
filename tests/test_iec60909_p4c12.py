from mcp_electrico import (
    engine_selection,
    iec60909_maturity,
    p4_completion,
    validation_status,
)


def test_p4c12_maturity_evidence_passes_only_with_declared_p4_v1_scope():
    result = iec60909_maturity.evaluar_madurez()

    assert result["ready"] is True
    assert result["status"] == "VALIDATED_WITH_LIMITATIONS"
    assert result["professional_emission"] is False
    assert result["full_conformance_claim"] is False
    assert result["checks"]
    assert all(item["status"] == "PASS" for item in result["checks"])
    ids = {item["id"] for item in result["checks"]}
    assert {
        "P4M01_TARGET",
        "P4M02_ENGINE_POLICY",
        "P4M03_SCOPE_CLOSED",
        "P4M04_FAULT_EVIDENCE",
        "P4M05_2FT_FAIL_CLOSED",
        "P4M06_EDITION_REVIEW",
        "P4M07_RESULT_SCOPE_FAIL_CLOSED",
        "P4M08_NO_PROFESSIONAL_EMISSION",
    }.issubset(ids)


def test_p4c12_validation_status_separates_iec60909_from_opendss_faultstudy():
    iec = validation_status.get_module_status("iec60909")
    exploratory = validation_status.get_module_status("short_circuit")
    matrix = validation_status.get_validation_matrix()

    assert iec["status"] == "VALIDATED_WITH_LIMITATIONS"
    assert "P4-v1" in iec["basis"]
    assert exploratory["status"] == "UNDER_VALIDATION"
    assert "OpenDSS FaultStudy" in exploratory["basis"]
    assert matrix["iec60909"]["status"] == "VALIDATED_WITH_LIMITATIONS"
    assert matrix["short_circuit"]["status"] == "UNDER_VALIDATION"


def test_p4c12_engine_matrix_binds_iec60909_to_its_own_maturity_module():
    matrix = engine_selection.obtener_capacidades_motores()
    iec = matrix["studies"]["iec60909"]
    exploratory = matrix["studies"]["short_circuit_exploratory"]

    assert iec["module"] == "iec60909"
    assert iec["preferred"] == "pandapower"
    assert iec["professional_emission_candidate"] is False
    assert "VALIDATED_WITH_LIMITATIONS" in iec["reason"]
    assert exploratory["module"] == "short_circuit"
    assert exploratory["preferred"] == "opendss"


def test_p4c12_closes_p4_ready_with_limitations_and_unlocks_only_next_phase():
    gate = p4_completion.evaluar_cierre_p4()
    states = {item["id"]: item["status"] for item in gate["criteria"]}

    assert all(states[f"P4C{i:02d}"] == "DONE" for i in range(1, 13))
    assert gate["pending_criteria"] == []
    assert gate["phase_version"] == "P4-v1"
    assert gate["phase_status"] == "READY_WITH_LIMITATIONS"
    assert gate["ready_for_next_phase"] is True
    assert gate["next_phase"] == "P5_PROTECTION_TCC"
    assert gate["module_maturity"]["status"] == "VALIDATED_WITH_LIMITATIONS"
    assert gate["professional_emission"] is False


def test_p4c12_limitations_preserve_known_non_promoted_scope():
    result = iec60909_maturity.evaluar_madurez()
    text = "\n".join(result["limitations"])

    assert "2F-T" in text and "OUT_OF_SCOPE_P4_V1" in text
    assert "Z2=Z1" in text
    assert "Generadores" in text
    assert "Sk''" in text
    assert "ip/Ith" in text
    assert "Ib" in text and "Ik" in text
    assert "endtemp_degree" in text
    assert "REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION" in text
    assert "professional_emission" in text
