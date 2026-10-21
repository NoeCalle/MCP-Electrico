"""Full public MCP delivery: valid design, failed design, blocked data, tampering.

Uses the controlled synthetic P10 substation, not a field installation. Fault
injection is separately tested at solver boundaries in test_execution_quality.
"""
import argparse
import asyncio
from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def verify(output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((ROOT/"examples/p10_reference_substation_stage5.json").read_text(encoding="utf8"))
    calls, deliveries = [], []
    parameters = StdioServerParameters(command=sys.executable, args=[str(ROOT/"server.py")],
                                      cwd=str(output), env=dict(os.environ, PYTHONUTF8="1"))
    with (output/"MCP-stderr.log").open("w", encoding="utf8") as log:
        async with stdio_client(parameters, errlog=log) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=300)) as client:
                await client.initialize()

                async def call(name, arguments):
                    response = await client.call_tool(name, arguments)
                    assert not response.isError, response
                    result = response.structuredContent or json.loads(next(c.text for c in response.content if c.type == "text"))
                    calls.append({"tool": name, "status": result.get("status", result.get("intake_status"))})
                    return result

                admission = await call("evaluar_admision_piloto_real", {"manifest": manifest})
                assert admission["ready_to_build_model"], admission
                for name, failed_design in (("base", False), ("failed-design", True)):
                    package = deepcopy(manifest)
                    if failed_design:
                        package["protection"]["devices"][0]["icu_ka"] = .001
                        package["protection"]["devices"][0]["ics_ka"] = .001
                        package["protection"]["devices"][0]["breaking_capacity_ka"] = .001
                    delivered = await call("generar_dossier_piloto_real", {
                        "manifest": package, "directorio_salida": str(output/name)})
                    assert delivered["status"] == "DOSSIER_READY_ENGINEERING_PREVIEW", delivered
                    assessment = delivered["design_assessment"]
                    assert assessment["calculation_valid"]
                    assert assessment["status"] == ("DECLARED_CHECKS_FAILED" if failed_design else "DECLARED_CHECKS_PASSED"), assessment
                    assert assessment["model_revision"] == delivered["model_revision"]
                    assert assessment["manifest_sha256"] == delivered["manifest_sha256"]
                    integrity = await call("verificar_integridad_dossier_real", {"ruta_indice": delivered["integrity"]["index_path"]})
                    assert integrity["ok"], integrity
                    execution = json.loads((output/name/"execution_p8d2.json").read_text(encoding="utf8"))
                    assert execution["p4_results_reused"] and not execution["p4_recalculation_inside_p5"]
                    assert execution["resultados_validos"]
                    assert not delivered["professional_emission"]
                    saved = json.loads((output/name/"design_checks.json").read_text(encoding="utf8"))
                    assert saved == assessment
                    deliveries.append({"name": name, "assessment": assessment,
                                       "manifest_sha256": delivered["manifest_sha256"],
                                       "model_revision": delivered["model_revision"],
                                       "integrity": integrity["status"],
                                       "snapshot_sha256": delivered["p7a"]["sha256"]})
                # Identical delivery request must create a distinct directory.
                repeated = await call("generar_dossier_piloto_real", {
                    "manifest": manifest, "directorio_salida": str(output/"base")})
                assert repeated["output_directory_collision_avoided"]
                assert Path(repeated["output_directory"]) == output/"base_2"
                assert repeated["manifest_sha256"] == deliveries[0]["manifest_sha256"]
                first = await call("verificar_integridad_dossier_real", {"ruta_indice": str(output/"base/dossier_integrity.json")})
                assert first["ok"]
                missing = deepcopy(manifest)
                del missing["source"]["scc_min_mva"]
                rejected = await call("generar_dossier_piloto_real", {
                    "manifest": missing, "directorio_salida": str(output/"rejected")})
                assert rejected["status"] == "BLOCKED_BY_P8D2_EXECUTION", rejected
                assert not (output/"rejected").exists()
                shutil.copytree(output/"failed-design", output/"tamper-check")
                tampered = output/"tamper-check/design_checks.json"
                tampered.write_text("{}", encoding="utf8")
                detected = await call("verificar_integridad_dossier_real", {
                    "ruta_indice": str(output/"tamper-check/dossier_integrity.json")})
                assert not detected["ok"], detected
                routed = await call("ejecutar_estudio", {"estudio": "falla_terminal_motor", "parametros": {
                    "paquete_estudio": {}, "directorio_salida": str(output/"invalid-motor")}})
                assert routed["execution_tool"] == "ejecutar_falla_terminal_motor_modelica"
                assert routed["result"]["status"] == "BLOCKED_MOTOR_FAULT_READINESS"
                assert not routed["fallback"] and not (output/"invalid-motor").exists()
    # tamper-check is a negative test; the original deliveries remain intact.
    summary = {"schema": "MCP_ELECTRICO_ENGINEERING_ACCEPTANCE_MCP_V1",
               "reference": "CONTROLLED_SYNTHETIC_P10_NOT_FIELD_INSTALLATION",
               "calls": calls, "call_count": len(calls), "deliveries": deliveries,
               "tampering_detected": True, "invalid_input_blocked": True,
               "repeat_preserves_first_delivery": True,
               "one_executor_per_study": True, "installation_validation_closed": False,
               "sources_sha256": {p: sha256((ROOT/p).read_bytes()).hexdigest() for p in (
                   "mcp_electrico/execution_quality.py", "mcp_electrico/real_controlled_execution.py",
                   "mcp_electrico/real_protection_execution.py", "examples/p10_reference_substation_stage5.json")}}
    (output/"Summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf8")
    print("ENGINEERING_ACCEPTANCE_SUMMARY="+json.dumps(summary, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(verify(parser.parse_args().output))
