"""Published feeders: real MCP, independent AC Newton and 100 line outages."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import re
import sys
import urllib.request
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from published_feeder_reference import ROOT, load_case, manifest, reference, compare, disconnected_loads


def check_upstream(case):
    url=f"https://raw.githubusercontent.com/MATPOWER/matpower/{case['upstream_commit']}/data/{case['case']}.m"
    with urllib.request.urlopen(url,timeout=30) as response:
        raw=response.read()
    text=raw.decode("utf8")
    for name in ("bus","branch","gen"):
        block=re.search(r"mpc\."+name+r"\s*=\s*\[(.*?)\];",text,re.S).group(1)
        rows=[]
        for line in block.splitlines():
            line=line.split("%")[0].strip().rstrip(";")
            if line:
                rows.append([float(value) for value in line.split()])
        assert rows==case[name],f"Numeric facts differ from pinned upstream {name}"
    assert float(re.search(r"mpc\.baseMVA\s*=\s*([\d.]+)",text).group(1))==case["base_mva"]
    return {"url":url,"sha256":hashlib.sha256(raw).hexdigest(),"all_numeric_tables_equal":True}


async def verify(output,verify_upstream=False):
    output.mkdir(parents=True,exist_ok=False)
    calls,results,outages,gaps,legacy,sources=[],[],[],[],[],[]
    params=StdioServerParameters(command=sys.executable,args=["-X","utf8",str(ROOT/"server.py")],
                                cwd=str(output),env=dict(os.environ,PYTHONUTF8="1"))
    with (output/"MCP-stderr.log").open("w",encoding="utf8") as err:
        async with stdio_client(params,errlog=err) as (read,write):
            async with ClientSession(read,write) as client:
                await client.initialize()
                async def call(name,args,expect_error=False):
                    response=await client.call_tool(name,arguments=args)
                    if expect_error:
                        assert response.isError,response
                        calls.append({"tool":name,"tool_error_expected":True})
                        return None
                    assert not response.isError,response
                    data=response.structuredContent
                    if data is None:
                        data=json.loads(next(item.text for item in response.content if item.type=="text"))
                    calls.append({"tool":name,"status":data.get("status",data.get("execution_status"))})
                    return data

                for name in ("case33bw","case69"):
                    case=load_case(name)
                    sources.append(check_upstream(case) if verify_upstream else {"url":case["source_url"],"verification":"NOT_REQUESTED"})
                    folder=output/name
                    folder.mkdir()
                    original_ref=reference(case)
                    # Expose legacy default representation without asserting equivalence.
                    built=await call("construir_modelo_rev0",{"manifest":manifest(case,explicit_boundary=False)})
                    assert built["materializer_status"]=="MODEL_BUILT_NOT_EXECUTED",built
                    old=await call("analizar_flujo_operacion",{})
                    legacy.append({"case":name,"settings":"LEGACY_DEFAULT_SOURCE_AND_LOAD_VOLTAGE_RANGE",
                                   "loss_kw":old["powerflow"]["perdidas_totales_kw"],
                                   "reference_loss_kw":original_ref["loss_kw"],
                                   "loss_difference_kw":abs(old["powerflow"]["perdidas_totales_kw"]-original_ref["loss_kw"])})
                    for factor in (.5,1.,1.25):
                        inputs=manifest(case,factor)
                        built=await call("construir_modelo_rev0",{"manifest":inputs})
                        assert built["materializer_status"]=="MODEL_BUILT_NOT_EXECUTED",built
                        assert not built["source_p2_materialized"] and not built["solve_performed"]
                        flow=await call("ejecutar_estudio",{"estudio":"flujo"})
                        assert flow["selected_engine"]=="opendss"
                        detail=await call("analizar_flujo_operacion",{})
                        drops=await call("ejecutar_estudio",{"estudio":"caida_tension","parametros":{"limite_pct":3.}})
                        expected=reference(case,factor)
                        checks=compare(flow["result"],detail,drops["result"],expected)
                        assert checks["passed"],(name,factor,checks)
                        assert detail["resumen"]["cargabilidad_max_pct"] is None
                        assert all(row["cargabilidad_pct"] is None for row in detail["alimentadores"])
                        results.append({"case":name,"load_factor":factor,**checks,
                                        "minimum_voltage_pu":min(expected["voltages_pu"].values()),
                                        "minimum_voltage_bus":min(expected["voltages_pu"],key=expected["voltages_pu"].get),
                                        "reference_loss_kw":expected["loss_kw"],
                                        "opendss_loss_kw":flow["result"]["perdidas_totales_kw"],
                                        "bus_count":len(expected["voltages_pu"]),"branch_count":len(expected["branches"])})
                        (folder/f"factor-{factor}.json").write_text(json.dumps(
                            {"Inputs":inputs,"PublicFlow":flow,"Detail":detail,"VoltageDrop":drops,"Reference":expected,"Comparison":checks},
                            indent=2,allow_nan=False),encoding="utf8")
                    await call("construir_modelo_rev0",{"manifest":manifest(case)})
                    await call("ejecutar_estudio",{"estudio":"flujo"})
                    for i,row in enumerate(case["branch"]):
                        if int(row[10])!=1:
                            continue
                        item=await call("simular_perdida_alimentador",{"nombre_elemento":f"Line.b{i+1}","restaurar":True})
                        expected=disconnected_loads(case,i)
                        assert item["convergio"], (name,i,"Contingency did not converge; service voltages cannot be qualified")
                        actual=sorted(item["cargas_criticas_sin_tension"])
                        assert actual==expected,(name,i,actual,expected)
                        assert item["estado_final_elemento"]=="cerrado" and item["convergio_estado_restaurado"]
                        outages.append({"case":name,"branch":f"Line.b{i+1}","expected_unserved_loads":expected,
                                        "actual_unserved_loads":actual,"contingency_solver_converged":item["convergio"],
                                        "base_restored_and_converged":True,"service_criterion":"FAIL" if actual else "PASS"})
                    restored=await call("ejecutar_estudio",{"estudio":"flujo"})
                    assert restored["result"]["perdidas_totales_kw"]==next(r["opendss_loss_kw"] for r in results if r["case"]==name and r["load_factor"]==1.)
                    sc=await call("ejecutar_estudio",{"estudio":"iec60909","tipo_falla":"three_phase","parametros":{"bus_falla":"n2"}})
                    assert not sc["result"]["electrical_calculation_executed"]
                    amp=await call("ejecutar_estudio",{"estudio":"ampacidad","parametros":{"nombre_elemento":"Line.b1"}})
                    assert amp["result"]["status"]=="DATOS_INSUFICIENTES"
                    await call("ejecutar_cortocircuito",{"bus_falla":"n2"},expect_error=True)
                    for study in ("armonicos","series_temporales","actuacion_reles","dinamica_scr","protection_coordination"):
                        blocked=await call("ejecutar_estudio",{"estudio":study})
                        assert not blocked["executor_invoked"] and blocked["status"]=="BLOCKED_PARAMETERS"
                    gaps.append({"case":name,"iec60909":"BLOCKED_NO_UTILITY_FAULT_EQUIVALENT_OR_REVIEW",
                                 "faultstudy":"BLOCKED_PF_ONLY_SOURCE","ampacity":"INSUFFICIENT_DATA",
                                 "loading":"NOT_EVALUABLE_NO_RATINGS","other_packages":"NOT_PROVIDED",
                                 "transformer_unbalance_validation":"NOT_COVERED_BY_THESE_CASES"})
                    await call("obtener_netlist",{"directorio":str(folder/"Netlist")})
                    (folder/"Inputs.json").write_text(json.dumps(manifest(case),indent=2),encoding="utf8")
    paths=["mcp_electrico/real_model_materializer.py","mcp_electrico/power_flow_boundaries.py",
           "mcp_electrico/runtime_safety.py","scripts/published_feeder_reference.py","scripts/verify_external_feeders_mcp.py","server.py"]
    evidence={"schema":"MCP_EXTERNAL_FEEDER_QUALIFICATION_V1","ok":True,"transport":"MCP_STDIO",
              "checked_at_utc":datetime.now(timezone.utc).isoformat(),
              "software":{key:metadata.version(key) for key in ("mcp","opendssdirect.py","dss-python","dss-python-backend","PYPOWER","numpy","scipy")},
              "sources":sources,"cases":results,"legacy_representation_diagnostics":legacy,"outage_count":len(outages),
              "outages":outages,"all_contingency_solves_converged":all(item["contingency_solver_converged"] for item in outages),
              "scope_gaps":gaps,"call_count":len(calls),"calls":calls,
              "source_sha256":{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
              "approval":"BENCHMARK_INTEGRATION_ONLY_NOT_CUSTOMER_PROJECT_APPROVAL",
              "production_engine":"OpenDSS","reference_engine":"PYPOWER_VALIDATION_ONLY"}
    (output/"Evidence.json").write_text(json.dumps(evidence,indent=2,allow_nan=False),encoding="utf8")
    inventory={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
               for p in output.rglob("*") if p.is_file() and p.name!="MCP-stderr.log"}
    (output/"Integrity.json").write_text(json.dumps({"files_sha256":inventory},indent=2),encoding="utf8")
    brief={key:evidence[key] for key in ("ok","software","cases","legacy_representation_diagnostics","outage_count","all_contingency_solves_converged","scope_gaps","call_count","source_sha256","sources")}
    print("QUALIFICATION_SUMMARY_JSON="+json.dumps(brief,allow_nan=False))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--verify-upstream",action="store_true")
    args=parser.parse_args()
    asyncio.run(verify(args.output.resolve(),args.verify_upstream))
