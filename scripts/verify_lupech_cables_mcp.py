"""Real published design checks through stdio; acceptance is not plant approval."""
import argparse
import asyncio
from copy import deepcopy
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
from scripts.lupech_cable_reference import FACTS, load_facts, reference, arguments, compare


async def verify(output, verify_upstream=False):
    output.mkdir(parents=True,exist_ok=False)
    facts = load_facts()
    if verify_upstream:
        with urllib.request.urlopen(facts["source_url"],timeout=180) as response:
            raw = response.read()
        assert len(raw) == facts["source_pdf_bytes"]
        assert hashlib.sha256(raw).hexdigest() == facts["source_pdf_sha256"], "Review changed source PDF"
    records, controls, rejected = [], [], []
    params = StdioServerParameters(command=sys.executable,args=["-X","utf8",str(ROOT/"server.py")],
        cwd=str(output),env=dict(os.environ,PYTHONUTF8="1"))
    with (output/"MCP-stderr.log").open("w",encoding="utf8") as err:
        async with stdio_client(params,errlog=err) as (read,write):
            async with ClientSession(read,write) as client:
                await client.initialize()
                async def call(args):
                    return await client.call_tool("evaluar_soportabilidad_termica_conductor_p5c",arguments=args)
                def data(response):
                    assert not response.isError,response
                    return response.structuredContent or json.loads(next(c.text for c in response.content if c.type=="text"))
                for row in facts["cases"]:
                    expected = reference(facts,row)
                    assert abs(expected["published_minimum_difference_mm2"]) <= .005
                    assert expected["status"] == row["expected_status"]
                    args = arguments(facts,row)
                    result = data(await call(args))
                    record = {"source_row":row,"Inputs":args,"MCP":result,"IndependentDecimalReference":expected,
                              "Comparison":compare(result,expected),"fault_current_origin":facts["current_origin"]}
                    records.append(record)
                    # Synthetic sensitivity controls are explicitly separate from published cases.
                    for factor,status in ((.999,"FAIL"),(1.001,"PASS")):
                        control = deepcopy(row)
                        control["section_mm2"] = expected["minimum_section_mm2"]*factor
                        response = data(await call(arguments(facts,control)))
                        control_ref = reference(facts,control)
                        assert response["status"] == status
                        controls.append({"source_case":row["id"],"kind":"SYNTHETIC_BOUNDARY_NOT_PUBLISHED",
                            "minimum_multiplier":factor,"MCP":response,"Comparison":compare(response,control_ref)})
                for key,code in (("fuente_k","P5C206"),("fuente_tiempo","P5C207"),("fuente_seccion","P5C209")):
                    args = arguments(facts,facts["cases"][0]); args[key] = ""
                    response = await call(args)
                    assert response.isError,response
                    message = "\n".join(c.text for c in response.content if c.type=="text")
                    assert code in message,message
                    rejected.append({"missing":key,"error_code":code,"isError":response.isError})
    paths = ["scripts/lupech_cable_reference.py","scripts/verify_lupech_cables_mcp.py",
             "mcp_electrico/protection_checks.py","mcp_electrico/protection_check_tools.py"]
    summary = {"schema":"MCP_Q12B_REAL_DESIGN_WITHSTAND_V1","ok":True,
        "status":"VERIFIED_PUBLISHED_ADIABATIC_SCOPE_WITH_ONE_DESIGN_DISCREPANCY",
        "checked_at_utc":datetime.now(timezone.utc).isoformat(),"transport":"MCP_STDIO",
        "published_cases":len(records),"published_pass":sum(r["MCP"]["status"]=="PASS" for r in records),
        "published_fail":sum(r["MCP"]["status"]=="FAIL" for r in records),
        "synthetic_boundary_controls":len(controls),"missing_provenance_rejected":rejected,
        "call_count":len(records)+len(controls)+len(rejected),
        "source_url":facts["source_url"],"source_pdf_sha256":facts["source_pdf_sha256"],
        "source_verified_upstream":verify_upstream,"fact_file_sha256":hashlib.sha256(FACTS.read_bytes()).hexdigest(),
        "cases":records,"boundary_controls":controls,
        "complete_real_project_qualified":False,"field_validation":False,
        "short_circuit_model_validated":False,"protection_clearing_times_validated":False,
        "full_standard_compliance_claim":False,"professional_emission":False,
        "software":{p:metadata.version(p) for p in ("mcp","opendssdirect.py")},
        "source_sha256":{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}}
    assert (summary["published_pass"],summary["published_fail"]) == (6,1)
    (output/"Summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False),encoding="utf8")
    print("LUPECH_CABLE_SUMMARY_JSON="+json.dumps(summary,allow_nan=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--verify-upstream",action="store_true")
    args = parser.parse_args()
    asyncio.run(verify(args.output.resolve(),args.verify_upstream))
