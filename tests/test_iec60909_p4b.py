import math

from mcp_electrico import core, iec60909, professional_data, visual_state


def _source_only():
    core.crear_circuito("p4_source_only", 22.9)
    visual_state.reset()
    professional_data.reset()
    professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=500.0,
        x_r_max=10.0,
        scc_min_mva=250.0,
        x_r_min=5.0,
        fuente_referencia="estudio de cortocircuito concesionaria",
    )


def _line_case():
    _source_only()
    core.agregar_linea(
        "f1", "sourcebus", "bus1", 0.25,
        fases=3, r1_ohm_km=0.18, x1_ohm_km=0.09,
    )


def _transformer_case():
    core.crear_circuito("p4_transformer", 22.9)
    visual_state.reset()
    professional_data.reset()
    professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=500.0,
        x_r_max=10.0,
        scc_min_mva=250.0,
        x_r_min=5.0,
        fuente_referencia="estudio de cortocircuito concesionaria",
    )
    professional_data.agregar_transformador_profesional(
        nombre="tr1",
        bus_hv="sourcebus",
        bus_lv="lv",
        kva=1000.0,
        kv_hv=22.9,
        kv_lv=0.48,
        uk_percent=6.0,
        grupo_vectorial="Dyn11",
        x_r=10.0,
        no_load_loss_kw=2.0,
        i0_percent=0.8,
        fuente_referencia="ficha técnica de prueba",
    )


def test_p4b_source_mapping_inverts_x_over_r_explicitly():
    _source_only()

    maximum = iec60909.evaluar_preparacion_3ph("max", "sourcebus")
    minimum = iec60909.evaluar_preparacion_3ph("min", "sourcebus")

    assert maximum["ready"] is True
    assert maximum["source_projection"]["scc3_mva"] == 500.0
    assert maximum["source_projection"]["x_r"] == 10.0
    assert maximum["source_projection"]["r_x_pandapower"] == 0.1
    assert maximum["source_projection"]["mapping"] == "rx = 1 / (X/R)"

    assert minimum["ready"] is True
    assert minimum["source_projection"]["scc3_mva"] == 250.0
    assert minimum["source_projection"]["x_r"] == 5.0
    assert minimum["source_projection"]["r_x_pandapower"] == 0.2


def test_p4b_executes_three_phase_max_and_min_at_source_bus():
    _source_only()

    maximum = iec60909.ejecutar_3ph("max", "sourcebus")
    minimum = iec60909.ejecutar_3ph("min", "sourcebus")

    assert maximum["ok"] is True
    assert minimum["ok"] is True
    assert maximum["fault"] == "3ph"
    assert maximum["case"] == "max"
    assert minimum["case"] == "min"
    assert maximum["results"]["ikss_ka"] > minimum["results"]["ikss_ka"] > 0
    assert maximum["results"]["skss_mva"] > minimum["results"]["skss_mva"] > 0
    assert maximum["backend_raw"]["skss_vs_mcp_abs_error"] < 1e-6
    assert minimum["backend_raw"]["skss_vs_mcp_abs_error"] < 1e-6
    assert maximum["engine"]["automatic_dispatch"] is False
    assert maximum["engine"]["crosscheck"] is False
    assert maximum["engine"]["target_edition_conformance"] == "UNVERIFIED_AGAINST_TARGET_EDITION"
    assert maximum["target_standard"]["id"] == "IEC_60909_0_2026"
    assert maximum["professional_emission"] is False


def test_p4b_source_bus_current_is_consistent_with_declared_short_circuit_power():
    _source_only()
    result = iec60909.ejecutar_3ph("max", "sourcebus")

    expected_ka = 500.0 / (math.sqrt(3.0) * 22.9)
    assert result["ok"] is True
    # En la barra de red equivalente, Scc3 declarada fija la magnitud del caso.
    assert result["results"]["ikss_ka"] == pytest.approx(expected_ka, rel=1e-6)
    assert result["results"]["skss_mva"] == pytest.approx(500.0, rel=1e-6)


def test_p4b_minimum_with_lines_fails_closed_without_end_temperature():
    _line_case()
    result = iec60909.ejecutar_3ph("min", "bus1")

    assert result["ok"] is False
    assert any(issue["code"] == "P4SC201" and issue["element"] == "Line.f1" for issue in result["issues"])


def test_p4b_minimum_with_line_temperature_executes():
    _line_case()
    result = iec60909.ejecutar_3ph(
        "min", "bus1", {"Line.f1": 90.0}
    )

    assert result["ok"] is True
    assert result["input_projection"]["line_endtemp_degree_c"]["line.f1"] == 90.0
    assert result["results"]["ikss_ka"] > 0


def test_p4b_three_phase_passes_through_complete_p2_transformer():
    _transformer_case()
    result = iec60909.ejecutar_3ph("max", "lv")

    assert result["ok"] is True
    assert result["bus"].lower() == "lv"
    assert result["vn_kv"] == 0.48
    assert result["results"]["ikss_ka"] > 0


def test_p4b_rejects_unknown_bus_and_invalid_case():
    _source_only()

    bad_bus = iec60909.ejecutar_3ph("max", "missing")
    bad_case = iec60909.ejecutar_3ph("medio", "sourcebus")

    assert bad_bus["ok"] is False
    assert any(issue["code"] == "P4SC002" for issue in bad_bus["issues"])
    assert bad_case["ok"] is False
    assert any(issue["code"] == "P4SC001" for issue in bad_case["issues"])
