"""Full public MCP execution of pinned Brno initial MAX faults; no field approval."""
import asyncio
from datetime import timedelta
import json
import math
import os
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT=Path(__file__).resolve().parents[1]

async def main():
    output=ROOT/"outputs/brno-sc3-research"
    inputs=json.loads((output/"mcp-inputs.json").read_text(encoding="utf8"))
    target=(output/"mcp").resolve();target.mkdir(exist_ok=False)
    calls=[];comparisons=[]
    params=StdioServerParameters(command=sys.executable,args=[str(ROOT/"server.py")],
        cwd=str(target),env=dict(os.environ,PYTHONUTF8="1"))
    with (target/"stderr.log").open("w",encoding="utf8") as log:
        async with stdio_client(params,errlog=log) as (read,write):
            async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=240)) as client:
                await client.initialize()
                catalog=await client.list_tools()
                async def call(name,args):
                    r=await client.call_tool(name,args)
                    if r.isError:raise AssertionError((name,r))
                    result=r.structuredContent
                    if result is None:
                        raw=next(c.text for c in r.content if c.type=="text")
                        try:result=json.loads(raw)
                        except json.JSONDecodeError:result=raw
                    calls.append({"tool":name,"arguments":args,"result":result})
                    return result
                for item in inputs["calls"]:
                    result=await call(item["tool"],item["arguments"])
                inventory=await call("obtener_fichas_maquinas_cortocircuito_3ph",{})
                assert not inventory["issues"],inventory
                assert len(inventory["loads"])==73
                for fault in inputs["faults"]:
                    request={"bus_falla":fault["mcp_bus"],"caso":"max","lv_tol_percent":6}
                    pre=await call("evaluar_preparacion_cortocircuito_3ph",request)
                    assert pre["numerical_ready"],pre
                    assert pre["requested_cases"]==["max"]
                    if not comparisons:
                        blocked=await call("ejecutar_cortocircuito_iec60909_3ph",request)
                        assert blocked["electrical_calculation_executed"] is False,blocked
                        pair=await call("evaluar_preparacion_cortocircuito_3ph",{"bus_falla":fault["mcp_bus"]})
                        assert not pair["numerical_ready"],"MIN must not be invented"
                    review={"model_sha256":pre["model_sha256"],"uso_previsto":pre["supported_scope"],
                        "calidad_datos":"MIXTOS",
                        "referencia_revision":"Automated reproduction of public academic model; research only, not plant-design approval",
                        "supuestos_aprobados":["Published model assumptions are retained for research comparison only.",
                            "Nominal equivalent motor Sn and locked-rotor Z are explicit; zero-PQ Load objects are mapping ports, not actual operating demands.",
                            "Only connected normal-configuration component, initial balanced 3ph MAX; no MIN, Ith, earth fault, protection or field validation."],
                        "exclusiones_revisadas":[i["id"] for i in pre["items_to_review"]]}
                    dispatched=await call("ejecutar_estudio",{"estudio":"iec60909","tipo_falla":"three_phase",
                        "parametros":{**request,"revision_modelo":review}})
                    assert dispatched["executor_invoked"] and dispatched["selected_engine"]=="pandapower",dispatched
                    assert not dispatched["fallback"] and not dispatched["crosscheck"]
                    result=dispatched["result"]
                    assert result["ok"],result
                    assert set(result["scenarios"])=={"max"}
                    assert result["omitted_cases"]==["min"] and not result["max_min_pair_complete"]
                    assert result["protection_validation_supported"] is False
                    current=result["scenarios"]["max"]["results"]["ikss_ka"]
                    error=abs(current/fault["reference_ka"]-1)
                    assert math.isfinite(current) and current>0 and error<=1e-4,(fault,current,error)
                    comparisons.append({**fault,"calculated_ka":current,"relative_error":error})
    summary={"schema":"BRNO_SC3_PUBLIC_MCP_REPLAY_V1","status":"INITIAL_MAX_REFERENCE_REPRODUCED_WITH_EXPLICIT_MODEL_SCOPE",
        "call_count":len(calls),"public_tool_count":len(catalog.tools),"motor_groups":73,"compared_fault_buses":len(comparisons),
        "distinct_electrical_fault_nodes":len({r["mcp_bus"] for r in inputs["faults"]}),
        "comparison_tolerance_relative":1e-4,"max_relative_error":max(r["relative_error"] for r in comparisons),
        "comparison":comparisons,"backend":"pandapower","lv_tol_percent":6,
        "minimum_reproduced":False,"ith_reproduced":False,"protection_validation_performed":False,
        "installation_validation_closed":False,"field_validation_performed":False}
    (target/"calls.json").write_text(json.dumps(calls,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf8")
    (target/"summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False),encoding="utf8")
    print("BRNO_SC3_PUBLIC_MCP="+json.dumps(summary,allow_nan=False))
if __name__=="__main__":asyncio.run(main())
