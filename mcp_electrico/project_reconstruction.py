"""P7B — reconstrucción verificable de un snapshot P7A.

P7B restaura únicamente el netlist DSS después de verificar integridad y
comprueba un round-trip canónico archivo por archivo. Los estados P2/P3/P5,
la representación visual y los resultados históricos NO se promueven a estado
vigente: requieren rebind o recálculo explícito.
"""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
from typing import Any

from opendssdirect import dss

from . import (
    ampacity,
    conductor_library,
    core,
    professional_data,
    project_snapshot,
    protection_curves,
    protection_data,
    visual_state,
    workspace_state,
    zero_sequence,
)

SCHEMA = "MCP_ELECTRICO_P7B_RECONSTRUCTION_V1"
CONTRACT_SCHEMA = "MCP_ELECTRICO_P7B_RECONSTRUCTION_CONTRACT_V1"
_STAGE_ENV = "MCP_ELECTRICO_P7B_STAGE_FILE"

_REBIND_STATUS = {
    "professional_p2": "NOT_RESTORED_REQUIRES_REBIND",
    "zero_sequence_p2": "NOT_RESTORED_REQUIRES_REBIND",
    "ampacity_p3": "NOT_RESTORED_REQUIRES_REBIND",
    "protection_p5": "NOT_RESTORED_REQUIRES_REBIND",
    "tcc_datasets_p5": "NOT_RESTORED_REQUIRES_REBIND",
    "workspace_visual": "NOT_RESTORED",
    "studies": "NOT_RESTORED_REQUIRES_RECALCULATION",
}


def _diagnostic_stage(stage: str, **extra: Any) -> None:
    """Registra la última etapa P7B solo cuando el proceso aislado lo solicita.

    Es telemetría operacional fail-safe: nunca participa en cálculos, hashes ni
    decisiones de ingeniería y cualquier error al escribirla se ignora.
    """
    raw = os.environ.get(_STAGE_ENV)
    if not raw:
        return
    try:
        payload = {
            "schema": "MCP_ELECTRICO_P7B_ISOLATED_STAGE_V1",
            "stage": str(stage),
            "professional_emission": False,
        }
        payload.update({str(key): value for key, value in extra.items()})
        Path(raw).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def obtener_contrato_p7b() -> dict[str, Any]:
    return {
        "schema": CONTRACT_SCHEMA,
        "source_schema": project_snapshot.SCHEMA,
        "integrity_before_write": True,
        "materialization": "ISOLATED_NEW_DIRECTORY",
        "roundtrip_verification": "CANONICAL_DSS_FILE_BY_FILE",
        "stored_results_promoted_to_current": False,
        "structured_state_auto_restore": False,
        "engineering_preview_ready": False,
        "professional_emission": False,
    }


def _active_circuit_name() -> str:
    """Devuelve el circuito activo sin convertir un estado vacío en excepción."""
    try:
        return str(dss.Circuit.Name() or "")
    except Exception:
        return ""


def _safe_target_dir(path: str | Path) -> Path:
    requested = Path(path).expanduser().resolve()
    target = requested
    if not target.exists():
        target.mkdir(parents=True, exist_ok=False)
        return target
    if not any(target.iterdir()):
        return target
    index = 2
    while True:
        candidate = target.with_name(f"{target.name}_{index}")
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        index += 1


def _validate_file_name(name: Any) -> str:
    text = str(name or "").strip()
    if not text:
        raise ValueError("P7B011: archivo DSS sin nombre.")
    candidate = Path(text)
    if candidate.is_absolute() or candidate.name != text or "/" in text or "\\" in text or text in {".", ".."}:
        raise ValueError(f"P7B012: nombre de archivo no seguro: {text!r}.")
    if candidate.suffix.lower() != ".dss":
        raise ValueError(f"P7B013: P7B solo materializa archivos .dss: {text!r}.")
    return text


