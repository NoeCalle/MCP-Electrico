from mcp_electrico import p3_completion


def test_p3c11_final_gate_cierra_cobertura_sin_desbloquear_p4():
    coverage = p3_completion._coverage_flags()
    assert coverage["base_ampacity_strategy"] is True
    assert coverage["table_5a"] is True
    assert coverage["table_5b"] is True
    assert coverage["table_5c"] is True
    assert coverage["table_5d"] is True
    assert coverage["table_5e"] is True

    gate = p3_completion.evaluar_cierre_p3()
    criteria = {item["id"]: item for item in gate["criteria"]}

    assert criteria["P3C11"]["status"] == "DONE"
    assert criteria["P3C12"]["status"] == "PENDING"
    assert criteria["P3C13"]["status"] == "PENDING"

    assert gate["phase_status"] == "NOT_READY"
    assert gate["ready_for_next_phase"] is False
    assert gate["next_phase"] is None
    assert gate["professional_emission"] is False
