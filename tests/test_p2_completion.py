from opendssdirect import dss

from mcp_electrico import conductor_library, core, p2_completion, professional_data


def test_p2_product_gate_is_complete_with_explicit_limitations_without_active_model():
    dss("Clear")
    result = p2_completion.evaluar_cierre_p2()

    assert result["phase_status"] == "COMPLETE_WITH_LIMITATIONS"
    assert result["ready_for_next_phase"] is True
    assert result["next_phase"] == "P3_ampacity"
    assert result["model"]["status"] == "NO_ACTIVE_MODEL"
    assert len(result["capabilities"]) >= 8
    assert all(item["status"] == "DONE" for item in result["capabilities"])
    assert any("no es Iz normativo" in text for text in result["limitations"])
    assert any("IEC 60909" in text for text in result["limitations"])


def test_professional_transformer_and_source_can_pass_p2_coherence_gate():
    core.crear_circuito("p2_exit_ok", 22.9)
    professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=500.0,
        x_r_max=10.0,
        scc_min_mva=250.0,
        x_r_min=7.0,
        fuente_referencia="estudio de red",
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
        fuente_referencia="ficha fabricante",
    )
    core.agregar_carga("load1", "lv", 100.0, 30.0, fases=3, kv=0.48)

    result = p2_completion.evaluar_cierre_p2()

    assert result["phase_status"] == "COMPLETE_WITH_LIMITATIONS"
    assert result["model"]["status"] == "MODEL_COHERENT"
    assert result["model"]["summary"]["errors"] == 0


def test_p2_coherence_detects_source_voltage_drift():
    core.crear_circuito("p2_exit_source_drift", 22.9)
    professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=500.0,
        x_r_max=10.0,
        fuente_referencia="estudio de red",
    )
    dss("Edit Vsource.source BasekV=13.8")

    result = p2_completion.evaluar_modelo_actual()

    assert result["status"] == "MODEL_ISSUES"
    assert any(item["code"] == "P2X103" for item in result["issues"])


def test_p2_coherence_detects_conductor_assignment_drift():
    core.crear_circuito("p2_exit_cable_drift", 22.9)
    core.agregar_linea("l1", "sourcebus", "b1", 0.2, fases=3, r1_ohm_km=0.3, x1_ohm_km=0.1)
    conductor_library.aplicar_conductor(
        "Line.l1",
        "NEXANS-N2XSY-18-30-CU-70-PH16",
        "air_trefoil_30c",
    )
    dss("Edit Line.l1 NormAmps=999")

    result = p2_completion.evaluar_modelo_actual()

    assert result["status"] == "MODEL_ISSUES"
    assert any(item["code"] == "P2X202" for item in result["issues"])


def test_legacy_transformer_is_warning_not_fake_p2_error():
    core.crear_circuito("p2_exit_legacy", 22.9)
    core.agregar_transformador("tr_old", "sourcebus", "lv", 500.0, 22.9, 0.48)

    result = p2_completion.evaluar_modelo_actual()

    assert result["status"] == "MODEL_COHERENT"
    assert result["summary"]["errors"] == 0
    assert result["summary"]["warnings"] >= 1
    assert any(item["code"] == "P2X301" for item in result["issues"])
