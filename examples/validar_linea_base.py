"""Valida en un solo comando la línea base local de MCP Eléctrico.

Ejecuta, en procesos aislados y en este orden:
1. diagnostico_local.py
2. primer_uso.py
3. caso_referencia_01.py
4. ejecutar_caso_minimo.py sobre la plantilla incluida

No implementa cálculos eléctricos nuevos. Orquesta ejecutables existentes y
construye un manifiesto de estados, rutas y huellas SHA-256 de artefactos.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "MCP_ELECTRICO_LOCAL_BASELINE_V1"


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _git_commit() -> str | None:
    try:
        done = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if done.returncode == 0:
            value = done.stdout.strip()
            return value or None
    except Exception:
        pass
    return None


def _run_stage(
    *,
    stage_id: str,
    description: str,
    command: list[str],
    result_json: Path,
    success_key: str,
    expected_artifacts: list[Path],
    output_root: Path,
    timeout: int,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        returncode = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
        execution_error = None
    except subprocess.TimeoutExpired as exc:
        returncode = 124
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        execution_error = f"TimeoutExpired: límite {timeout}s"
    except Exception as exc:
        returncode = 125
        stdout = ""
        stderr = ""
        execution_error = f"{type(exc).__name__}: {exc}"

    payload, read_error = _read_json(result_json)
    semantic_success = bool(payload and payload.get(success_key) is True)
    artifacts = []
    for path in expected_artifacts:
        try:
            relative = str(path.resolve().relative_to(output_root.resolve()))
        except ValueError:
            relative = str(path.resolve())
        artifacts.append(
            {
                "path": relative,
                "exists": path.is_file(),
                "size_bytes": path.stat().st_size if path.is_file() else None,
                "sha256_raw_file": _sha256(path),
            }
        )

    success = (
        returncode == 0
        and semantic_success
        and read_error is None
        and all(item["exists"] for item in artifacts)
    )
    return {
        "id": stage_id,
        "description": description,
        "status": "PASS" if success else "FAIL",
        "success": success,
        "command": [str(item) for item in command],
        "returncode": returncode,
        "success_key": success_key,
        "semantic_success": semantic_success,
        "result_json": str(result_json.resolve().relative_to(output_root.resolve())),
        "result_schema": payload.get("schema") if payload else None,
        "read_error": read_error,
        "execution_error": execution_error,
        "stdout_tail": stdout[-4000:],
        "stderr_tail": stderr[-4000:],
        "artifacts": artifacts,
    }


def run(output_dir: str | Path = "salida_validacion_local", timeout: int = 180) -> dict[str, Any]:
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    diag_dir = out / "01_diagnostico"
    first_dir = out / "02_primer_uso"
    ref_dir = out / "03_ref01"
    minimal_dir = out / "04_caso_minimo"
    for folder in (diag_dir, first_dir, ref_dir, minimal_dir):
        folder.mkdir(parents=True, exist_ok=True)

    diag_json = diag_dir / "diagnostico_local.json"
    first_json = first_dir / "resultado_primer_uso.json"
    ref_json = ref_dir / "resultado_caso_referencia_01.json"
    minimal_json = minimal_dir / "resultado_caso_minimo.json"

    py = sys.executable
    stages = [
        _run_stage(
            stage_id="diagnostico_local",
            description="Preflight de Python, dependencias, OpenDSS, API pública y gates",
            command=[py, str(ROOT / "examples" / "diagnostico_local.py"), "--output", str(diag_json)],
            result_json=diag_json,
            success_key="ok",
            expected_artifacts=[diag_json],
            output_root=out,
            timeout=timeout,
        ),
        _run_stage(
            stage_id="primer_uso",
            description="Smoke integral y workspace MT/BT",
            command=[py, str(ROOT / "examples" / "primer_uso.py"), "--output-dir", str(first_dir)],
            result_json=first_json,
            success_key="ok",
            expected_artifacts=[first_json, first_dir / "workspace_primer_uso.html"],
            output_root=out,
            timeout=timeout,
        ),
        _run_stage(
            stage_id="ref01",
            description="Patrón oro numérico independiente P1",
            command=[py, str(ROOT / "examples" / "caso_referencia_01.py"), "--output", str(ref_json)],
            result_json=ref_json,
            success_key="pass",
            expected_artifacts=[ref_json],
            output_root=out,
            timeout=timeout,
        ),
        _run_stage(
            stage_id="caso_minimo",
            description="Primer caso JSON editable radial P1",
            command=[
                py,
                str(ROOT / "examples" / "ejecutar_caso_minimo.py"),
                str(ROOT / "examples" / "caso_minimo.json"),
                "--output-dir",
                str(minimal_dir),
            ],
            result_json=minimal_json,
            success_key="ok",
            expected_artifacts=[
                minimal_json,
                minimal_dir / "caso_entrada_normalizado.json",
                minimal_dir / "workspace_caso_minimo.html",
            ],
            output_root=out,
            timeout=timeout,
        ),
    ]

    all_pass = all(stage["success"] for stage in stages)
    manifest_path = out / "manifiesto_linea_base.json"
    result = {
        "schema": SCHEMA,
        "ok": all_pass,
        "status": "PASS" if all_pass else "FAIL",
        "runtime": {
            "python_version": platform.python_version(),
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "git_commit": _git_commit(),
        },
        "policy": {
            "electrical_logic_added_by_orchestrator": False,
            "automatic_dispatch": False,
            "crosscheck": False,
            "professional_emission": False,
        },
        "summary": {
            "total_stages": len(stages),
            "passed": sum(stage["success"] for stage in stages),
            "failed": sum(not stage["success"] for stage in stages),
        },
        "stages": stages,
        "artifact_hash_note": (
            "sha256_raw_file identifica exactamente el archivo generado en esta ejecución. "
            "Algunos artefactos contienen rutas absolutas, por lo que su hash no se usa como "
            "criterio de equivalencia entre equipos."
        ),
        "outputs": {"manifest": str(manifest_path)},
    }
    manifest_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Validar línea base local de MCP Eléctrico")
    parser.add_argument(
        "--output-dir",
        default="salida_validacion_local",
        help="Carpeta raíz de la validación (default: salida_validacion_local)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Timeout máximo por etapa en segundos (default: 180)",
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout debe ser mayor que cero")

    result = run(args.output_dir, args.timeout)
    compact = {
        "schema": result["schema"],
        "ok": result["ok"],
        "status": result["status"],
        "summary": result["summary"],
        "stages": [{"id": s["id"], "status": s["status"]} for s in result["stages"]],
        "manifest": result["outputs"]["manifest"],
    }
    print(json.dumps(compact, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
