"""P13E — dossier reproducible para motores y arranque.

El dossier se reproduce exclusivamente desde entradas P13 canónicas. P13D se
ejecuta dos veces en contextos OpenDSS aislados y se exige igualdad SHA-256 de
la proyección de resultados de ingeniería antes de generar la entrega.

No se toma snapshot del circuito DSS global, porque P13B–D deliberadamente no
materializan allí el modelo del estudio.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from . import motor_starting_sequences, motor_starting_static, motor_starting_workspace

SCHEMA = "MCP_ELECTRICO_P13E_MOTOR_STARTING_DOSSIER_V1"
REPLAY_SCHEMA = "MCP_ELECTRICO_P13E_MOTOR_REPLAY_VERIFICATION_V1"
INTEGRITY_SCHEMA = "MCP_ELECTRICO_P13E_MOTOR_DOSSIER_INTEGRITY_V1"

STATUS_READY = "MOTOR_STARTING_DOSSIER_READY"
STATUS_BLOCKED = "MOTOR_STARTING_DOSSIER_BLOCKED_BY_EXECUTION"
STATUS_REPLAY_MISMATCH = "MOTOR_STARTING_DOSSIER_REPLAY_MISMATCH"
STATUS_ARTIFACT_FAILED = "MOTOR_STARTING_DOSSIER_ARTIFACT_FAILED"
REPLAY_MATCH = "MOTOR_STARTING_REPLAY_MATCH"
INTEGRITY_OK = "MOTOR_STARTING_DOSSIER_INTEGRITY_VERIFIED"
INTEGRITY_MISMATCH = "MOTOR_STARTING_DOSSIER_INTEGRITY_MISMATCH"

INDEX_NAME = "motor_dossier_integrity.json"
REQUIRED_TOP_LEVEL = (
    "motor_manifest.json",
    "motor_profile_package.json",
    "motor_sequence_package.json",
    "motor_sequence_execution.json",
    "motor_replay_verification.json",
    "motor_workspace.html",
    "motor_report.html",
    "motor_dossier_manifest.json",
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


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _safe_dir(path: str | Path) -> tuple[Path, bool]:
    requested = Path(path).expanduser().resolve()
    if not requested.exists():
        requested.mkdir(parents=True, exist_ok=False)
        return requested, False
    if requested.is_dir() and not any(requested.iterdir()):
        return requested, False
    index = 2
    while True:
        candidate = requested.with_name(f"{requested.name}_{index}")
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate, True
        index += 1


def _engineering_projection(execution: dict[str, Any]) -> dict[str, Any]:
    """Elimina metadata del contexto padre; conserva resultados eléctricos P13."""
    return {
        "schema": execution.get("schema"),
        "execution_status": execution.get("execution_status"),
        "sequence_count": execution.get("sequence_count"),
        "engine": execution.get("engine"),
        "isolation_mode": execution.get("isolation_mode"),
        "step_isolation": execution.get("step_isolation"),
        "results": deepcopy(execution.get("results") or []),
        "electrical_calculation_performed": execution.get("electrical_calculation_performed"),
        "motor_starting_calculation_performed": execution.get("motor_starting_calculation_performed"),
        "elapsed_time_used_by_solver": execution.get("elapsed_time_used_by_solver"),
        "interpolation_performed": execution.get("interpolation_performed"),
        "dynamic_integration_performed": execution.get("dynamic_integration_performed"),
        "torque_calculation_performed": execution.get("torque_calculation_performed"),
        "automatic_motor_selection": execution.get("automatic_motor_selection"),
        "automatic_start_order": execution.get("automatic_start_order"),
        "automatic_profile_generation": execution.get("automatic_profile_generation"),
        "automatic_starting_current_derivation": execution.get("automatic_starting_current_derivation"),
        "automatic_defaults": execution.get("automatic_defaults"),
        "automatic_dispatch": execution.get("automatic_dispatch"),
        "crosscheck": execution.get("crosscheck"),
        "professional_emission": execution.get("professional_emission"),
    }


def _execution_complete(execution: dict[str, Any]) -> bool:
    results = execution.get("results") or []
    return (
        execution.get("execution_status")
        == motor_starting_sequences.STATUS_COMPLETED
        and bool(results)
        and all(item.get("ok") is True for item in results)
        and execution.get("parent_context_mutated") is False
        and execution.get("parent_workspace_mutated") is False
    )


def _relative_files(root: Path) -> list[Path]:
    index = root / INDEX_NAME
    return sorted(
        (path for path in root.iterdir() if path.is_file() and path != index),
        key=lambda path: path.name,
    )


def _structure_issues(root: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not root.is_dir():
        return [{"code": "P13EINT001", "path": str(root), "message": "No existe el directorio del dossier."}]

    for path in root.iterdir():
        if path.is_symlink():
            issues.append({
                "code": "P13EINT002",
                "path": path.name,
                "message": "El dossier P13E no admite symlinks.",
            })

    for name in REQUIRED_TOP_LEVEL:
        path = root / name
        if not path.is_file() or path.is_symlink():
            issues.append({
                "code": "P13EINT003",
                "path": name,
                "message": "Falta artefacto obligatorio o es symlink.",
            })

    return issues


def _build_integrity(root: Path, context: dict[str, Any]) -> dict[str, Any]:
    issues = _structure_issues(root)
    if issues:
        raise ValueError(f"P13EINT004: estructura incompleta: {issues}")

    files = [
        {
            "path": path.name,
            "size_bytes": path.stat().st_size,
            "sha256": _file_sha256(path),
        }
        for path in _relative_files(root)
    ]
    payload = {
        "schema": INTEGRITY_SCHEMA,
        "hash_algorithm": "sha256",
        "portable_relative_paths": True,
        "self_hash_included": False,
        "symlinks_allowed": False,
        "required_top_level": list(REQUIRED_TOP_LEVEL),
        "file_count": len(files),
        "files": files,
        "context": deepcopy(context),
        "professional_emission": False,
    }
    index = {
        "schema": INTEGRITY_SCHEMA,
        "payload_hash": {"algorithm": "sha256", "value": _digest_json(payload)},
        "payload": payload,
        "professional_emission": False,
    }
    target = root / INDEX_NAME
    _write_json(target, index)
    return {
        "path": str(target),
        "index_file_sha256": _file_sha256(target),
        "verification": verificar_integridad(target),
    }


def verificar_integridad(path: str | Path) -> dict[str, Any]:
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        return {
            "schema": INTEGRITY_SCHEMA,
            "ok": False,
            "status": INTEGRITY_MISMATCH,
            "issues": [{"code": "P13EVER001", "message": "No existe el índice de integridad."}],
            "professional_emission": False,
        }

    root = target.parent
    try:
        index = json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "schema": INTEGRITY_SCHEMA,
            "ok": False,
            "status": INTEGRITY_MISMATCH,
            "issues": [{"code": "P13EVER002", "message": f"Índice ilegible: {exc}"}],
            "professional_emission": False,
        }

    issues: list[dict[str, Any]] = []
    if index.get("schema") != INTEGRITY_SCHEMA:
        issues.append({"code": "P13EVER003", "message": "Schema de integridad no reconocido."})

    payload = index.get("payload")
    expected_hash = (index.get("payload_hash") or {}).get("value")
    if not isinstance(payload, dict) or not expected_hash:
        issues.append({"code": "P13EVER004", "message": "Falta payload/payload_hash."})
        payload = {}
    elif _digest_json(payload) != expected_hash:
        issues.append({"code": "P13EVER005", "message": "El payload del índice fue alterado."})

    issues.extend(_structure_issues(root))

    declared = payload.get("files") if isinstance(payload, dict) else []
    if not isinstance(declared, list):
        issues.append({"code": "P13EVER006", "message": "files debe ser lista."})
        declared = []

    declared_paths: set[str] = set()
    for record in declared:
        if not isinstance(record, dict):
            issues.append({"code": "P13EVER007", "message": "Registro de archivo inválido."})
            continue
        relative = str(record.get("path") or "")
        rel = Path(relative)
        if (
            not relative
            or rel.is_absolute()
            or len(rel.parts) != 1
            or relative == INDEX_NAME
            or ".." in rel.parts
        ):
            issues.append({"code": "P13EVER008", "path": relative, "message": "Ruta insegura."})
            continue
        if relative in declared_paths:
            issues.append({"code": "P13EVER009", "path": relative, "message": "Ruta duplicada."})
            continue
        declared_paths.add(relative)
        actual = root / relative
        if actual.is_symlink() or not actual.is_file():
            issues.append({"code": "P13EVER010", "path": relative, "message": "Archivo ausente o symlink."})
            continue
        if actual.stat().st_size != record.get("size_bytes"):
            issues.append({"code": "P13EVER011", "path": relative, "message": "Tamaño no coincide."})
        if _file_sha256(actual) != record.get("sha256"):
            issues.append({"code": "P13EVER012", "path": relative, "message": "SHA-256 no coincide."})

    actual_paths = {path.name for path in _relative_files(root)}
    if actual_paths != declared_paths:
        issues.append({
            "code": "P13EVER013",
            "message": "El file-set no coincide exactamente con el índice.",
            "missing": sorted(declared_paths - actual_paths),
            "unindexed": sorted(actual_paths - declared_paths),
        })
    if payload.get("file_count") != len(declared_paths):
        issues.append({"code": "P13EVER014", "message": "file_count no coincide."})

    ok = not issues
    return {
        "schema": INTEGRITY_SCHEMA,
        "ok": ok,
        "status": INTEGRITY_OK if ok else INTEGRITY_MISMATCH,
        "issues": issues,
        "payload_sha256": expected_hash,
        "verified_file_count": len(declared_paths),
        "portable_relative_paths": True,
        "professional_emission": False,
    }


def generar_dossier(
    manifest: dict[str, Any],
    profile_package: dict[str, Any],
    sequence_package: dict[str, Any],
    directorio_salida: str = "mcp_electrico_motor_dossier",
) -> dict[str, Any]:
    if not all(isinstance(item, dict) for item in (manifest, profile_package, sequence_package)):
        raise TypeError("manifest, profile_package y sequence_package deben ser dict.")

    manifest_copy = deepcopy(manifest)
    profile_copy = deepcopy(profile_package)
    sequence_copy = deepcopy(sequence_package)
    parent_before = motor_starting_static._parent_signature()

    execution = motor_starting_sequences.ejecutar_secuencias(
        deepcopy(manifest_copy),
        deepcopy(profile_copy),
        deepcopy(sequence_copy),
    )
    if not _execution_complete(execution):
        parent_after = motor_starting_static._parent_signature()
        return {
            "schema": SCHEMA,
            "status": STATUS_BLOCKED,
            "execution": execution,
            "artifact_generation_performed": False,
            "parent_context_mutated": parent_after != parent_before,
            "dynamic_integration_performed": False,
            "professional_report": False,
            "professional_emission": False,
        }

    replay = motor_starting_sequences.ejecutar_secuencias(
        deepcopy(manifest_copy),
        deepcopy(profile_copy),
        deepcopy(sequence_copy),
    )
    if not _execution_complete(replay):
        parent_after = motor_starting_static._parent_signature()
        return {
            "schema": SCHEMA,
            "status": STATUS_REPLAY_MISMATCH,
            "execution": execution,
            "replay_execution": replay,
            "artifact_generation_performed": False,
            "parent_context_mutated": parent_after != parent_before,
            "dynamic_integration_performed": False,
            "professional_report": False,
            "professional_emission": False,
        }

    projection = _engineering_projection(execution)
    replay_projection = _engineering_projection(replay)
    first_hash = _digest_json(projection)
    replay_hash = _digest_json(replay_projection)
    replay_match = first_hash == replay_hash

    parent_after_replay = motor_starting_static._parent_signature()
    if parent_after_replay != parent_before:
        raise RuntimeError(
            "P13E001: execution/replay modificó el contexto DSS/Workspace padre."
        )

    replay_verification = {
        "schema": REPLAY_SCHEMA,
        "status": REPLAY_MATCH if replay_match else STATUS_REPLAY_MISMATCH,
        "match": replay_match,
        "hash_algorithm": "sha256",
        "execution_projection_sha256": first_hash,
        "replay_projection_sha256": replay_hash,
        "projection_scope": "P13D_ENGINEERING_RESULTS_WITHOUT_PARENT_CONTEXT_METADATA",
        "fresh_context_per_step": True,
        "dynamic_integration_performed": False,
        "professional_emission": False,
    }
    if not replay_match:
        return {
            "schema": SCHEMA,
            "status": STATUS_REPLAY_MISMATCH,
            "execution": execution,
            "replay_verification": replay_verification,
            "artifact_generation_performed": False,
            "parent_context_mutated": False,
            "professional_report": False,
            "professional_emission": False,
        }

    requested = Path(directorio_salida).expanduser().resolve()
    target, collision_avoided = _safe_dir(requested)
    paths = {
        "manifest": target / "motor_manifest.json",
        "profiles": target / "motor_profile_package.json",
        "sequences": target / "motor_sequence_package.json",
        "execution": target / "motor_sequence_execution.json",
        "replay": target / "motor_replay_verification.json",
        "workspace": target / "motor_workspace.html",
        "report": target / "motor_report.html",
        "dossier_manifest": target / "motor_dossier_manifest.json",
        "integrity": target / INDEX_NAME,
    }

    try:
        _write_json(paths["manifest"], manifest_copy)
        _write_json(paths["profiles"], profile_copy)
        _write_json(paths["sequences"], sequence_copy)
        _write_json(paths["execution"], execution)
        _write_json(paths["replay"], replay_verification)

        workspace_result = motor_starting_workspace.escribir_workspace(
            paths["workspace"],
            manifest_copy,
            profile_copy,
            sequence_copy,
            execution,
        )
        report_html = motor_starting_workspace.construir_html(
            manifest_copy,
            profile_copy,
            sequence_copy,
            execution,
            title="Reporte reproducible · Motores y arranque P13E",
        )
        paths["report"].write_text(report_html, encoding="utf-8")

        dossier_manifest = {
            "schema": SCHEMA,
            "project_id": (manifest_copy.get("project") or {}).get("id"),
            "input_hashes": {
                "manifest_sha256": _digest_json(manifest_copy),
                "profile_package_sha256": _digest_json(profile_copy),
                "sequence_package_sha256": _digest_json(sequence_copy),
            },
            "execution": {
                "schema": execution.get("schema"),
                "projection_sha256": first_hash,
                "replay_status": replay_verification["status"],
                "sequence_count": execution.get("sequence_count"),
            },
            "workspace_schema": motor_starting_workspace.SCHEMA,
            "browser_engineering_calculation": False,
            "dynamic_integration_performed": False,
            "automatic_motor_selection": False,
            "automatic_start_order": False,
            "professional_report": False,
            "professional_emission": False,
        }
        _write_json(paths["dossier_manifest"], dossier_manifest)

        context = {
            "project_id": dossier_manifest["project_id"],
            **dossier_manifest["input_hashes"],
            "execution_projection_sha256": first_hash,
            "replay_status": replay_verification["status"],
            "workspace_schema": motor_starting_workspace.SCHEMA,
            "professional_emission": False,
        }
        integrity = _build_integrity(target, context)
        verification = integrity["verification"]
        if verification.get("status") != INTEGRITY_OK:
            raise RuntimeError(f"P13E002: integridad no verificó: {verification}")

        parent_after_artifacts = motor_starting_static._parent_signature()
        if parent_after_artifacts != parent_before:
            raise RuntimeError("P13E003: generación de artefactos modificó el contexto padre.")

        return {
            "schema": SCHEMA,
            "status": STATUS_READY,
            "requested_output_directory": str(requested),
            "output_directory": str(target),
            "output_directory_collision_avoided": collision_avoided,
            "execution_status": execution.get("execution_status"),
            "sequence_results": [
                {
                    "sequence_id": item.get("sequence_id"),
                    "status": item.get("status"),
                    "ok": item.get("ok"),
                }
                for item in execution.get("results") or []
            ],
            "replay": replay_verification,
            "workspace": workspace_result,
            "integrity": {
                "status": verification.get("status"),
                "ok": verification.get("ok"),
                "index_path": str(paths["integrity"]),
                "payload_sha256": verification.get("payload_sha256"),
                "index_file_sha256": integrity.get("index_file_sha256"),
            },
            "parent_context_mutated": False,
            "artifact_generation_performed": True,
            "browser_engineering_calculation": False,
            "dynamic_integration_performed": False,
            "automatic_motor_selection": False,
            "automatic_start_order": False,
            "professional_report": False,
            "professional_emission": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": STATUS_ARTIFACT_FAILED,
            "output_directory": str(target),
            "error": f"{type(exc).__name__}: {exc}",
            "artifact_generation_performed": True,
            "professional_report": False,
            "professional_emission": False,
        }
