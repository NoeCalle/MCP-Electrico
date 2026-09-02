"""P7B — reconstrucción verificable de un snapshot P7A.

P7B restaura únicamente el netlist DSS después de verificar integridad y
comprueba un round-trip canónico archivo por archivo. Los estados P2/P3/P5,
la representación visual y los resultados históricos NO se promueven a estado
vigente: requieren rebind o recálculo explícito.

La ruta usada por el dossier P8 puede ejecutar P7B en un ``NewContext`` de
OpenDSSDirect. Ese contexto contiene un motor DSS independiente dentro del
mismo proceso y evita destruir o rebindear el circuito activo del servidor MCP.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
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
ISOLATION_MODE_CONTEXT = "OPENDSS_NEW_CONTEXT"

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
    """Registra una etapa P7B solo cuando el llamador solicita telemetría.

    Nunca participa en cálculos, hashes ni decisiones de ingeniería. Cualquier
    error al escribir la telemetría se ignora deliberadamente.
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
        "isolated_context_supported": True,
        "isolated_context_mode": ISOLATION_MODE_CONTEXT,
        "engineering_preview_ready": False,
        "professional_emission": False,
    }


def _active_circuit_name(engine: Any = dss) -> str:
    """Devuelve el circuito activo del contexto indicado sin forzar excepción."""
    try:
        return str(engine.Circuit.Name() or "")
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


def _safe_export_dir(path: str | Path) -> Path:
    requested = Path(path).expanduser().resolve()
    target = requested
    if target.exists() and any(
        item.is_file() and item.suffix.lower() == ".dss"
        for item in target.iterdir()
    ):
        index = 2
        while True:
            candidate = target.with_name(f"{target.name}_{index}")
            if not candidate.exists():
                target = candidate
                break
            index += 1
    target.mkdir(parents=True, exist_ok=True)
    return target


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


def _normalize_context_dss_content(name: str, content: str) -> str:
    """Replica la canonización P7A para un netlist exportado por otro contexto."""
    text = str(content)
    if str(name).lower() != "master.dss":
        return text
    normalized: list[str] = []
    for line in text.splitlines(keepends=True):
        raw = line.rstrip("\r\n")
        ending = line[len(raw):]
        if raw.startswith("! Last saved by ") and " on " in raw:
            prefix, _timestamp = raw.rsplit(" on ", 1)
            line = f"{prefix} on {project_snapshot.SAVE_COMMENT_PLACEHOLDER}{ending}"
        normalized.append(line)
    return "".join(normalized)


def _context_netlist_payload(engine: Any, directory: str | Path) -> dict[str, Any]:
    """Exporta un contexto DSS sin utilizar el contexto global de ``core``."""
    target = _safe_export_dir(directory)
    response = engine(f'Save Circuit Dir="{target}"')
    files: list[dict[str, str]] = []
    for path in sorted(
        (item for item in target.iterdir() if item.is_file() and item.suffix.lower() == ".dss"),
        key=lambda item: item.name.lower(),
    ):
        files.append(
            {
                "name": path.name,
                "content": _normalize_context_dss_content(
                    path.name,
                    path.read_text(encoding="utf-8", errors="replace"),
                ),
            }
        )
    if not files:
        raise RuntimeError(
            "P7B040: el contexto OpenDSS aislado no exportó archivos DSS. "
            f"Respuesta: {response!r}"
        )
    master = next((item["name"] for item in files if item["name"].lower() == "master.dss"), None)
    return {
        "master_file": master,
        "file_count": len(files),
        "files": files,
        "paths_included": False,
        "canonicalization": {
            "save_circuit_master_timestamp_comment": "NORMALIZED",
            "placeholder": project_snapshot.SAVE_COMMENT_PLACEHOLDER,
            "other_dss_content_modified": False,
        },
    }


def _content_sha256(content: str) -> str:
    return sha256(str(content).encode("utf-8")).hexdigest()


