import pytest

from mcp_electrico import (
    core,
    iec60909_tools,
    iec60909_two_phase_ground,
    iec60909_two_phase_ground_suite,
    professional_data,
    visual_state,
    workspace_p4_view,
    workspace_state,
    zero_sequence,
)


def _reset(name: str = "p4v11") -> None:
    core.crear_circuito(name, 22.9)
    visual_state.reset()
    professional_data.reset()
    zero_sequence.reset()
    workspace_state.reset_for_circuit("test")


def _source() -> None:
    professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=500.0,
        x_r_max=10.0,
        scc_min_mva=250.0,
        x_r_min=5.0,
        fuente_referencia="P4V11 source",
    )
    zero_sequence.definir_fuente(
        r0_max_ohm=0.10,
        x0_max_ohm=0.35,
        r0_min_ohm=0.20,
        x0_min_ohm=0.70,
        fuente_referencia="P4V11 source Z0",
    )


def _line_case(name: str = "p4v11_line") -> None:
    _reset(name)
    _source()
    core.agregar_linea(
        "f1",
        "sourcebus",
        "bus1",
        0.25,
        fases=3,
        r1_ohm_km=0.18,
        x1_ohm_km=0.09,
    )
    zero_sequence.definir_linea(
        "f1",
        r0_ohm_km=0.60,
        x0_ohm_km=0.30,
        c0_nf_km=10.0,
        fuente_referencia="P4V11 line Z0/C0",
    )


def _transformer_case(name: str, neutral_mode: str, rn_ohm=None, xn_ohm=None) -> dict:
    _reset(name)
    _source()
    professional_data.agregar_transformador_profesional(
        nombre="tr1",
        bus_hv="sourcebus",
        bus_lv="lvbus",
        kva=1000.0,
        kv_hv=22.9,
        kv_lv=0.48,
        uk_percent=6.0,
        grupo_vectorial="Dyn11",
        x_r=10.0,
        no_load_loss_kw=2.0,
        i0_percent=0.8,
        fuente_referencia="P4V11 transformer",
    )
    zero_sequence.definir_transformador(
        "tr1",
        uk0_percent=5.5,
        ur0_percent=0.6,
        magnetizing_z0_ratio_percent=100.0,
        magnetizing_r_over_x=0.0,
        leakage_share_hv=0.5,
        neutral_side="lv",
        neutral_mode=neutral_mode,
        rn_ohm=rn_ohm,
        xn_ohm=xn_ohm,
        fuente_referencia="P4V11 transformer Z0",
    )
    return iec60909_two_phase_ground.ejecutar_2ph_ground("lvbus", "max")


def _base_html() -> str:
    return '''<html><head><style></style></head><body>
<button type="button" class="tab" data-tab="ampacidad">Ampacidad</button>
<div id="workspace-unifilar"><g data-element-id="Bus.bus1"></g></div>
  </div>
  <aside class="inspector"><select id="elementSelect"><option value="Bus.bus1">bus1</option></select></aside>
</body></html>'''


def test_p4v11b_sourcebus_uses_pandapower_only_for_sequence_impedances():
    _reset("p4v11_source")
    _source()

    result = iec60909_two_phase_ground.ejecutar_2ph_ground("sourcebus", "max")

    assert result["ok"] is True
    assert result["fault_type"] == "two_phase_ground"
    assert result["engine"] == "mcp_sequence_solver"
    assert result["sequence_impedance_backend"] == "pandapower"
    assert result["maturity"] == "USABLE_WITH_DECLARED_SCOPE"
    assert result["professional_emission"] is False
    extraction = result["inputs"]["sequence_impedance_extraction"]
    assert extraction["backend_fault_used_only_for_impedance_extraction"] == "1ph"
    assert extraction["backend_fault_current_consumed"] is False
    assert result["inputs"]["sequence_thevenin"]["z2_relation"] == "Z2 = Z1"
    assert result["results"]["ikss_ka"] > 0
    assert result["results"]["ib_ka"] > 0
    assert result["results"]["ic_ka"] > 0
    assert result["results"]["rk0_ohm"] is not None
    assert result["results"]["xk0_ohm"] is not None
    assert result["results"]["skss_mva"] is None
    assert result["results"]["ip_ka"] is None
    assert result["results"]["ith_ka"] is None
    assert result["result_promotion"]["ikss_contractual"] is False
    assert result["foundation"]["invariants"]["ia_boundary_ok"] is True
    assert result["foundation"]["invariants"]["vb_boundary_ok"] is True
    assert result["foundation"]["invariants"]["vc_boundary_ok"] is True


