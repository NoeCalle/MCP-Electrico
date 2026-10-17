"""MCP presentation checks; optional saved native studies, no physics execution."""
import argparse
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


def fixtures(output):
    inputs = json.loads((ROOT/"examples/msl_motor_two.json").read_text(encoding="utf8"))
    inputs["source_reference"] = "PRESENTATION_FIXTURE_ONLY_NOT_ENGINE_OUTPUT"
    results = []
    for i,motor in enumerate(inputs["motors"]):
        results.append({"motor_id":motor["id"],"starting_method":"DOL","acceleration_time_s":.1+i*.1,
                        "minimum_voltage_pu":.72,"minimum_bus_voltage_pu":.96,"maximum_cycle_rms_current_a":120+i,
                        "verification":{"passed":True},"criterion":{"passed":i==0},
                        "trajectory":[{"time_s":.1+j*.02,"current_a":110+i+j,"speed_rad_s":j*10,
                                       "torque_nm":j*30-20,"voltage_pu":.72+j*.01,"bus_voltage_pu":.96+j*.005,
                                       "controller_voltage_reference_pu":1} for j in range(5)]})
    specs = []
    for name,status in [("presentation-values","MODELICA_MOTOR_STUDIES_COMPLETED"),("execution-failure","MODELICA_EXECUTION_FAILED")]:
        folder = output/name
        folder.mkdir()
        (folder/"Inputs.json").write_text(json.dumps(inputs),encoding="utf8")
        result = {"status":status,"backend":"OPENMODELICA_MSL_4_0_0","results":results if "COMPLETED" in status else [],
                  "failed_stage":"REFINED_SIMULATION","last_emitted_time_s":.12,
                  "files_sha256":{"Inputs.json":hashlib.sha256((folder/"Inputs.json").read_bytes()).hexdigest()}}
        (folder/"Results.json").write_text(json.dumps(result),encoding="utf8")
        specs.append({"case_id":name,"study_directory":str(folder)})
    return specs


async def verify(output, studies):
    output.mkdir(parents=True,exist_ok=False)
    specs = json.loads(studies.read_text(encoding="utf8")) if studies else fixtures(output)
    before = {str(Path(s["study_directory"])/name):hashlib.sha256((Path(s["study_directory"])/name).read_bytes()).hexdigest()
              for s in specs for name in ("Inputs.json","Results.json")}
    calls = []
    params = StdioServerParameters(command=sys.executable,args=["-X","utf8",str(ROOT/"server.py")],cwd=str(output),env=dict(os.environ,PYTHONUTF8="1"))
    with (output/"MCP-stderr.log").open("w",encoding="utf8") as log:
        async with stdio_client(params,errlog=log) as (rd,wr):
            async with ClientSession(rd,wr) as client:
                await client.initialize()
                names = {t.name for t in (await client.list_tools()).tools}
                assert {"obtener_contrato_informe_dinamica_modelica","generar_informe_dinamica_modelica","verificar_informe_dinamica_modelica"} <= names
                async def call(name,args):
                    response = await client.call_tool(name,arguments=args)
                    assert not response.isError, response
                    value = response.structuredContent or json.loads(next(c.text for c in response.content if c.type=="text"))
                    calls.append({"tool":name,"status":value.get("status"),"ok":value.get("ok")})
                    return value
                contract = await call("obtener_contrato_informe_dinamica_modelica",{})
                assert not contract["solver_executed"] and not contract["qualification_promoted"]
                await call("crear_circuito",{"nombre":"report-parent","kv_base":12.47,"frecuencia":60})
                parent = await call("obtener_estado_workspace",{})
                generated = await call("generar_informe_dinamica_modelica",{"estudios":specs,"directorio_salida":str(output/"Report")})
                assert generated["status"] == "MSL_REPORT_CREATED",generated
                checked = await call("verificar_informe_dinamica_modelica",{"directorio_informe":str(output/"Report")})
                assert checked["ok"] and not generated["solver_executed"]
                data = json.loads((output/"Report/ReportData.json").read_text(encoding="utf8"))
                preserved = 0
                for source,copied in zip(specs,data["cases"]):
                    original = json.loads((Path(source["study_directory"])/"Results.json").read_text(encoding="utf8"))
                    assert copied["result"] == original
                    preserved += sum(len(r.get("trajectory",[])) for r in original.get("results",[]))
                if not studies:
                    assert data["comparison"][0]["minimum_bus_voltage_pu"] == .96
                    assert data["comparison"][0]["minimum_voltage_pu"] == .72
                    assert data["comparison"][1]["design_criterion"] == "NO CUMPLE"
                    assert data["comparison"][2]["design_criterion"] == "NO EVALUABLE"
                blocked = await call("generar_informe_dinamica_modelica",{"estudios":[],"directorio_salida":str(output/"blocked")})
                assert blocked["status"] == "BLOCKED_MSL_REPORT_INPUTS" and not (output/"blocked").exists()
                blocked = await call("generar_informe_dinamica_modelica",{"estudios":specs,"directorio_salida":str(output/"Report")})
                assert blocked["status"] == "BLOCKED_MSL_REPORT_OUTPUT"
                assert parent == await call("obtener_estado_workspace",{})
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in before.items())
    evidence = {"ok":True,"transport":"MCP_STDIO","calls":calls,"call_count":len(calls),"registered_tools":len(names),
                "case_count":len(specs),"motor_count":generated["motor_count"],"preserved_trajectory_rows":preserved,
                "mode":"SAVED_NATIVE_STUDIES" if studies else "PRESENTATION_FIXTURES_NOT_PHYSICS",
                "solver_executed":False,"parent_model_preserved":True,"source_files_preserved":True,
                "checked_at_utc":datetime.now(timezone.utc).isoformat(),"source_file_hashes":before,
                "report_source_sha256":hashlib.sha256((ROOT/"mcp_electrico/motor_study_report.py").read_bytes()).hexdigest(),
                "report_files_sha256":generated["files_sha256"]}
    (output/"Evidence.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps({k:evidence[k] for k in ("ok","call_count","case_count","motor_count","preserved_trajectory_rows","mode")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--studies",type=Path,help="JSON list of explicit case_id/study_directory entries")
    args = parser.parse_args()
    asyncio.run(verify(args.output.resolve(),args.studies))
