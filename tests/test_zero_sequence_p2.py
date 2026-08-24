import pytest
from opendssdirect import dss

from mcp_electrico import core, model_qa, professional_data, visual_state, workspace_state, zero_sequence


def _new(name: str = "p2_z0", kv: float = 22.9):
    core.crear_circuito(name, kv)
    visual_state.reset()
    professional_data.reset()
    zero_sequence.reset()
    workspace_state.reset_for_circuit("test")


def _source():
    return professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=500,
        x_r_max=10,
        scc_min_mva=250,
        x_r_min=7,
        fuente_referencia="estudio cc concesionaria",
        fuente_url="https://example.invalid/source",
    )


def _transformer():
    return professional_data.agregar_transformador_profesional(
        nombre="tr1",
        bus_hv="sourcebus",
        bus_lv="lvbus",
        kva=1000,
        kv_hv=22.9,
        kv_lv=0.48,
        uk_percent=6.0,
        grupo_vectorial="Dyn11",
        x_r=10.0,
        no_load_loss_kw=2.0,
        i0_percent=0.8,
        fuente_referencia="ficha tecnica",
        fuente_url="https://example.invalid/tr1",
    )


def _query_float(prop: str) -> float:
    dss(f"? {prop}")
    return float(dss.Text.Result())


def test_fuente_z0_explica_max_min_y_reaplica_escenario():
    _new("p2_z0_source")
    _source()
    z0 = zero_sequence.definir_fuente(
        r0_max_ohm=0.30,
        x0_max_ohm=0.90,
        r0_min_ohm=0.55,
        x0_min_ohm=1.40,
        fuente_referencia="estudio homopolar concesionaria",
        fuente_url="https://example.invalid/z0-source",
    )

    assert z0["status"] == "EXPLICIT"
    assert z0["active_projection"]["scenario"] == "max"
    assert _query_float("Vsource.source.R0") == pytest.approx(0.30)
    assert _query_float("Vsource.source.X0") == pytest.approx(0.90)

    professional_data.seleccionar_escenario_red("min")
    applied = zero_sequence.reapply_active_source()
    assert applied["applied"] is True
    assert applied["scenario"] == "min"
    assert _query_float("Vsource.source.R0") == pytest.approx(0.55)
    assert _query_float("Vsource.source.X0") == pytest.approx(1.40)


def test_fuente_z0_no_reutiliza_max_si_min_no_fue_suministrada():
    _new("p2_z0_source_missing_min")
    _source()
    zero_sequence.definir_fuente(0.3, 0.9)
    professional_data.seleccionar_escenario_red("min")

    applied = zero_sequence.reapply_active_source()
    assert applied["applied"] is False
    assert "no definida" in applied["reason"]

    qa = model_qa.auditar_modelo(["short_circuit"])
    assert any(f["code"] == "QA304" and f["severity"] == "BLOCKER" for f in qa["findings"])


def test_linea_z0_aplica_r0_x0_c0_sin_derivar_desde_r1_x1():
    _new("p2_z0_line")
    core.agregar_linea("l1", "sourcebus", "b1", 1.0, r1_ohm_km=0.2, x1_ohm_km=0.08)

    result = zero_sequence.definir_linea(
        "Line.l1",
        r0_ohm_km=0.65,
        x0_ohm_km=0.32,
        c0_nf_km=4.2,
        fuente_referencia="ensayo/calculo geometrico",
        fuente_url="https://example.invalid/l1-z0",
    )

    dss.Lines.Name("l1")
    assert dss.Lines.R0() == pytest.approx(0.65)
    assert dss.Lines.X0() == pytest.approx(0.32)
    assert dss.Lines.C0() == pytest.approx(4.2)
    assert result["projection"]["opendss_ready"] is True
    assert result["provenance"]["reference"] == "ensayo/calculo geometrico"


def test_transformador_z0_queda_canonico_y_pandapower_ready_sin_forzar_opendss():
    _new("p2_z0_tr")
    _transformer()

    result = zero_sequence.definir_transformador(
        "tr1",
        uk0_percent=5.5,
        ur0_percent=0.6,
        magnetizing_z0_ratio_percent=100.0,
        magnetizing_r_over_x=0.0,
        leakage_share_hv=0.5,
        neutral_side="lv",
        neutral_mode="solid",
        fuente_referencia="informe ensayo secuencia cero",
        fuente_url="https://example.invalid/tr1-z0",
    )

    assert result["impedance"]["uk0_percent"] == 5.5
    assert result["neutral"]["ground_path_declared"] is True
    assert result["projection"]["pandapower_ready"] is True
    assert result["projection"]["pandapower"]["vk0_percent"] == 5.5
    assert result["projection"]["opendss_ready"] is False
    assert "no se proyecta" in result["projection"]["opendss_reason"]

    qa = model_qa.auditar_modelo(["short_circuit"])
    assert not any(f["code"] == "QA215" for f in qa["findings"])
    assert any(f["code"] == "QA217" and f["severity"] == "BLOCKER" for f in qa["findings"])


def test_transformador_z0_rechaza_neutro_en_lado_delta():
    _new("p2_z0_tr_bad_neutral")
    _transformer()

    with pytest.raises(ValueError, match="P2ZT009"):
        zero_sequence.definir_transformador(
            "tr1",
            uk0_percent=5.5,
            ur0_percent=0.6,
            magnetizing_z0_ratio_percent=100.0,
            magnetizing_r_over_x=0.0,
            leakage_share_hv=0.5,
            neutral_side="hv",
            neutral_mode="solid",
        )


def test_qa_fault_requiere_z0_explicita_en_linea_y_fuente():
    _new("p2_z0_qa")
    _source()
    core.agregar_linea("l1", "sourcebus", "b1", 1.0, r1_ohm_km=0.2, x1_ohm_km=0.08)
    core.agregar_carga("c1", "b1", 100, 30, fases=3, kv=22.9)

    before = model_qa.auditar_modelo(["short_circuit"])
    assert any(f["code"] == "QA120" and f["severity"] == "BLOCKER" for f in before["findings"])
    assert any(f["code"] == "QA302" and f["severity"] == "BLOCKER" for f in before["findings"])

    zero_sequence.definir_fuente(0.3, 0.9, 0.55, 1.4)
    zero_sequence.definir_linea("l1", 0.65, 0.32)
    after = model_qa.auditar_modelo(["short_circuit"])
    assert not any(f["code"] in {"QA120", "QA302", "QA304"} for f in after["findings"])
    assert any(f["code"] == "QA901" for f in after["findings"]), "short_circuit sigue UNDER_VALIDATION"
