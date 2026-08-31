"""P8F4 — primer uso del piloto real a través del servidor MCP público.

Levanta ``server.py`` por stdio usando el SDK MCP y ejecuta exclusivamente las
tools públicas de admisión, dossier e integridad. No importa módulos eléctricos
internos ni crea una ruta alternativa de cálculo.
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
    raise RuntimeError("P8F4MCP001: la tool MCP no devolvió un objeto JSON interpretable.")


def _server_environment() -> dict[str, str]:
    env = os.environ.copy()
    current = env.get("PYTHONPATH")
    root = str(REPO_ROOT)
    env["PYTHONPATH"] = root if not current else root + os.pathsep + current
    return env


async def ejecutar_smoke(manifest: dict[str, Any], requested_output: Path) -> dict[str, Any]:
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(REPO_ROOT / "server.py")],
        cwd=str(REPO_ROOT),
        env=_server_environment(),
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            available = sorted(tool.name for tool in listed.tools)
            missing = sorted(REQUIRED_TOOLS - set(available))
            if missing:
                raise RuntimeError(f"P8F4MCP002: faltan tools públicas requeridas: {missing}")

            contract = _json_from_tool_result(
                await session.call_tool("obtener_contrato_p8f4_primer_uso", arguments={})
            )
            intake = _json_from_tool_result(
                await session.call_tool("evaluar_admision_piloto_real", arguments={"manifest": manifest})
            )
            if intake.get("intake_status") != "READY_TO_BUILD_MODEL":
                return {
                    "schema": "MCP_ELECTRICO_P8F4_STDIO_SMOKE_V1",
                    "ok": False,
                    "stage": "ADMISSION",
                    "tool_transport": "MCP_STDIO_SERVER_PY",
                    "available_required_tools": sorted(REQUIRED_TOOLS),
                    "contract": contract,
                    "intake": intake,
                    "professional_emission": False,
                }

            execution = _json_from_tool_result(
                await session.call_tool(
                    "generar_dossier_piloto_real",
                    arguments={
                        "manifest": manifest,
                        "directorio_salida": str(requested_output),
                    },
                )
            )
            if execution.get("status") != "DOSSIER_READY_ENGINEERING_PREVIEW":
                return {
                    "schema": "MCP_ELECTRICO_P8F4_STDIO_SMOKE_V1",
                    "ok": False,
                    "stage": "EXECUTION",
                    "tool_transport": "MCP_STDIO_SERVER_PY",
                    "available_required_tools": sorted(REQUIRED_TOOLS),
                    "contract": contract,
                    "intake": intake,
                    "execution": execution,
                    "professional_emission": False,
                }

            index_path = ((execution.get("integrity") or {}).get("index_path"))
            if not index_path:
                raise RuntimeError("P8F4MCP003: ejecución READY sin ruta de índice P8F2.")
            integrity = _json_from_tool_result(
                await session.call_tool(
                    "verificar_integridad_dossier_real",
                    arguments={"ruta_indice": str(index_path)},
                )
            )

            ok = (
                integrity.get("status") == "DOSSIER_INTEGRITY_VERIFIED"
                and integrity.get("ok") is True
                and execution.get("professional_emission") is False
                and execution.get("automatic_dispatch") is False
                and execution.get("automatic_fault_binding") is False
                and execution.get("crosscheck") is False
                and contract.get("professional_emission") is False
                and contract.get("automatic_retry") is False
                and contract.get("automatic_repair") is False
            )
            return {
                "schema": "MCP_ELECTRICO_P8F4_STDIO_SMOKE_V1",
                "ok": ok,
                "stage": "COMPLETE" if ok else "INTEGRITY_OR_POLICY",
                "tool_transport": "MCP_STDIO_SERVER_PY",
                "server_entrypoint": "server.py",
                "available_required_tools": sorted(REQUIRED_TOOLS),
                "contract_schema": contract.get("schema"),
                "intake_status": intake.get("intake_status"),
                "execution_status": execution.get("status"),
                "integrity_status": integrity.get("status"),
                "manifest_sha256": execution.get("manifest_sha256"),
                "requested_output_directory": execution.get("requested_output_directory"),
                "output_directory": execution.get("output_directory"),
                "output_directory_collision_avoided": execution.get("output_directory_collision_avoided"),
                "integrity_index": index_path,
                "verified_file_count": integrity.get("verified_file_count"),
                "automatic_defaults": False,
                "automatic_dispatch": execution.get("automatic_dispatch"),
                "automatic_fault_binding": execution.get("automatic_fault_binding"),
                "crosscheck": execution.get("crosscheck"),
                "professional_emission": False,
            }


def main() -> None:
    parser = argparse.ArgumentParser(description="P8F4 smoke de primer uso por MCP stdio")
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="Manifiesto P8 completo. El ejemplo incluido es demostrativo, no datos de proyecto.",
    )
    parser.add_argument(
        "--output-dir",
        default="salida_p8_first_use/dossier",
        help="Directorio solicitado para el dossier. P8F3 evita sobrescritura silenciosa.",
    )
    parser.add_argument(
        "--summary",
        default=None,
        help="Ruta opcional del JSON resumen. Debe quedar fuera del dossier indexado.",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    requested_output = Path(args.output_dir).expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    result = asyncio.run(ejecutar_smoke(manifest, requested_output))
    result["manifest_path"] = str(manifest_path)
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)

    if args.summary:
        summary_path = Path(args.summary).expanduser().resolve()
    else:
        summary_path = requested_output.parent / f"{requested_output.name}_p8f4_smoke.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(text, encoding="utf-8")
    print(text)
    raise SystemExit(0 if result.get("ok") else 2)


if __name__ == "__main__":
    main()
