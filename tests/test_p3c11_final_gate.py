from mcp_electrico import p3_completion


def test_p3c11_permanece_done_y_p3c12_cierra_sin_desbloquear_p4():
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
    assert criteria["P3C12"]["status"] == "DONE"
    assert criteria["P3C13"]["status"] == "DONE"

    assert gate["phase_status"] == "READY_WITH_LIMITATIONS"
    assert gate["ready_for_next_phase"] is True
    assert gate["next_phase"] == "P4_IEC_60909"
    assert gate["professional_emission"] is False
