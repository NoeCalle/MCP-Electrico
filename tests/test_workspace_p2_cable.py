from pathlib import Path

from mcp_electrico import (
    conductor_library,
    core,
    visual_state,
    workspace,
    workspace_state,
    workspace_studies_view,
)


def _build_line():
    core.crear_circuito("p2_cable_workspace", 22.9)
    visual_state.reset()
    workspace_state.reset_for_circuit("test")
    core.agregar_linea(
        "f1",
        "sourcebus",
        "b1",
        0.25,
        fases=3,
        r1_ohm_km=0.5,
        x1_ohm_km=0.2,
    )
    workspace_state.mark_model_changed("agregar_linea:f1")


def _generate(tmp_path: Path) -> str:
    workspace.configure(
        str(tmp_path / "workspace_p2.html"),
        "P2 cable workspace",
        auto_regenerar=False,
    )
    generated = workspace.regenerate()
    result = workspace_studies_view.enhance_file(
        generated["archivo_html"], workspace_state.snapshot()
    )
    assert result["ok"] is True
    assert result["p2_cable_inspector"] is True
    return Path(generated["archivo_html"]).read_text(encoding="utf-8")


def test_snapshot_exposes_structured_conductor_assignment():
    _build_line()
    assignment = conductor_library.aplicar_conductor(
        "Line.f1",
        "NEXANS-N2XSY-18-30-CU-70-PH16",
        "air_trefoil_30c",
    )
    workspace_state.mark_model_changed("aplicar_conductor:f1")

    line = workspace_state.snapshot()["model"]["lines"][0]
    cable = line["conductor_assignment"]

    assert cable["codigo"] == assignment["codigo"]
    assert cable["producto"]["familia"] == "N2XSY"
    assert cable["producto"]["seccion_mm2"] == 70
    assert cable["instalacion"] == "air_trefoil_30c"
    assert cable["ampacidad_aplicada_a"] == 296
    assert cable["r1_aplicado_ohm_km"] == 0.3422
    assert cable["x1_aplicado_ohm_km"] == 0.1619
    assert cable["fuente"]["confidence"] == "HIGH"


def test_workspace_injects_p2_cable_inspector_without_claiming_normative_iz(tmp_path: Path):
    _build_line()
    conductor_library.aplicar_conductor(
        "Line.f1",
        "NEXANS-N2XSY-18-30-CU-70-PH16",
        "air_trefoil_30c",
    )
    workspace_state.mark_model_changed("aplicar_conductor:f1")

    html = _generate(tmp_path)

    assert "<!-- MCP-P2-CABLE-V2 -->" in html
    assert 'data-module="mcp-p2-cable-v2"' in html
    assert "Cable / instalación P2" in html
    assert "Ampacidad catálogo" in html
    assert "no es Iz normativo P3" in html
    assert "p2-table-trace" in html
    assert "NEXANS-N2XSY-18-30-CU-70-PH16" in html
    assert "air_trefoil_30c" in html
    assert "https://www.nexans.pe/" in html


def test_workspace_marks_visual_only_conductor_as_not_traceable(tmp_path: Path):
    _build_line()
    visual_state.configure_feeder(
        "Line.f1",
        etiqueta="F-01",
        conductor="3x70 mm2 Cu XLPE",
    )
    workspace_state.mark_visual_changed("anotacion_visual")

    html = _generate(tmp_path)

    assert "sin trazabilidad" in html
    assert "La anotación visual no equivale a una ficha técnica trazable" in html
    snap = workspace_state.snapshot()
    assert snap["model"]["lines"][0]["conductor_assignment"] is None
