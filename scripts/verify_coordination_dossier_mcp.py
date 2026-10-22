"""Public MCP acceptance of optional temporal ranges in a complete dossier."""
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
    manifest = json.loads((ROOT / "examples/p10_reference_coordination_range.json").read_text(encoding="utf8"))
    calls, deliveries = [], []
    parameters = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")],
                                       cwd=str(output), env=dict(os.environ, PYTHONUTF8="1"))
    with (output / "MCP-stderr.log").open("w", encoding="utf8") as log:
        async with stdio_client(parameters, errlog=log) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=120)) as client:
                await client.initialize()
                async def call(name, arguments):
                    response = await client.call_tool(name, arguments)
                    assert not response.isError, response
                    result = response.structuredContent or json.loads(next(c.text for c in response.content if c.type == "text"))
                    entry = {"tool": name, "arguments": arguments, "result": result}
                    calls.append(entry)
                    (output / f"call-{len(calls):03d}.json").write_text(
                        json.dumps(entry, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf8")
                    return result

                for name, failed in (("base", False), ("failed-design", True)):
                    package = deepcopy(manifest)
                    if failed:
                        package["protection"]["coordination_ranges"][0]["required_margin_s"] = 100
                    delivery = await call("generar_dossier_piloto_real", {
                        "manifest": package, "directorio_salida": str(output / name)})
                    assert delivery["status"] == "DOSSIER_READY_ENGINEERING_PREVIEW", delivery
                    status = "FAIL" if failed else "PASS"
                    assert delivery["coordination_ranges"]["status"] == status
                    assessment = delivery["design_assessment"]
                    assert assessment["calculation_valid"]
                    assert assessment["status"] == ("DECLARED_CHECKS_FAILED" if failed else "DECLARED_CHECKS_PASSED")
                    assert any(c["scope"] == "TEMPORAL_COORDINATION_RANGE" and c["status"] == status
                               for c in assessment["checks"])
                    summary = json.loads(Path(delivery["coordination_ranges_path"]).read_text(encoding="utf8"))
                    assert summary == delivery["coordination_ranges"]
                    assert summary["manifest_sha256"] == delivery["manifest_sha256"]
                    assert summary["model_revision"] == delivery["model_revision"]
                    assert summary["executor_invocation_count"] == 1
                    assert summary["p4_recalculation_inside_p5"] is False
                    assert summary["ranges"][0]["result_usable"]
                    assert not summary["selectivity_integral_evaluated"]
                    for path in (delivery["workspace"]["path"], delivery["p7c"]["report_path"]):
                        html = Path(path).read_text(encoding="utf8")
                        assert 'data-module="mcp-coordination-ranges"' in html
                        assert "LV_SERIES_PAIR" in html and "Peor margen" in html
                    integrity = await call("verificar_integridad_dossier_real", {
                        "ruta_indice": delivery["integrity"]["index_path"]})
                    assert integrity["ok"]
                    deliveries.append(delivery)

                shutil.copytree(output / "failed-design", output / "tamper-check")
                (output / "tamper-check/coordination_ranges.json").write_text("{}", encoding="utf8")
                altered = await call("verificar_integridad_dossier_real", {
                    "ruta_indice": str(output / "tamper-check/dossier_integrity.json")})
                assert not altered["ok"]

                currents = deliveries[0]["coordination_ranges"]["ranges"][0]["result"]["currents"]
                low, high = currents["downstream_min_a"], currents["downstream_max_a"]
                a, b = low + .4 * (high - low), low + .6 * (high - low)
                point = lambda i: {"current_a": i, "time_min_s": 3, "time_max_s": 4}
                gap = deepcopy(manifest)
                gap["protection"]["tcc_datasets"][-1]["segments"] = [
                    {"id": "low", "points": [point(800), point(a)]},
                    {"id": "high", "points": [point(b), point(120000)]}]
                rejected = await call("generar_dossier_piloto_real", {
                    "manifest": gap, "directorio_salida": str(output / "gap-rejected")})
                assert rejected["status"] == "BLOCKED_BY_P8D2_EXECUTION", rejected
                assert rejected["p8d2_execution"]["coordination_ranges"]["status"] == "NOT_EVALUABLE"
                assert not (output / "gap-rejected").exists()

                invalid = deepcopy(manifest)
                invalid["protection"]["coordination_ranges"][0]["current_bounds"]["minimum"]["case"] = "max"
                rejected_input = await call("generar_dossier_piloto_real", {
                    "manifest": invalid, "directorio_salida": str(output / "input-rejected")})
                assert rejected_input["status"] == "BLOCKED_BY_P8D2_EXECUTION"
                assert not rejected_input["p8d2_execution"]["electrical_calculation_performed"]
                assert not (output / "input-rejected").exists()
                repeated = await call("generar_dossier_piloto_real", {
                    "manifest": manifest, "directorio_salida": str(output / "base")})
                assert repeated["output_directory_collision_avoided"]
                assert Path(repeated["output_directory"]) == output / "base_2"
                assert repeated["coordination_ranges"]["status"] == "PASS"
                preserved = await call("verificar_integridad_dossier_real", {
                    "ruta_indice": deliveries[0]["integrity"]["index_path"]})
                assert preserved["ok"]

    summary = {"schema": "MCP_ELECTRICO_COORDINATION_DOSSIER_ACCEPTANCE_V1", "passed": True,
               "reference": "CONTROLLED_SYNTHETIC_NOT_FIELD_INSTALLATION", "call_count": len(calls),
               "pass_and_failed_design_preserved": True, "internal_gap_blocked": True,
               "invalid_input_blocked_before_calculation": True, "repeat_preserves_original": True,
               "tampered_range_trace_detected": True, "installation_validation_closed": False,
               "sources_sha256": {p: sha256((ROOT / p).read_bytes()).hexdigest() for p in (
                   "mcp_electrico/real_coordination_execution.py", "mcp_electrico/real_protection_execution.py",
                   "mcp_electrico/execution_quality.py", "mcp_electrico/real_project_dossier.py",
                   "examples/p10_reference_coordination_range.json")},
               "call_files_sha256": {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(output.glob("call-*.json"))}}
    (output / "Summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf8")
    print(json.dumps({"passed": True, "call_count": len(calls), "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(asyncio.wait_for(verify(parser.parse_args().output), timeout=600))