def _netlist_diff_summary(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    """Resume un mismatch sin incrustar el contenido completo de los DSS."""
    def file_map(value: dict[str, Any]) -> dict[str, dict[str, Any]]:
        mapped: dict[str, dict[str, Any]] = {}
        for item in value.get("files") or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "")
            if name:
                mapped[name.lower()] = item
        return mapped

    expected_files = file_map(expected)
    actual_files = file_map(actual)
    expected_keys = set(expected_files)
    actual_keys = set(actual_files)
    changed: list[dict[str, Any]] = []
    for key in sorted(expected_keys & actual_keys):
        expected_content = str(expected_files[key].get("content") or "")
        actual_content = str(actual_files[key].get("content") or "")
        if expected_content == actual_content:
            continue
        changed.append(
            {
                "name_expected": str(expected_files[key].get("name") or key),
                "name_actual": str(actual_files[key].get("name") or key),
                "expected_sha256": _content_sha256(expected_content),
                "actual_sha256": _content_sha256(actual_content),
                "expected_bytes": len(expected_content.encode("utf-8")),
                "actual_bytes": len(actual_content.encode("utf-8")),
            }
        )
    return {
        "missing_files": [str(expected_files[key].get("name") or key) for key in sorted(expected_keys - actual_keys)],
        "extra_files": [str(actual_files[key].get("name") or key) for key in sorted(actual_keys - expected_keys)],
        "changed_files": changed,
        "master_file_expected": expected.get("master_file"),
        "master_file_actual": actual.get("master_file"),
        "canonicalization_match": expected.get("canonicalization") == actual.get("canonicalization"),
        "paths_included_match": expected.get("paths_included") == actual.get("paths_included"),
    }


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


def _clear_failed_reconstruction(
    action: str,
    *,
    engine: Any = dss,
    reset_structured_state: bool = True,
) -> None:
    try:
        engine("Clear")
    finally:
        if reset_structured_state:
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


def _reconstruir_snapshot_engine(
    snapshot: dict[str, Any],
    directorio_reconstruccion: str,
    *,
    engine: Any,
    reset_structured_state: bool,
    isolation_mode: str | None,
) -> dict[str, Any]:
    _diagnostic_stage("RECONSTRUCTION_ENTERED", isolation_mode=isolation_mode)
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
    previous_circuit = _active_circuit_name(engine)
    if not verification.get("ok"):
        _diagnostic_stage("BLOCKED_SNAPSHOT_INTEGRITY")
        result = _base_result("BLOCKED_SNAPSHOT_INTEGRITY", snapshot, verification)
        result["previous_circuit"] = previous_circuit
        result["write_performed"] = False
        result["compile_performed"] = False
        result["redirect_performed"] = False
        result["load_command"] = None
        if isolation_mode:
            result["isolation_mode"] = isolation_mode
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
        result["redirect_performed"] = False
        result["load_command"] = None
        result["error"] = str(exc)
        if isolation_mode:
            result["isolation_mode"] = isolation_mode
        return result
    _diagnostic_stage("NETLIST_VALIDATED", file_count=netlist["file_count"])

    target = _safe_target_dir(directorio_reconstruccion)
    master = _materialize(netlist, target)
    _diagnostic_stage("NETLIST_MATERIALIZED", master_file=str(master))
    load_command = "Redirect" if isolation_mode == ISOLATION_MODE_CONTEXT else "Compile"
    compile_performed = load_command == "Compile"
    redirect_performed = load_command == "Redirect"

    try:
        _diagnostic_stage("DSS_CLEAR_STARTED")
        engine("Clear")
        _diagnostic_stage("DSS_CLEAR_COMPLETED")
        _diagnostic_stage("DSS_LOAD_STARTED", load_command=load_command, master_file=str(master))
        engine(f'{load_command} "{master}"')
        _diagnostic_stage("DSS_LOAD_COMPLETED", load_command=load_command)
        reconstructed_circuit = _active_circuit_name(engine).strip()
        if not reconstructed_circuit:
            raise RuntimeError(f"P7B030: {load_command} no produjo un circuito activo.")
        if reset_structured_state:
            _reset_structured_state("p7b_reconstructed_netlist")
            _diagnostic_stage("STRUCTURED_STATE_RESET", circuit=reconstructed_circuit)

        _diagnostic_stage("ROUNDTRIP_EXPORT_STARTED")
        if isolation_mode == ISOLATION_MODE_CONTEXT:
            roundtrip = _context_netlist_payload(engine, target / "_roundtrip")
        else:
            roundtrip = project_snapshot.construir_netlist_canonico(str(target / "_roundtrip"))
        _diagnostic_stage("ROUNDTRIP_EXPORT_COMPLETED", file_count=roundtrip.get("file_count"))
        match = roundtrip == netlist
        roundtrip_info = {
            "performed": True,
            "canonical_netlist_match": match,
            "file_count_expected": netlist["file_count"],
            "file_count_actual": roundtrip.get("file_count"),
        }
        if not match:
            roundtrip_info["mismatch"] = _netlist_diff_summary(netlist, roundtrip)
            _diagnostic_stage("ROUNDTRIP_MISMATCH", mismatch=roundtrip_info["mismatch"])
            _clear_failed_reconstruction(
                "p7b_roundtrip_mismatch",
                engine=engine,
                reset_structured_state=reset_structured_state,
            )
            result = _base_result("RECONSTRUCTION_ROUNDTRIP_MISMATCH", snapshot, verification)
            result.update({
                "previous_circuit": previous_circuit,
                "reconstructed_circuit": reconstructed_circuit,
                "materialized_directory": str(target),
                "master_file": str(master),
                "write_performed": True,
                "compile_performed": compile_performed,
                "redirect_performed": redirect_performed,
                "load_command": load_command,
                "roundtrip": roundtrip_info,
                "active_circuit_after_failure": _active_circuit_name(engine),
            })
            result["restoration"]["netlist"] = "RESTORED_MISMATCH_CLEARED"
            if isolation_mode:
                result["isolation_mode"] = isolation_mode
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
            "compile_performed": compile_performed,
            "redirect_performed": redirect_performed,
            "load_command": load_command,
            "roundtrip": roundtrip_info,
        })
        if reset_structured_state:
            result["workspace_status"] = workspace_state.status()
        if isolation_mode:
            result["isolation_mode"] = isolation_mode
            result["parent_structured_state_mutated"] = False
            result["parent_dss_context_mutated"] = False
        result["restoration"]["netlist"] = "RESTORED_VERIFIED"
        _diagnostic_stage("RECONSTRUCTION_VERIFIED", circuit=reconstructed_circuit)
        return result
    except Exception as exc:
        _diagnostic_stage("RECONSTRUCTION_EXCEPTION", error=str(exc))
        _clear_failed_reconstruction(
            "p7b_reconstruction_failed",
            engine=engine,
            reset_structured_state=reset_structured_state,
        )
        result = _base_result("RECONSTRUCTION_FAILED", snapshot, verification)
        result.update({
            "previous_circuit": previous_circuit,
            "materialized_directory": str(target),
            "master_file": str(master),
            "write_performed": True,
            "compile_performed": compile_performed,
            "redirect_performed": redirect_performed,
            "load_command": load_command,
            "error": str(exc),
            "active_circuit_after_failure": _active_circuit_name(engine),
        })
        if isolation_mode:
            result["isolation_mode"] = isolation_mode
        return result


