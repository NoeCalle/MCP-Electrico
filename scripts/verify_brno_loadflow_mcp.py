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
                delivery=await call("generar_dossier_piloto_real",{"manifest":manifest,"directorio_salida":str(trace/"dossier")})
                assert delivery["status"]=="DOSSIER_READY_ENGINEERING_PREVIEW",delivery
                assert delivery["manifest_sha256"]==replay["manifest_sha256"]
                assert delivery["p7a"]["status"]=="HASH_MATCH"
                assert delivery["p7b"]["parent_dss_context_mutated"] is False
                assert delivery["coordination_ranges"]["status"]=="NOT_REQUESTED"
                integrity=await call("verificar_integridad_dossier_real",{"ruta_indice":delivery["integrity"]["index_path"]})
                assert integrity["ok"],integrity
                summary={"schema":"BRNO_PF_PUBLIC_MCP_REPLAY_V1","calls":len(calls),"status":delivery["status"],
                    "scope":["POWER_FLOW"],"manifest_sha256":delivery["manifest_sha256"],
                    "p7b_status":delivery["p7b"]["status"],"integrity_status":integrity["status"],
                    "verified_file_count":integrity["verified_file_count"],
                    "installation_validation_closed":False,"field_validation_performed":False}
                (trace/"summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False),encoding="utf8")
                print("BRNO_PUBLIC_MCP="+json.dumps(summary))
if __name__=="__main__":asyncio.run(main())
