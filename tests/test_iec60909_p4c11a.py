from pathlib import Path

from mcp_electrico import (
    core,
    iec60909_suite,
    p4_completion,
    professional_data,
    visual_state,
    workspace_p4_view,
)


def _case_with_line():
    core.crear_circuito("p4c11a", 22.9)
    visual_state.reset()
    professional_data.reset()
    professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=500.0,
        x_r_max=10.0,
        scc_min_mva=250.0,
        x_r_min=5.0,
        fuente_referencia="P4C11A fixture",
    )
    core.agregar_linea(
        "f1", "sourcebus", "bus1", 0.25,
        fases=3, r1_ohm_km=0.18, x1_ohm_km=0.09,
    )


def test_p4c11a_suite_preserves_max_min_and_duty_payloads():
    _case_with_line()
    result = iec60909_suite.ejecutar_3ph_max_min(
        "bus1",
        line_endtemp_degree_c={"Line.f1": 20.0},
        calcular_ip_ith=True,
        topology="radial",
        tk_s=0.2,
        kappa_method="C",
    )

    assert result["ok"] is True
    assert result["schema"] == "MCP_ELECTRICO_IEC60909_3PH_SUITE_V1"
    assert result["fault"] == "3ph"
    for case in ("max", "min"):
        payload = result["scenarios"][case]
        assert payload["ok"] is True
        assert payload["results"]["ikss_ka"] > 0
        assert payload["results"]["skss_mva"] > 0
        assert payload["results"]["ip_ka"] > payload["results"]["ikss_ka"]
        assert payload["results"]["ith_ka"] > 0
        assert payload["input_projection"]["duty"]["topology"] == "radial"
        assert payload["input_projection"]["duty"]["tk_s"] == 0.2
    assert result["professional_emission"] is False


def test_p4c11a_suite_keeps_min_failure_visible_instead_of_copying_max():
    _case_with_line()
    result = iec60909_suite.ejecutar_3ph_max_min("bus1")

    assert result["ok"] is False
    assert result["scenarios"]["max"]["ok"] is True
    assert result["scenarios"]["min"]["ok"] is False
    assert any(
        issue["code"] == "P4SC201"
        for issue in result["scenarios"]["min"]["issues"]
    )


def test_p4c11a_view_is_read_only_and_exposes_3ph_engine_maturity_and_fault_bus():
    _case_with_line()
    study = iec60909_suite.ejecutar_3ph_max_min(
        "bus1",
        line_endtemp_degree_c={"Line.f1": 20.0},
        calcular_ip_ith=True,
        topology="radial",
        tk_s=0.2,
        kappa_method="C",
    )
    snapshot = {
        "status": {
            "studies": {
                "iec60909_3ph": {"valid": True, "result": study},
            }
        }
    }
    base = '''<html><head><style></style></head><body>
<button type="button" class="tab" data-tab="ampacidad">Ampacidad</button>
<div id="workspace-unifilar"><g data-element-id="Bus.bus1"></g></div>
  </div>
  <aside class="inspector"></aside>
</body></html>'''

    enhanced = workspace_p4_view.enhance_html(base, snapshot)

    assert workspace_p4_view.MARKER in enhanced
    assert 'data-tab="cortocircuito"' in enhanced
    assert 'id="panel-cortocircuito"' in enhanced
    assert 'data-p4-fault-bus="bus1"' in enhanced
    assert "Ik'' MAX" in enhanced
    assert "Sk''" in enhanced
    assert "Ith" in enhanced
    assert "radial" in enhanced
    assert "0.2 s" in enhanced
    assert "EXPERIMENTAL_P4" in enhanced
    assert "SIN EMISIÓN PROFESIONAL" in enhanced
    assert "REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION" in enhanced
    assert "overlay-short-circuit-bus" in enhanced


def test_p4c11a_remains_submilestone_evidence_after_global_v4_closure():
    gate = p4_completion.evaluar_cierre_p4()
    criteria = {item["id"]: item for item in gate["criteria"]}

    assert criteria["P4C11"]["status"] == "DONE"
    assert "P4C11A 3F DONE" in criteria["P4C11"]["evidence"]
    assert "P4C11B 2F DONE" in criteria["P4C11"]["evidence"]
    assert "P4C11C 1F-T DONE" in criteria["P4C11"]["evidence"]
    assert criteria["P4C10"]["status"] == "DONE"
    assert criteria["P4C12"]["status"] == "PENDING"
    assert gate["phase_status"] == "NOT_READY"
    assert gate["ready_for_next_phase"] is False
    assert gate["professional_emission"] is False