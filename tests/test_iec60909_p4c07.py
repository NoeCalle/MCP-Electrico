import pytest

from mcp_electrico import (
    core,
    iec60909_benchmarks_1ph,
    iec60909_single_phase_ground,
    professional_data,
    visual_state,
    workspace_state,
    zero_sequence,
)


def _reset(name: str = "p4c07") -> None:
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
        fuente_referencia="P4C07 test source",
    )
    zero_sequence.definir_fuente(
        r0_max_ohm=0.10,
        x0_max_ohm=0.35,
        r0_min_ohm=0.20,
        x0_min_ohm=0.70,
        fuente_referencia="P4C07 test source Z0",
    )


def test_p4c07_source_projection_preserves_absolute_zero_sequence():
    _reset("p4c07_source_projection")
    _source()

    projection = iec60909_single_phase_ground._source_zero_projection("max")

    assert projection["r0_ohm"] == pytest.approx(0.10)
    assert projection["x0_ohm"] == pytest.approx(0.35)
    assert projection["r0x0"] == pytest.approx(0.10 / 0.35)
    assert projection["x0x"] * projection["x1_backend_ohm"] == pytest.approx(0.35)
    assert projection["mapping"]["preserves_absolute_z0"] is True
    assert projection["voltage_factor_c"] == pytest.approx(1.10)


def test_p4c07_requires_explicit_c0_for_each_line():
    _reset("p4c07_c0_gate")
    _source()
    core.agregar_linea("l1", "sourcebus", "b1", 0.2, r1_ohm_km=0.2, x1_ohm_km=0.08)
    zero_sequence.definir_linea("l1", r0_ohm_km=0.6, x0_ohm_km=0.3)

    with pytest.raises(ValueError, match="P4C07L002"):
        iec60909_single_phase_ground.ejecutar_1ph_ground("b1", "max")


def test_p4c07_independent_benchmark_passes_max_and_min():
    suite = iec60909_benchmarks_1ph.run_suite()

    assert suite["pass"] is True
    assert suite["p4c07_foundation_complete"] is True
    assert suite["p4c09_complete"] is False
    assert suite["professional_emission"] is False
    assert {item["case"] for item in suite["cases"]} == {"max", "min"}
    for item in suite["cases"]:
        assert item["pass"] is True
        assert item["actual"]["results"]["skss_mva"] is None
        assert item["actual"]["results"]["ip_ka"] is None
        assert item["actual"]["results"]["ith_ka"] is None
        assert item["actual"]["negative_sequence_policy"]["relation"] == "Z2 = Z1"
        assert item["actual"]["negative_sequence_policy"]["universal_assumption"] is False


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
        fuente_referencia="P4C07 transformer test",
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
        fuente_referencia="P4C07 transformer Z0 test",
    )
    return iec60909_single_phase_ground.ejecutar_1ph_ground("lvbus", "max")


def test_p4c07_projects_dyn11_zero_sequence_and_neutral_impedance_reduces_fault_current():
    solid = _transformer_case("p4c07_dyn_solid", "solid")
    impedance = _transformer_case("p4c07_dyn_impedance", "impedance", rn_ohm=0.05, xn_ohm=0.02)

    assert solid["ok"] is True
    assert impedance["ok"] is True
    solid_tr = solid["inputs"]["zero_sequence_projection"]["transformers"][0]
    imp_tr = impedance["inputs"]["zero_sequence_projection"]["transformers"][0]
    assert solid_tr["vector_group_effective"] == "Dyn"
    assert solid_tr["pandapower"]["rn_ohm"] == pytest.approx(0.0)
    assert imp_tr["pandapower"]["rn_ohm"] == pytest.approx(0.05)
    assert imp_tr["pandapower"]["xn_ohm"] == pytest.approx(0.02)
    assert impedance["results"]["ikss_ka"] < solid["results"]["ikss_ka"]
