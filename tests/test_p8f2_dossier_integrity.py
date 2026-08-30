from __future__ import annotations

import json
from pathlib import Path
import runpy
import shutil

import pytest

from mcp_electrico import (
    dossier_integrity,
    real_project_dossier,
    real_project_dossier_tools,
)


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def _manifest() -> dict:
    fixture = runpy.run_path(str(Path(__file__).with_name("test_p8d2_real_protection_execution.py")))
    return fixture["_manifest"]()


@pytest.fixture(scope="module")
def pristine_dossier(tmp_path_factory):
    root = tmp_path_factory.mktemp("p8f2") / "real_dossier"
    result = real_project_dossier.generar_dossier(_manifest(), str(root))
    assert result["status"] == "DOSSIER_READY_ENGINEERING_PREVIEW"
    return root, result


def test_p8f2_ready_requires_verified_exact_artifact_index(pristine_dossier):
    root, result = pristine_dossier

    assert result["integrity"]["status"] == "DOSSIER_INTEGRITY_VERIFIED"
    assert result["integrity"]["ok"] is True
    assert result["integrity"]["portable_relative_paths"] is True
    assert result["integrity"]["self_hash_included"] is False
    assert result["integrity"]["verified_file_count"] > 6

    index_path = root / "dossier_integrity.json"
    assert index_path.is_file()
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert index["schema"] == "MCP_ELECTRICO_P8F2_DOSSIER_INTEGRITY_V1"
    assert index["payload"]["context"]["manifest_sha256"] == result["manifest_sha256"]
    assert index["payload"]["context"]["p7a_payload_sha256"] == result["p7a"]["sha256"]
    assert index["payload"]["context"]["p7c_report_sha256"] == result["p7c"]["report_sha256"]
    assert index["payload"]["symlinks_allowed"] is False
    assert "dossier_integrity.json" not in {item["path"] for item in index["payload"]["files"]}

    verification = dossier_integrity.verificar_indice(index_path)
    assert verification["ok"] is True
    assert verification["status"] == "DOSSIER_INTEGRITY_VERIFIED"
    assert verification["symlinks_allowed"] is False
    assert verification["issues"] == []


def test_p8f2_index_is_portable_after_copy(pristine_dossier, tmp_path):
    root, _result = pristine_dossier
    copied = tmp_path / "copied_elsewhere_with_new_name"
    shutil.copytree(root, copied)

    verification = dossier_integrity.verificar_indice(copied / "dossier_integrity.json")

    assert verification["ok"] is True
    assert verification["status"] == "DOSSIER_INTEGRITY_VERIFIED"
    assert verification["portable_relative_paths"] is True


def test_p8f2_detects_modified_indexed_artifact(pristine_dossier, tmp_path):
    root, _result = pristine_dossier
    copied = tmp_path / "tampered"
    shutil.copytree(root, copied)
    target = copied / "execution_p8d2.json"
    target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    verification = dossier_integrity.verificar_indice(copied / "dossier_integrity.json")

    assert verification["ok"] is False
    assert verification["status"] == "DOSSIER_INTEGRITY_MISMATCH"
    assert any(
        issue.get("path") == "execution_p8d2.json" and issue["code"] in {"P8F2V011", "P8F2V012"}
        for issue in verification["issues"]
    )


def test_p8f2_detects_unindexed_extra_file(pristine_dossier, tmp_path):
    root, _result = pristine_dossier
    copied = tmp_path / "extra-file"
    shutil.copytree(root, copied)
    (copied / "untracked_note.txt").write_text("not part of frozen dossier", encoding="utf-8")

    verification = dossier_integrity.verificar_indice(copied / "dossier_integrity.json")

    assert verification["ok"] is False
    issue = next(item for item in verification["issues"] if item["code"] == "P8F2V013")
    assert "untracked_note.txt" in issue["unindexed_files"]


def test_p8f2_nested_file_named_like_index_is_not_silently_ignored(pristine_dossier, tmp_path):
    root, _result = pristine_dossier
    copied = tmp_path / "nested-index-name"
    shutil.copytree(root, copied)
    nested = copied / "p7a_netlist" / "dossier_integrity.json"
    nested.write_text("nested extra bytes", encoding="utf-8")

    verification = dossier_integrity.verificar_indice(copied / "dossier_integrity.json")

    assert verification["ok"] is False
    issue = next(item for item in verification["issues"] if item["code"] == "P8F2V013")
    assert "p7a_netlist/dossier_integrity.json" in issue["unindexed_files"]


def test_p8f2_rejects_symlinks_in_frozen_package(pristine_dossier, tmp_path):
    root, _result = pristine_dossier
    copied = tmp_path / "symlinked"
    shutil.copytree(root, copied)
    outside = tmp_path / "outside.txt"
    outside.write_text("external bytes", encoding="utf-8")
    link = copied / "p7a_netlist" / "external-link.txt"
    link.symlink_to(outside)

    verification = dossier_integrity.verificar_indice(copied / "dossier_integrity.json")

    assert verification["ok"] is False
    assert any(
        issue.get("code") == "P8F2S004" and issue.get("path") == "p7a_netlist/external-link.txt"
        for issue in verification["issues"]
    )


def test_p8f2_detects_missing_required_artifact(pristine_dossier, tmp_path):
    root, _result = pristine_dossier
    copied = tmp_path / "missing-file"
    shutil.copytree(root, copied)
    (copied / "project_report_p7c.html").unlink()

    verification = dossier_integrity.verificar_indice(copied / "dossier_integrity.json")

    assert verification["ok"] is False
    assert any(
        issue.get("path") == "project_report_p7c.html" and issue["code"] in {"P8F2S001", "P8F2V010"}
        for issue in verification["issues"]
    )


def test_p8f2_integrity_verifier_is_exposed_through_same_real_pilot_registry(pristine_dossier):
    root, _result = pristine_dossier
    mcp = FakeMCP()
    real_project_dossier_tools.register(mcp)

    assert "obtener_contrato_p8f2_integridad_dossier" in mcp.tools
    assert "verificar_integridad_dossier_real" in mcp.tools
    contract = mcp.tools["obtener_contrato_p8f2_integridad_dossier"]()
    assert contract["integrity_schema"] == "MCP_ELECTRICO_P8F2_DOSSIER_INTEGRITY_V1"
    assert contract["exact_file_set_required"] is True
    assert contract["portable_relative_paths"] is True
    assert contract["professional_emission"] is False

    verification = mcp.tools["verificar_integridad_dossier_real"](
        str(root / "dossier_integrity.json")
    )
    assert verification["status"] == "DOSSIER_INTEGRITY_VERIFIED"
