from mcp_electrico import ampacity_datasets, p3_completion


DATASET = "PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_PRIMARY_V1"


def test_revision_primary_verified_cierra_p3c09_sin_cerrar_p3():
    item = ampacity_datasets.obtener_dataset(DATASET)
    assert item["provenance"]["verification_status"] == "PRIMARY_VERIFIED"
    assert item["provenance"]["source_type"] == "primary_official"
    assert item["usage_policy"]["professional_emission"] is True

    gate = p3_completion.evaluar_cierre_p3()
    status = {criterion["id"]: criterion["status"] for criterion in gate["criteria"]}
    assert status["P3C09"] == "DONE"
    assert status["P3C10"] == "DONE"
    assert status["P3C11"] == "DONE"
    assert status["P3C12"] == "PENDING"
    assert status["P3C13"] == "PENDING"
    assert gate["phase_status"] == "NOT_READY"
    assert gate["professional_emission"] is False
