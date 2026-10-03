"""Query the deterministic selector over MCP; no electrical studies are run."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def verify(output):
    output.mkdir(parents=True, exist_ok=True)
    params = StdioServerParameters(command=sys.executable, args=["-X", "utf8", str(ROOT / "server.py")],
                                  cwd=str(output), env=dict(os.environ, PYTHONUTF8="1"))
    sources = ["mcp_electrico/engine_selection.py", "mcp_electrico/study_readiness.py",
               "mcp_electrico/external_engine_catalogue.py", "mcp_electrico/professional_tools.py"]
    evidence = {"transport": "MCP_STDIO", "electrical_studies_executed": False, "calls": [],
                "checked_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources}}
    with (output / "MCP-stderr.log").open("w", encoding="utf8") as err:
        async with stdio_client(params, errlog=err) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                listing = await client.list_tools()
                evidence["registered_tools"] = len(listing.tools)

                async def call(tool, arguments):
                    response = await client.call_tool(tool, arguments=arguments)
                    if response.isError:
                        raise RuntimeError(str(response))
                    data = response.structuredContent or json.loads(next(c.text for c in response.content if c.type == "text"))
                    evidence["calls"].append({"tool": tool, "arguments": arguments, "result": data})
                    return data

                matrix = await call("obtener_capacidades_motores", {})
                planned = {name: cap for name, cap in matrix["studies"].items() if cap.get("planning_only")}
                assert len(planned) == 8
                for name, cap in planned.items():
                    selected = await call("seleccionar_motor_estudio", {"estudio": name, "permitir_experimental": True})
                    ready = await call("evaluar_preparacion_estudio", {"estudio": name, "permitir_experimental": True})
                    assert selected["selected_engine"] == cap["preferred"]
                    assert selected["executable"] is False and selected["professional_emission"] is False
                    assert ready["overall_status"] == "MODULE_NOT_READY" and ready["data_evaluated"] is False
                for name, expected in [("flujo", "opendss"), ("iec60909", "pandapower")]:
                    result = await call("seleccionar_motor_estudio", {"estudio": name})
                    assert result["selected_engine"] == expected
                evidence["ok"] = True
    (output / "Evidencia-selector-MCP.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf8")
    print(json.dumps({"ok": True, "calls": len(evidence["calls"]), "tools": evidence["registered_tools"], "planned_routes": len(planned)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(verify(parser.parse_args().output.resolve()))
