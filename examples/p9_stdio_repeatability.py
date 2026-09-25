"""P9C — repetibilidad del dossier dentro de una única sesión MCP stdio.

Ejecuta tres veces el flujo público de dossier sobre el mismo servidor MCP,
verifica integridad en cada entrega y vuelve a verificar la primera después de
la tercera. No importa módulos eléctricos internos ni crea una ruta alternativa
de cálculo.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = REPO_ROOT / "examples" / "p8_first_use_manifest.json"
REQUIRED_TOOLS = {
    "obtener_contrato_p8f4_primer_uso",
    "evaluar_admision_piloto_real",
    "generar_dossier_piloto_real",
    "verificar_integridad_dossier_real",
}
P7B_OK = "RECONSTRUCTED_NETLIST_VERIFIED_WITH_REBIND_REQUIRED"
P7B_ISOLATION = "OPENDSS_NEW_CONTEXT"
DOSSIER_OK = "DOSSIER_READY_ENGINEERING_PREVIEW"
INTEGRITY_OK = "DOSSIER_INTEGRITY_VERIFIED"


def _json_from_tool_result(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        return structured

    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if not isinstance(text, str):
            continue
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise RuntimeError("P9C001: la tool MCP no devolvió un objeto JSON interpretable.")


def _server_environment() -> dict[str, str]:
    env = os.environ.copy()
    root = str(REPO_ROOT)
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = root if not current else root + os.pathsep + current
    return env


def _expected_output(requested: Path, iteration: int) -> Path:
    if iteration == 1:
        return requested
    return requested.with_name(f"{requested.name}_{iteration}")


def _execution_is_safe(execution: dict[str, Any], expected_output: Path, iteration: int) -> bool:
    p7b = execution.get("p7b") or {}
    output = Path(str(execution.get("output_directory") or "")).resolve()
    expected = expected_output.resolve()
    return bool(
        execution.get("status") == DOSSIER_OK
        and output == expected
        and execution.get("output_directory_collision_avoided") is (iteration > 1)
        and execution.get("active_circuit_preserved") is True
        and p7b.get("status") == P7B_OK
        and p7b.get("isolation_mode") == P7B_ISOLATION
        and p7b.get("isolated_context") is True
        and p7b.get("isolated_process") is False
        and p7b.get("parent_dss_context_mutated") is False
        and p7b.get("parent_structured_state_mutated") is False
        and p7b.get("stored_results_promoted_to_current") is False
        and execution.get("automatic_dispatch") is False
        and execution.get("automatic_fault_binding") is False
        and execution.get("crosscheck") is False
        and execution.get("professional_emission") is False
    )


async def ejecutar_repeatability(
    manifest: dict[str, Any],
    requested_output: Path,
    repetitions: int = 3,
) -> dict[str, Any]:
    if repetitions < 3:
        raise ValueError("P9C002: P9C exige al menos tres ejecuciones en la misma sesión.")

    params = StdioServerParameters(
        command=sys.executable,
        args=[str(REPO_ROOT / "server.py")],
        cwd=str(REPO_ROOT),
        env=_server_environment(),
    )

    result: dict[str, Any]
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            available = sorted(tool.name for tool in listed.tools)
            missing = sorted(REQUIRED_TOOLS - set(available))
            if missing:
                raise RuntimeError(f"P9C003: faltan tools públicas requeridas: {missing}")

            contract = _json_from_tool_result(
                await session.call_tool("obtener_contrato_p8f4_primer_uso", arguments={})
            )
            intake = _json_from_tool_result(
                await session.call_tool(
                    "evaluar_admision_piloto_real",
                    arguments={"manifest": manifest},
                )
            )
            if intake.get("intake_status") != "READY_TO_BUILD_MODEL":
                result = {
                    "schema": "MCP_ELECTRICO_P9C_STDIO_REPEATABILITY_V1",
                    "ok": False,
                    "stage": "ADMISSION",
                    "same_mcp_session": True,
                    "requested_repetitions": repetitions,
                    "intake": intake,
                    "professional_emission": False,
                }
            else:
                executions: list[dict[str, Any]] = []
                manifest_hashes: list[str] = []
                first_index: str | None = None

                for iteration in range(1, repetitions + 1):
                    execution = _json_from_tool_result(
                        await session.call_tool(
                            "generar_dossier_piloto_real",
                            arguments={
                                "manifest": manifest,
                                "directorio_salida": str(requested_output),
                            },
                        )
                    )

                    index_path = str((execution.get("integrity") or {}).get("index_path") or "")
                    verification = (
                        _json_from_tool_result(
                            await session.call_tool(
                                "verificar_integridad_dossier_real",
                                arguments={"ruta_indice": index_path},
                            )
                        )
                        if index_path
                        else {}
                    )
                    if iteration == 1:
                        first_index = index_path or None

                    expected_output = _expected_output(requested_output, iteration)
                    execution_ok = _execution_is_safe(execution, expected_output, iteration)
                    integrity_ok = bool(
                        verification.get("status") == INTEGRITY_OK
                        and verification.get("ok") is True
                    )
                    manifest_hash = str(execution.get("manifest_sha256") or "")
                    manifest_hashes.append(manifest_hash)
                    executions.append(
                        {
                            "iteration": iteration,
                            "ok": execution_ok and integrity_ok,
                            "execution_status": execution.get("status"),
                            "output_directory": execution.get("output_directory"),
                            "expected_output_directory": str(expected_output.resolve()),
                            "collision_avoided": execution.get("output_directory_collision_avoided"),
                            "manifest_sha256": manifest_hash,
                            "model_revision": execution.get("model_revision"),
                            "p7b_status": (execution.get("p7b") or {}).get("status"),
                            "p7b_isolation_mode": (execution.get("p7b") or {}).get("isolation_mode"),
                            "parent_dss_context_mutated": (execution.get("p7b") or {}).get(
                                "parent_dss_context_mutated"
                            ),
                            "parent_structured_state_mutated": (execution.get("p7b") or {}).get(
                                "parent_structured_state_mutated"
                            ),
                            "integrity_status": verification.get("status"),
                            "integrity_ok": verification.get("ok"),
                            "integrity_index": index_path,
                        }
                    )

                first_reverification = (
                    _json_from_tool_result(
                        await session.call_tool(
                            "verificar_integridad_dossier_real",
                            arguments={"ruta_indice": first_index},
                        )
                    )
                    if first_index
                    else {}
                )
                first_preserved = bool(
                    first_reverification.get("status") == INTEGRITY_OK
                    and first_reverification.get("ok") is True
                )
                unique_outputs = {
                    str(item.get("output_directory") or "")
                    for item in executions
                    if item.get("output_directory")
                }
                same_manifest = bool(
                    manifest_hashes
                    and all(value == manifest_hashes[0] and value for value in manifest_hashes)
                )
                all_runs_ok = all(bool(item.get("ok")) for item in executions)

                result = {
                    "schema": "MCP_ELECTRICO_P9C_STDIO_REPEATABILITY_V1",
                    "ok": bool(
                        all_runs_ok
                        and first_preserved
                        and same_manifest
                        and len(unique_outputs) == repetitions
                        and contract.get("automatic_retry") is False
                        and contract.get("automatic_repair") is False
                        and contract.get("professional_emission") is False
                    ),
                    "stage": "COMPLETE",
                    "same_mcp_session": True,
                    "server_entrypoint": "server.py",
                    "tool_transport": "MCP_STDIO_SERVER_PY",
                    "requested_repetitions": repetitions,
                    "completed_repetitions": len(executions),
                    "available_required_tools": sorted(REQUIRED_TOOLS),
                    "intake_status": intake.get("intake_status"),
                    "manifest_hash_stable": same_manifest,
                    "unique_output_directories": len(unique_outputs),
                    "first_delivery_reverified_after_final_run": first_preserved,
                    "p7b_required_isolation_mode": P7B_ISOLATION,
                    "executions": executions,
                    "automatic_retry": contract.get("automatic_retry"),
                    "automatic_repair": contract.get("automatic_repair"),
                    "professional_emission": False,
                }

    # Alcanzar este punto demuestra que ambos context managers cerraron la
    # sesión y el proceso stdio sin quedar colgados.
    result["clean_stdio_shutdown"] = True
    result["ok"] = bool(result.get("ok") and result["clean_stdio_shutdown"])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="P9C: tres dossiers consecutivos dentro de una única sesión MCP stdio"
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output-dir", default="salida_p9c_stdio/dossier")
    parser.add_argument("--summary", default=None)
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    requested_output = Path(args.output_dir).expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    result = asyncio.run(
        ejecutar_repeatability(
            manifest,
            requested_output=requested_output,
            repetitions=args.repetitions,
        )
    )
    result["manifest_path"] = str(manifest_path)
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)

    summary_path = (
        Path(args.summary).expanduser().resolve()
        if args.summary
        else requested_output.parent / f"{requested_output.name}_p9c_repeatability.json"
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(rendered, encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if result.get("ok") else 2)


if __name__ == "__main__":
    main()
