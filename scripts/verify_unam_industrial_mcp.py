"""Q12A real MCP diagnostic; incomplete reference can never become approved."""
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
sys.path.insert(0,str(ROOT))
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from scripts.unam_industrial_reference import FACTS, VARIANTS, load_facts, audit, manifest, reference, compare_translation, compare_published


async def verify(output, verify_upstream=False):
    output.mkdir(parents=True,exist_ok=False)
    facts = load_facts()
    if verify_upstream:
        with urllib.request.urlopen(facts["source_url"],timeout=60) as response:
            digest = hashlib.sha256(response.read()).hexdigest()
        assert digest == facts["source_pdf_sha256"],"Source PDF changed; audit transcriptions again"
    audit_result = audit(facts)
    assert not audit_result["can_claim_complete_reference"]
    cases, calls = [], []
    params = StdioServerParameters(command=sys.executable,args=["-X","utf8",str(ROOT/"server.py")],
        cwd=str(output),env=dict(os.environ,PYTHONUTF8="1"))
    with (output/"MCP-stderr.log").open("w",encoding="utf8") as err:
        async with stdio_client(params,errlog=err) as (read,write):
            async with ClientSession(read,write) as client:
                await client.initialize()
                async def call(name,args):
                    response = await client.call_tool(name,arguments=args)
                    assert not response.isError,response
                    data = response.structuredContent
                    if data is None:
                        data = json.loads(next(c.text for c in response.content if c.type=="text"))
                    calls.append({"tool":name,"status":data.get("status",data.get("materializer_status"))})
                    return data
                original = await call("construir_modelo_rev0",{"manifest":manifest(facts,diagnostic=False)})
                assert original["materializer_status"] == "BLOCKED_BY_P8B_INTAKE", original
                (output/"UnresolvedSourceAdmission.json").write_text(json.dumps(original,indent=2),encoding="utf8")
                for variant in VARIANTS:
                    data = manifest(facts,variant)
                    built = await call("construir_modelo_rev0",{"manifest":data})
                    assert built["materializer_status"] == "MODEL_BUILT_NOT_EXECUTED",built
                    flow = await call("ejecutar_estudio",{"estudio":"flujo"})
                    assert flow["selected_engine"] == "opendss" and flow["result"]["convergio"]
                    detail = await call("analizar_flujo_operacion",{})
                    drops = await call("ejecutar_estudio",{"estudio":"caida_tension","parametros":{"limite_pct":3.}})
                    expected = reference(facts,variant)
                    comparison = compare_translation(flow["result"],detail,expected)
                    assert comparison["translation_passed"],comparison
                    published = compare_published(flow["result"],facts)
                    assert not published["can_claim_etap_parity"]
                    record = {"variant":variant,"Inputs":data,"Build":built,"Flow":flow,"Detail":detail,
                        "VoltageDrop":drops,"voltage_drop_threshold_origin":"Diagnostic 3% illustration, not approved project/normative criterion",
                        "IndependentDiagnosticReference":expected,"TranslationComparison":comparison,"PublishedComparison":published}
                    (output/f"{variant}.json").write_text(json.dumps(record,indent=2,allow_nan=False),encoding="utf8")
                    cases.append({"variant":variant,**comparison,**published})
                ansi = await call("ejecutar_estudio",{"estudio":"cortocircuito","norma":"IEEE/ANSI C37","tipo_falla":"three_phase","parametros":{"bus_falla":"bus_08"}})
                assert not ansi["executor_invoked"] and ansi["status"] == "BLOCKED_STANDARD", ansi
                iec = await call("ejecutar_estudio",{"estudio":"iec60909","tipo_falla":"three_phase","parametros":{"bus_falla":"bus_08"}})
                assert not iec["result"]["electrical_calculation_executed"],iec
                protection = await call("ejecutar_estudio",{"estudio":"protection_coordination"})
                assert not protection["executor_invoked"] and protection["status"] == "BLOCKED_PARAMETERS",protection
                await call("construir_modelo_rev0",{"manifest":manifest(facts)})
                restored = await call("ejecutar_estudio",{"estudio":"flujo"})
                restored_detail = await call("analizar_flujo_operacion",{})
                assert compare_translation(restored["result"],restored_detail,reference(facts,"tables"))["translation_passed"]
                await call("obtener_netlist",{"directorio":str(output/"RestoredNetlist")})
    paths = ["scripts/unam_industrial_reference.py","scripts/verify_unam_industrial_mcp.py",
             "mcp_electrico/real_model_materializer.py","mcp_electrico/professional_data.py","mcp_electrico/core.py"]
    summary = {"schema":"MCP_Q12A_INDUSTRIAL_DIAGNOSTIC_V1","status":"DIAGNOSTIC_TRANSLATION_VERIFIED_REFERENCE_INCOMPLETE",
        "ok":True,"complete_real_project_qualified":False,"etap_parity_qualified":False,
        "checked_at_utc":datetime.now(timezone.utc).isoformat(),"transport":"MCP_STDIO","case_count":len(cases),"cases":cases,
        "native_bus_count":13,"published_bus_labels":14,"transformer_count":4,"line_count":8,"load_count":5,
        "source_url":facts["source_url"],"source_pdf_sha256":facts["source_pdf_sha256"],"source_verified_upstream":verify_upstream,
        "fact_file_sha256":hashlib.sha256(FACTS.read_bytes()).hexdigest(),"source_audit":audit_result,
        "restored_base_matches":True,"call_count":len(calls),"calls":calls,
        "blocked_studies":{"IEEE_ANSI":"BLOCKED_STANDARD","IEC60909":"NO_CALCULATION_INSUFFICIENT_INPUTS","protection":"BLOCKED_PARAMETERS"},
        "software":{p:metadata.version(p) for p in ("mcp","opendssdirect.py","dss-python-backend","PYPOWER","numpy")},
        "source_sha256":{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}}
    (output/"Summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False),encoding="utf8")
    print("UNAM_DIAGNOSTIC_SUMMARY_JSON="+json.dumps(summary,allow_nan=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--verify-upstream",action="store_true")
    args = parser.parse_args()
    asyncio.run(verify(args.output.resolve(),args.verify_upstream))