def test_p4v11b_suite_runs_max_min_and_preserves_pending_validation():
    _reset("p4v11_suite_source")
    _source()

    result = iec60909_two_phase_ground_suite.ejecutar_2ph_ground_max_min("sourcebus")

    assert result["ok"] is True
    assert result["fault_label"] == "2F-T"
    assert result["maturity"] == "USABLE_WITH_DECLARED_SCOPE"
    assert result["engine"]["engine"] == "mcp_sequence_solver"
    assert result["engine"]["sequence_impedance_backend"] == "pandapower"
    assert result["result_promotion"]["ikss_contractual"] is False
    assert "VP-2FT-01" in result["result_promotion"]["pending_validation_ids"]
    assert result["scenarios"]["max"]["results"]["ikss_ka"] > 0
    assert result["scenarios"]["min"]["results"]["ikss_ka"] > 0
    assert result["scenarios"]["max"]["case"] == "max"
    assert result["scenarios"]["min"]["case"] == "min"


def test_p4v11b_min_with_line_stays_fail_closed_without_temperature():
    _line_case("p4v11_min_temp")

    blocked = iec60909_two_phase_ground_suite.ejecutar_2ph_ground_max_min("bus1")
    ready = iec60909_two_phase_ground_suite.ejecutar_2ph_ground_max_min(
        "bus1", line_endtemp_degree_c={"Line.f1": 20.0}
    )

    assert blocked["ok"] is False
    assert blocked["scenarios"]["max"]["ok"] is True
    assert blocked["scenarios"]["min"]["ok"] is False
    assert any(
        issue["code"] == "P4SC201"
        for issue in blocked["scenarios"]["min"]["issues"]
    )
    assert ready["ok"] is True


def test_p4v11b_transformer_neutral_impedance_reduces_fault_current():
    solid = _transformer_case("p4v11_dyn_solid", "solid")
    impedance = _transformer_case(
        "p4v11_dyn_impedance", "impedance", rn_ohm=0.05, xn_ohm=0.02
    )

    assert solid["ok"] is True
    assert impedance["ok"] is True
    assert impedance["results"]["ikss_ka"] < solid["results"]["ikss_ka"]
    assert impedance["results"]["ground_current_ka"] < solid["results"]["ground_current_ka"]


def test_p4v11b_workspace_displays_2ft_without_js_calculation_claim():
    _line_case("p4v11_view")
    result = iec60909_two_phase_ground_suite.ejecutar_2ph_ground_max_min(
        "bus1", line_endtemp_degree_c={"Line.f1": 20.0}
    )
    snapshot = {
        "status": {
            "studies": {
                "iec60909_2ph_ground": {"valid": True, "result": result},
            }
        }
    }

    enhanced = workspace_p4_view.enhance_html(_base_html(), snapshot)

    assert 'data-p4-study="iec60909_2ph_ground"' in enhanced
    assert 'data-p4-fault="2F-T"' in enhanced
    assert "Falla 2F-T" in enhanced
    assert "Extensión operacional 2F-T" in enhanced
    assert "no es todavía Ik'' contractual IEC" in enhanced
    assert "USABLE_WITH_DECLARED_SCOPE" in enhanced
    assert "Secuencia cero explícita" in enhanced
    assert "Secuencia negativa explícita" in enhanced
    assert "La vista presenta el snapshot Python y no reconstruye Z0 en JavaScript" in enhanced


def test_p4v11b_public_tool_is_registered():
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
    assert "ejecutar_cortocircuito_iec60909_2ph_ground" in fake.names