def reconstruir_snapshot(
    snapshot: dict[str, Any],
    directorio_reconstruccion: str = "reconstructed_p7b",
) -> dict[str, Any]:
    """Reconstruye P7B sobre el contexto DSS global y resetea estado estructurado."""
    return _reconstruir_snapshot_engine(
        snapshot,
        directorio_reconstruccion,
        engine=dss,
        reset_structured_state=True,
        isolation_mode=None,
    )


def reconstruir_snapshot_contexto_aislado(
    snapshot: dict[str, Any],
    directorio_reconstruccion: str = "reconstructed_p7b",
) -> dict[str, Any]:
    """Reconstruye P7B en un ``dss.NewContext()`` sin mutar el modelo padre.

    Esta es la ruta de aislamiento para P8E2/P8F4. Evita un proceso Python hijo,
    necesario para portabilidad del servidor MCP stdio en Windows, y mantiene
    la verificación canónica archivo por archivo.
    """
    isolated = dss.NewContext()
    # Con múltiples contextos evitamos mutar el cwd del proceso. DSS-Extensions
    # mantiene internamente las rutas de Redirect; Master.dss se carga por ruta
    # absoluta en el contexto aislado.
    isolated.Basic.AllowChangeDir(False)
    result = _reconstruir_snapshot_engine(
        snapshot,
        directorio_reconstruccion,
        engine=isolated,
        reset_structured_state=False,
        isolation_mode=ISOLATION_MODE_CONTEXT,
    )
    result["isolated_context"] = True
    result["isolated_process"] = False
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