def _validated_netlist(snapshot: dict[str, Any]) -> dict[str, Any]:
    payload = snapshot.get("payload") or {}
    netlist = payload.get("netlist")
    if not isinstance(netlist, dict):
        raise ValueError("P7B020: falta payload.netlist.")
    files = netlist.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("P7B021: netlist.files debe contener al menos un archivo.")
    if int(netlist.get("file_count") or -1) != len(files):
        raise ValueError("P7B022: file_count no coincide con files.")

    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("P7B023: cada archivo DSS debe ser un objeto name/content.")
        name = _validate_file_name(item.get("name"))
        key = name.lower()
        if key in seen:
            raise ValueError(f"P7B024: nombre DSS duplicado: {name}.")
        seen.add(key)
        content = item.get("content")
        if not isinstance(content, str):
            raise ValueError(f"P7B025: contenido DSS inválido para {name}.")
        normalized.append({"name": name, "content": content})

    master = _validate_file_name(netlist.get("master_file"))
    if master.lower() not in seen:
        raise ValueError("P7B026: master_file no existe dentro de netlist.files.")
    if master.lower() != "master.dss":
        raise ValueError("P7B027: P7B-v1 exige Master.dss como archivo maestro canónico.")

    normalized.sort(key=lambda item: item["name"].lower())
    return {
        "master_file": master,
        "file_count": len(normalized),
        "files": normalized,
        "paths_included": False,
        "canonicalization": deepcopy(netlist.get("canonicalization") or {}),
    }


def _materialize(netlist: dict[str, Any], target: Path) -> Path:
    for item in netlist["files"]:
        (target / item["name"]).write_text(item["content"], encoding="utf-8")
    return target / netlist["master_file"]


def _clear_core_runtime_metadata() -> None:
    # Compile de OpenDSS no pasa por core.crear_circuito; limpiamos solo
    # metadatos auxiliares del MCP para no heredar cargas críticas/bases previas.
    critical = getattr(core, "_cargas_criticas", None)
    if hasattr(critical, "clear"):
        critical.clear()
    voltage_bases = getattr(core, "_voltage_bases", None)
    if hasattr(voltage_bases, "clear"):
        voltage_bases.clear()


def _reset_structured_state(action: str) -> None:
    _clear_core_runtime_metadata()
    visual_state.reset()
    conductor_library.reset()
    professional_data.reset()
    zero_sequence.reset()
    ampacity.reset()
    protection_data.reset()
    protection_curves.reset()
    workspace_state.reset_for_circuit(action)


def _clear_failed_reconstruction(action: str) -> None:
    try:
        dss("Clear")
    finally:
        _reset_structured_state(action)


def _base_result(status: str, snapshot: dict[str, Any], verification: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "source_snapshot": {
            "schema": snapshot.get("schema"),
            "hash": deepcopy(snapshot.get("hash")),
        },
        "integrity": deepcopy(verification),
        "restoration": deepcopy(_REBIND_STATUS),
        "stored_results_promoted_to_current": False,
        "engineering_preview_ready": False,
        "professional_emission": False,
    }


