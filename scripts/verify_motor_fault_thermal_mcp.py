"""Actual MCP execution and independent postfault-waveform/energy benchmarks."""
import argparse
import asyncio
from copy import deepcopy
from datetime import timedelta
import json
from math import pi
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from motor_fault_thermal_reference import compare_trace

ROOT = Path(__file__).resolve().parents[1]


async def verify(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    parameters = StdioServerParameters(command=sys.executable, args=[str(ROOT/"server.py")],
                                      cwd=str(ROOT), env=dict(os.environ, PYTHONUTF8="1"))
    calls, results = [], []
    with (output/"MCP-stderr.log").open("w", encoding="utf8") as log:
        async with stdio_client(parameters, errlog=log) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=1200)) as client:
                await client.initialize()
                async def call(name, arguments):
                    result = await client.call_tool(name, arguments)
                    if result.isError: raise RuntimeError(str(result))
                    value = result.structuredContent or json.loads(next(b.text for b in result.content if b.type == "text"))
                    calls.append(name)
                    return value
                rt = await call("configurar_dinamica_modelica", {"ruta_omc": str(args.omc.resolve()), "directorio_msl": str(args.msl.resolve())})
                fixture = json.loads((ROOT/"examples/qualification/motor_terminal_fault_emt.json").read_text(encoding="utf8"))
                invalid = deepcopy(fixture)
                invalid["machine"]["rotor_resistance_ohm"] = None
                rejected = await call("ejecutar_falla_terminal_motor_modelica", {"paquete_estudio": invalid, "directorio_salida": str(output/"Rejected")})
                assert rejected["status"] == "BLOCKED_MOTOR_FAULT_READINESS" and not (output/"Rejected").exists()
                for hz, angle in ((50, 0), (50, 37), (60, 0)):
                    package = deepcopy(fixture)
                    package.update(id=f"MSL-FAULT-{hz}HZ-{angle}DEG", frequency_hz=hz, angle_deg=angle,
                                   shaft_speed_rad_s=.98*2*pi*hz/package["machine"]["pole_pairs"])
                    directory = output/f"Fault-{hz}-{angle}"
                    ready = await call("validar_falla_terminal_motor_modelica", {"paquete_estudio": package})
                    assert ready["ready_for_execution"], ready
                    actual = await call("ejecutar_falla_terminal_motor_modelica", {"paquete_estudio": package, "directorio_salida": str(directory)})
                    assert actual["status"] == "MOTOR_FAULT_EMT_VERIFIED", actual
                    comparison = compare_trace(package, directory/"Refined.csv")
                    errors = [abs(a-b)/b for a,b in zip(actual["results"]["joule_integral_a2s_by_phase"], comparison["reference_joule_integral_a2s_by_phase"])]
                    # Limits fixed before running. No current/energy tuning to source results.
                    assert comparison["waveform_relative_error"] < .001, comparison
                    assert max(errors) < .001, errors
                    assert not actual["results_are_iec60909_ith"] and actual["computed_clearing_time_s"] is None
                    assert not actual["contract"]["installation_validation_closed"]
                    results.append({"id": package["id"], "comparison": comparison, "energy_relative_errors": errors,
                                    "actual": actual["results"], "refinement": actual["verification"]["energy_refinement_relative_errors"],
                                    "input_sha256": actual["input_sha256"]})
    summary = {"cases": results, "mcp_calls": len(calls), "calls": calls,
               "runtime": rt, "waveform_and_energy_relative_tolerance": .001,
               "independent_reference": "TEST_ONLY_COMPLEX_WINDING_MATRIX_EXPONENTIAL_AND_SCIPY_QUADRATURE",
               "installation_validation_closed": False, "iec60909_ith_promoted": False}
    (output/"Summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf8")
    print("MOTOR_FAULT_SUMMARY="+json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--omc", type=Path, required=True)
    parser.add_argument("--msl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
