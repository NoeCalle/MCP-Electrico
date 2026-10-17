"""Real MCP stdio verification of native Daily/Yearly profiles and energy."""
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
from time_series_reference import analytical, reference_package

ROOT = Path(__file__).resolve().parents[1]


async def verify(output):
    output.mkdir(parents=True, exist_ok=False)
    calls, checks = [], []
    params = StdioServerParameters(command=sys.executable, args=["-X", "utf8", str(ROOT/"server.py")],
                                  cwd=str(output), env=dict(os.environ, PYTHONUTF8="1"))
    with (output/"MCP-stderr.log").open("w", encoding="utf8") as err:
        async with stdio_client(params, errlog=err) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                names = {t.name for t in (await client.list_tools()).tools}
                assert {"obtener_contrato_series_temporales", "validar_series_temporales", "ejecutar_series_temporales"} <= names

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
                    calls.append({"tool": name, "status": data.get("status"), "results_valid": data.get("results_valid")})
                    return data

                contract = await call("obtener_contrato_series_temporales", {})
                assert not contract["physical_solver_owned_by_mcp"]
                route = await call("seleccionar_motor_estudio", {"estudio": "series_temporales"})
                assert route["selected_engine"] == "opendss" and not route["executable"]
                await call("crear_circuito", {"nombre": "temporal_parent", "kv_base": 12.47, "frecuencia": 60})
                parent = await call("obtener_estado_workspace", {})
                package = reference_package()
                package["load_profiles"][0]["q_multipliers"] = []
                invalid = await call("ejecutar_series_temporales", {"paquete_estudio": package,
                                     "directorio_salida": str(output/"must-not-exist")})
                assert invalid["status"] == "BLOCKED_TIME_SERIES_INPUTS"
                assert not (output/"must-not-exist").exists()
                for mode in ("daily", "yearly"):
                    for frequency in (50, 60):
                        for model in (1, 2):
                            for step in (.25, 1):
                                package = reference_package(mode, frequency, model, step, days=2)
                                name = f"{mode}-{frequency}-{model}-{step}"
                                ready = await call("validar_series_temporales", {"paquete_estudio": package})
                                assert ready["ready_for_execution"] and not ready["electrical_calculation_performed"]
                                result = await call("ejecutar_series_temporales", {"paquete_estudio": package,
                                                    "directorio_salida": str(output/name)})
                                assert result["results_valid"] and not result["parent_model_mutated"], result
                                shape = package["load_profiles"][0]
                                expected = [analytical(shape["p_multipliers"][i % len(shape["p_multipliers"])],
                                                       shape["q_multipliers"][i % len(shape["q_multipliers"])], model)
                                            for i in range(package["timeline"]["steps"])]
                                p_error = max(abs(r["source"]["p_kw"]-v["source_kw"]) for r,v in zip(result["results"], expected))
                                v_error = max(abs(r["buses"][1]["minimum_pu"]-v["voltage_pu"]) for r,v in zip(result["results"], expected))
                                energy = sum(v["source_kw"]*step for v in expected)
                                e_error = abs(result["summary"]["source_energy_kwh"]-energy)
                                assert p_error <= 2e-6 and v_error <= 2e-7 and e_error <= 2e-5
                                assert result["results"][-1]["interval_end_hour"] == 48
                                checks.append({"case": name, "steps": len(expected), "maximum_source_power_error_kw": p_error,
                                               "source_power_tolerance_kw": 2e-6, "maximum_voltage_error_pu": v_error,
                                               "voltage_tolerance_pu": 2e-7, "energy_error_kwh": e_error,
                                               "energy_tolerance_kwh": 2e-5, "passed": True})
                sample = json.loads((ROOT/"examples/time_series_stage1.json").read_text(encoding="utf8"))
                result = await call("ejecutar_series_temporales", {"paquete_estudio": sample,
                                    "directorio_salida": str(output/"transformer-two-loads")})
                assert result["results_valid"], result
                assert parent == await call("obtener_estado_workspace", {})
    sources = ["mcp_electrico/time_series.py", "mcp_electrico/reactive_compensation.py",
               "mcp_electrico/motor_starting_static.py", "scripts/time_series_reference.py",
               "scripts/verify_time_series_mcp.py"]
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
