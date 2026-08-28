"""P7A — snapshot reproducible y hash determinista de un proyecto MCP Eléctrico.

El snapshot congela el netlist DSS por contenido y los estados estructurados de
P2/P3/P5/estudios. Las rutas de exportación y timestamps transitorios se
excluyen del contenido hasheado para que dos exportaciones del mismo estado
produzcan el mismo SHA-256.

P7A NO implementa todavía importación/reconstrucción, reporte profesional ni
emisión firmada. Es la base de P7 para la Engineering Preview.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from importlib import metadata
import json
from pathlib import Path
from typing import Any

from opendssdirect import dss

from . import (
    ampacity,
    core,
    engine_selection,
    p5_completion,
    professional_data,
    protection_curves,
    protection_data,
    validation_status,
    workspace_state,
    zero_sequence,
)

SCHEMA = "MCP_ELECTRICO_P7A_PROJECT_SNAPSHOT_V1"
HASH_ALGORITHM = "sha256"
HASH_SCOPE = "canonical_payload_without_export_paths_or_transient_timestamps"
TRANSIENT_KEYS = {"last_update", "recorded_at"}
SAVE_COMMENT_PLACEHOLDER = "<P7A_TRANSIENT_TIMESTAMP_REMOVED>"


def _package_version(distribution: str) -> str | None:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return None


def _runtime_versions() -> dict[str, Any]:
    return {
        "opendssdirect.py": _package_version("opendssdirect.py"),
        "dss-python": _package_version("dss-python"),
        "pandapower": _package_version("pandapower"),
        "mcp": _package_version("mcp"),
        "engine_contract": {
            "opendss_default_for_distribution": True,
            "pandapower_iec60909_backend": True,
            "automatic_dispatch": False,
            "crosscheck": False,
        },
    }


def _strip_transient(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _strip_transient(item)
            for key, item in value.items()
            if str(key) not in TRANSIENT_KEYS
        }
    if isinstance(value, list):
        return [_strip_transient(item) for item in value]
    return deepcopy(value)


def _normalize_dss_content(name: str, content: str) -> str:
    """Normaliza solo metadatos transitorios conocidos de ``Save Circuit``.

    AltDSS/DSS C-API agrega en ``Master.dss`` un comentario con el instante
    exacto de guardado. Ese instante no representa un cambio de ingeniería y
    rompería el hash de dos exportaciones equivalentes. Se conserva toda la
    información anterior al último `` on `` (incluidas versión/revisión del
    motor) y se sustituye únicamente el timestamp final por un marcador.
    """
    text = str(content)
    if str(name).lower() != "master.dss":
        return text
    normalized: list[str] = []
    for line in text.splitlines(keepends=True):
        raw = line.rstrip("\r\n")
        ending = line[len(raw):]
        if raw.startswith("! Last saved by ") and " on " in raw:
            prefix, _timestamp = raw.rsplit(" on ", 1)
            line = f"{prefix} on {SAVE_COMMENT_PLACEHOLDER}{ending}"
        normalized.append(line)
    return "".join(normalized)


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(payload: dict[str, Any]) -> str:
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _netlist_payload(directorio: str) -> dict[str, Any]:
    exported = core.obtener_netlist(directorio)
    files = [
        {
            "name": str(item["nombre"]),
            "content": _normalize_dss_content(
                str(item["nombre"]),
                str(item["contenido"]),
            ),
        }
        for item in exported.get("archivos", [])
    ]
    files.sort(key=lambda item: item["name"].lower())
    if not files:
        raise RuntimeError("P7A001: la exportación DSS no produjo archivos serializables.")
    return {
        "master_file": exported.get("archivo_master"),
        "file_count": len(files),
        "files": files,
        "paths_included": False,
        "canonicalization": {
            "save_circuit_master_timestamp_comment": "NORMALIZED",
            "placeholder": SAVE_COMMENT_PLACEHOLDER,
            "other_dss_content_modified": False,
        },
    }


def _limitations(validation: dict[str, Any]) -> dict[str, list[str]]:
    return {
        name: [str(item) for item in (record.get("limitations") or [])]
        for name, record in sorted(validation.items())
        if record.get("limitations")
    }


def construir_snapshot(
    directorio_netlist: str = "temp_export_p7a",
) -> dict[str, Any]:
    """Construye el snapshot canónico del circuito activo y su SHA-256."""
    circuit = str(dss.Circuit.Name() or "").strip()
    if not circuit:
        raise ValueError("P7A002: no existe un circuito activo para congelar.")

    validation = validation_status.get_validation_matrix()
    workspace = _strip_transient(workspace_state.snapshot())
    p5_gate = p5_completion.evaluar_cierre_p5()

    payload = {
        "schema": SCHEMA,
        "project": {
            "circuit": circuit,
            "model_revision": (workspace.get("status") or {}).get("model_revision"),
            "visual_revision": (workspace.get("status") or {}).get("visual_revision"),
        },
        "netlist": _netlist_payload(directorio_netlist),
        "workspace": workspace,
        "engineering_data": {
            "professional_p2": professional_data.snapshot(),
            "zero_sequence_p2": zero_sequence.snapshot(),
            "ampacity_p3": ampacity.snapshot(),
            "protection_p5": protection_data.snapshot(),
            "tcc_datasets_p5": protection_curves.listar_datasets(),
        },
        "governance": {
            "validation_matrix": validation,
            "limitations": _limitations(validation),
            "p5_completion": p5_gate,
            "engine_selection": engine_selection.obtener_capacidades_motores(),
            "runtime_versions": _runtime_versions(),
            "automatic_dispatch": False,
            "crosscheck": False,
            "professional_emission": False,
        },
        "p7_status": {
            "phase": "P7",
            "milestone": "P7A_PROJECT_SNAPSHOT",
            "maturity": "EXPERIMENTAL",
            "reconstruction_import": "NOT_IMPLEMENTED_P7A",
            "professional_report": "NOT_IMPLEMENTED_P7A",
            "engineering_preview_ready": False,
            "professional_emission": False,
        },
    }
    digest = _digest(payload)
    return {
        "schema": SCHEMA,
        "hash": {
            "algorithm": HASH_ALGORITHM,
            "scope": HASH_SCOPE,
            "value": digest,
        },
        "payload": payload,
        "professional_emission": False,
    }


def verificar_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Verifica estructura mínima y hash sin ejecutar ni reconstruir el modelo."""
    if snapshot.get("schema") != SCHEMA:
        return {
            "ok": False,
            "status": "SCHEMA_MISMATCH",
            "expected_schema": SCHEMA,
            "professional_emission": False,
        }
    payload = snapshot.get("payload")
    expected = ((snapshot.get("hash") or {}).get("value"))
    if not isinstance(payload, dict) or not expected:
        return {
            "ok": False,
            "status": "MISSING_PAYLOAD_OR_HASH",
            "professional_emission": False,
        }
    actual = _digest(payload)
    ok = actual == expected
    return {
        "ok": ok,
        "status": "HASH_MATCH" if ok else "HASH_MISMATCH",
        "algorithm": HASH_ALGORITHM,
        "expected_hash": expected,
        "actual_hash": actual,
        "reconstruction_performed": False,
        "professional_emission": False,
    }


def _safe_output_path(path: str | Path) -> Path:
    requested = Path(path).expanduser()
    requested.parent.mkdir(parents=True, exist_ok=True)
    if not requested.exists():
        return requested
    suffix = requested.suffix or ".json"
    stem = requested.stem if requested.suffix else requested.name
    index = 2
    while True:
        candidate = requested.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def exportar_snapshot(
    ruta_salida: str = "mcp_electrico_project.json",
    directorio_netlist: str = "temp_export_p7a",
) -> dict[str, Any]:
    """Escribe un snapshot JSON sin sobrescribir exportaciones anteriores."""
    snapshot = construir_snapshot(directorio_netlist=directorio_netlist)
    target = _safe_output_path(ruta_salida)
    target.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    verification = verificar_snapshot(snapshot)
    return {
        "ok": bool(verification.get("ok")),
        "schema": SCHEMA,
        "path": str(target.resolve()),
        "hash": deepcopy(snapshot["hash"]),
        "verification": verification,
        "engineering_preview_ready": False,
        "professional_emission": False,
    }
