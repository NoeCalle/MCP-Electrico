from opendssdirect import dss

from mcp_electrico import core, engine_selection, professional_data, zero_sequence


def _radial(name="readiness"):
    core.crear_circuito(name, 22.9)
    core.agregar_linea(
        "l1", "sourcebus", "b1", 0.2, fases=3, r1_ohm_km=0.25, x1_ohm_km=0.10
    )
    core.agregar_carga("load1", "b1", 500.0, 120.0, fases=3, kv=22.9)


def _source():
    professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=500.0,
        x_r_max=10.0,
        scc_min_mva=250.0,
        x_r_min=7.0,
        fuente_referencia="estudio de red de concesionaria",
    )


def test_readiness_sin_modelo_es_missing_data():
    dss("Clear")
    result = engine_selection.evaluar_preparacion_estudio("power_flow")

    assert result["data_status"] == "MISSING_DATA"
    assert result["overall_status"] == "MISSING_DATA"
    assert any(item["code"] == "P2READY001" for item in result["missing_data"])


def test_flujo_radial_simple_tiene_datos_y_motor_listos():
    _radial("ready_powerflow")
    result = engine_selection.evaluar_preparacion_estudio("flujo")

    assert result["data_status"] == "READY_DATA"
    assert result["engine_status"] == "READY_ENGINE"
    assert result["overall_status"] == "READY_TO_EXECUTE"
    assert result["selected_engine"] == "opendss"


def test_transformador_p2_incompleto_bloquea_readiness_profesional_de_flujo():
    core.crear_circuito("ready_tr_incomplete", 22.9)
    professional_data.agregar_transformador_profesional(
        nombre="tr1",
        bus_hv="sourcebus",
        bus_lv="lv",
        kva=1000,
        kv_hv=22.9,
        kv_lv=0.48,
        uk_percent=6.0,
        grupo_vectorial="Dyn11",
        x_r=10.0,
        fuente_referencia="ficha parcial",
    )
    result = engine_selection.evaluar_preparacion_estudio("power_flow")

    assert result["data_status"] == "MISSING_DATA"
    assert any(item["code"] == "P2READY206" for item in result["missing_data"])


def test_cortocircuito_no_asume_tipo_de_falla():
    _radial("ready_fault_unspecified")
    _source()
    result = engine_selection.evaluar_preparacion_estudio("cortocircuito")

    assert result["overall_status"] == "MISSING_DATA"
    assert any(item["code"] == "P2READY010" for item in result["request_issues"])


def test_3f_no_exige_z0_como_dato_pero_backend_actual_puede_no_estar_listo():
    _radial("ready_fault_3f")
    _source()
    result = engine_selection.evaluar_preparacion_estudio(
        "cortocircuito", tipo_falla="3f"
    )

    assert result["fault_type"] == "three_phase"
    assert result["data_status"] == "READY_DATA"
    assert result["engine_status"] == "ENGINE_NOT_READY"
    assert result["overall_status"] == "ENGINE_NOT_READY"
    assert any(item["code"] == "P2ZFAULT011" for item in result["engine_reasons"])


def test_1f_t_exige_z0_explicita_de_fuente_y_linea():
    _radial("ready_fault_1ft_missing")
    _source()
    result = engine_selection.evaluar_preparacion_estudio(
        "iec60909", tipo_falla="1f_t"
    )

    assert result["fault_type"] == "single_phase_ground"
    assert result["data_status"] == "MISSING_DATA"
    codes = {item["code"] for item in result["missing_data"]}
    assert "P2READY402" in codes
    assert "P2READY410" in codes


def test_iec60909_puede_tener_datos_listos_aunque_p4_siga_no_implementada():
    _radial("ready_60909")
    _source()
    zero_sequence.definir_fuente(0.30, 0.90, 0.50, 1.20)
    zero_sequence.definir_linea("l1", 0.65, 0.32)

    result = engine_selection.evaluar_preparacion_estudio(
        "iec60909", tipo_falla="single_phase_ground"
    )

    assert result["data_status"] == "READY_DATA"
    assert result["engine_status"] == "MODULE_NOT_READY"
    assert result["overall_status"] == "MODULE_NOT_READY"
    assert result["selected_engine"] == "pandapower"


def test_selector_distingue_ejecucion_tecnica_de_readiness_profesional():
    _radial("ready_selector")
    _source()

    result = engine_selection.seleccionar_motor_estudio(
        "cortocircuito", tipo_falla="three_phase"
    )

    assert result["technical_executable"] is True
    assert result["executable"] is True
    assert result["professional_execution_ready"] is False
    assert result["readiness"]["data_status"] == "READY_DATA"
    assert result["readiness"]["engine_status"] == "ENGINE_NOT_READY"
    assert result["decision"] == "NO_APTO_PARA_EJECUCION_PROFESIONAL"
