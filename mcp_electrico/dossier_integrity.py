"""P8F2 — integridad portable del dossier real P8E2.

El índice cubre por SHA-256 todos los archivos del dossier salvo el propio
índice raíz. No contiene rutas absolutas ni timestamps; puede verificarse
después de copiar el directorio completo a otra ubicación. Los symlinks se
rechazan para impedir que el inventario siga contenido fuera del dossier.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

SCHEMA = "MCP_ELECTRICO_P8F2_DOSSIER_INTEGRITY_V1"
INDEX_NAME = "dossier_integrity.json"
STATUS_VERIFIED = "DOSSIER_INTEGRITY_VERIFIED"
STATUS_MISMATCH = "DOSSIER_INTEGRITY_MISMATCH"

REQUIRED_TOP_LEVEL = (
    "manifest.json",
    "execution_p8d2.json",
    "workspace_v5.html",
    "project_snapshot_p7a.json",
    "reconstruction_p7b.json",
    "project_report_p7c.html",
)
REQUIRED_DIRECTORIES = (
    "p7a_netlist",
    "p7b_reconstructed",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest_json(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _relative_files(root: Path) -> list[Path]:
    root_index = root / INDEX_NAME
    return sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file() and path != root_index
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def _symlink_issues(root: Path) -> list[dict[str, Any]]:
    issues = []
    for path in root.rglob("*"):
        if path.is_symlink():
            issues.append(
                {
                    "code": "P8F2S004",
                    "path": path.relative_to(root).as_posix(),
                    "message": "El dossier no admite symlinks; todos los bytes deben residir dentro del paquete.",
                }
            )
    return issues


def _validate_required_structure(root: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = _symlink_issues(root)
    for name in REQUIRED_TOP_LEVEL:
        path = root / name
        if not path.is_file():
            issues.append({"code": "P8F2S001", "path": name, "message": "Falta artefacto obligatorio del dossier."})
    for name in REQUIRED_DIRECTORIES:
        path = root / name
        if not path.is_dir():
            issues.append({"code": "P8F2S002", "path": name, "message": "Falta directorio obligatorio del dossier."})
            continue
        if not any(item.is_file() for item in path.rglob("*") if not item.is_symlink()):
            issues.append({"code": "P8F2S003", "path": name, "message": "El directorio obligatorio no contiene archivos propios."})
    return issues


def construir_indice(
    directorio_dossier: str | Path,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construye y escribe el índice SHA-256 del dossier completo."""
    root = Path(directorio_dossier).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("P8F2I001: directorio_dossier no existe o no es directorio.")

    structure_issues = _validate_required_structure(root)
    if structure_issues:
        raise ValueError(f"P8F2I002: estructura de dossier incompleta o insegura: {structure_issues}")

    files = _relative_files(root)
    records = []
    for path in files:
        relative = path.relative_to(root).as_posix()
        records.append(
            {
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": _file_sha256(path),
            }
        )

    payload = {
        "schema": SCHEMA,
        "hash_algorithm": "sha256",
        "portable_relative_paths": True,
        "self_hash_included": False,
        "symlinks_allowed": False,
        "required_top_level": list(REQUIRED_TOP_LEVEL),
        "required_directories": list(REQUIRED_DIRECTORIES),
        "file_count": len(records),
        "files": records,
        "context": deepcopy(context or {}),
        "professional_emission": False,
    }
    index = {
        "schema": SCHEMA,
        "payload_hash": {
            "algorithm": "sha256",
            "value": _digest_json(payload),
        },
        "payload": payload,
        "professional_emission": False,
    }
    target = root / INDEX_NAME
    target.write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    return {
        "index": index,
        "path": str(target),
        "index_file_sha256": _file_sha256(target),
        "verification": verificar_indice(target),
        "professional_emission": False,
    }


