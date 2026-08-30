"""P8E2 — dossier reproducible del proyecto real ejecutado P1/P3/P4/P5.

Orquesta una sola ejecución P8D2 en el proceso principal y congela sus
resultados en Workspace V5 + P7A + P7C. La reconstrucción P7B se verifica en un
proceso hijo para no destruir ni rebindear el modelo activo del usuario.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from opendssdirect import dss

from . import (
    project_report,
    project_snapshot,
    real_protection_execution,
    workspace,
    workspace_state,
    workspace_v5,
)

SCHEMA = "MCP_ELECTRICO_P8E2_REAL_PROJECT_DOSSIER_V1"
STATUS_BLOCKED_EXECUTION = "BLOCKED_BY_P8D2_EXECUTION"
STATUS_FAILED_ARTIFACT = "DOSSIER_ARTIFACT_GENERATION_FAILED"
STATUS_READY = "DOSSIER_READY_ENGINEERING_PREVIEW"
P7B_OK = "RECONSTRUCTED_NETLIST_VERIFIED_WITH_REBIND_REQUIRED"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _manifest_hash(manifest: dict[str, Any]) -> str:
    return sha256(_canonical_json(manifest).encode("utf-8")).hexdigest()


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


def _active_circuit() -> str:
    try:
        return str(dss.Circuit.Name() or "")
    except Exception:
        return ""


def _p7b_isolated(snapshot_path: Path, reconstruction_dir: Path, result_path: Path) -> dict[str, Any]:
    script = r'''
import json
from pathlib import Path
import sys
from mcp_electrico import project_reconstruction

snapshot_path = Path(sys.argv[1])
reconstruction_dir = Path(sys.argv[2])
result_path = Path(sys.argv[3])
snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
result = project_reconstruction.reconstruir_snapshot(
    snapshot,
    directorio_reconstruccion=str(reconstruction_dir),
)
result_path.write_text(
    json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False),
    encoding="utf-8",
)
raise SystemExit(0 if result.get("status") == "RECONSTRUCTED_NETLIST_VERIFIED_WITH_REBIND_REQUIRED" else 3)
'''
    env = os.environ.copy()
    package_root = str(Path(__file__).resolve().parent.parent)
    current_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = package_root if not current_pythonpath else package_root + os.pathsep + current_pythonpath
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(snapshot_path),
            str(reconstruction_dir),
            str(result_path),
        ],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if not result_path.is_file():
        return {
            "schema": "MCP_ELECTRICO_P8E2_P7B_ISOLATED_FAILURE_V1",
            "status": "P7B_ISOLATED_PROCESS_FAILED",
            "returncode": completed.returncode,
            "stderr": completed.stderr[-4000:],
            "professional_emission": False,
        }
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["isolated_process"] = True
    result["isolated_process_returncode"] = completed.returncode
    return result


def generar_dossier(
    manifest: dict[str, Any],
    directorio_salida: str = "mcp_electrico_real_dossier",
) -> dict[str, Any]:
    """Ejecuta P8D2 y genera Workspace/P7A/P7B/P7C trazables del mismo estado."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest debe ser dict.")

    manifest_copy = deepcopy(manifest)
    manifest_sha = _manifest_hash(manifest_copy)
    execution = real_protection_execution.ejecutar_protecciones(deepcopy(manifest_copy))
    if execution.get("execution_status") != real_protection_execution.STATUS_COMPLETED:
        return {
            "schema": SCHEMA,
            "status": STATUS_BLOCKED_EXECUTION,
            "manifest_sha256": manifest_sha,
            "p8d2_execution": execution,
            "artifact_generation_performed": False,
            "p7b_isolated": True,
            "automatic_dispatch": False,
            "crosscheck": False,
            "professional_emission": False,
        }

    circuit_before = _active_circuit()
    revision_before = workspace_state.status().get("model_revision")
    target = _safe_dir(directorio_salida)
    paths = {
        "manifest": target / "manifest.json",
        "execution": target / "execution_p8d2.json",
        "workspace": target / "workspace_v5.html",
        "snapshot": target / "project_snapshot_p7a.json",
        "report": target / "project_report_p7c.html",
        "reconstruction": target / "reconstruction_p7b.json",
        "netlist": target / "p7a_netlist",
        "reconstructed": target / "p7b_reconstructed",
    }

    try:
        _write_json(paths["manifest"], manifest_copy)
        _write_json(paths["execution"], execution)

        project_name = str((manifest_copy.get("project") or {}).get("name") or circuit_before or "Proyecto real")
        workspace.configure(
            ruta_salida=str(paths["workspace"]),
            titulo=f"{project_name} — MCP Eléctrico",
            auto_regenerar=False,
        )
        base_workspace = workspace.regenerate()
        if not base_workspace.get("ok"):
            raise RuntimeError(f"P8E2W001: Workspace base no generado: {base_workspace}")
        workspace_result = workspace_v5.enhance_file(paths["workspace"], workspace_state.snapshot())
        if not workspace_result.get("ok") or not workspace_result.get("p8d2_integrated_view"):
            raise RuntimeError(f"P8E2W002: Workspace V5 no contiene resultado integrado P8D2: {workspace_result}")

        snapshot = project_snapshot.construir_snapshot(directorio_netlist=str(paths["netlist"]))
        verification = project_snapshot.verificar_snapshot(snapshot)
        if verification.get("status") != "HASH_MATCH":
            raise RuntimeError(f"P8E2S001: snapshot P7A no verificable: {verification}")
        _write_json(paths["snapshot"], snapshot)

        report = project_report.construir_reporte(snapshot)
        if not report.get("ok"):
            raise RuntimeError(f"P8E2R001: P7C bloqueado: {report}")
        paths["report"].write_text(str(report["html"]), encoding="utf-8")

        reconstruction = _p7b_isolated(
            paths["snapshot"],
            paths["reconstructed"],
            paths["reconstruction"],
        )
        if reconstruction.get("status") != P7B_OK:
            raise RuntimeError(f"P8E2B001: P7B aislado no verificó round-trip: {reconstruction}")

        circuit_after = _active_circuit()
        revision_after = workspace_state.status().get("model_revision")
        if circuit_after != circuit_before or revision_after != revision_before:
            raise RuntimeError(
                "P8E2ISO001: la verificación P7B aislada alteró el circuito/revisión del proceso principal."
            )

        return {
            "schema": SCHEMA,
            "status": STATUS_READY,
            "manifest_sha256": manifest_sha,
            "model_revision": revision_after,
            "active_circuit_preserved": True,
            "p8d2_execution_status": execution.get("execution_status"),
            "workspace": {
                "status": "WORKSPACE_V5_READY",
                "path": str(paths["workspace"]),
                "p8d2_integrated_view": True,
                "browser_engineering_calculation": False,
            },
            "p7a": {
                "status": verification.get("status"),
                "snapshot_path": str(paths["snapshot"]),
                "sha256": (snapshot.get("hash") or {}).get("value"),
            },
            "p7b": {
                "status": reconstruction.get("status"),
                "result_path": str(paths["reconstruction"]),
                "isolated_process": True,
                "stored_results_promoted_to_current": False,
            },
            "p7c": {
                "status": report.get("status"),
                "report_path": str(paths["report"]),
                "report_sha256": (report.get("report_hash") or {}).get("value"),
                "source_snapshot_sha256": (report.get("data") or {}).get("source_snapshot", {}).get("sha256"),
                "browser_engineering_calculation": False,
            },
            "trace_files": {
                "manifest": str(paths["manifest"]),
                "execution_p8d2": str(paths["execution"]),
            },
            "automatic_dispatch": False,
            "automatic_fault_binding": False,
            "p4_recalculation_inside_p5": False,
            "crosscheck": False,
            "professional_report": False,
            "professional_emission": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": STATUS_FAILED_ARTIFACT,
            "manifest_sha256": manifest_sha,
            "error": str(exc),
            "output_directory": str(target),
            "active_circuit_preserved": _active_circuit() == circuit_before,
            "model_revision_preserved": workspace_state.status().get("model_revision") == revision_before,
            "p7b_isolated": True,
            "automatic_dispatch": False,
            "crosscheck": False,
            "professional_emission": False,
        }
