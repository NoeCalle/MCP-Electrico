from mcp_electrico import validation_status


def test_p7c_maturity_separates_technical_from_professional_report():
    technical = validation_status.get_module_status("technical_report")
    professional = validation_status.get_module_status("professional_report")
    reconstruction = validation_status.get_module_status("project_reconstruction")

    assert technical["status"] == "EXPERIMENTAL"
    assert "P7C" in str(technical["basis"])
    assert any("BROWSER_PRINT" in item for item in technical["limitations"])
    assert any("professional_emission=false" in item for item in technical["limitations"])

    assert professional["status"] == "NOT_IMPLEMENTED"
    assert professional["basis"] is None
    assert any("P7C" in item for item in professional["limitations"])

    assert reconstruction["status"] == "EXPERIMENTAL"
    assert any("P7C" in item for item in reconstruction["limitations"])
