from mcp_electrico import p3_completion, validation_status


def test_p3c13_cierra_p3_v1_sin_habilitar_emision_profesional_global():
    maturity = validation_status.get_module_status("ampacity")
    assert maturity["status"] == "VALIDATED_WITH_LIMITATIONS"

    gate = p3_completion.evaluar_cierre_p3()
    statuses = {item["id"]: item["status"] for item in gate["criteria"]}

    assert statuses == {f"P3C{index:02d}": "DONE" for index in range(1, 14)}
    assert gate["pending_criteria"] == []
    assert gate["phase_status"] == "READY_WITH_LIMITATIONS"
    assert gate["ready_for_next_phase"] is True
    assert gate["next_phase"] == "P4_IEC_60909"
    assert gate["professional_emission"] is False


def test_cierre_p3_no_convierte_faultstudy_en_iec60909():
    short_circuit = validation_status.get_module_status("short_circuit")
    assert short_circuit["status"] == "UNDER_VALIDATION"
    assert any("IEC 60909" in item for item in short_circuit["limitations"])
