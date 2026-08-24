from mcp_electrico import core, model_qa, professional_data, visual_state, workspace_state


def test_qa_advierte_si_opendss_conserva_defaults_por_p0_i0_ausentes():
    core.crear_circuito("p2_projection_warning", 22.9)
    visual_state.reset()
    professional_data.reset()
    workspace_state.reset_for_circuit("test")

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
        fuente_referencia="placa parcial de prueba",
    )
    core.agregar_carga("c1", "lv", 100, 30, fases=3, kv=0.48)

    result = model_qa.auditar_modelo(["power_flow"])
    finding = next(f for f in result["findings"] if f["code"] == "QA216")

    assert finding["severity"] == "WARNING"
    assert finding["element"] == "Transformer.tr1"
    assert "OpenDSS" in finding["message"]
    assert "no_load_loss_kw" in finding["message"]
    assert "i0_percent" in finding["message"]
    # La advertencia no se convierte por sí sola en error/bloqueo de datos.
    assert result["summary"]["errors"] == 0