def reconstruir_snapshot(
    snapshot: dict[str, Any],
    directorio_reconstruccion: str = "reconstructed_p7b",
) -> dict[str, Any]:
    """Reconstruye y verifica el netlist P7A sin restaurar resultados antiguos."""
    _diagnostic_stage("RECONSTRUCTION_ENTERED")
    if not isinstance(snapshot, dict):
        _diagnostic_stage("BLOCKED_INVALID_SNAPSHOT_OBJECT")
        return {
            "schema": SCHEMA,
            "status": "BLOCKED_INVALID_SNAPSHOT_OBJECT",
            "stored_results_promoted_to_current": False,
            "engineering_preview_ready": False,
            "professional_emission": False,
        }

    verification = project_snapshot.verificar_snapshot(snapshot)
    previous_circuit = _active_circuit_name()
    if not verification.get("ok"):
        _diagnostic_stage("BLOCKED_SNAPSHOT_INTEGRITY")
        result = _base_result("BLOCKED_SNAPSHOT_INTEGRITY", snapshot, verification)
        result["previous_circuit"] = previous_circuit
        result["write_performed"] = False
        result["compile_performed"] = False
        return result
    _diagnostic_stage("SNAPSHOT_INTEGRITY_VERIFIED")

    try:
        netlist = _validated_netlist(snapshot)
    except (TypeError, ValueError) as exc:
        _diagnostic_stage("BLOCKED_INVALID_NETLIST", error=str(exc))
        result = _base_result("BLOCKED_INVALID_NETLIST", snapshot, verification)
        result["previous_circuit"] = previous_circuit
        result["write_performed"] = False
        result["compile_performed"] = False
        result["error"] = str(exc)
        return result
    _diagnostic_stage("NETLIST_VALIDATED", file_count=netlist["file_count"])

    target = _safe_target_dir(directorio_reconstruccion)
    master = _materialize(netlist, target)
    _diagnostic_stage("NETLIST_MATERIALIZED", master_file=str(master))

    try:
        _diagnostic_stage("DSS_CLEAR_STARTED")
        dss("Clear")
        _diagnostic_stage("DSS_CLEAR_COMPLETED")
        _diagnostic_stage("DSS_COMPILE_STARTED", master_file=str(master))
        dss(f'Compile "{master}"')
        _diagnostic_stage("DSS_COMPILE_COMPLETED")
        reconstructed_circuit = _active_circuit_name().strip()
        if not reconstructed_circuit:
            raise RuntimeError("P7B030: Compile no produjo un circuito activo.")
        _reset_structured_state("p7b_reconstructed_netlist")
        _diagnostic_stage("STRUCTURED_STATE_RESET", circuit=reconstructed_circuit)

        _diagnostic_stage("ROUNDTRIP_EXPORT_STARTED")
        roundtrip = project_snapshot.construir_netlist_canonico(
            str(target / "_roundtrip")
        )
        _diagnostic_stage("ROUNDTRIP_EXPORT_COMPLETED", file_count=roundtrip.get("file_count"))
        match = roundtrip == netlist
        roundtrip_info = {
            "performed": True,
            "canonical_netlist_match": match,
            "file_count_expected": netlist["file_count"],
            "file_count_actual": roundtrip.get("file_count"),
        }
        if not match:
            _diagnostic_stage("ROUNDTRIP_MISMATCH")
            _clear_failed_reconstruction("p7b_roundtrip_mismatch")
            result = _base_result("RECONSTRUCTION_ROUNDTRIP_MISMATCH", snapshot, verification)
            result.update({
                "previous_circuit": previous_circuit,
                "reconstructed_circuit": reconstructed_circuit,
                "materialized_directory": str(target),
                "master_file": str(master),
                "write_performed": True,
                "compile_performed": True,
                "roundtrip": roundtrip_info,
                "active_circuit_after_failure": _active_circuit_name(),
            })
            result["restoration"]["netlist"] = "RESTORED_MISMATCH_CLEARED"
            return result

        result = _base_result(
            "RECONSTRUCTED_NETLIST_VERIFIED_WITH_REBIND_REQUIRED",
            snapshot,
            verification,
        )
        result.update({
            "previous_circuit": previous_circuit,
            "reconstructed_circuit": reconstructed_circuit,
            "materialized_directory": str(target),
            "master_file": str(master),
            "write_performed": True,
            "compile_performed": True,
            "roundtrip": roundtrip_info,
            "workspace_status": workspace_state.status(),
        })
        result["restoration"]["netlist"] = "RESTORED_VERIFIED"
        _diagnostic_stage("RECONSTRUCTION_VERIFIED", circuit=reconstructed_circuit)
        return result
    except Exception as exc:
        _diagnostic_stage("RECONSTRUCTION_EXCEPTION", error=str(exc))
        _clear_failed_reconstruction("p7b_reconstruction_failed")
        result = _base_result("RECONSTRUCTION_FAILED", snapshot, verification)
        result.update({
            "previous_circuit": previous_circuit,
            "materialized_directory": str(target),
            "master_file": str(master),
            "write_performed": True,
            "compile_performed": True,
            "error": str(exc),
            "active_circuit_after_failure": _active_circuit_name(),
        })
        return result


def reconstruir_archivo(
    ruta_snapshot: str,
    directorio_reconstruccion: str = "reconstructed_p7b",
) -> dict[str, Any]:
    path = Path(ruta_snapshot).expanduser()
    if not path.is_file():
        return {
            "schema": SCHEMA,
            "status": "SNAPSHOT_FILE_NOT_FOUND",
            "path": str(path),
            "stored_results_promoted_to_current": False,
            "engineering_preview_ready": False,
            "professional_emission": False,
        }
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {
            "schema": SCHEMA,
            "status": "INVALID_SNAPSHOT_JSON",
            "path": str(path),
            "error": str(exc),
            "stored_results_promoted_to_current": False,
            "engineering_preview_ready": False,
            "professional_emission": False,
        }
    return reconstruir_snapshot(
        snapshot,
        directorio_reconstruccion=directorio_reconstruccion,
    )
