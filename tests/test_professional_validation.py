from mcp_electrico import conductor_library, core, model_qa, validation_status, visual_state, workspace_state


def _modelo_linea():
    core.crear_circuito("qa_profesional", 22.9)
    visual_state.reset()
    workspace_state.reset_for_circuit("test")
    core.agregar_linea("f1", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    workspace_state.mark_model_changed("agregar_linea:f1")


def test_matriz_no_presenta_ieee1584_como_implementado():
    matrix = validation_status.get_validation_matrix()
    assert matrix["arc_flash_ieee1584"]["status"] == "NOT_IMPLEMENTED"
    assert matrix["power_flow"]["status"] == "UNDER_VALIDATION"
    assert matrix["conductor_library"]["status"] == "VALIDATED_WITH_LIMITATIONS"


def test_qa_bloquea_emision_mientras_flujo_siga_en_validacion():
    _modelo_linea()
    conductor_library.aplicar_conductor(
        "Line.f1",
        "NEXANS-N2XSY-18-30-CU-70-PH16",
        "air_trefoil_30c",
    )
    result = model_qa.auditar_modelo(["power_flow"])

    assert result["summary"]["blockers"] >= 1
    assert result["summary"]["apto_para_emision"] is False
    assert any(f["code"] == "QA901" for f in result["findings"])


def test_qa_detecta_alimentador_sin_conductor_trazable():
    _modelo_linea()
    result = model_qa.auditar_modelo(["conductor_library"])

    assert any(f["code"] == "QA110" and f["element"] == "Line.f1" for f in result["findings"])
    assert result["summary"]["warnings"] >= 1


def test_qa_acepta_madurez_con_limitaciones_pero_no_oculta_warnings_de_modelo():
    _modelo_linea()
    conductor_library.aplicar_conductor(
        "Line.f1",
        "NEXANS-N2XSY-18-30-CU-70-PH16",
        "air_trefoil_30c",
    )
    result = model_qa.auditar_modelo(["conductor_library"])

    check = result["module_checks"][0]
    assert check["acceptable_for_emission"] is True
    assert check["status"] == "VALIDATED_WITH_LIMITATIONS"
    assert result["summary"]["blockers"] == 0
    assert result["summary"]["errors"] == 0
