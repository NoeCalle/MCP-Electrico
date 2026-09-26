#!/usr/bin/env python3
"""Restore a clean MCP Eléctrico repository from a P11C release bundle."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from typing import Any


RESTORE_SCHEMA = "MCP_ELECTRICO_P11D_CLEAN_RESTORE_V1"


def _run_git(
    *args: str,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd is not None else None,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksum_file(export_dir: Path, checksum_file: Path) -> dict[str, Any]:
    issues: list[str] = []
    verified: list[str] = []

    for raw in checksum_file.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        parts = raw.split("  ", 1)
        if len(parts) != 2:
            issues.append(f"invalid checksum row: {raw}")
            continue
        expected, relative = parts
        path = export_dir / relative
        if not path.is_file():
            issues.append(f"missing export file: {relative}")
            continue
        actual = _sha256_file(path)
        if actual != expected:
            issues.append(f"SHA-256 mismatch: {relative}")
            continue
        verified.append(relative)

    return {
        "ok": not issues,
        "verified_files": sorted(verified),
        "issues": issues,
    }


def restore_release_bundle(
    *,
    bundle: Path,
    metadata: Path,
    checksum_file: Path,
    output_dir: Path,
    target_branch: str = "main",
) -> dict[str, Any]:
    bundle_path = bundle.expanduser().resolve()
    metadata_path = metadata.expanduser().resolve()
    checksum_path = checksum_file.expanduser().resolve()

    for path in (bundle_path, metadata_path, checksum_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    export_dir = bundle_path.parent
    if metadata_path.parent != export_dir or checksum_path.parent != export_dir:
        raise ValueError("bundle, metadata and checksum file must belong to the same export directory")

    meta = json.loads(metadata_path.read_text(encoding="utf-8"))
    if meta.get("schema") != "MCP_ELECTRICO_P11C_RELEASE_EXPORT_V1":
        raise ValueError("unsupported P11C export metadata schema")
    expected = str(meta.get("expected_commit_sha") or "").strip().lower()
    resolved = str(meta.get("resolved_commit_sha") or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", expected):
        raise ValueError("export metadata expected_commit_sha is invalid")
    if resolved != expected:
        raise ValueError("export metadata resolved/expected SHA mismatch")
    if meta.get("bundle_verify_ok") is not True:
        raise ValueError("export metadata does not declare a verified bundle")

    checksums = verify_checksum_file(export_dir, checksum_path)
    if not checksums["ok"]:
        raise ValueError(f"export checksum verification failed: {checksums['issues']}")

    target = output_dir.expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        raise FileExistsError(f"restore directory is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)

    _run_git("init", cwd=target)
    bundle_verification = _run_git("bundle", "verify", str(bundle_path), cwd=target)

    source_ref = f"refs/heads/__mcp_export_tmp__/{expected[:12]}"
    target_ref = f"refs/heads/{target_branch}"
    _run_git(
        "fetch",
        str(bundle_path),
        f"{source_ref}:{target_ref}",
        cwd=target,
    )
    _run_git("checkout", target_branch, cwd=target)

    head = _run_git("rev-parse", "HEAD", cwd=target).stdout.strip().lower()
    if head != expected:
        raise RuntimeError(f"restored HEAD mismatch: {head} != {expected}")

    status = _run_git("status", "--porcelain", cwd=target).stdout.strip()
    if status:
        raise RuntimeError(f"restored working tree is not clean: {status}")

    remotes = [
        line.strip()
        for line in _run_git("remote", cwd=target).stdout.splitlines()
        if line.strip()
    ]
    if remotes:
        raise RuntimeError(f"clean restore unexpectedly contains remotes: {remotes}")

    return {
        "schema": RESTORE_SCHEMA,
        "status": "CLEAN_RESTORE_VERIFIED",
        "release_id": meta.get("release_id"),
        "expected_commit_sha": expected,
        "restored_commit_sha": head,
        "target_branch": target_branch,
        "source_bundle": bundle_path.name,
        "checksum_verification": checksums,
        "bundle_verify_ok": True,
        "bundle_verify_output": (
            bundle_verification.stderr.strip() or bundle_verification.stdout.strip()
        ),
        "working_tree_clean": True,
        "remote_count": 0,
        "independent_mirror_created": False,
        "professional_emission": False,
        "output_directory": str(target),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Restore MCP Electrico from a P11C Git bundle")
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--checksums", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--target-branch", default="main")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = restore_release_bundle(
        bundle=args.bundle,
        metadata=args.metadata,
        checksum_file=args.checksums,
        output_dir=args.output_dir,
        target_branch=args.target_branch,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
