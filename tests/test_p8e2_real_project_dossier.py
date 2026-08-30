from __future__ import annotations

import json
from pathlib import Path
import runpy

from opendssdirect import dss

from mcp_electrico import real_project_dossier, workspace_state


def _manifest() -> dict:
    fixture = runpy.run_path(str(Path(__file__).with_name("test_p8d2_real_protection_execution.py")))
    return fixture["_manifest"]()


def test_p8e2_generates_workspace_snapshot_reconstruction_and_report_without_destroying_parent(tmp_path):
    manifest = _manifest()
    output = tmp_path / "real_dossier"

    result = real_project_dossier.generar_dossier(manifest, str(output))

    assert result["schema"] == "MCP_ELECTRICO_P8E2_REAL_PROJECT_DOSSIER_V1"
    assert result["status"] == "DOSSIER_READY_ENGINEERING_PREVIEW"
    assert result["p8d2_execution_status"] == "PROTECTION_EXECUTION_COMPLETED"
    assert result["active_circuit_preserved"] is True
    assert result["p7a"]["status"] == "HASH_MATCH"
    assert result["p7b"]["status"] == "RECONSTRUCTED_NETLIST_VERIFIED_WITH_REBIND_REQUIRED"
    assert result["p7b"]["isolated_process"] is True
    assert result["p7b"]["stored_results_promoted_to_current"] is False
    assert result["p7c"]["status"] == "TECHNICAL_REPORT_READY_FOR_PRINT"
    assert result["p7c"]["source_snapshot_sha256"] == result["p7a"]["sha256"]
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
    )
    for name in expected:
        assert (output / name).is_file(), name

    workspace_html = (output / "workspace_v5.html").read_text(encoding="utf-8")
    assert "MCP-P5-PROTECTION-V5" in workspace_html
    assert "MCP-P8E1-P8D2-RESULTS-V5" in workspace_html
    assert "Protection.QF01" in workspace_html
    assert "load_bus" in workspace_html
    assert "ikss_ka" in workspace_html

    snapshot = json.loads((output / "project_snapshot_p7a.json").read_text(encoding="utf-8"))
    studies = snapshot["payload"]["workspace"]["status"]["studies"]
    assert studies["protection_tcc"]["valid"] is True
    assert studies["protection_tcc"]["result"]["schema"] == "MCP_ELECTRICO_P8D2_PROTECTION_RESULTS_V1"
    assert snapshot["hash"]["value"] == result["p7a"]["sha256"]

    reconstruction = json.loads((output / "reconstruction_p7b.json").read_text(encoding="utf-8"))
    assert reconstruction["status"] == "RECONSTRUCTED_NETLIST_VERIFIED_WITH_REBIND_REQUIRED"
    assert reconstruction["roundtrip"]["canonical_netlist_match"] is True
    assert reconstruction["stored_results_promoted_to_current"] is False

    report_html = (output / "project_report_p7c.html").read_text(encoding="utf-8")
    assert "protection_tcc" in report_html
    assert "NO APTO PARA EMISIÓN PROFESIONAL" in report_html
    assert "BROWSER_PRINT" in report_html

    # P7B ocurrió en otro proceso: el proyecto calculado sigue activo y vigente aquí.
    assert str(dss.Circuit.Name() or "")
    assert workspace_state.status()["model_revision"] == result["model_revision"]
    assert workspace_state.status()["studies"]["protection_tcc"]["valid"] is True


def test_p8e2_invalid_fault_binding_blocks_before_creating_dossier(tmp_path):
    manifest = _manifest()
    manifest["protection"].pop("fault_bindings")
    output = tmp_path / "blocked_dossier"

    result = real_project_dossier.generar_dossier(manifest, str(output))

    assert result["status"] == "BLOCKED_BY_P8D2_EXECUTION"
    assert result["artifact_generation_performed"] is False
    assert result["p8d2_execution"]["execution_status"] == "BLOCKED_BY_EXPLICIT_FAULT_BINDING"
    assert result["professional_emission"] is False
    assert not output.exists()
