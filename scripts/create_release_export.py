#!/usr/bin/env python3
"""Create a portable, verifiable export package for a known-good MCP release.

The export is generated from an exact Git commit, not from the working tree.
It contains a source ZIP, a Git bundle, a release manifest copy, metadata and
SHA-256 checksums. A CI artifact is staging material, not an independent mirror.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any
import zipfile


EXPORT_SCHEMA = "MCP_ELECTRICO_P11C_RELEASE_EXPORT_V1"
EXPORT_CLASSIFICATION = "EXPORT_STAGING_NOT_INDEPENDENT_MIRROR"
TOOL_VERSION = 1


def _run_git(*args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd is not None else None,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def repository_root() -> Path:
    result = _run_git("rev-parse", "--show-toplevel")
    return Path(result.stdout.strip()).resolve()


def resolve_commit(ref: str, *, cwd: Path | None = None) -> str:
    value = str(ref or "").strip()
    if not value:
        raise ValueError("ref must be non-empty")
    result = _run_git("rev-parse", "--verify", f"{value}^{{commit}}", cwd=cwd)
    resolved = result.stdout.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", resolved):
        raise RuntimeError(f"git returned an invalid commit SHA for {value!r}: {resolved!r}")
    return resolved


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _slug(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("._-")
    return text or "mcp-release"


def _load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "MCP_ELECTRICO_RELEASE_MANIFEST_V1":
        raise ValueError("release manifest schema is not MCP_ELECTRICO_RELEASE_MANIFEST_V1")
    return data


def _ref_exists(root: Path, refname: str) -> bool:
    result = _run_git("show-ref", "--verify", "--quiet", refname, cwd=root, check=False)
    return result.returncode == 0


def _write_checksums(output_dir: Path, names: list[str]) -> Path:
    rows = []
    for name in sorted(names):
        path = output_dir / name
        rows.append(f"{sha256_file(path)}  {name}")
    checksum_path = output_dir / "SHA256SUMS.txt"
    checksum_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return checksum_path


def verify_checksums(output_dir: Path) -> dict[str, Any]:
    checksum_path = output_dir / "SHA256SUMS.txt"
    if not checksum_path.is_file():
        return {"ok": False, "issues": ["SHA256SUMS.txt missing"]}

    issues: list[str] = []
    verified: list[str] = []
    for raw in checksum_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        parts = raw.split("  ", 1)
        if len(parts) != 2:
            issues.append(f"invalid checksum row: {raw}")
            continue
        expected, name = parts
        path = output_dir / name
        if not path.is_file():
            issues.append(f"missing file: {name}")
            continue
        actual = sha256_file(path)
        if actual != expected:
            issues.append(f"SHA-256 mismatch: {name}")
            continue
        verified.append(name)

    return {
        "ok": not issues,
        "verified_files": sorted(verified),
        "issues": issues,
    }


def create_release_export(
    *,
    ref: str,
    expected_sha: str,
    release_manifest: Path,
    output_dir: Path,
    name: str,
) -> dict[str, Any]:
    root = repository_root()
    manifest_path = release_manifest.expanduser().resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(f"release manifest not found: {manifest_path}")

    manifest = _load_manifest(manifest_path)
    expected = str(expected_sha or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", expected):
        raise ValueError("expected_sha must be an exact 40-character commit SHA")

    resolved = resolve_commit(ref, cwd=root)
    if resolved != expected:
        raise ValueError(
            f"release ref mismatch: ref {ref!r} resolves to {resolved}, expected {expected}"
        )
    manifest_sha = str(manifest.get("commit_sha") or "").strip().lower()
    if manifest_sha != expected:
        raise ValueError(
            f"release manifest mismatch: manifest commit_sha={manifest_sha!r}, expected={expected!r}"
        )

    target = output_dir.expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        raise FileExistsError(f"output directory is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)

    safe_name = _slug(name)
    source_name = f"{safe_name}-source.zip"
    bundle_name = f"{safe_name}.bundle"
    manifest_name = "release_manifest.json"
    metadata_name = "export_metadata.json"

    source_path = target / source_name
    bundle_path = target / bundle_name
    manifest_copy = target / manifest_name
    metadata_path = target / metadata_name

    _run_git(
        "archive",
        "--format=zip",
        f"--prefix={safe_name}/",
        f"--output={source_path}",
        resolved,
        cwd=root,
    )

    temp_suffix = expected[:12]
    temp_branch = f"refs/heads/__mcp_export_tmp__/{temp_suffix}"
    temp_tag = f"refs/tags/__mcp_export_tmp__-{temp_suffix}"
    for refname in (temp_branch, temp_tag):
        if _ref_exists(root, refname):
            raise RuntimeError(
                f"temporary export ref already exists: {refname}; clean it before retrying"
            )

    try:
        _run_git("update-ref", temp_branch, expected, cwd=root)
        _run_git("update-ref", temp_tag, expected, cwd=root)
        _run_git(
            "bundle",
            "create",
            str(bundle_path),
            temp_branch,
            temp_tag,
            cwd=root,
        )
        verify_bundle = _run_git("bundle", "verify", str(bundle_path), cwd=root)
    finally:
        _run_git("update-ref", "-d", temp_branch, cwd=root, check=False)
        _run_git("update-ref", "-d", temp_tag, cwd=root, check=False)

    shutil.copyfile(manifest_path, manifest_copy)

    with zipfile.ZipFile(source_path, "r") as archive:
        names = archive.namelist()
    if not names or any(".git/" in entry or entry.endswith("/.git") for entry in names):
        raise RuntimeError("source archive validation failed")
    if not all(entry.startswith(f"{safe_name}/") for entry in names):
        raise RuntimeError("source archive contains an unexpected root path")

    metadata = {
        "schema": EXPORT_SCHEMA,
        "tool_version": TOOL_VERSION,
        "classification": EXPORT_CLASSIFICATION,
        "release_id": manifest.get("release_id"),
        "product_release": manifest.get("product_release"),
        "requested_ref": ref,
        "resolved_commit_sha": resolved,
        "expected_commit_sha": expected,
        "recovery_branch": manifest.get("recovery_branch"),
        "source_archive": source_name,
        "git_bundle": bundle_name,
        "release_manifest": manifest_name,
        "bundle_verify_ok": True,
        "bundle_verify_output": verify_bundle.stderr.strip() or verify_bundle.stdout.strip(),
        "contains_working_tree_untracked_files": False,
        "contains_private_dossiers_by_design": False,
        "independent_mirror_created": False,
        "professional_emission": False,
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    checksum_path = _write_checksums(
        target,
        [source_name, bundle_name, manifest_name, metadata_name],
    )
    checksum_verification = verify_checksums(target)
    if not checksum_verification["ok"]:
        raise RuntimeError(f"export checksum verification failed: {checksum_verification['issues']}")

    return {
        **metadata,
        "output_directory": str(target),
        "checksum_file": checksum_path.name,
        "checksum_verification": checksum_verification,
        "source_entry_count": len(names),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create MCP Electrico stable release export")
    parser.add_argument("--ref", required=True, help="Git ref/commit to export")
    parser.add_argument("--expected-sha", required=True, help="Exact approved 40-char commit SHA")
    parser.add_argument("--release-manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--name", required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = create_release_export(
        ref=args.ref,
        expected_sha=args.expected_sha,
        release_manifest=args.release_manifest,
        output_dir=args.output_dir,
        name=args.name,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
