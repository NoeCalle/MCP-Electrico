from opendssdirect import dss

from mcp_electrico import core, engine_selection, visual_state


def _balanced_case():
    core.crear_circuito("engine_selection", 0.48)
    visual_state.reset()
    core.agregar_linea("f1", "sourcebus", "loadbus", 0.05, fases=3, r1_ohm_km=0.2, x1_ohm_km=0.08)
    core.agregar_carga("c1", "loadbus", 30.0, 10.0, fases=3, kv=0.48)


def test_matrix_preserves_no_dispatch_no_crosscheck():
    matrix = engine_selection.obtener_capacidades_motores()

    assert matrix["schema_version"] == 2
    assert matrix["automatic_dispatch"] is False
    assert matrix["crosscheck"] is False
    assert matrix["studies"]["power_flow"]["preferred"] == "opendss"
    assert matrix["studies"]["iec60909"]["preferred"] == "pandapower"
    assert matrix["studies"]["ampacity"]["preferred"] == "mcp"
    assert "READY_DATA" in matrix["readiness_states"]["data"]
    assert "ENGINE_NOT_READY" in matrix["readiness_states"]["engine"]


def test_power_flow_requires_active_model():
    dss("Clear")
    result = engine_selection.seleccionar_motor_estudio("flujo")

    assert result["selected_engine"] == "opendss"
    assert result["executable"] is False
    assert result["decision"] == "NO_APTO_PARA_EJECUCION"
    assert result["model_active"] is False


def test_power_flow_prefers_opendss_and_only_enables_pandapower_explicitly():
    _balanced_case()

    normal = engine_selection.seleccionar_motor_estudio("power_flow")
    experimental = engine_selection.seleccionar_motor_estudio(
        "power_flow", permitir_experimental=True
    )

    assert normal["selected_engine"] == "opendss"
    assert normal["executable"] is True
    pp_normal = normal["alternatives"][0]
    assert pp_normal["engine"] == "pandapower"
    assert pp_normal["eligible"] is False

    pp_exp = experimental["alternatives"][0]
    assert pp_exp["compatible_model"] is True
    assert pp_exp["eligible"] is True
    assert experimental["automatic_dispatch"] is False


def test_iec60909_is_routed_to_pandapower_but_blocked_until_p4():
    _balanced_case()
    result = engine_selection.seleccionar_motor_estudio(
        "cortocircuito", norma="IEC 60909"
    )

    assert result["study"] == "iec60909"
    assert result["selected_engine"] == "pandapower"
    assert result["executable"] is False
    assert result["professional_emission"] is False
    assert result["decision"] == "NO_APTO_PARA_EJECUCION"


def test_ampacity_is_mcp_owned_but_not_implemented_before_p3():
    _balanced_case()
    result = engine_selection.seleccionar_motor_estudio("ampacidad")

    assert result["selected_engine"] == "mcp"
    assert result["executable"] is False
    assert result["decision"] == "NO_APTO_PARA_EJECUCION"


def test_unknown_study_is_not_guessed():
    result = engine_selection.seleccionar_motor_estudio("estudio_magico")

    assert result["decision"] == "UNKNOWN_STUDY"
    assert result["selected_engine"] is None
    assert result["executable"] is False
