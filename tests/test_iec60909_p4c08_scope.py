from mcp_electrico import (
    core,
    engine_selection,
    iec60909_contract,
    p4_completion,
    professional_data,
    zero_sequence,
)


def _source_only(name: str = "p4c08") -> None:
    core.crear_circuito(name, 22.9)
    professional_data.reset()
    zero_sequence.reset()
    professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=500.0,
        x_r_max=10.0,
        scc_min_mva=250.0,
        x_r_min=5.0,
        fuente_referencia="P4C08 fixture",
    )
    zero_sequence.definir_fuente(
        r0_max_ohm=0.30,
        x0_max_ohm=0.90,
        r0_min_ohm=0.50,
        x0_min_ohm=1.20,
        fuente_referencia="P4C08 fixture Z0",
    )


def test_p4c08_contract_closes_p4_v1_scope_without_2ft_approximation():
    contract = iec60909_contract.obtener_contrato_p4()
    scope = contract["p4_v1_scope"]
    faults = contract["fault_scope"]
    two_phase_ground = faults["two_phase_ground"]
    strategy = two_phase_ground["strategy"]

    assert scope["status"] == "CLOSED"
    assert scope["included_faults"] == [
        "three_phase", "two_phase", "single_phase_ground"
    ]
    assert scope["excluded_faults"] == ["two_phase_ground"]

    assert two_phase_ground["pandapower_fault"] is None
    assert two_phase_ground["backend_api_supported"] is False
    assert two_phase_ground["p4_v1_candidate"] is False
    assert two_phase_ground["status"] == "OUT_OF_SCOPE_P4_V1"
    assert strategy["id"] == "P4C08_EXCLUDE_2PH_GROUND_FROM_P4_V1"
    assert strategy["decision"] == "EXCLUDE_FROM_P4_V1"
    assert strategy["no_approximation"] is True
    assert "v3.5.4" in strategy["backend_source"]
    assert len(strategy["future_reentry_conditions"]) == 2


def test_p4c08_in_scope_faults_have_benchmark_and_workspace_evidence():
    contract = iec60909_contract.obtener_contrato_p4()
    faults = contract["fault_scope"]

    for name in contract["p4_v1_scope"]["included_faults"]:
        fault = faults[name]
        assert fault["p4_v1_candidate"] is True
        assert fault["status"] == "FOUNDATION_READY"
        assert fault["independent_benchmark"]["status"] == "PASS"
        assert fault["workspace_v4"]["status"] == "DONE"

    excluded = faults["two_phase_ground"]
    assert excluded["independent_benchmark"]["status"] == "NOT_REQUIRED_OUT_OF_SCOPE"
    assert excluded["workspace_v4"]["status"] == "NOT_REQUIRED_OUT_OF_SCOPE"


def test_p4c08_readiness_recognizes_2ft_and_returns_explicit_out_of_scope_block():
    _source_only("p4c08_readiness")

    result = engine_selection.evaluar_preparacion_estudio(
        "iec60909",
        tipo_falla="2F-T",
        permitir_experimental=True,
    )

    assert result["fault_type"] == "two_phase_ground"
    assert result["data_status"] == "READY_DATA"
    assert result["engine_status"] == "ENGINE_NOT_READY"
    assert result["overall_status"] == "ENGINE_NOT_READY"
    assert result["selected_engine"] == "pandapower"
    assert any(item["code"] == "P4READY804" for item in result["engine_reasons"])
    assert "No se aproxima 2F-T" in result["engine_note"]


def test_p4c08_engine_selection_never_turns_2ft_into_an_executable_fault():
    _source_only("p4c08_selection")

    result = engine_selection.seleccionar_motor_estudio(
        "iec60909",
        tipo_falla="two_phase_ground",
        permitir_experimental=True,
    )

    assert result["fault_type"] == "two_phase_ground"
    assert result["professional_execution_ready"] is False
    assert result["professional_emission"] is False
    assert result["decision"] == "NO_APTO_PARA_EJECUCION_PROFESIONAL"
    assert result["automatic_dispatch"] is False
    assert result["crosscheck"] is False
    assert any(
        item["code"] == "P4READY804"
        for item in result["readiness"]["engine_reasons"]
    )


def test_p4c08_scope_remains_closed_after_final_p4_maturity():
    gate = p4_completion.evaluar_cierre_p4()
    criteria = {item["id"]: item for item in gate["criteria"]}

    for cid in (
        "P4C01", "P4C02", "P4C03", "P4C04", "P4C05", "P4C06",
        "P4C07", "P4C08", "P4C09", "P4C10", "P4C11", "P4C12",
    ):
        assert criteria[cid]["status"] == "DONE"

    assert gate["phase_status"] == "READY_WITH_LIMITATIONS"
    assert gate["ready_for_next_phase"] is True
    assert gate["next_phase"] == "P5_PROTECTION_TCC"
    assert gate["professional_emission"] is False
    assert gate["p4_v1_scope"]["status"] == "CLOSED"
