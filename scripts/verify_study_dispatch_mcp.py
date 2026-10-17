"""Verify public single-engine execution through a real MCP stdio connection."""
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
    output.mkdir(parents=True, exist_ok=False)
    calls, checks = [], []
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT/"server.py")],
                                  cwd=str(output), env=dict(os.environ, PYTHONUTF8="1"))
    with (output/"MCP-stderr.log").open("w", encoding="utf8") as err:
        async with stdio_client(params, errlog=err) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                names = {tool.name for tool in (await client.list_tools()).tools}

                async def call(name, args):
                    response = await client.call_tool(name, arguments=args)
                    assert not response.isError, response
                    data = response.structuredContent
                    if data is None:
                        data = json.loads(next(item.text for item in response.content if item.type == "text"))
                    calls.append({"tool": name, "study": args.get("estudio"),
                                  "status": data.get("status", data.get("execution_status")),
                                  "executor": data.get("execution_tool"), "invoked": data.get("executor_invoked")})
                    return data

                contract = await call("obtener_contrato_ejecucion_estudios", {})
                assert not contract["unavailable_tools"]
                assert not contract["fallback"] and contract["single_executor_per_request"]
                checks.append("Registered contracts and parameter schemas")
                for args in ({"estudio": "arc_flash"}, {"estudio": "iec60909"},
                             {"estudio": "flujo", "parametros": {"motor": "pandapower"}},
                             {"estudio": "dinamica_variador"}):
                    blocked = await call("ejecutar_estudio", args)
                    assert not blocked["executor_invoked"]
                checks.append("Unsupported, ambiguous and invalid requests do not invoke executors")

                await call("crear_circuito", {"nombre": "dispatch_fixture", "kv_base": .48, "frecuencia": 60})
                await call("agregar_linea", {"nombre": "f1", "bus1": "sourcebus", "bus2": "load",
                                             "longitud_km": .05, "fases": 3, "r1_ohm_km": .2, "x1_ohm_km": .08})
                await call("agregar_carga", {"nombre": "c1", "bus": "load", "kw": 30, "kvar": 10,
                                             "fases": 3, "kv": .48})
                flow = await call("ejecutar_estudio", {"estudio": "flujo"})
                direct = await call("ejecutar_flujo_potencia", {})
                assert flow["selected_engine"] == "opendss" and flow["result"] == direct
                assert direct["convergio"]
                voltage = await call("ejecutar_estudio", {"estudio": "caida_tension", "parametros": {"limite_pct": 1.0}})
                assert voltage["result"] == await call("analizar_caida_tension", {"limite_pct": 1.0})
                checks.append("OpenDSS flow and voltage drop equal explicit public execution")
                parent = await call("obtener_estado_workspace", {})
                for study, file in (("armonicos", "harmonics_stage1"), ("series_temporales", "time_series_stage1"),
                                    ("actuacion_reles", "relay_operation_stage1"), ("compensacion_reactiva", "reactive_compensation_stage1")):
                    package = json.loads((ROOT/f"examples/{file}.json").read_text(encoding="utf8"))
                    result = await call("ejecutar_estudio", {"estudio": study, "parametros": {
                        "paquete_estudio": package, "directorio_salida": str(output/file)}})
                    assert result["status"] == "EXECUTOR_RETURNED", result
                    assert "COMPLETED" in result["result"]["status"]
                    assert not result["result"]["parent_model_mutated"]
                    integrity = json.loads((output/file/"Integrity.json").read_text())
                    hashes = integrity.get("files_sha256", integrity.get("files", {}))
                    for name, digest in hashes.items():
                        assert hashlib.sha256((output/file/name).read_bytes()).hexdigest() == digest
                    checks.append(f"Native {study} execution, saved artifacts and parent model preservation")
                assert parent == await call("obtener_estado_workspace", {})
                for study, file in (("dinamica_arranque_directo", "msl_motor_dol"),
                                    ("dinamica_scr", "msl_motor_scr"), ("dinamica_simultanea", "msl_motor_two")):
                    package = json.loads((ROOT/f"examples/{file}.json").read_text(encoding="utf8"))
                    package["motors"][0]["electrical"]["rotor_resistance_ohm"] = -1
                    folder = output/file
                    result = await call("ejecutar_estudio", {"estudio": study, "parametros": {
                        "paquete_estudio": package, "directorio_salida": str(folder)}})
                    assert result["result"]["status"] == "BLOCKED_MODELICA_READINESS"
                    assert not folder.exists()
                checks.append("Modelica DOL, SCR and multimotor gates preserved; no new physical simulations")
                blocked = await call("ejecutar_estudio", {"estudio": "iec60909", "tipo_falla": "three_phase",
                                                         "parametros": {"bus_falla": "load"}})
                assert not blocked["result"]["electrical_calculation_executed"]
                checks.append("IEC 3F review gate cannot be bypassed")
                await call("definir_red_equivalente", {"kv_ll": .48, "scc_max_mva": 10., "x_r_max": 10.,
                           "scc_min_mva": 5., "x_r_min": 5., "fuente_referencia": "Synthetic dispatch integration fixture"})
                precheck = await call("evaluar_preparacion_cortocircuito_3ph", {
                    "bus_falla": "load", "line_endtemp_degree_c": {"Line.f1": 20.}})
                assert precheck["numerical_ready"], precheck
                review = {"model_sha256": precheck["model_sha256"], "uso_previsto": precheck["supported_scope"],
                          "calidad_datos": "SUPUESTOS_APROBADOS", "referencia_revision": "Synthetic integration test only",
                          "supuestos_aprobados": ["Synthetic source, line, PQ load and temperature; not a project study"],
                          "exclusiones_revisadas": [item["id"] for item in precheck["items_to_review"]]}
                sc = await call("ejecutar_estudio", {"estudio": "cortocircuito", "norma": "IEC 60909",
                    "tipo_falla": "three_phase", "parametros": {"bus_falla": "load",
                    "line_endtemp_degree_c": {"Line.f1": 20.}, "revision_modelo": review}})
                assert sc["selected_engine"] == "pandapower"
                assert sc["result"]["electrical_calculation_executed"], sc
                checks.append("Pandapower IEC 3F executes with explicitly reviewed synthetic inputs")
                manifest = json.loads((ROOT/"examples/p10_reference_substation_stage1.json").read_text())
                package = json.loads((ROOT/"examples/p12_operating_scenarios_reference.json").read_text())
                scenarios = await call("ejecutar_estudio", {"estudio": "N-1", "parametros": {
                    "manifest": manifest, "paquete_escenarios": package}})
                assert scenarios["result"]["summary"]["executed"] == 2
                assert scenarios["result"]["summary"]["fail"] == 1
                assert scenarios["result"]["model_restored_after_each_scenario"]
                checks.append("P12 restores declared manifest base and preserves failed design criterion")
    sources = ["mcp_electrico/study_dispatch.py", "mcp_electrico/engine_selection.py",
               "server.py", "scripts/verify_study_dispatch_mcp.py"]
    evidence = {"ok": True, "transport": "MCP_STDIO", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
                "registered_tools": len(names), "call_count": len(calls), "checks": checks, "calls": calls,
                "modelica_physical_simulations_performed": False,
                "source_sha256": {path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in sources}}
    (output/"Evidence.json").write_text(json.dumps(evidence, indent=2, allow_nan=False), encoding="utf8")
    print(json.dumps({key: evidence[key] for key in ("ok", "registered_tools", "call_count")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(verify(parser.parse_args().output.resolve()))
