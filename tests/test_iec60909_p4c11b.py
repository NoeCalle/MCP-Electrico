from mcp_electrico import (
    core,
    iec60909_suite,
    iec60909_two_phase_suite,
    professional_data,
    visual_state,
    workspace_p4_view,
)


def _case_with_line(name="p4c11b"):
    core.crear_circuito(name, 22.9)
    visual_state.reset()
    professional_data.reset()
    professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=500.0,
        x_r_max=10.0,
        scc_min_mva=250.0,
        x_r_min=5.0,
        fuente_referencia="P4C11B fixture",
    )
    core.agregar_linea(
        "f1", "sourcebus", "bus1", 0.25,
        fases=3, r1_ohm_km=0.18, x1_ohm_km=0.09,
    )


def _base_html():
    return '''<html><head><style></style></head><body>
<button type="button" class="tab" data-tab="ampacidad">Ampacidad</button>
<div id="workspace-unifilar"><g data-element-id="Bus.bus1"></g></div>
  </div>
  <aside class="inspector"><select id="elementSelect"><option value="Bus.bus1">bus1</option></select></aside>
</body></html>'''


def test_p4c11b_suite_preserves_2ph_max_min_policy_and_no_normalized_skss():
    _case_with_line("p4c11b_suite")
    result = iec60909_two_phase_suite.ejecutar_2ph_max_min(
        "bus1",
        line_endtemp_degree_c={"Line.f1": 20.0},
        calcular_ip_ith=True,
        topology="radial",
        tk_s=0.2,
        kappa_method="C",
    )

    assert result["ok"] is True
    assert result["schema"] == "MCP_ELECTRICO_IEC60909_2PH_SUITE_V1"
    assert result["fault"] == "2ph"
    assert result["maturity"] == "VALIDATED_WITH_LIMITATIONS"
    assert result["negative_sequence_policy"]["z2_relation"] == "Z2 = Z1"
    assert result["negative_sequence_policy"]["universal_assumption"] is False
    for case in ("max", "min"):
        payload = result["scenarios"][case]
        assert payload["ok"] is True
        assert payload["results"]["ikss_ka"] > 0
        assert payload["results"]["ip_ka"] > payload["results"]["ikss_ka"]
        assert payload["results"]["ith_ka"] > 0
        assert "skss_mva" not in payload["results"]
    assert result["professional_emission"] is False


def test_p4c11b_suite_keeps_min_blocked_without_line_temperature():
    _case_with_line("p4c11b_partial")
    result = iec60909_two_phase_suite.ejecutar_2ph_max_min("bus1")

    assert result["ok"] is False
    assert result["scenarios"]["max"]["ok"] is True
    assert result["scenarios"]["min"]["ok"] is False
    assert any(issue["code"] == "P4SC201" for issue in result["scenarios"]["min"]["issues"])


def test_p4c11b_view_renders_2ph_and_explicit_negative_sequence_policy():
    _case_with_line("p4c11b_view")
    result = iec60909_two_phase_suite.ejecutar_2ph_max_min(
        "bus1",
        line_endtemp_degree_c={"Line.f1": 20.0},
        calcular_ip_ith=True,
        topology="radial",
        tk_s=0.2,
    )
    snapshot = {
        "status": {
            "studies": {
                "iec60909_2ph": {"valid": True, "result": result},
            }
        }
    }

    enhanced = workspace_p4_view.enhance_html(_base_html(), snapshot)

    assert 'data-p4-study="iec60909_2ph"' in enhanced
    assert 'data-p4-fault="2PH"' in enhanced
    assert 'data-p4-fault-bus="bus1"' in enhanced
    assert 'data-p4-fault-buses="bus1"' in enhanced
    assert "Falla 2PH" in enhanced
    assert "Secuencia negativa explícita" in enhanced
    assert "Z2 = Z1" in enhanced
    assert "supuesto universal: <strong>no</strong>" in enhanced
    assert "Sk'' 2F no se promociona" in enhanced
    assert "VALIDATED_WITH_LIMITATIONS" in enhanced
    assert "SIN EMISIÓN PROFESIONAL" in enhanced


def test_p4c11b_view_can_show_3ph_and_2ph_without_overwriting_either_study():
    _case_with_line("p4c11b_both")
    result_3ph = iec60909_suite.ejecutar_3ph_max_min(
        "bus1", line_endtemp_degree_c={"Line.f1": 20.0}
    )
    result_2ph = iec60909_two_phase_suite.ejecutar_2ph_max_min(
        "bus1", line_endtemp_degree_c={"Line.f1": 20.0}
    )
    snapshot = {
        "status": {
            "studies": {
                "iec60909_3ph": {"valid": True, "result": result_3ph},
                "iec60909_2ph": {"valid": True, "result": result_2ph},
            }
        }
    }

    enhanced = workspace_p4_view.enhance_html(_base_html(), snapshot)

    assert enhanced.count('class="p4-study-block"') == 2
    assert 'data-p4-study="iec60909_3ph"' in enhanced
    assert 'data-p4-study="iec60909_2ph"' in enhanced
    assert "Falla 3PH" in enhanced
    assert "Falla 2PH" in enhanced
    button = '<button type="button" class="tab" data-tab="cortocircuito">Cortocircuito</button>'
    assert enhanced.count(button) == 1
    assert "faultBuses.forEach" in enhanced