def verificar_indice(ruta_indice: str | Path) -> dict[str, Any]:
    """Verifica hash del índice, estructura y conjunto exacto de archivos."""
    target = Path(ruta_indice).expanduser().resolve()
    issues: list[dict[str, Any]] = []
    if not target.is_file():
        return {
            "schema": SCHEMA,
            "ok": False,
            "status": STATUS_MISMATCH,
            "issues": [{"code": "P8F2V001", "message": "No existe dossier_integrity.json."}],
            "professional_emission": False,
        }

    root = target.parent
    try:
        index = json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "ok": False,
            "status": STATUS_MISMATCH,
            "issues": [{"code": "P8F2V002", "message": f"Índice JSON ilegible: {exc}"}],
            "professional_emission": False,
        }

    if index.get("schema") != SCHEMA:
        issues.append({"code": "P8F2V003", "message": "Schema de integridad no reconocido."})
    payload = index.get("payload")
    expected_payload_hash = ((index.get("payload_hash") or {}).get("value"))
    if not isinstance(payload, dict) or not expected_payload_hash:
        issues.append({"code": "P8F2V004", "message": "Falta payload o payload_hash del índice."})
        payload = {}
    elif _digest_json(payload) != expected_payload_hash:
        issues.append({"code": "P8F2V005", "message": "El payload del índice fue alterado."})

    structure_issues = _validate_required_structure(root)
    issues.extend(structure_issues)

    declared_records = payload.get("files") if isinstance(payload, dict) else []
    if not isinstance(declared_records, list):
        declared_records = []
        issues.append({"code": "P8F2V006", "message": "files debe ser una lista."})

    declared_paths: set[str] = set()
    for record in declared_records:
        if not isinstance(record, dict):
            issues.append({"code": "P8F2V007", "message": "Registro de archivo inválido."})
            continue
        relative = str(record.get("path") or "")
        rel_path = Path(relative)
        if not relative or rel_path.is_absolute() or ".." in rel_path.parts or relative == INDEX_NAME:
            issues.append({"code": "P8F2V008", "path": relative, "message": "Ruta relativa insegura o inválida."})
            continue
        if relative in declared_paths:
            issues.append({"code": "P8F2V009", "path": relative, "message": "Ruta duplicada en el índice."})
            continue
        declared_paths.add(relative)
        path = root / rel_path
        if path.is_symlink():
            issues.append({"code": "P8F2V015", "path": relative, "message": "Archivo indexado convertido en symlink."})
            continue
        if not path.is_file():
            issues.append({"code": "P8F2V010", "path": relative, "message": "Archivo indexado ausente."})
            continue
        actual_size = path.stat().st_size
        actual_sha = _file_sha256(path)
        if actual_size != record.get("size_bytes"):
            issues.append({"code": "P8F2V011", "path": relative, "message": "Tamaño de archivo no coincide."})
        if actual_sha != record.get("sha256"):
            issues.append({"code": "P8F2V012", "path": relative, "message": "SHA-256 de archivo no coincide."})

    actual_paths = {path.relative_to(root).as_posix() for path in _relative_files(root)}
    if actual_paths != declared_paths:
        issues.append(
            {
                "code": "P8F2V013",
                "message": "El conjunto actual de archivos no coincide exactamente con el índice.",
                "missing_from_disk": sorted(declared_paths - actual_paths),
                "unindexed_files": sorted(actual_paths - declared_paths),
            }
        )

    expected_count = payload.get("file_count") if isinstance(payload, dict) else None
    if expected_count != len(declared_paths):
        issues.append({"code": "P8F2V014", "message": "file_count no coincide con el índice declarado."})

    ok = not issues
    return {
        "schema": SCHEMA,
        "ok": ok,
        "status": STATUS_VERIFIED if ok else STATUS_MISMATCH,
        "payload_sha256": expected_payload_hash,
        "verified_file_count": len(declared_paths),
        "issues": issues,
        "portable_relative_paths": True,
        "symlinks_allowed": False,
        "professional_emission": False,
    }
