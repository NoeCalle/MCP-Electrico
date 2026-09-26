from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
EXPORT_SCRIPT = ROOT / "scripts" / "create_release_export.py"
RESTORE_SCRIPT = ROOT / "scripts" / "restore_release_bundle.py"
MANIFEST = ROOT / "releases" / "mcp_electrico_0_9_reference_validated.json"
RELEASE_SHA = "5228e358cf0716dc963f109a15b9e1a2d309f635"
EXPORT_NAME = "mcp_electrico_0_9_reference_validated"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _require_full_history() -> None:
    result = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.stdout.strip().lower() == "true":
        pytest.skip("P11D restore test requires fetch-depth: 0; dedicated P11D CI provides it")


def _build_export(tmp_path: Path) -> Path:
    exporter = _load(EXPORT_SCRIPT, "p11c_export_for_p11d")
    output = tmp_path / "release_export"
    exporter.create_release_export(
        ref=RELEASE_SHA,
        expected_sha=RELEASE_SHA,
        release_manifest=MANIFEST,
        output_dir=output,
        name=EXPORT_NAME,
    )
    return output


def test_p11d_restore_contract_schema_is_stable():
    restore = _load(RESTORE_SCRIPT, "p11d_restore_contract")
    assert restore.RESTORE_SCHEMA == "MCP_ELECTRICO_P11D_CLEAN_RESTORE_V1"


def test_p11d_clean_restore_recovers_exact_release_without_remote(tmp_path: Path):
    _require_full_history()
    restore = _load(RESTORE_SCRIPT, "p11d_restore")
    export = _build_export(tmp_path)
    target = tmp_path / "restored"

    result = restore.restore_release_bundle(
        bundle=export / f"{EXPORT_NAME}.bundle",
        metadata=export / "export_metadata.json",
        checksum_file=export / "SHA256SUMS.txt",
        output_dir=target,
    )

    assert result["schema"] == "MCP_ELECTRICO_P11D_CLEAN_RESTORE_V1"
    assert result["status"] == "CLEAN_RESTORE_VERIFIED"
    assert result["expected_commit_sha"] == RELEASE_SHA
    assert result["restored_commit_sha"] == RELEASE_SHA
    assert result["target_branch"] == "main"
    assert result["checksum_verification"]["ok"] is True
    assert result["bundle_verify_ok"] is True
    assert result["working_tree_clean"] is True
    assert result["remote_count"] == 0
    assert result["independent_mirror_created"] is False
    assert result["professional_emission"] is False

    assert (target / "server.py").is_file()
    assert (target / "examples" / "p10_reference_substation_stage5.json").is_file()
    assert (target / "tests" / "test_p10g_reference_dossier.py").is_file()

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=target,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    assert head == RELEASE_SHA

    remotes = subprocess.run(
        ["git", "remote"],
        cwd=target,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    assert remotes == ""


def test_p11d_restore_refuses_tampered_export(tmp_path: Path):
    _require_full_history()
    restore = _load(RESTORE_SCRIPT, "p11d_restore_tamper")
    export = _build_export(tmp_path)
    manifest_copy = export / "release_manifest.json"
    manifest_copy.write_text(
        manifest_copy.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    target = tmp_path / "must_not_restore"
    with pytest.raises(ValueError, match="checksum verification failed"):
        restore.restore_release_bundle(
            bundle=export / f"{EXPORT_NAME}.bundle",
            metadata=export / "export_metadata.json",
            checksum_file=export / "SHA256SUMS.txt",
            output_dir=target,
        )

    assert not target.exists()


def test_p11d_canonical_release_still_points_to_p10g():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["commit_sha"] == RELEASE_SHA
    assert manifest["validation"]["p10"] == "CLOSED"
    assert manifest["validation"]["reference_validation"] == "PASSED"
