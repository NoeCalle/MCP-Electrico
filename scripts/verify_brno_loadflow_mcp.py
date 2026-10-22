"""Exercise the public MCP dossier entrypoint with the reconstructed Brno PF."""
import asyncio
from datetime import timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT=Path(__file__).resolve().parents[1]
async def main():
    output=(ROOT/"outputs/brno-lf-replay").resolve()
    manifest=json.loads((output/"manifest.json").read_text(encoding="utf8"))
    replay=json.loads((output/"comparison.json").read_text(encoding="utf8"))
    trace=output/"mcp";trace.mkdir(exist_ok=False)
    calls=[]
    params=StdioServerParameters(command=sys.executable,args=[str(ROOT/"server.py")],
        cwd=str(trace),env=dict(os.environ,PYTHONUTF8="1"))
    with (trace/"stderr.log").open("w",encoding="utf8") as log:
        async with stdio_client(params,errlog=log) as (read,write):
            async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=240)) as client:
                await client.initialize()
                async def call(name,args):
                    response=await client.call_tool(name,args)
                    assert not response.isError,response
                    result=response.structuredContent or json.loads(next(c.text for c in response.content if c.type=="text"))
                    calls.append({"tool":name,"result":result})
                    (trace/f"call-{len(calls)}.json").write_text(json.dumps(calls[-1],indent=2,ensure_ascii=False,allow_nan=False),encoding="utf8")
                    return result
                admission=await call("evaluar_admision_piloto_real",{"manifest":manifest})
                assert admission["intake_status"]=="READY_TO_BUILD_MODEL",admission
                blocked=await call("generar_dossier_piloto_real",{"manifest":manifest,"directorio_salida":str(trace/"full-protection-dossier")})
                assert blocked["status"]=="BLOCKED_BY_P8D2_EXECUTION",blocked
                assert blocked["artifact_generation_performed"] is False
                assert not (trace/"full-protection-dossier").exists()
                built=await call("construir_modelo_rev0",{"manifest":manifest})
                assert built["materializer_status"]=="MODEL_BUILT_NOT_EXECUTED",built
                assert built["solve_performed"] is False
                readiness=await call("evaluar_preparacion_estudio",{"estudio":"power_flow"})
                assert readiness["overall_status"]=="READY_TO_EXECUTE",readiness
                flow=await call("analizar_flujo_operacion",{})
                assert flow["powerflow"]["convergio"] is True,flow
                assert flow.get("resultados_validos") is not False
                exported=await call("exportar_snapshot_proyecto_p7a",{
                    "ruta_salida":str(trace/"snapshot.json"),"directorio_netlist":str(trace/"netlist")})
                assert exported["ok"],exported
                snapshot=json.loads(Path(exported["path"]).read_text(encoding="utf8"))
                verified=await call("verificar_snapshot_proyecto_p7a",{"snapshot":snapshot})
                assert verified["status"]=="HASH_MATCH",verified
                report=await call("exportar_reporte_desde_archivo_p7c",{
                    "ruta_snapshot":exported["path"],"ruta_salida":str(trace/"report.html")})
                assert report["ok"],report
                reconstructed=await call("reconstruir_archivo_proyecto_p7b",{
                    "ruta_snapshot":exported["path"],"directorio_reconstruccion":str(trace/"reconstructed")})
                assert reconstructed["status"]=="RECONSTRUCTED_NETLIST_VERIFIED_WITH_REBIND_REQUIRED",reconstructed
                summary={"schema":"BRNO_PF_PUBLIC_MCP_REPLAY_V1","calls":len(calls),
                    "status":"PF_REPORT_SNAPSHOT_RECONSTRUCTION_VERIFIED",
                    "scope":["POWER_FLOW"],"manifest_sha256":replay["manifest_sha256"],
                    "p7b_status":reconstructed["status"],"snapshot_verification":verified["status"],
                    "full_protection_dossier_without_p5":"BLOCKED_AS_REQUIRED",
                    "installation_validation_closed":False,"field_validation_performed":False}
                (trace/"summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False),encoding="utf8")
                print("BRNO_PUBLIC_MCP="+json.dumps(summary))
if __name__=="__main__":asyncio.run(main())
