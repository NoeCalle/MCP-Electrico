from opendssdirect import dss

from mcp_electrico import benchmarks, core, pandapower_engine, validation_status, visual_state


def _single_voltage_case():
    core.crear_circuito("pp_bridge", 0.48)
    visual_state.reset()
    core.agregar_linea(
        "f1",
        "sourcebus",
        "loadbus",
        0.05,
        fases=3,
        r1_ohm_km=0.2,
        x1_ohm_km=0.08,
    )
    # El benchmark independiente P1 modela una línea serie sin shunt.
    dss("Edit Line.f1 C1=0 C0=0")
    core.agregar_carga("c1", "loadbus", 30.0, 10.0, fases=3, kv=0.48)


def test_pandapower_v1_reports_explicit_scope():
    _single_voltage_case()
    result = pandapower_engine.evaluar_compatibilidad()

    assert result["engine"] == "pandapower"
    assert result["maturity"] == "EXPERIMENTAL"
    assert result["scope"] == "balanced_three_phase_single_voltage_line_load"
    assert result["compatible"] is True
    assert validation_status.get_module_status("pandapower_power_flow")["status"] == "EXPERIMENTAL"


def test_pandapower_v1_solves_single_voltage_case():
    _single_voltage_case()
    result = pandapower_engine.ejecutar_flujo()

    assert result["ok"] is True
    assert result["convergio"] is True
    buses = {row["bus"].lower(): row for row in result["resultados"]["buses"]}
    assert 0.95 < buses["loadbus"]["vm_pu"] < 1.0
    line = result["resultados"]["lines"][0]
    assert line["i_from_a"] > 0
    assert line["perdidas_kw"] > 0
    assert line["cargabilidad_pct"] is None


def test_pandapower_v1_matches_independent_two_bus_reference_without_opendss_crosscheck():
    _single_voltage_case()
    result = pandapower_engine.ejecutar_flujo()
    reference = benchmarks.solve_balanced_two_bus_reference(
        {
            "name": "pp_bridge_reference",
            "kv_ll": 0.48,
            "length_km": 0.05,
            "r_ohm_km": 0.2,
            "x_ohm_km": 0.08,
            "kw": 30.0,
            "kvar": 10.0,
        }
    )

    buses = {row["bus"].lower(): row for row in result["resultados"]["buses"]}
    line = result["resultados"]["lines"][0]

    assert abs(buses["loadbus"]["vm_pu"] - reference["vpu_receiving"]) < 0.0002
    assert abs(line["i_from_a"] - reference["current_a"]) < 0.15
    assert abs(result["resultados"]["resumen"]["perdidas_totales_kw"] - reference["loss_kw"]) < 0.005


def test_pandapower_v1_rejects_transformers_instead_of_guessing_parameters():
    core.crear_circuito("pp_transformer_reject", 22.9)
    visual_state.reset()
    core.agregar_transformador("tr1", "sourcebus", "lv", 1000, 22.9, 0.48)

    result = pandapower_engine.ejecutar_flujo()

    assert result["ok"] is False
    assert result["compatible"] is False
    assert any(issue["code"] == "PP010" for issue in result["issues"])
    assert "no se aplicaron aproximaciones silenciosas" in result["nota"]
