from pathlib import Path

from mcp_electrico import core, visual_state, workspace, workspace_state


def _build_case():
    core.crear_circuito("workspace_test", 13.2)
    visual_state.reset()
    workspace_state.reset_for_circuit("test")
    core.agregar_transformador("tr1", "sourcebus", "tgbt", 500, 13.2, 0.48)
    workspace_state.mark_model_changed("tr1")
    core.agregar_linea("f1", "tgbt", "mcc", 0.04, r1_ohm_km=0.25, x1_ohm_km=0.12)
    workspace_state.mark_model_changed("f1")
    core.agregar_carga("bomba", "mcc", 55, 20, kv=0.48)
    visual_state.set_load_type("bomba", "motor")
    visual_state.set_load_label("bomba", "M-01 · BOMBA")
    visual_state.configure_feeder(
        "Line.f1",
        etiqueta="F-01",
        proteccion="mccb",
        conductor="3x70 mm2 Cu XLPE",
        corriente_nominal_a=160,
        capacidad_ruptura_ka=25,
    )
    workspace_state.mark_model_changed("bomba")


def test_resultado_se_invalida_al_cambiar_revision():
    _build_case()
    powerflow = core.ejecutar_flujo_potencia()
    workspace_state.record_solution(powerflow)
    solved = workspace_state.status()
    assert solved["state"] == "SOLVED"
    assert solved["results_current"] is True
    assert solved["studies"]["powerflow"]["valid"] is True

    core.agregar_carga("extra", "mcc", 5, 1, kv=0.48)
    workspace_state.mark_model_changed("agregar_extra")
    modified = workspace_state.status()
    assert modified["state"] == "MODIFIED"
    assert modified["results_current"] is False
    assert modified["studies"]["powerflow"]["valid"] is False


def test_cambio_visual_no_invalida_solucion():
    _build_case()
    powerflow = core.ejecutar_flujo_potencia()
    workspace_state.record_solution(powerflow)
    revision = workspace_state.status()["model_revision"]
    visual_state.set_load_label("bomba", "M-01 · BOMBA PRINCIPAL")
    workspace_state.mark_visual_changed("cambiar_etiqueta")
    status = workspace_state.status()
    assert status["model_revision"] == revision
    assert status["state"] == "SOLVED"
    assert status["results_current"] is True
    assert status["visual_revision"] == 1


def test_workspace_genera_html_autocontenido_svg_e_inspector(tmp_path: Path):
    _build_case()
    powerflow = core.ejecutar_flujo_potencia()
    workspace_state.record_solution(powerflow)
    workspace.configure(str(tmp_path / "workspace.html"), "Prueba Workspace", True)
    result = workspace.regenerate()
    html_path = Path(result["archivo_html"])
    svg_path = Path(result["archivo_svg"])
    assert html_path.exists()
    assert svg_path.exists()
    html = html_path.read_text(encoding="utf-8")
    assert "Prueba Workspace" in html
    assert "RESUELTO" in html
    assert "Imprimir / PDF" in html
    assert "Descargar SVG" in html
    assert 'id="workspace-snapshot"' in html
    assert 'id="workspace-catalog"' in html
    assert 'id="elementSelect"' in html
    assert 'id="inspectorBody"' in html
    assert '"schema_version":2' in html
    assert "F-01" in html
    assert "3x70 mm2 Cu XLPE" in html
    assert "M-01 · BOMBA" in html
    assert 'data-element-id="Line.f1"' in html
    assert 'data-element-id="Load.bomba"' in html
    assert "<script src=" not in html
    assert '<link rel="stylesheet"' not in html


def test_catalogo_interactivo_usa_ids_estables():
    _build_case()
    snap = workspace_state.snapshot()
    catalog = workspace._element_catalog(snap)
    by_id = {item["id"]: item for item in catalog}
    assert by_id["Line.f1"]["label"] == "F-01"
    assert by_id["Transformer.tr1"]["label"] == "TR1"
    assert by_id["Load.bomba"]["label"] == "M-01 · BOMBA"
    assert by_id["Bus.tgbt"]["kind"] == "bus"


def test_filas_de_datos_reutilizan_mismos_ids_del_catalogo():
    _build_case()
    snap = workspace_state.snapshot()
    rows = workspace._data_rows(snap)
    assert 'data-element-id="Line.f1"' in rows
    assert 'data-element-id="Transformer.tr1"' in rows
    assert 'data-element-id="Load.bomba"' in rows


def test_error_de_render_no_invalida_estado_electrico_y_se_limpia_al_recuperar(tmp_path: Path, monkeypatch):
    _build_case()
    powerflow = core.ejecutar_flujo_potencia()
    workspace_state.record_solution(powerflow)
    workspace.configure(str(tmp_path / "workspace.html"), auto_regenerar=False)
    real_renderer = workspace.generar_diagrama_unifilar

    def fail_renderer(*args, **kwargs):
        raise RuntimeError("fallo visual controlado")

    monkeypatch.setattr(workspace, "generar_diagrama_unifilar", fail_renderer)
    workspace.configure(str(tmp_path / "workspace.html"), auto_regenerar=True)
    failed = workspace.safe_regenerate()
    failed_status = workspace_state.status()
    assert failed["ok"] is False
    assert failed_status["state"] == "SOLVED"
    assert failed_status["results_current"] is True
    assert "fallo visual controlado" in failed_status["workspace_error"]

    monkeypatch.setattr(workspace, "generar_diagrama_unifilar", real_renderer)
    recovered = workspace.safe_regenerate()
    recovered_status = workspace_state.status()
    html = Path(recovered["archivo_html"]).read_text(encoding="utf-8")
    assert recovered["ok"] is True
    assert recovered_status["state"] == "SOLVED"
    assert recovered_status["workspace_error"] is None
    assert "fallo visual controlado" not in html


def test_snapshot_distingue_modelo_y_metadatos_visuales():
    _build_case()
    snap = workspace_state.snapshot()
    assert snap["schema_version"] == 2
    assert snap["model"]["circuit"]
    assert snap["model"]["lines"][0]["id"].lower() == "line.f1"
    assert snap["model"]["lines"][0]["visual"]["etiqueta"] == "F-01"
    assert snap["model"]["loads"][0]["label"] == "M-01 · BOMBA"
