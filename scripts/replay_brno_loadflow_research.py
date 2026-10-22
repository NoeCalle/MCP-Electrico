"""Exploratory balanced LF replay of pinned Brno report inputs.
Load-model semantics are hypotheses until independently recovered from ETAP.
No result from LFR/LFSourceLoad is ever used to build the circuit.
"""
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys
import tempfile
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opendssdirect import dss
from mcp_electrico import core, real_controlled_execution
import audit_brno_industrial_archive as audit

def main():
    facts = json.loads(audit.FACTS.read_text(encoding="utf8"))
    blob = audit.download(facts["archive"])
    with tempfile.TemporaryDirectory() as tmp:
        archive_path = Path(tmp)/"source.zip"
        archive_path.write_bytes(blob)
        db = audit.read_archive(archive_path, facts)["LF1S"]
        with zipfile.ZipFile(archive_path) as archive:
            info = next(x for x in archive.infolist() if x.filename.endswith("/Untitled.LF1S"))
            path = Path(tmp)/"report.sqlite"
            path.write_bytes(archive.read(info))
        con = sqlite3.connect(path.resolve().as_uri()+"?mode=ro&immutable=1", uri=True)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA trusted_schema=OFF")
        case = dict(con.execute('SELECT * FROM "ILFStudyCase"').fetchone())
        references = [dict(r) for r in con.execute('SELECT * FROM "LFR"')]
        con.close()
    buses = {r["IDBus"]:r for r in db["IBus"]}
    names = {bus:"b"+str(i) for i,bus in enumerate(sorted(buses))}
    parent = dict(zip(buses,buses))
    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    cable_ids = {r["ID"] for r in db["Icable"]}
    xfmr_ids = {r["ID"] for r in db["IXFMR2"]}
    tie_rows = []
    for row in db["IConnect"]:
        if row["ID"] in cable_ids or row["ID"] in xfmr_ids:
            continue
        audit.require(row["From"] in buses and row["ToSec"] in buses, "Unknown connection endpoints")
        audit.require(row["R"] == 0 and row["X"] == 0, "Unmapped nonzero branch: "+str(row))
        audit.require(abs(buses[row["From"]]["NomlkV"]-buses[row["ToSec"]]["NomlkV"]) < 1e-5, "Tie voltage mismatch")
        parent[root(row["ToSec"])] = root(row["From"])
        tie_rows.append({"id":row["ID"],"type":row["Type"].strip(),"from":row["From"],"to":row["ToSec"]})
    adjacency = {root(b):set() for b in buses}
    for row in db["IConnect"]:
        a,b=root(row["From"]),root(row["ToSec"])
        adjacency[a].add(b); adjacency[b].add(a)
    reachable = set()
    stack = [root("HV1")]
    while stack:
        a=stack.pop()
        if a in reachable: continue
        reachable.add(a);stack.extend(adjacency[a]-reachable)
    outside=[r for b,r in buses.items() if root(b) not in reachable]
    load_keys = ("MtrMW","MtrMvar","StatMW","StatMvar","ConstIMW","ConstIMvar","GenericMW","GenericMvar")
    audit.require(all(abs(float(r[k])) < 1e-8 for r in outside for k in load_keys), "Excluded island carries load")
    def busname(raw): return names[root(raw)]
    reference = "Brno 176344, pinned LF1S 6b175ddb2aabc8e2637c47ad82df51cd0c6830cd04950fbb303279995af0eab5; Normal/Base LF"
    source_bus = buses["HV1"]
    manifest = {
        "project":{"id":"BRNO_LF_REPORT_PROJECTION","name":"Brno public factory — LF report projection","source_reference":reference},
        "requested_scope":["POWER_FLOW"],
        "source":{"bus":busname("HV1"),"kv_ll":float(source_bus["NomlkV"]),"frequency_hz":float(case["Freq"]),
            "pu":float(source_bus["SourceIniVMag"])/100,"angle_deg":float(source_bus["SourceIniAng"]),
            "source_reference":reference,
            "power_flow_boundary":{"model":"QUASI_IDEAL_SLACK","base_mva":100.0,"r_pu":1e-6,"x_pu":1e-6,
                "tolerance":1e-9,"max_iterations":99,"source_reference":reference+"; explicit fixed-terminal PF projection"}},
        "topology":{"buses":sorted({busname(b) for b in buses if root(b) in reachable}),"transformers":[],"lines":[],"loads":[]}}
    for i,r in enumerate(db["Icable"]):
        if root(r["FromBus"]) not in reachable: continue
        n=float(r["No/Ph"]); length=float(r["Length"])/1000
        audit.require(n>0 and length>0,"Invalid cable geometry")
        manifest["topology"]["lines"].append({
            "id":f"Line.c{i}","bus1":busname(r["FromBus"]),"bus2":busname(r["ToBus"]),"phases":3,
            "length_km":length,"r1_ohm_km":float(r["RPos"])/n,"x1_ohm_km":float(r["XPos"])/n,
            "c1_nf_km":float(r["YPos"])/(2*math.pi*float(case["Freq"]))*1e9*n,
            "source_reference":reference+"; Icable "+r["ID"]})
    for i,r in enumerate(db["IXFMR2"]):
        if root(r["FromBus"]) not in reachable: continue
        audit.require(r["Conn"].strip()=="D/Y", "Unexpected transformer connection")
        audit.require(all(float(r[k])==0 for k in ("Prim%Tap","Sec%Tap","Min%Tap","Max%Tap","Step%Tap","LTCTapPosition")), "Non-nominal or regulating tap requires another projection")
        manifest["topology"]["transformers"].append({
            "id":f"Transformer.t{i}","bus_hv":busname(r["FromBus"]),"bus_lv":busname(r["ToBus"]),
            "kva":float(r["MVA"])*1000,"kv_hv":float(r["PrimkV"]),"kv_lv":float(r["SeckV"]),
            "uk_percent":float(r["PosZ"]),"x_r":float(r["PosX/R"]),
            "vector_group":"Dyn1","no_load_loss_kw":float(r["NoLoadkW"]),"i0_percent":float(r["NoLoadIPos"]),
            "tap_side":"hv","tap_min":0,"tap_max":0,"tap_neutral":0,"tap_pos":0,"tap_step_percent":0.0,
            "source_reference":reference+"; IXFMR2 "+r["ID"]+"; D/Y + thesis Dyn1, magnitudes-only projection"})
    for i,(b,r) in enumerate(buses.items()):
        if root(b) not in reachable: continue
        audit.require(abs(r["GenericMW"])+abs(r["GenericMvar"])+abs(r["ConstIMW"])+abs(r["ConstIMvar"])<1e-9,"Unsupported load category")
        for category,model in (("Mtr",1),("Stat",2)):
            p=float(r[category+"MW"])*1000;q=float(r[category+"Mvar"])*1000
            if abs(p)+abs(q)<1e-10:continue
            manifest["topology"]["loads"].append({
                "id":f"Load.l{i}_{category}","bus":busname(b),"phases":3,"kv":float(r["NomlkV"]),
                "kw":p,"kvar":q,"connection":"wye","model":model,"vminpu":0.1,"vmaxpu":2.0,
                "source_reference":reference+"; nominal IBus "+b+" "+category})
    output=Path("outputs/brno-lf-replay");output.mkdir(parents=True,exist_ok=False)
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf8")
    execution=real_controlled_execution.ejecutar_controlado(manifest)
    (output/"execution.json").write_text(json.dumps(execution,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf8")
    audit.require(execution["execution_status"]=="CONTROLLED_EXECUTION_COMPLETED",
                  "P8 did not admit/execute PF: "+json.dumps(execution,default=str)[:12000])
    solved=execution["results"]["POWER_FLOW"]["powerflow"]
    compared={}
    for r in references:
        b=r["IDFrom"]
        if b not in buses or root(b) not in reachable or float(r["VoltMag"])<=0:continue
        dss.Circuit.SetActiveBus(busname(b))
        values=dss.Bus.VMagAngle()[0::2]
        v=sum(values)/len(values)/(float(buses[b]["NomlkV"])*1000/math.sqrt(3))
        ref=float(r["VoltMag"])/100
        compared[b]={"source_pu":ref,"calculated_pu":v,"abs_error_pu":abs(v-ref)}
    audit.require(len(compared)==269,"Incomplete frozen bus comparison")
    worst=max(compared,key=lambda b:compared[b]["abs_error_pu"])
    audit.require(all(math.isfinite(r["calculated_pu"]) for r in compared.values()),"Nonfinite voltage")
    voltage_tolerance_pu=1e-4
    audit.require(compared[worst]["abs_error_pu"] <= voltage_tolerance_pu,"Voltage comparison outside declared research tolerance")
    # Aggregate losses come from the SAME pinned LF database, not April PDFs.
    con = None
    with tempfile.TemporaryDirectory() as tmp:
        ap=Path(tmp)/"source.zip";ap.write_bytes(blob)
        with zipfile.ZipFile(ap) as archive:
            info=next(x for x in archive.infolist() if x.filename.endswith("/Untitled.LF1S"))
            rp=Path(tmp)/"report.sqlite";rp.write_bytes(archive.read(info))
        con=sqlite3.connect(rp.resolve().as_uri()+"?mode=ro&immutable=1",uri=True)
        con.row_factory=sqlite3.Row
        con.execute("PRAGMA trusted_schema=OFF")
        total=dict(con.execute('SELECT * FROM "LFSumTotal"').fetchone())
        con.close()
    measured_power=[-x for x in dss.Circuit.TotalPower()]
    measured_losses=[x/1000 for x in dss.Circuit.Losses()]
    reference_power=[total["SwingMW"]*1000,total["SwingMvar"]*1000]
    reference_losses=[total["AppLossMW"]*1000,total["AppLossMvar"]*1000]
    power_tolerance_relative=1e-3
    for kind,actual,expected in (("source",measured_power,reference_power),("losses",measured_losses,reference_losses)):
        audit.require(all(math.isfinite(v) for v in actual),"Nonfinite "+kind)
        audit.require(all(abs(a-e) <= power_tolerance_relative*max(abs(e),1e-9) for a,e in zip(actual,expected)),"Aggregate "+kind+" outside declared tolerance")
    report={"schema":"BRNO_LF_EXPLORATORY_REPLAY_V1",
        "status":"RESEARCH_ONLY_LOAD_MODEL_SEMANTICS_UNCONFIRMED",
        "archive_sha256":facts["archive"]["sha256"],"report_sha256":facts["archive"]["members"]["Untitled.LF1S"],
        "case":{k:case[k] for k in ("ID","Config","Revision","Freq","LoadCat")},
        "engine":"OpenDSS","engine_version":dss.Basic.Version(),
        "converged":True,"electrical_calculation_performed":True,"p8_execution_status":execution["execution_status"],
        "model_revision":execution["model_revision"],"manifest_sha256":execution["manifest_sha256"],
        "installation_validation_closed":False,"field_validation_performed":False,
        "reference_outputs_used_as_inputs":False,
        "hypotheses":["IBus.MtrMW/Mvar treated as constant PQ", "IBus.StatMW/Mvar treated as constant impedance (including compensation)",
          "Exported IConnect zero-impedance branches merged as ideal closed contacts","Utility fixed-terminal swing source; not source Thevenin impedance"],
        "not_compared":["HV/LV phase angles","ampacity","short circuit","protection","machine decay","ground faults"],
        "research_comparison_passed":True,
        "comparison_criteria":{"voltage_abs_error_pu":voltage_tolerance_pu,"aggregate_power_relative_error":power_tolerance_relative},
        "reference_power_kw_kvar":reference_power,"reference_losses_kw_kvar":reference_losses,
        "input_buses":len(buses),"compared_buses":len(compared),"excluded_unloaded_buses":[r["IDBus"] for r in outside],
        "ideal_ties":tie_rows,"maximum_voltage_error_pu":compared[worst]["abs_error_pu"],
        "worst_bus":worst,"voltages":compared,"total_power_kw_kvar":[-x for x in dss.Circuit.TotalPower()],
        "losses_kw_kvar":[x/1000 for x in dss.Circuit.Losses()]}
    (output/"comparison.json").write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf8")
    print("BRNO_LF_REPLAY="+json.dumps({k:v for k,v in report.items() if k not in ("voltages","engine_version")},allow_nan=False))
if __name__=="__main__":main()
