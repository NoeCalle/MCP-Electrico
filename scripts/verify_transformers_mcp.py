"""Q11: real MCP stdio, published IEEE4 and independent fixed-tap checks."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from scripts.transformer_reference import (DATA, PIN, ieee_manifest, compare_ieee,
    tap_manifest, balanced_reference, compare_balanced)


def check_sources(online):
    sources = []
    for path in sorted(DATA.glob("*.csv")):
        raw = path.read_bytes()
        url = f"https://raw.githubusercontent.com/PowerGridModel/power-grid-model-io/{PIN}/_network_data_generation/ieee_4_node/{path.name}"
        if online:
            with urllib.request.urlopen(url, timeout=30) as response:
                original = response.read()
            assert original.decode().splitlines() == raw.decode().splitlines(), path.name
        sources.append({"url":url, "sha256":hashlib.sha256(raw).hexdigest(),
                        "pinned_upstream_verified":online})
    return sources


async def verify(output, online=False):
    output.mkdir(parents=True,exist_ok=False)
    sources = check_sources(online)
    calls, cases = [], []
    params = StdioServerParameters(command=sys.executable,args=["-X","utf8",str(ROOT/"server.py")],
        cwd=str(output),env=dict(os.environ,PYTHONUTF8="1"))
    with (output/"MCP-stderr.log").open("w",encoding="utf8") as err:
        async with stdio_client(params,errlog=err) as (read,write):
            async with ClientSession(read,write) as client:
                await client.initialize()
                async def call(name, args):
                    response = await client.call_tool(name,arguments=args)
                    assert not response.isError, response
                    data = response.structuredContent
                    if data is None:
                        data = json.loads(next(c.text for c in response.content if c.type=="text"))
                    calls.append({"tool":name,"status":data.get("status",data.get("execution_status"))})
                    return data
                async def run(inputs, expected, comparator, kind):
                    built = await call("construir_modelo_rev0",{"manifest":inputs})
                    assert built["materializer_status"] == "MODEL_BUILT_NOT_EXECUTED", built
                    flow = await call("ejecutar_estudio",{"estudio":"flujo"})
                    assert flow["selected_engine"] == "opendss"
                    detail = await call("analizar_flujo_operacion",{})
                    check = comparator(flow["result"],detail)
                    assert check["passed"], (inputs["project"]["id"], check)
                    identifier = inputs["project"]["id"]
                    (output/f"{identifier}.json").write_text(json.dumps({"Inputs":inputs,"Build":built,
                        "Flow":flow,"Detail":detail,"Reference":expected,"Comparison":check},indent=2,allow_nan=False),encoding="utf8")
                    cases.append({"id":identifier,"kind":kind,**check})
                for direction in ("down","up"):
                    for connection in ("ynyn","dyn"):
                        for loading in ("balanced","unbalanced"):
                            inputs = ieee_manifest(direction,connection,loading)
                            from scripts.transformer_reference import expected_ieee
                            await run(inputs,expected_ieee(direction,connection,loading),
                                lambda f,d:compare_ieee(f,d,direction,connection,loading),"PUBLISHED_IEEE4")
                for group in ("Yy0","Yyn0","Dd0","Dyn1","Dyn11","Yd1","Yd11"):
                    for side in ("hv","lv"):
                        for position in (-2,0,2):
                            inputs = tap_manifest(group,side,position)
                            ref = balanced_reference(inputs)
                            await run(inputs,ref,lambda f,d:compare_balanced(f,ref),"CONTROLLED_TAP_NEWTON")
                for side in ("hv","lv"):
                    for position in (-2,0,2):
                        inputs = tap_manifest("Dyn11",side,position,True)
                        ref = balanced_reference(inputs)
                        await run(inputs,ref,lambda f,d:compare_balanced(f,ref),"CONTROLLED_EXCITATION_NEWTON")
                # Reconstruct the first model after all variants; no stale tap,
                # excitation, matrix or phase selection may leak into a rebuild.
                first = ieee_manifest()
                await call("construir_modelo_rev0",{"manifest":first})
                flow = await call("ejecutar_estudio",{"estudio":"flujo"})
                detail = await call("analizar_flujo_operacion",{})
                assert compare_ieee(flow["result"],detail,"down","ynyn","balanced")["passed"]
                await call("obtener_netlist",{"directorio":str(output/"RestoredNetlist")})
    paths = ["server.py","mcp_electrico/core.py","mcp_electrico/studies.py",
        "mcp_electrico/phase_network_inputs.py","mcp_electrico/real_model_materializer.py",
        "mcp_electrico/real_pilot_intake.py","mcp_electrico/professional_data.py",
        "scripts/transformer_reference.py","scripts/verify_transformers_mcp.py"]
    summary = {"schema":"MCP_TRANSFORMER_QUALIFICATION_Q11_V1","ok":True,
        "checked_at_utc":datetime.now(timezone.utc).isoformat(), "transport":"MCP_STDIO",
        "software":{p:metadata.version(p) for p in ("mcp","opendssdirect.py","dss-python-backend","PYPOWER","numpy")},
        "published_case_count":8,"controlled_case_count":48,"cases":cases,"call_count":len(calls),"calls":calls,
        "sources":sources,"restored_base_matches":True,
        "source_sha256":{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        "scope_limits":["No real installation qualified; thesis candidates lack reproducible inputs",
            "No SC/protection qualification", "No explicit neutral voltages", "No automatic tap regulation",
            "No open-delta, three-winding, saturation or arbitrary vector groups",
            "Published low-voltage results validate calculations, not design compliance"]}
    (output/"Summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False),encoding="utf8")
    print("TRANSFORMER_SUMMARY_JSON="+json.dumps(summary,allow_nan=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--verify-upstream",action="store_true")
    args = parser.parse_args()
    asyncio.run(verify(args.output.resolve(),args.verify_upstream))
