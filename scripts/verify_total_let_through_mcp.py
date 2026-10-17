"""Q12C: sourced manufacturer energy point and fail-closed checks over MCP."""
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
from scripts.abb_let_through_reference import FACTS, load_facts, arguments, compare, reference


async def verify(output, verify_upstream=False):
    output.mkdir(parents=True,exist_ok=False)
    facts = load_facts()
    if verify_upstream:
        with urllib.request.urlopen(facts["source_url"],timeout=60) as response:
            raw = response.read()
        assert len(raw) == facts["source_pdf_bytes"]
        assert hashlib.sha256(raw).hexdigest() == facts["source_pdf_sha256"]
    params = StdioServerParameters(command=sys.executable,args=["-X","utf8",str(ROOT/"server.py")],
        cwd=str(output),env=dict(os.environ,PYTHONUTF8="1"))
    records, calls = [], []
    with (output/"MCP-stderr.log").open("w",encoding="utf8") as err:
        async with stdio_client(params,errlog=err) as (read,write):
            async with ClientSession(read,write) as client:
                await client.initialize()
                names = {t.name for t in (await client.list_tools()).tools}
                tool = "evaluar_energia_pasante_conductor_p5c"
                assert tool in names
                async def call(name,args):
                    response = await client.call_tool(name,arguments=args)
                    calls.append(name)
                    assert not response.isError,response
                    data = response.structuredContent
                    if data is None:
                        raw_text = next(c.text for c in response.content if c.type=="text")
                        try:
                            data = json.loads(raw_text)
                        except json.JSONDecodeError:
                            data = {"text":raw_text}
                    return data
                # A bus carries the P5 device binding only. No artificial cable, source
                # impedance, load, fault solution or frequency-dependent result is used.
                await call("crear_circuito",{"nombre":"abb_energy_point_container","kv_base":.4,"frecuencia":50,"bus_fuente":"sourcebus"})
                source = facts["energy_point"]["source_reference"]
                device = await call("definir_dispositivo_proteccion_p5a",{
                    "nombre":"abb_cb1","tipo":"circuit_breaker","elemento_protegido":"Bus.sourcebus",
                    "in_a":160,"ue_kv":.4,"fabricante":"ABB","modelo":"T1N160 In160","icu_ka":36,
                    "norma_referencia":"ABB published IEC device rating; no full normative verification",
                    "fuente_referencia":source,"fuente_url":facts["source_url"]})
                args = arguments(facts)
                result = await call(tool,args)
                records.append({"kind":"PUBLISHED_MANUFACTURER_CASE","Inputs":args,"MCP":result,"Comparison":compare(result)})
                original = deepcopy(args)
                args["punto_energia"].update(value=750000,unit="A2s")
                converted = await call(tool,args)
                records.append({"kind":"EXPLICIT_EQUIVALENT_UNIT_CONTROL","MCP":converted,"Comparison":compare(converted)})
                for factor,status in ((.999,"FAIL"),(1.001,"PASS")):
                    args = deepcopy(original); args["seccion_mm2"] = reference()["minimum_section_mm2"]*factor
                    r = await call(tool,args); assert r["status"] == status
                    records.append({"kind":"SYNTHETIC_BOUNDARY_NOT_PUBLISHED","factor":factor,"MCP":r})
                for key,value,status in (("semantics","PRE_ARCING_I2T","ENERGY_SEMANTICS_NOT_TOTAL"),
                    ("unit","J","ENERGY_UNIT_NOT_SUPPORTED"),("current_ka",29,"ENERGY_REFERENCE_POINT_MISMATCH"),
                    ("voltage_kv",.415,"ENERGY_REFERENCE_POINT_MISMATCH"),
                    ("model","T1N160 In125","ENERGY_DEVICE_IDENTITY_MISMATCH")):
                    args = deepcopy(original);args["punto_energia"][key] = value
                    r = await call(tool,args)
                    assert r["status"] == status and not r["thermal_calculation_performed"]
                    records.append({"kind":"NEGATIVE_APPLICABILITY_CONTROL","changed":{key:value},"MCP":r})
                clearing = await call("evaluar_tiempo_despeje_p5d",{"dispositivo":"abb_cb1","current_a":30000})
                assert clearing["status"] == "TCC_DATA_NOT_BOUND" and clearing["clearing_time"] is None
                restored = await call(tool,original)
                assert compare(restored)["comparison_passed"]
    paths = ["mcp_electrico/protection_let_through.py","mcp_electrico/protection_check_tools.py",
             "scripts/abb_let_through_reference.py","scripts/verify_total_let_through_mcp.py"]
    summary = {"schema":"MCP_Q12C_TOTAL_I2T_ACCEPTANCE_V1","ok":True,
        "status":"VERIFIED_PUBLISHED_MANUFACTURER_POINT_NOT_FIELD_VALIDATION",
        "checked_at_utc":datetime.now(timezone.utc).isoformat(),"transport":"MCP_STDIO",
        "registered_tools":len(names),"call_count":len(calls),"calls":calls,"records":records,
        "Device":device,"TCCClearingGate":clearing,"restored_reference_passed":True,
        "source_url":facts["source_url"],"source_pdf_sha256":facts["source_pdf_sha256"],
        "source_verified_upstream":verify_upstream,"fact_file_sha256":hashlib.sha256(FACTS.read_bytes()).hexdigest(),
        "source_sha256":{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        "software":{p:metadata.version(p) for p in ("mcp","opendssdirect.py")},
        "field_validation":False,"complete_real_project_qualified":False,
        "clearing_time_derived_from_i2t":False,"full_standard_compliance_claim":False}
    (output/"Summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False),encoding="utf8")
    print("TOTAL_I2T_SUMMARY_JSON="+json.dumps(summary,allow_nan=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--verify-upstream",action="store_true")
    args = parser.parse_args()
    asyncio.run(verify(args.output.resolve(),args.verify_upstream))
