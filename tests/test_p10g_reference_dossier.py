from __future__ import annotations

import json
from pathlib import Path

from mcp_electrico import dossier_integrity, real_project_dossier, workspace_state


def _manifest() -> dict:
    path = Path(__file__).resolve().parents[1] / "examples" / "p10_reference_substation_stage5.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_ready_dossier(result: dict, root: Path) -> None:
    assert result["status"] == "DOSSIER_READY_ENGINEERING_PREVIEW", result
    assert result["p8d2_execution_status"] == "PROTECTION_EXECUTION_COMPLETED"
    assert result["active_circuit_preserved"] is True

    assert result["workspace"]["status"] == "WORKSPACE_V5_READY"
    assert result["workspace"]["p8d2_integrated_view"] is True
    assert result["workspace"]["browser_engineering_calculation"] is False

    assert result["p7a"]["status"] == "HASH_MATCH"
    assert result["p7a"]["sha256"]

    assert result["p7b"]["status"] == "RECONSTRUCTED_NETLIST_VERIFIED_WITH_REBIND_REQUIRED"
    assert result["p7b"]["isolated_process"] is False
    assert result["p7b"]["isolated_context"] is True
    assert result["p7b"]["isolation_mode"] == "OPENDSS_NEW_CONTEXT"
    assert result["p7b"]["parent_dss_context_mutated"] is False
    assert result["p7b"]["parent_structured_state_mutated"] is False
    assert result["p7b"]["stored_results_promoted_to_current"] is False

    assert result["p7c"]["status"] == "TECHNICAL_REPORT_READY_FOR_PRINT"
    assert result["p7c"]["source_snapshot_sha256"] == result["p7a"]["sha256"]
    assert result["p7c"]["browser_engineering_calculation"] is False

    assert result["integrity"]["status"] == "DOSSIER_INTEGRITY_VERIFIED"
    assert result["integrity"]["ok"] is True
    assert result["integrity"]["portable_relative_paths"] is True
    assert result["integrity"]["self_hash_included"] is False
    assert result["integrity"]["verified_file_count"] > 6

    assert result["automatic_dispatch"] is False
    assert result["automatic_fault_binding"] is False
    assert result["p4_recalculation_inside_p5"] is False
    assert result["crosscheck"] is False
    assert result["professional_report"] is False
    assert result["professional_emission"] is False

    expected = (
        "manifest.json",
        "execution_p8d2.json",
        "workspace_v5.html",
        "project_snapshot_p7a.json",
        "project_report_p7c.html",
        "reconstruction_p7b.json",
        "dossier_integrity.json",
    )
    for name in expected:
        assert (root / name).is_file(), name

    verification = dossier_integrity.verificar_indice(root / "dossier_integrity.json")
    assert verification["status"] == "DOSSIER_INTEGRITY_VERIFIED"
    assert verification["ok"] is True
    assert verification["issues"] == []


def test_p10g_reference_generates_complete_workspace_and_reproducible_dossier(tmp_path):
    output = tmp_path / "p10g_reference_dossier"
    result = real_project_dossier.generar_dossier(_manifest(), str(output))

    _assert_ready_dossier(result, output)

    workspace_html = (output / "workspace_v5.html").read_text(encoding="utf-8")
    assert "MCP-P5-PROTECTION-V5" in workspace_html
    assert "MCP-P8E1-P8D2-RESULTS-V5" in workspace_html
    assert "Protection.QF_MV" in workspace_html
    assert "Protection.QF_LV" in workspace_html
    assert "mv_load_bus" in workspace_html
    assert "lv_load_bus" in workspace_html
    assert "ikss_ka" in workspace_html

    execution = json.loads((output / "execution_p8d2.json").read_text(encoding="utf-8"))
    assert execution["execution_status"] == "PROTECTION_EXECUTION_COMPLETED"
    assert len(execution["device_results"]) == 2
    assert all(item["fault_binding_explicit"] is True for item in execution["device_results"])
    assert all(item["automatic_fault_binding"] is False for item in execution["device_results"])
    assert all(item["breaking_capacity"]["status"] == "PASS" for item in execution["device_results"])
    assert all(item["clearing_time"]["status"] == "CLEARING_TIME_READY" for item in execution["device_results"])

    snapshot = json.loads((output / "project_snapshot_p7a.json").read_text(encoding="utf-8"))
    studies = snapshot["payload"]["workspace"]["status"]["studies"]
    for study in (
        "powerflow",
        "flow",
        "voltage_drop",
        "ampacity",
        "iec60909_3ph_targets",
        "iec60909_1ph_ground_targets",
        "protection_tcc",
    ):
        assert study in studies
        assert studies[study]["valid"] is True

    report_html = (output / "project_report_p7c.html").read_text(encoding="utf-8")
    assert "protection_tcc" in report_html
    assert "NO APTO PARA EMISIÓN PROFESIONAL" in report_html

    assert workspace_state.status()["model_revision"] == result["model_revision"]
    assert workspace_state.status()["studies"]["protection_tcc"]["valid"] is True


def test_p10g_reference_repeated_delivery_is_collision_safe_and_preserves_first(tmp_path):
    requested = tmp_path / "p10g_repeatable"
    manifest = _manifest()

    first = real_project_dossier.generar_dossier(manifest, str(requested))
    _assert_ready_dossier(first, requested)

    first_index_before = (requested / "dossier_integrity.json").read_bytes()
    first_manifest_before = (requested / "manifest.json").read_bytes()

    second = real_project_dossier.generar_dossier(manifest, str(requested))
    second_root = tmp_path / "p10g_repeatable_2"

    _assert_ready_dossier(second, second_root)

    assert first["output_directory_collision_avoided"] is False
    assert second["output_directory_collision_avoided"] is True
    assert Path(first["output_directory"]) == requested.resolve()
    assert Path(second["output_directory"]) == second_root.resolve()

    assert first["manifest_sha256"] == second["manifest_sha256"]
    assert (requested / "dossier_integrity.json").read_bytes() == first_index_before
    assert (requested / "manifest.json").read_bytes() == first_manifest_before

    first_verify_after_second = dossier_integrity.verificar_indice(requested / "dossier_integrity.json")
    second_verify = dossier_integrity.verificar_indice(second_root / "dossier_integrity.json")
    assert first_verify_after_second["status"] == "DOSSIER_INTEGRITY_VERIFIED"
    assert second_verify["status"] == "DOSSIER_INTEGRITY_VERIFIED"
    assert first_verify_after_second["ok"] is True
    assert second_verify["ok"] is True


def test_p10g_reference_manifest_remains_non_professional(tmp_path):
    output = tmp_path / "p10g_boundary"
    result = real_project_dossier.generar_dossier(_manifest(), str(output))

    assert result["status"] == "DOSSIER_READY_ENGINEERING_PREVIEW"
    assert result["professional_report"] is False
    assert result["professional_emission"] is False

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["project"]["id"] == "MCP-REF-SUB-01"
    assert "CONTROLLED_REFERENCE_DATA" in manifest["project"]["source_reference"]

    integrity = json.loads((output / "dossier_integrity.json").read_text(encoding="utf-8"))
    context = integrity["payload"]["context"]
    assert context["professional_emission"] is False
    assert context["workspace_version"] == 5
    assert context["p7b_isolation_mode"] == "OPENDSS_NEW_CONTEXT"
