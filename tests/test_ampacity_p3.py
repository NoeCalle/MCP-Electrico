import pytest

from mcp_electrico import (
    ampacity,
    ampacity_norms,
    conductor_library,
    core,
    engine_selection,
    validation_status,
    visual_state,
)


def _linea_p3(nombre="f_p3"):
    core.crear_circuito("ampacity_test", 22.9)
    visual_state.reset()
    conductor_library.reset()
    ampacity.reset()
    core.agregar_linea(nombre, "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    return conductor_library.aplicar_conductor(
        f"Line.{nombre}",
        "NEXANS-N2XSY-18-30-CU-70-PH16",
        "air_trefoil_30c",
    )


def _perfil_base(nombre="f_p3", in_a=250.0, ib_a=200.0):
    return ampacity.definir_condiciones(
        nombre_elemento=f"Line.{nombre}",
        norma_id="IEC_60364_5_52_2009_A1_2024",
        in_proteccion_a=in_a,
        confirmar_condiciones_base=True,
        ib_diseno_a=ib_a,
        referencia_in="MCCB-QF1 ficha técnica / ajuste declarado",
        referencia_ib="Memoria de cargas - corriente de diseño",
        referencia_condiciones_instalacion="Inspección: aire 30 C, formación trefoil coincidente con catálogo",
    )


def test_referencias_p3_no_declaran_tablas_automaticas():
    refs = {item["id"]: item for item in ampacity_norms.listar_referencias()}
    assert "IEC_60364_5_52_2009_A1_2024" in refs
    assert "PERU_CNE_UTILIZACION_2006" in refs
    assert all(item["automatic_tables"] is False for item in refs.values())


def test_no_asume_factor_total_uno_ni_compatibilidad_de_instalacion():
    _linea_p3()
    with pytest.raises(ValueError, match="P3A008"):
        ampacity.definir_condiciones(
            "Line.f_p3",
            "IEC_60364_5_52_2009_A1_2024",
            250,
            ib_diseno_a=200,
            referencia_in="QF1",
            referencia_ib="memoria",
            referencia_condiciones_instalacion="inspección",
        )

    with pytest.raises(ValueError, match="P3A009"):
        ampacity.definir_condiciones(
            "Line.f_p3",
            "IEC_60364_5_52_2009_A1_2024",
            250,
            confirmar_condiciones_base=True,
            ib_diseno_a=200,
            referencia_in="QF1",
            referencia_ib="memoria",
        )


def test_base_confirmada_evalua_ib_in_iz_sin_confundir_rating_visual_con_in():
    assignment = _linea_p3()
    assert assignment["ampacidad_aplicada_a"] == pytest.approx(296.0)
    _perfil_base()

    result = ampacity.evaluar("Line.f_p3")
    assert result["status"] == "CUMPLE"
    assert result["criterion"] == "Ib <= In <= Iz"
    assert result["values"]["ib_a"] == pytest.approx(200.0)
    assert result["values"]["in_a"] == pytest.approx(250.0)
    assert result["values"]["iz_base_a"] == pytest.approx(296.0)
    assert result["values"]["factor_total"] == pytest.approx(1.0)
    assert result["values"]["iz_a"] == pytest.approx(296.0)
    assert result["maturity"] == "VALIDATED_WITH_LIMITATIONS"
    assert result["automatic_normative_lookup"] is False


def test_factores_explicitos_referenciados_se_multiplican_y_pueden_hacer_no_cumplir():
    _linea_p3()
    ampacity.definir_condiciones(
        "Line.f_p3",
        "IEC_60364_5_52_2009_A1_2024",
        220,
        factores=[
            {"id": "k_temp", "value": 0.91, "reference": "IEC tabla autorizada proyecto", "table_or_clause": "tabla X"},
            {"id": "k_group", "value": 0.80, "reference": "IEC tabla autorizada proyecto", "table_or_clause": "tabla Y"},
        ],
        ib_diseno_a=180,
        referencia_in="MCCB-QF1 220 A",
        referencia_ib="memoria cargas",
        referencia_condiciones_instalacion="Informe de instalación: factores aplicables a condición base declarada",
    )

    result = ampacity.evaluar("f_p3")
    assert result["values"]["factor_total"] == pytest.approx(0.728)
    assert result["values"]["iz_a"] == pytest.approx(215.488)
    assert result["checks"]["ib_le_in"] is True
    assert result["checks"]["in_le_iz"] is False
    assert result["status"] == "NO_CUMPLE"


def test_perfil_se_invalida_si_cambia_conductor_o_instalacion_p2():
    _linea_p3()
    _perfil_base()
    conductor_library.aplicar_conductor(
        "Line.f_p3",
        "NEXANS-N2XSY-18-30-CU-95-PH16",
        "air_trefoil_30c",
    )

    result = ampacity.evaluar("Line.f_p3")
    assert result["status"] == "DATOS_INSUFICIENTES"
    assert "conductor_modificado" in result["missing"]


def test_readiness_ampacidad_es_especifico_y_no_habilita_emision():
    _linea_p3()
    before = engine_selection.evaluar_preparacion_estudio("ampacidad")
    assert before["data_status"] == "MISSING_DATA"
    assert any(item["code"] == "P3READY010" for item in before["missing_data"])

    _perfil_base()
    ready = engine_selection.evaluar_preparacion_estudio("ampacidad")
    assert ready["data_status"] == "READY_DATA"
    assert ready["engine_status"] == "READY_ENGINE"
    assert ready["overall_status"] == "READY_TO_EXECUTE"
    assert ready["module_status"]["status"] == "VALIDATED_WITH_LIMITATIONS"

    selection = engine_selection.seleccionar_motor_estudio("ampacidad")
    assert selection["technical_executable"] is True
    assert selection["professional_execution_ready"] is True
    assert selection["professional_emission"] is False
    assert selection["decision"] == "EJECUTABLE_NO_APTO_PARA_EMISION"


def test_matriz_validacion_declara_ampacidad_under_validation_y_barrera_p3b():
    status = validation_status.get_module_status("ampacity")
    assert status["status"] == "VALIDATED_WITH_LIMITATIONS"
    limitations = " ".join(status["limitations"]).lower()
    assert "secund" in limitations
    assert "professional_emission=false" in limitations
    assert "tablas 1/2" in limitations
    assert "fail-closed" in limitations


def test_evaluar_todos_resume_estados():
    _linea_p3()
    _perfil_base()
    result = ampacity.evaluar_todos()
    assert result["status"] == "CUMPLE"
    assert result["summary"] == {
        "total": 1,
        "cumple": 1,
        "no_cumple": 0,
        "datos_insuficientes": 0,
    }
