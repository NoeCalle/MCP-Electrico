"""Verify explicit harmonic studies through MCP stdio against independent RL/C data."""
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
from harmonics_reference import analytical, reference_package

ROOT = Path(__file__).resolve().parents[1]


async def verify(output):
    output.mkdir(parents=True, exist_ok=False)
    checks = []
    calls = []
    params = StdioServerParameters(command=sys.executable, args=["-X", "utf8", str(ROOT/"server.py")],
                                  cwd=str(output), env=dict(os.environ, PYTHONUTF8="1"))
    with (output/"MCP-stderr.log").open("w", encoding="utf8") as err:
        async with stdio_client(params, errlog=err) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                names = {item.name for item in (await client.list_tools()).tools}
                assert {"obtener_contrato_armonicos", "validar_armonicos", "ejecutar_armonicos"} <= names

                async def call(name, args):
                    response = await client.call_tool(name, arguments=args)
                    assert not response.isError, response
                    data = response.structuredContent
                    if data is None:
                        text = next(c.text for c in response.content if c.type == "text")
                        try:
                            data = json.loads(text)
                        except json.JSONDecodeError:
                            data = {"message": text}
                    calls.append({"tool": name, "status": data.get("status"),
                                  "results_valid": data.get("results_valid")})
                    return data

                contract = await call("obtener_contrato_armonicos", {})
                assert not contract["physical_solver_owned_by_mcp"]
                await call("crear_circuito", {"nombre": "harmonics_parent", "kv_base": 12.47, "frecuencia": 60})
                parent = await call("obtener_estado_workspace", {})
                invalid = reference_package()
                invalid["orders"] = [3, 5]
                blocked = await call("ejecutar_armonicos", {"paquete_estudio": invalid,
                                      "directorio_salida": str(output/"must-not-exist")})
                assert blocked["status"] == "BLOCKED_HARMONICS_INPUTS"
                assert not (output/"must-not-exist").exists()
                for frequency in (50, 60):
                    for connection in ("wye", "delta"):
                        for enabled in (False, True):
                            for series in (0, 50, 100):
                                package = reference_package(frequency, connection, enabled, series)
                                case = f"{frequency}-{connection}-{int(enabled)}-{series}"
                                readiness = await call("validar_armonicos", {"paquete_estudio": package})
                                assert readiness["ready_for_execution"] and not readiness["electrical_calculation_performed"]
                                result = await call("ejecutar_armonicos", {"paquete_estudio": package,
                                                    "directorio_salida": str(output/case)})
                                assert result["results_valid"] and not result["parent_model_mutated"], result
                                voltage_error = max(abs(row["buses"][1]["voltage_ln_v"][0]-analytical(package,row["order"])["voltage_v"])
                                                    for row in result["harmonics"])
                                impedance_error = max(abs(row["z_ohm"]-analytical(package,row["order"])["z_ohm"])
                                                      for row in result["scans"][0]["points"])
                                assert voltage_error <= 2e-6 and impedance_error <= 2e-7
                                checks.append({"case": case, "maximum_voltage_error_v": voltage_error,
                                               "voltage_tolerance_v": 2e-6,
                                               "maximum_impedance_error_ohm": impedance_error,
                                               "impedance_tolerance_ohm": 2e-7, "passed": True})
                sample = json.loads((ROOT/"examples/harmonics_stage1.json").read_text(encoding="utf8"))
                result = await call("ejecutar_armonicos", {"paquete_estudio": sample,
                                    "directorio_salida": str(output/"transformer-sample")})
                assert result["results_valid"], result
                assert parent == await call("obtener_estado_workspace", {})
    sources = ["mcp_electrico/harmonics.py", "mcp_electrico/motor_starting_static.py",
               "mcp_electrico/reactive_compensation.py", "scripts/harmonics_reference.py",
               "scripts/verify_harmonics_mcp.py"]
    evidence = {"ok": True, "transport": "MCP_STDIO", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
                "case_count": len(checks), "call_count": len(calls), "registered_tools": len(names),
                "reference_depends_on_adapter": False, "checks": checks, "calls": calls,
                "source_sha256": {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}}
    (output/"Evidence.json").write_text(json.dumps(evidence, indent=2, allow_nan=False), encoding="utf8")
    print(json.dumps({k: evidence[k] for k in ("ok", "case_count", "call_count", "registered_tools")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(verify(parser.parse_args().output.resolve()))
