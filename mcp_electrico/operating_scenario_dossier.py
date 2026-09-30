"""P12F — dossier reproducible para escenarios operativos.

El dossier P12 es aditivo y no modifica el contrato P8/P11 congelado. Congela
manifiesto, paquete de escenarios, resultados, Workspace estático, snapshot P7A
y reconstrucción P7B. Un resultado de escenario FAIL es válido; solo se bloquea
si la ejecución no terminó o la restauración del modelo no fue verificable.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from opendssdirect import dss

from . import (
    operating_scenario_workspace,
    operating_scenarios,
    project_reconstruction,
    project_snapshot,
    workspace_state,
)

SCHEMA = "MCP_ELECTRICO_P12F_SCENARIO_DOSSIER_V1"
INTEGRITY_SCHEMA = "MCP_ELECTRICO_P12F_SCENARIO_DOSSIER_INTEGRITY_V1"
STATUS_READY = "SCENARIO_DOSSIER_READY"
STATUS_BLOCKED = "SCENARIO_DOSSIER_BLOCKED_BY_EXECUTION"
STATUS_FAILED = "SCENARIO_DOSSIER_ARTIFACT_FAILED"
INTEGRITY_OK = "SCENARIO_DOSSIER_INTEGRITY_VERIFIED"
INTEGRITY_MISMATCH = "SCENARIO_DOSSIER_INTEGRITY_MISMATCH"
INDEX_NAME = "scenario_dossier_integrity.json"
P7B_OK = "RECONSTRUCTED_NETLIST_VERIFIED_WITH_REBIND_REQUIRED"

REQUIRED_TOP_LEVEL = (
    "electrical_manifest.json",
    "scenario_package.json",
    "scenario_execution.json",
    "scenario_workspace.html",
    "scenario_report.html",
    "base_snapshot_p7a.json",
    "base_reconstruction_p7b.json",
)
REQUIRED_DIRECTORIES = ("p7a_netlist", "p7b_reconstructed")


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


def _safe_dir(path: str | Path) -> Path:
    requested = Path(path).expanduser().resolve()
    if not requested.exists():
        requested.mkdir(parents=True, exist_ok=False)
        return requested
    if requested.is_dir() and not any(requested.iterdir()):
        return requested
    index = 2
    while True:
        candidate = requested.with_name(f"{requested.name}_{index}")
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        index += 1


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )


def _relative_files(root: Path) -> list[Path]:
    index = root / INDEX_NAME
    return sorted(
        (path for path in root.rglob("*") if path.is_file() and path != index),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def _structure_issues(root: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            issues.append({
                "code": "P12FINT001",
                "path": path.relative_to(root).as_posix(),
                "message": "El dossier P12 no admite symlinks.",
            })
    for name in REQUIRED_TOP_LEVEL:
        if not (root / name).is_file():
            issues.append({
                "code": "P12FINT002",
                "path": name,
                "message": "Falta artefacto obligatorio del dossier de escenarios.",
            })
    for name in REQUIRED_DIRECTORIES:
        directory = root / name
        if not directory.is_dir():
            issues.append({
                "code": "P12FINT003",
                "path": name,
                "message": "Falta directorio obligatorio del dossier de escenarios.",
            })
        elif not any(path.is_file() for path in directory.rglob("*")):
            issues.append({
                "code": "P12FINT004",
                "path": name,
                "message": "El directorio obligatorio está vacío.",
            })
    return issues


def _build_integrity(root: Path, context: dict[str, Any]) -> dict[str, Any]:
    issues = _structure_issues(root)
    if issues:
        raise ValueError(f"P12FINT005: estructura incompleta: {issues}")

    records = [
        {
            "path": path.relative_to(root).as_posix(),
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
        "required_directories": list(REQUIRED_DIRECTORIES),
        "file_count": len(records),
        "files": records,
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
            "issues": [{"code": "P12FVER001", "message": "No existe el índice de integridad."}],
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
            "issues": [{"code": "P12FVER002", "message": f"Índice ilegible: {exc}"}],
            "professional_emission": False,
        }

    issues: list[dict[str, Any]] = []
    if index.get("schema") != INTEGRITY_SCHEMA:
        issues.append({"code": "P12FVER003", "message": "Schema de integridad no reconocido."})

    payload = index.get("payload")
    expected_payload_hash = (index.get("payload_hash") or {}).get("value")
    if not isinstance(payload, dict) or not expected_payload_hash:
        issues.append({"code": "P12FVER004", "message": "Falta payload/payload_hash."})
        payload = {}
    elif _digest_json(payload) != expected_payload_hash:
        issues.append({"code": "P12FVER005", "message": "El payload del índice fue alterado."})

    issues.extend(_structure_issues(root))
    declared = payload.get("files") if isinstance(payload, dict) else []
    if not isinstance(declared, list):
        declared = []
        issues.append({"code": "P12FVER006", "message": "files debe ser lista."})

    declared_paths: set[str] = set()
    for record in declared:
        if not isinstance(record, dict):
            issues.append({"code": "P12FVER007", "message": "Registro de archivo inválido."})
            continue
        relative = str(record.get("path") or "")
        rel = Path(relative)
        if not relative or rel.is_absolute() or ".." in rel.parts or relative == INDEX_NAME:
            issues.append({"code": "P12FVER008", "path": relative, "message": "Ruta insegura."})
            continue
        if relative in declared_paths:
            issues.append({"code": "P12FVER009", "path": relative, "message": "Ruta duplicada."})
            continue
        declared_paths.add(relative)
        actual = root / rel
        if actual.is_symlink() or not actual.is_file():
            issues.append({"code": "P12FVER010", "path": relative, "message": "Archivo ausente o symlink."})
            continue
        if actual.stat().st_size != record.get("size_bytes"):
            issues.append({"code": "P12FVER011", "path": relative, "message": "Tamaño no coincide."})
        if _file_sha256(actual) != record.get("sha256"):
            issues.append({"code": "P12FVER012", "path": relative, "message": "SHA-256 no coincide."})

    actual_paths = {path.relative_to(root).as_posix() for path in _relative_files(root)}
    if actual_paths != declared_paths:
        issues.append({
            "code": "P12FVER013",
            "message": "El file-set no coincide exactamente con el índice.",
            "missing": sorted(declared_paths - actual_paths),
            "unindexed": sorted(actual_paths - declared_paths),
        })
    if payload.get("file_count") != len(declared_paths):
        issues.append({"code": "P12FVER014", "message": "file_count no coincide."})

    ok = not issues
    return {
        "schema": INTEGRITY_SCHEMA,
        "ok": ok,
        "status": INTEGRITY_OK if ok else INTEGRITY_MISMATCH,
        "issues": issues,
        "payload_sha256": expected_payload_hash,
        "verified_file_count": len(declared_paths),
        "portable_relative_paths": True,
        "professional_emission": False,
    }


def _active_circuit() -> str:
    try:
        return str(dss.Circuit.Name() or "")
    except Exception:
        return ""


def generar_dossier(
    manifest: dict[str, Any],
    package: dict[str, Any],
    directorio_salida: str = "mcp_electrico_scenario_dossier",
) -> dict[str, Any]:
    if not isinstance(manifest, dict) or not isinstance(package, dict):
        raise TypeError("manifest y package deben ser dict.")

    manifest_copy = deepcopy(manifest)
    package_copy = deepcopy(package)
    execution = operating_scenarios.ejecutar_paquete(
        deepcopy(manifest_copy),
        deepcopy(package_copy),
    )
    scenario_results = execution.get("scenario_results") or []
    fully_executed = (
        execution.get("execution_status") == operating_scenarios.EXECUTION_COMPLETED
        and bool(scenario_results)
        and all(item.get("execution_status") == "SCENARIO_EXECUTED" for item in scenario_results)
        and execution.get("model_restored_after_each_scenario") is True
    )
    if not fully_executed:
        return {
            "schema": SCHEMA,
            "status": STATUS_BLOCKED,
            "execution": execution,
            "artifact_generation_performed": False,
            "automatic_contingency_selection": False,
            "automatic_source_selection": False,
            "automatic_transfer": False,
            "professional_emission": False,
        }

    requested = Path(directorio_salida).expanduser().resolve()
    target = _safe_dir(requested)
    collision_avoided = target != requested
    paths = {
        "manifest": target / "electrical_manifest.json",
        "package": target / "scenario_package.json",
        "execution": target / "scenario_execution.json",
        "workspace": target / "scenario_workspace.html",
        "report": target / "scenario_report.html",
        "snapshot": target / "base_snapshot_p7a.json",
        "reconstruction": target / "base_reconstruction_p7b.json",
        "integrity": target / INDEX_NAME,
        "netlist": target / "p7a_netlist",
        "reconstructed": target / "p7b_reconstructed",
    }

    circuit_before_p7b = _active_circuit()
    revision_before_p7b = workspace_state.status().get("model_revision")

    try:
        _write_json(paths["manifest"], manifest_copy)
        _write_json(paths["package"], package_copy)
        _write_json(paths["execution"], execution)

        workspace_result = operating_scenario_workspace.escribir_workspace(
            paths["workspace"],
            manifest_copy,
            package_copy,
            execution,
        )
        report_html = operating_scenario_workspace.construir_html(
            manifest_copy,
            package_copy,
            execution,
        ).replace("<h1>Escenarios operativos P12</h1>", "<h1>Reporte reproducible de escenarios P12</h1>")
        paths["report"].write_text(report_html, encoding="utf-8")

        snapshot = project_snapshot.construir_snapshot(
            directorio_netlist=str(paths["netlist"])
        )
        snapshot_verification = project_snapshot.verificar_snapshot(snapshot)
        if snapshot_verification.get("status") != "HASH_MATCH":
            raise RuntimeError(f"P12FS001: snapshot P7A no verificable: {snapshot_verification}")
        _write_json(paths["snapshot"], snapshot)

        reconstruction = project_reconstruction.reconstruir_snapshot_contexto_aislado(
            snapshot,
            directorio_reconstruccion=str(paths["reconstructed"]),
        )
        _write_json(paths["reconstruction"], reconstruction)
        if reconstruction.get("status") != P7B_OK:
            raise RuntimeError(f"P12FB001: reconstrucción P7B no verificó: {reconstruction}")
        if reconstruction.get("parent_dss_context_mutated") is not False:
            raise RuntimeError("P12FB002: P7B aislado no preservó el contexto padre.")

        circuit_after_p7b = _active_circuit()
        revision_after_p7b = workspace_state.status().get("model_revision")
        if circuit_after_p7b != circuit_before_p7b or revision_after_p7b != revision_before_p7b:
            raise RuntimeError("P12FB003: P7B alteró el circuito/revisión padre.")

        context = {
            "manifest_sha256": _digest_json(manifest_copy),
            "scenario_package_sha256": _digest_json(package_copy),
            "scenario_execution_sha256": _digest_json(execution),
            "p7a_payload_sha256": (snapshot.get("hash") or {}).get("value"),
            "workspace_schema": operating_scenario_workspace.SCHEMA,
            "scenario_schema": operating_scenarios.SCHEMA,
            "scenario_total": (execution.get("summary") or {}).get("total"),
            "scenario_pass": (execution.get("summary") or {}).get("pass"),
            "scenario_fail": (execution.get("summary") or {}).get("fail"),
            "professional_emission": False,
        }
        integrity = _build_integrity(target, context)
        verification = integrity["verification"]
        if verification.get("status") != INTEGRITY_OK:
            raise RuntimeError(f"P12FI001: integridad no verificó: {verification}")

        return {
            "schema": SCHEMA,
            "status": STATUS_READY,
            "requested_output_directory": str(requested),
            "output_directory": str(target),
            "output_directory_collision_avoided": collision_avoided,
            "execution_status": execution.get("execution_status"),
            "summary": deepcopy(execution.get("summary") or {}),
            "workspace": {
                **workspace_result,
                "browser_engineering_calculation": False,
            },
            "p7a": {
                "status": snapshot_verification.get("status"),
                "snapshot_path": str(paths["snapshot"]),
                "sha256": (snapshot.get("hash") or {}).get("value"),
            },
            "p7b": {
                "status": reconstruction.get("status"),
                "result_path": str(paths["reconstruction"]),
                "isolated_context": True,
                "parent_dss_context_mutated": False,
            },
            "integrity": {
                "status": verification.get("status"),
                "ok": verification.get("ok"),
                "index_path": str(paths["integrity"]),
                "payload_sha256": verification.get("payload_sha256"),
                "index_file_sha256": integrity.get("index_file_sha256"),
                "verified_file_count": verification.get("verified_file_count"),
            },
            "trace_files": {
                "manifest": str(paths["manifest"]),
                "scenario_package": str(paths["package"]),
                "scenario_execution": str(paths["execution"]),
                "workspace": str(paths["workspace"]),
                "report": str(paths["report"]),
                "integrity": str(paths["integrity"]),
            },
            "automatic_contingency_selection": False,
            "automatic_switching": False,
            "automatic_load_shedding": False,
            "automatic_source_selection": False,
            "automatic_transfer": False,
            "crosscheck": False,
            "professional_report": False,
            "professional_emission": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": STATUS_FAILED,
            "requested_output_directory": str(requested),
            "output_directory": str(target),
            "output_directory_collision_avoided": collision_avoided,
            "error": f"{type(exc).__name__}: {exc}",
            "integrity_index_generated": paths["integrity"].is_file(),
            "p7b_parent_circuit_preserved": _active_circuit() == circuit_before_p7b,
            "p7b_parent_revision_preserved": workspace_state.status().get("model_revision") == revision_before_p7b,
            "automatic_contingency_selection": False,
            "automatic_source_selection": False,
            "automatic_transfer": False,
            "professional_emission": False,
        }
