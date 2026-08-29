import json
import re

from mcp_electrico import core, project_report, project_snapshot, workspace_state


def _empty_study_snapshot(tmp_path):
    core.crear_circuito("p7c_empty_case", 0.48)
    workspace_state.reset_for_circuit("p7c_empty_case")
    core.agregar_linea(
        "f1", "sourcebus", "bus1", 0.05,
        fases=3, r1_ohm_km=0.20, x1_ohm_km=0.08,
    )
    workspace_state.mark_model_changed("p7c_empty_add_f1")
    return project_snapshot.construir_snapshot(str(tmp_path / "source_dss"))


def test_p7c_renders_empty_study_sections_without_error(tmp_path):
    snapshot = _empty_study_snapshot(tmp_path)
    report = project_report.construir_reporte(snapshot)

    assert report["ok"] is True
    assert report["data"]["studies"]["current"] == {}
    assert report["data"]["studies"]["historical"] == {}
    assert "No hay estudios vigentes registrados." in report["html"]
    assert "No hay resultados históricos registrados." in report["html"]


def test_p7c_embedded_application_json_is_parseable_and_matches_report_data(tmp_path):
    snapshot = _empty_study_snapshot(tmp_path)
    report = project_report.construir_reporte(snapshot)
    match = re.search(
        r'<script type="application/json" id="p7c-report-data">(.*?)</script>',
        report["html"],
        re.S,
    )

    assert match is not None
    embedded = json.loads(match.group(1))
    assert embedded == report["data"]
    assert embedded["rendering_contract"]["browser_engineering_calculation"] is False
