from copy import deepcopy
import json
from pathlib import Path

from mcp_electrico import (
    core,
    project_report,
    project_report_tools,
    project_snapshot,
    workspace_state,
)


def _snapshot_with_current_and_historical_studies(tmp_path) -> dict:
    core.crear_circuito("p7c_report_case", 0.48)
    workspace_state.reset_for_circuit("p7c_report_case")
    workspace_state.record_study(
        "historical_probe",
        {"status": "OLD", "professional_emission": False},
        "p7c_historical",
    )
    core.agregar_linea(
        "f1", "sourcebus", "bus1", 0.05,
        fases=3, r1_ohm_km=0.20, x1_ohm_km=0.08,
    )
    workspace_state.mark_model_changed("p7c_add_f1")
    core.agregar_carga("load1", "bus1", 60.0, 15.0, fases=3, kv=0.48)
    workspace_state.mark_model_changed("p7c_add_load1")
    workspace_state.record_solution(
        {"convergio": True, "status": "TEST_SOLUTION"},
        "powerflow",
        "p7c_solution",
    )
    workspace_state.record_study(
        "current_probe",
        {"status": "CURRENT", "professional_emission": False},
        "p7c_current",
    )
    return project_snapshot.construir_snapshot(str(tmp_path / "source_dss"))


def test_p7c_same_verified_snapshot_produces_same_report_hash_and_html(tmp_path):
    snapshot = _snapshot_with_current_and_historical_studies(tmp_path)

    first = project_report.construir_reporte(snapshot)
    second = project_report.construir_reporte(snapshot)

    assert first["ok"] is True
    assert first["status"] == "TECHNICAL_REPORT_READY_FOR_PRINT"
    assert first["report_hash"] == second["report_hash"]
    assert first["html"] == second["html"]
    assert first["data"] == second["data"]
    assert first["data"]["source_snapshot"]["sha256"] == snapshot["hash"]["value"]
    assert first["data"]["studies"]["current_count"] == 2
    assert first["data"]["studies"]["historical_count"] == 1
    assert set(first["data"]["studies"]["current"]) == {"current_probe", "powerflow"}
    assert set(first["data"]["studies"]["historical"]) == {"historical_probe"}
    assert first["data"]["product_status"]["p6_arc_flash_ieee1584"] == "DEFERRED"
    assert first["engineering_preview_ready"] is False
    assert first["professional_report"] is False
    assert first["professional_emission"] is False


def test_p7c_html_is_print_ready_and_contains_no_engineering_javascript(tmp_path):
    snapshot = _snapshot_with_current_and_historical_studies(tmp_path)
    report = project_report.construir_reporte(snapshot)
    html = report["html"]

    assert 'data-module="mcp-p7c-technical-report"' in html
    assert "NO APTO PARA EMISIÓN PROFESIONAL" in html
    assert "Imprimir / Guardar PDF" in html
    assert "window.print()" in html
    assert "BROWSER_PRINT" in html
    assert "professional_emission=false" in html
    assert snapshot["hash"]["value"] in html
    assert '<script type="application/json" id="p7c-report-data">' in html
    assert "Math." not in html
    assert "interpolate" not in html.lower()
    assert "calc_sc" not in html
    assert "browser_engineering_calculation" in html


def test_p7c_tampered_snapshot_is_blocked_before_write(tmp_path):
    snapshot = _snapshot_with_current_and_historical_studies(tmp_path)
    tampered = deepcopy(snapshot)
    tampered["payload"]["project"]["circuit"] = "tampered"
    target = tmp_path / "must_not_exist.html"

    result = project_report.exportar_reporte(tampered, str(target))

    assert result["ok"] is False
    assert result["status"] == "BLOCKED_SNAPSHOT_INTEGRITY"
    assert result["source_verification"]["status"] == "HASH_MISMATCH"
    assert result["write_performed"] is False
    assert not target.exists()
    assert result["professional_emission"] is False


def test_p7c_export_does_not_overwrite_and_matches_report_hash(tmp_path):
    snapshot = _snapshot_with_current_and_historical_studies(tmp_path)
    target = tmp_path / "report.html"

    first = project_report.exportar_reporte(snapshot, str(target))
    second = project_report.exportar_reporte(snapshot, str(target))

    assert first["ok"] is True
    assert second["ok"] is True
    assert Path(first["path"]).name == "report.html"
    assert Path(second["path"]).name == "report_2.html"
    assert first["report_hash"] == second["report_hash"]
    assert Path(first["path"]).read_text(encoding="utf-8") == Path(second["path"]).read_text(encoding="utf-8")
    assert first["pdf_export_mode"] == "BROWSER_PRINT"
    assert first["browser_engineering_calculation"] is False


def test_p7c_export_from_json_file_and_invalid_json_are_fail_closed(tmp_path):
    snapshot = _snapshot_with_current_and_historical_studies(tmp_path)
    snapshot_path = tmp_path / "project.json"
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

    ok = project_report.exportar_reporte_desde_archivo(
        str(snapshot_path), str(tmp_path / "from_file.html")
    )
    assert ok["ok"] is True
    assert ok["source_snapshot_sha256"] == snapshot["hash"]["value"]

    broken = tmp_path / "broken.json"
    broken.write_text("{broken", encoding="utf-8")
    fail = project_report.exportar_reporte_desde_archivo(
        str(broken), str(tmp_path / "broken.html")
    )
    assert fail["ok"] is False
    assert fail["status"] == "INVALID_SNAPSHOT_JSON"
    assert fail["professional_emission"] is False


def test_p7c_contract_and_tools_keep_professional_emission_closed():
    contract = project_report.obtener_contrato_p7c()
    assert contract["source_integrity_required"] == "HASH_MATCH"
    assert contract["deterministic_from_verified_snapshot"] is True
    assert contract["electrical_recalculation"] is False
    assert contract["browser_engineering_calculation"] is False
    assert contract["pdf_export_mode"] == "BROWSER_PRINT"
    assert contract["native_pdf_generation"] is False
    assert contract["engineering_preview_ready"] is False
    assert contract["professional_report"] is False
    assert contract["professional_emission"] is False

    class FakeMCP:
        def __init__(self):
            self.names = []

        def tool(self):
            def decorator(func):
                self.names.append(func.__name__)
                return func
            return decorator

    fake = FakeMCP()
    project_report_tools.register(fake)
    assert fake.names == [
        "obtener_contrato_reporte_p7c",
        "exportar_reporte_tecnico_p7c",
        "exportar_reporte_desde_archivo_p7c",
        "evaluar_cierre_p7d_engineering_preview",
    ]
