from mcp_electrico import (
    core,
    iec60909_single_phase_ground_suite,
    iec60909_suite,
    iec60909_tools,
    iec60909_two_phase_suite,
    p4_completion,
    professional_data,
    visual_state,
    workspace_p4_view,
    workspace_state,
    zero_sequence,
)


def _case_with_line(name: str = "p4c11c") -> None:
    core.crear_circuito(name, 22.9)
    visual_state.reset()
    professional_data.reset()
    zero_sequence.reset()
    workspace_state.reset_for_circuit("test")
    professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=500.0,
        x_r_max=10.0,
        scc_min_mva=250.0,
        x_r_min=5.0,
        fuente_referencia="P4C11C fixture",
    )
    zero_sequence.definir_fuente(
        r0_max_ohm=0.10,
        x0_max_ohm=0.35,
        r0_min_ohm=0.20,
        x0_min_ohm=0.70,
        fuente_referencia="P4C11C fixture Z0 source",
    )
    core.agregar_linea(
        "f1", "sourcebus", "bus1", 0.25,
        fases=3, r1_ohm_km=0.18, x1_ohm_km=0.09,
    )
    zero_sequence.definir_linea(
        "f1",
        r0_ohm_km=0.60,
        x0_ohm_km=0.30,
        c0_nf_km=10.0,
        fuente_referencia="P4C11C fixture Z0/C0 line",
    )


def _base_html() -> str:
    return '''<html><head><style></style></head><body>
<button type="button" class="tab" data-tab="ampacidad">Ampacidad</button>
<div id="workspace-unifilar"><g data-element-id="Bus.bus1"></g></div>
  </div>
  <aside class="inspector"><select id="elementSelect"><option value="Bus.bus1">bus1</option></select></aside>
</body></html>'''


def test_p4c11c_suite_preserves_1ft_max_min_zero_sequence_and_absent_uncontracted_values():
    _case_with_line("p4c11c_suite")
    result = iec60909_single_phase_ground_suite.ejecutar_1ph_ground_max_min(
        "bus1",
        line_endtemp_degree_c={"Line.f1": 20.0},
        lv_tol_percent=10,
    )

    assert result["ok"] is True
    assert result["schema"] == "MCP_ELECTRICO_IEC60909_1PH_GROUND_SUITE_V1"
    assert result["fault"] == "1ph_ground"
    assert result["fault_label"] == "1F-T"
    assert result["negative_sequence_policy"]["relation"] == "Z2 = Z1"
    assert result["negative_sequence_policy"]["universal_assumption"] is False
    assert result["professional_emission"] is False

    for case in ("max", "min"):
        payload = result["scenarios"][case]
        values = payload["results"]
        z0 = payload["inputs"]["zero_sequence_projection"]
        assert payload["ok"] is True
        assert payload["case"] == case
        assert values["ikss_ka"] > 0
        assert values["rk0_ohm"] is not None
        assert values["xk0_ohm"] is not None
        assert values["skss_mva"] is None
        assert values["ip_ka"] is None
        assert values["ith_ka"] is None
        assert len(z0["lines"]) == 1
        assert z0["lines"][0]["c0_nf_per_km"] == 10.0


def test_p4c11c_suite_keeps_min_blocked_without_explicit_line_temperature():
    _case_with_line("p4c11c_partial")
    result = iec60909_single_phase_ground_suite.ejecutar_1ph_ground_max_min("bus1")

    assert result["ok"] is False
    assert result["scenarios"]["max"]["ok"] is True
    assert result["scenarios"]["min"]["ok"] is False
    assert any(
        issue["code"] == "P4SC201"
        for issue in result["scenarios"]["min"]["issues"]
    )


def test_p4c11c_view_renders_1ft_z0_and_does_not_derive_skss_ip_or_ith():
    _case_with_line("p4c11c_view")
    result = iec60909_single_phase_ground_suite.ejecutar_1ph_ground_max_min(
        "bus1",
        line_endtemp_degree_c={"Line.f1": 20.0},
    )
    snapshot = {
        "status": {
            "studies": {
                "iec60909_1ph_ground": {"valid": True, "result": result},
            }
        }
    }

    enhanced = workspace_p4_view.enhance_html(_base_html(), snapshot)

    assert 'data-p4-study="iec60909_1ph_ground"' in enhanced
    assert 'data-p4-fault="1F-T"' in enhanced
    assert 'data-p4-fault-bus="bus1"' in enhanced
    assert "Falla 1F-T" in enhanced
    assert "Secuencia negativa explícita" in enhanced
    assert "Secuencia cero explícita" in enhanced
    assert "Z2 = Z1" in enhanced
    assert "líneas Z0/C0 proyectadas: <strong>1</strong>" in enhanced
    assert "Rk0" in enhanced
    assert "Xk0" in enhanced
    assert "Sk'' 1F-T no se promociona" in enhanced
    assert "ip/Ith tampoco se derivan en la vista" in enhanced
    assert "EXPERIMENTAL_P4" in enhanced
    assert "SIN EMISIÓN PROFESIONAL" in enhanced
    assert "REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION" in enhanced
    assert "overlay-short-circuit-bus" in enhanced


def test_p4c11c_view_can_show_3ph_2ph_and_1ft_without_overwriting_any_study():
    _case_with_line("p4c11c_three_studies")
    temp = {"Line.f1": 20.0}
    result_3ph = iec60909_suite.ejecutar_3ph_max_min(
        "bus1", line_endtemp_degree_c=temp
    )
    result_2ph = iec60909_two_phase_suite.ejecutar_2ph_max_min(
        "bus1", line_endtemp_degree_c=temp
    )
    result_1ft = iec60909_single_phase_ground_suite.ejecutar_1ph_ground_max_min(
        "bus1", line_endtemp_degree_c=temp
    )
    snapshot = {
        "status": {
            "studies": {
                "iec60909_3ph": {"valid": True, "result": result_3ph},
                "iec60909_2ph": {"valid": True, "result": result_2ph},
                "iec60909_1ph_ground": {"valid": True, "result": result_1ft},
            }
        }
    }

    enhanced = workspace_p4_view.enhance_html(_base_html(), snapshot)

    assert enhanced.count('class="p4-study-block"') == 3
    assert 'data-p4-study="iec60909_3ph"' in enhanced
    assert 'data-p4-study="iec60909_2ph"' in enhanced
    assert 'data-p4-study="iec60909_1ph_ground"' in enhanced
    assert "Falla 3PH" in enhanced
    assert "Falla 2PH" in enhanced
    assert "Falla 1F-T" in enhanced
    button = '<button type="button" class="tab" data-tab="cortocircuito">Cortocircuito</button>'
    assert enhanced.count(button) == 1
    assert "faultBuses.forEach" in enhanced


def test_p4c11c_public_tool_registers_with_mcp_and_global_v4_gate_is_closed():
    class FakeMCP:
        def __init__(self):
            self.names = []

        def tool(self):
            def decorator(func):
                self.names.append(func.__name__)
                return func
            return decorator

    fake = FakeMCP()
    iec60909_tools.register(fake)
    assert "ejecutar_cortocircuito_iec60909_1ph_ground" in fake.names

    gate = p4_completion.evaluar_cierre_p4()
    criteria = {item["id"]: item for item in gate["criteria"]}
    assert criteria["P4C11"]["status"] == "DONE"
    assert criteria["P4C10"]["status"] == "DONE"
    assert criteria["P4C12"]["status"] == "PENDING"
    assert gate["phase_status"] == "NOT_READY"
    assert gate["professional_emission"] is False