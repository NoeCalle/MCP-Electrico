from opendssdirect import dss

from mcp_electrico import (
    benchmarks,
    core,
    pandapower_engine,
    professional_data,
    validation_status,
    visual_state,
)


def _single_voltage_case(source_bus: str = "sourcebus"):
    core.crear_circuito("pp_bridge", 0.48, bus_fuente=source_bus)
    visual_state.reset()
    professional_data.reset()
    core.agregar_linea(
        "f1", source_bus, "loadbus", 0.05,
        fases=3, r1_ohm_km=0.2, x1_ohm_km=0.08,
    )
    dss("Edit Line.f1 C1=0 C0=0")
    core.agregar_carga("c1", "loadbus", 30.0, 10.0, fases=3, kv=0.48)


def _p2_transformer_case(complete: bool = True):
    core.crear_circuito("pp_transformer_p2", 22.9)
    visual_state.reset()
    professional_data.reset()
    professional_data.agregar_transformador_profesional(
        nombre="tr1",
        bus_hv="sourcebus",
        bus_lv="lv",
        kva=1000,
        kv_hv=22.9,
        kv_lv=0.48,
        uk_percent=6.0,
        grupo_vectorial="Dyn11",
        x_r=10.0,
        no_load_loss_kw=2.0 if complete else None,
        i0_percent=0.8 if complete else None,
        fuente_referencia="ficha de prueba",
    )
    core.agregar_carga("c1", "lv", 300, 100, fases=3, kv=0.48)


def test_pandapower_reports_explicit_scope():
    _single_voltage_case()
    result = pandapower_engine.evaluar_compatibilidad()

    assert result["engine"] == "pandapower"
    assert result["maturity"] == "EXPERIMENTAL"
    assert result["scope"] == "balanced_three_phase_line_load_p2_transformer_optional"
    assert result["compatible"] is True
    assert result["model_summary"]["source_bus"] == "sourcebus"
    assert validation_status.get_module_status("pandapower_power_flow")["status"] == "EXPERIMENTAL"


def test_pandapower_solves_single_voltage_case():
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


def test_pandapower_supports_explicit_nonlegacy_source_bus():
    _single_voltage_case("red_mt")
    result = pandapower_engine.ejecutar_flujo()

    assert result["ok"] is True
    assert result["convergio"] is True
    assert result["model_summary"]["source_bus"] == "red_mt"
    buses = {row["bus"].lower(): row for row in result["resultados"]["buses"]}
    assert "red_mt" in buses
    assert "sourcebus" not in buses
    assert any("red_mt" in item for item in result["assumptions"])


def test_pandapower_p2_source_bus_must_match_effective_vsource():
    core.crear_circuito("pp_source_binding", 22.9, bus_fuente="red_mt")
    visual_state.reset()
    professional_data.reset()
    professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=350.0,
        x_r_max=10.0,
        fuente_referencia="estudio de prueba",
        bus_fuente="red_mt",
    )
    core.agregar_linea("f1", "red_mt", "loadbus", 0.05, fases=3, r1_ohm_km=0.2, x1_ohm_km=0.08)
    core.agregar_carga("c1", "loadbus", 30.0, 10.0, fases=3, kv=22.9)

    dss("Edit Vsource.source Bus1=otra_red")
    result = pandapower_engine.evaluar_compatibilidad()

    assert result["compatible"] is False
    assert any(issue["code"] == "PP003" for issue in result["issues"])


def test_pandapower_matches_independent_two_bus_reference_without_opendss_crosscheck():
    _single_voltage_case()
    result = pandapower_engine.ejecutar_flujo()
    reference = benchmarks.solve_balanced_two_bus_reference(dict(benchmarks.BENCHMARK_CASES[0]))

    buses = {row["bus"].lower(): row for row in result["resultados"]["buses"]}
    line = result["resultados"]["lines"][0]

    assert abs(buses["loadbus"]["vm_pu"] - reference["vpu_receiving"]) < 0.0002
    assert abs(line["i_from_a"] - reference["current_a"]) < 0.15
    assert abs(result["resultados"]["resumen"]["perdidas_totales_kw"] - reference["loss_kw"]) < 0.005


def test_pandapower_still_rejects_legacy_transformer_instead_of_guessing_parameters():
    core.crear_circuito("pp_transformer_reject", 22.9)
    visual_state.reset()
    professional_data.reset()
    core.agregar_transformador("tr1", "sourcebus", "lv", 1000, 22.9, 0.48)

    result = pandapower_engine.ejecutar_flujo()

    assert result["ok"] is False
    assert result["compatible"] is False
    assert any(issue["code"] == "PP010" for issue in result["issues"])
    assert "no se aplicaron aproximaciones silenciosas" in result["nota"]


def test_pandapower_rejects_p2_transformer_if_required_no_load_data_are_missing():
    _p2_transformer_case(complete=False)
    result = pandapower_engine.ejecutar_flujo()

    assert result["ok"] is False
    assert any(issue["code"] == "PP012" for issue in result["issues"])


def test_pandapower_solves_with_complete_p2_transformer_without_crosscheck():
    _p2_transformer_case(complete=True)
    result = pandapower_engine.ejecutar_flujo()

    assert result["ok"] is True
    assert result["convergio"] is True
    buses = {row["bus"].lower(): row for row in result["resultados"]["buses"]}
    assert "sourcebus" in buses and "lv" in buses
    assert 0.85 < buses["lv"]["vm_pu"] < 1.05
    assert len(result["resultados"]["transformers"]) == 1
    assert result["resultados"]["transformers"][0]["loading_percent"] > 0
