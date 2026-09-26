from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_release_export.py"
MANIFEST = ROOT / "releases" / "mcp_electrico_0_9_reference_validated.json"
RELEASE_SHA = "5228e358cf0716dc963f109a15b9e1a2d309f635"
EXPORT_NAME = "mcp_electrico_0_9_reference_validated"


def _module():
    spec = importlib.util.spec_from_file_location("p11c_export", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _head_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip().lower()


def _manifest_for_sha(tmp_path: Path, sha: str) -> Path:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    data["release_id"] = "P11C_TEST_HEAD"
    data["commit_sha"] = sha
    data["recovery_branch"] = "TEST_HEAD_ONLY"
    path = tmp_path / "test_release_manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_p11c_canonical_manifest_records_exact_stable_release_sha():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["release_id"] == "MCP_ELECTRICO_0_9_REFERENCE_VALIDATED"
    assert data["commit_sha"] == RELEASE_SHA
    assert data["recovery_branch"] == "stable/0.9-reference-validated"


def test_p11c_export_builder_verifies_exact_available_commit(tmp_path: Path):
    module = _module()
    head = _head_sha()
    manifest = _manifest_for_sha(tmp_path, head)
    output = tmp_path / "release_export"

    result = module.create_release_export(
        ref=head,
        expected_sha=head,
        release_manifest=manifest,
        output_dir=output,
        name=EXPORT_NAME,
    )

    assert result["schema"] == "MCP_ELECTRICO_P11C_RELEASE_EXPORT_V1"
    assert result["classification"] == "EXPORT_STAGING_NOT_INDEPENDENT_MIRROR"
    assert result["resolved_commit_sha"] == head
    assert result["expected_commit_sha"] == head
    assert result["bundle_verify_ok"] is True
    assert result["checksum_verification"]["ok"] is True
    assert result["independent_mirror_created"] is False
    assert result["professional_emission"] is False

    expected_files = {
        f"{EXPORT_NAME}-source.zip",
        f"{EXPORT_NAME}.bundle",
        "release_manifest.json",
        "export_metadata.json",
        "SHA256SUMS.txt",
    }
    assert {item.name for item in output.iterdir()} == expected_files

    copied_manifest = json.loads((output / "release_manifest.json").read_text(encoding="utf-8"))
    assert copied_manifest["commit_sha"] == head

    metadata = json.loads((output / "export_metadata.json").read_text(encoding="utf-8"))
    assert metadata["contains_working_tree_untracked_files"] is False
    assert metadata["contains_private_dossiers_by_design"] is False

    verification = module.verify_checksums(output)
    assert verification["ok"] is True
    assert set(verification["verified_files"]) == expected_files - {"SHA256SUMS.txt"}

    bundle = output / f"{EXPORT_NAME}.bundle"
    check = subprocess.run(
        ["git", "bundle", "verify", str(bundle)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert check.returncode == 0


def test_p11c_source_zip_contains_only_selected_git_tree(tmp_path: Path):
    module = _module()
    head = _head_sha()
    manifest = _manifest_for_sha(tmp_path, head)
    output = tmp_path / "release_export"

    module.create_release_export(
        ref=head,
        expected_sha=head,
        release_manifest=manifest,
        output_dir=output,
        name=EXPORT_NAME,
    )

    source_zip = output / f"{EXPORT_NAME}-source.zip"
    with zipfile.ZipFile(source_zip, "r") as archive:
        names = archive.namelist()

    assert names
    assert all(name.startswith(f"{EXPORT_NAME}/") for name in names)
    assert not any("/.git/" in name or name.endswith("/.git") for name in names)
    assert not any(name.endswith(".env") for name in names)
    assert f"{EXPORT_NAME}/server.py" in names
    assert f"{EXPORT_NAME}/mcp_electrico/real_project_dossier.py" in names


def test_p11c_ref_mismatch_fails_before_export(tmp_path: Path):
    module = _module()
    head = _head_sha()
    manifest = _manifest_for_sha(tmp_path, head)
    wrong_sha = "0" * 40

    with pytest.raises(ValueError, match="release ref mismatch"):
        module.create_release_export(
            ref=head,
            expected_sha=wrong_sha,
            release_manifest=manifest,
            output_dir=tmp_path / "must_not_exist",
            name=EXPORT_NAME,
        )

    assert not (tmp_path / "must_not_exist").exists()


def test_p11c_manifest_sha_is_also_required_to_match(tmp_path: Path):
    module = _module()
    head = _head_sha()
    altered = json.loads(MANIFEST.read_text(encoding="utf-8"))
    altered["commit_sha"] = "1" * 40
    altered_path = tmp_path / "altered_manifest.json"
    altered_path.write_text(json.dumps(altered), encoding="utf-8")

    with pytest.raises(ValueError, match="release manifest mismatch"):
        module.create_release_export(
            ref=head,
            expected_sha=head,
            release_manifest=altered_path,
            output_dir=tmp_path / "must_not_exist",
            name=EXPORT_NAME,
        )

    assert not (tmp_path / "must_not_exist").exists()
