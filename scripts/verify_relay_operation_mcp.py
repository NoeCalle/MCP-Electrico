"""Real MCP stdio verification of native OCRelay operation and independent timing."""
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
from relay_operation_reference import CURVE_PARAMETERS, expected_time, reference_package

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
                assert {"obtener_contrato_actuacion_reles", "validar_actuacion_reles", "ejecutar_actuacion_reles"} <= names

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

                contract = await call("obtener_contrato_actuacion_reles", {})
                assert not contract["physical_solver_owned_by_mcp"]
                assert contract["qualification"]["verification_status"] == "VERIFIED_IN_SCOPE"
                route = await call("seleccionar_motor_estudio", {"estudio": "actuacion_reles"})
                assert route["selected_engine"] == "pandapower" and not route["executable"]
                assert route["module_status"]["integration_verification"] == "VERIFIED_IN_SCOPE"
                await call("crear_circuito", {"nombre": "relay_parent", "kv_base": 12.47, "frecuencia": 60})
                parent = await call("obtener_estado_workspace", {})
                bad = reference_package()
                bad["relays"][0]["settings"]["pickup_primary_a"] = 0
                invalid = await call("ejecutar_actuacion_reles", {"paquete_estudio": bad,
                                     "directorio_salida": str(output/"must-not-exist")})
                assert invalid["status"] == "BLOCKED_RELAY_OPERATION_INPUTS"
                assert not (output/"must-not-exist").exists()
                kinds = [("DTOC", "standard_inverse")]+[(k,c) for k in ("IDMT","IDTOC") for c in CURVE_PARAMETERS]
                for kind,curve in kinds:
                    for scenario in ("sc","pp"):
                        for breaker in (None,.05):
                            package = reference_package(kind,curve,scenario,breaker)
                            name = f"{kind}-{curve}-{scenario}-{breaker}"
                            ready = await call("validar_actuacion_reles", {"paquete_estudio": package})
                            assert ready["ready_for_execution"] and not ready["electrical_calculation_performed"]
                            result = await call("ejecutar_actuacion_reles", {"paquete_estudio": package,
                                               "directorio_salida": str(output/name)})
                            assert result["results_valid"] and not result["parent_model_mutated"], result
                            assert result["criteria"] == {"evaluated": True, "passed": True}
                            errors = []
                            for case,inputs in zip(result["results"],package["cases"]):
                                row = case["relays"][0]
                                current = inputs["currents"]["R1"]["primary_rms_a"]
                                time = expected_time(kind,curve,current)
                                assert row["trip_command"] == (time is not None)
                                assert row["native_switch_closed_after_command"] == (time is None)
                                if time is None:
                                    assert row["relay_operating_time_s"] is None and row["total_clearing_time_s"] is None
                                else:
                                    error = abs(time-row["relay_operating_time_s"])
                                    errors.append(error)
                                    assert error <= 1e-9*max(1,abs(time))
                                    if breaker is None:
                                        assert row["total_clearing_time_s"] is None
                                    else:
                                        assert abs(row["total_clearing_time_s"]-time-breaker) <= 1e-9*max(1,abs(time))
                            checks.append({"case": name,"points":12,"maximum_time_error_s":max(errors,default=0),
                                           "time_tolerance": "1e-9 * max(1, absolute_reference_seconds)","passed":True})
                sample = json.loads((ROOT/"examples/relay_operation_stage1.json").read_text(encoding="utf8"))
                result = await call("ejecutar_actuacion_reles", {"paquete_estudio": sample,
                                    "directorio_salida": str(output/"example")})
                assert result["results_valid"], result
                assert parent == await call("obtener_estado_workspace", {})
    sources = ["mcp_electrico/relay_operation.py", "scripts/relay_operation_reference.py",
               "scripts/verify_relay_operation_mcp.py"]
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
