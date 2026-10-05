from opendssdirect import dss
import pytest

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
    assert matrix["studies"]["iec60909"]["implemented"] is True
    assert matrix["studies"]["iec60909"]["professional_emission_candidate"] is False
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


def test_iec60909_is_routed_as_experimental_but_not_professional():
    _balanced_case()
    result = engine_selection.seleccionar_motor_estudio(
        "cortocircuito", norma="IEC 60909", tipo_falla="three_phase"
    )

    assert result["study"] == "iec60909"
    assert result["selected_engine"] == "pandapower"
    assert result["executable"] is True
    assert result["technical_executable"] is True
    assert result["professional_execution_ready"] is False
    assert result["professional_emission"] is False
    assert result["readiness"]["data_status"] == "MISSING_DATA"
    assert result["decision"] == "EJECUTABLE_CON_DATOS_PROFESIONALES_INCOMPLETOS"


def test_ampacity_foundation_is_mcp_owned_under_validation():
    _balanced_case()
    result = engine_selection.seleccionar_motor_estudio("ampacidad")

    assert result["selected_engine"] == "mcp"
    assert result["executable"] is True
    assert result["technical_executable"] is True
    assert result["professional_execution_ready"] is False
    assert result["professional_emission"] is False
    assert result["readiness"]["data_status"] == "MISSING_DATA"
    assert result["module_status"]["status"] == "VALIDATED_WITH_LIMITATIONS"
    assert result["decision"] == "EJECUTABLE_CON_DATOS_PROFESIONALES_INCOMPLETOS"


def test_unknown_study_is_not_guessed():
    result = engine_selection.seleccionar_motor_estudio("estudio_magico")

    assert result["decision"] == "UNKNOWN_STUDY"
    assert result["selected_engine"] is None
    assert result["executable"] is False


@pytest.mark.parametrize("study,expected", [
    ("dinámica arranque directo", "openmodelica+msl"),
    ("dinámica SCR", "openmodelica+msl"),
    ("dinámica simultánea", "openmodelica+msl"),
    ("dinámica variador", "openmodelica+msl"),
    ("estabilidad transitoria", "andes"),
    ("estabilidad pequeña señal", "andes"),
    ("flujo continuado", "veragrid"),
    ("transitorios electromagnéticos", "openmodelica+msl"),
])
@pytest.mark.parametrize("allow_experimental", [False, True])
@pytest.mark.parametrize("active", [False, True])
def test_external_routes_cannot_be_promoted_by_model_or_opt_in(study, expected, allow_experimental, active):
    if active:
        _balanced_case()
    else:
        dss("Clear")
    result = engine_selection.seleccionar_motor_estudio(study, permitir_experimental=allow_experimental)
    readiness = engine_selection.evaluar_preparacion_estudio(study, permitir_experimental=allow_experimental)
    assert result["selected_engine"] == expected
    assert result["planning_only"] is True
    scoped_status={
        'motor_dynamics_soft_starter_scr':'VERIFIED_SCOPED_ADAPTER_ONLY',
        'motor_dynamics_dol':'VERIFIED_SCOPED_ADAPTER_ONLY',
        'motor_dynamics_simultaneous':'VERIFIED_SCOPED_ADAPTER_ONLY',
    }
    assert result["integration_status"] == scoped_status.get(result['study'],'ADAPTER_NOT_IMPLEMENTED')
    assert result["decision"] == "NO_APTO_PARA_EJECUCION"
    assert result["technical_executable"] is False
    assert result["professional_execution_ready"] is False
    assert result["professional_emission"] is False
    assert result["automatic_dispatch"] is False
    assert result["crosscheck"] is False
    assert readiness["overall_status"] == "MODULE_NOT_READY"
    assert readiness["data_evaluated"] is False
    assert readiness["data_status"] == "MISSING_DATA"
    assert all(not item["eligible"] and item["reason"] for item in result["alternatives"])


def test_scr_does_not_fall_back_to_phasor_or_legacy_custom_model():
    result = engine_selection.seleccionar_motor_estudio("dinamica_scr", permitir_experimental=True)
    assert result["selected_engine"] == "openmodelica+msl"
    assert result["alternatives"] == []
    assert engine_selection.seleccionar_motor_estudio("dinamica")["decision"] == "UNKNOWN_STUDY"


def test_catalogue_is_returned_as_an_independent_copy():
    matrix = engine_selection.obtener_capacidades_motores()
    assert matrix["integration_policy"] == "USE_EXISTING_OPEN_SOURCE_MODELS_FIRST"
    matrix["studies"]["transient_stability"]["implemented"] = True
    matrix["external_engine_catalogue"]["andes"]["limits"].clear()
    fresh = engine_selection.obtener_capacidades_motores()
    assert fresh["studies"]["transient_stability"]["implemented"] is False
    assert fresh["external_engine_catalogue"]["andes"]["limits"]


@pytest.mark.parametrize("fault", [None, "three_phase", "two_phase", "single_phase_ground"])
def test_iec_without_active_circuit_reports_readiness_instead_of_throwing(fault):
    dss("Clear")
    result = engine_selection.seleccionar_motor_estudio("iec60909", tipo_falla=fault)
    assert result["technical_executable"] is False
    assert result["readiness"]["overall_status"] == "MISSING_DATA"
    assert result["readiness"]["engine_status"] == "ENGINE_NOT_READY"
    assert any(item["code"] == "P2READY001" for item in result["readiness"]["missing_data"])
