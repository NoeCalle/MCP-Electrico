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
from mcp_electrico import core
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
    core.crear_circuito("brno_lf_research", 22.0, frecuencia=float(case["Freq"]), bus_fuente=busname("HV1"))
    # The source report prescribes the utility swing-bus terminal at 1 pu.
    dss("Edit Vsource.source pu=1 angle=0 R1=1e-10 X1=1e-10 R0=1e-10 X0=1e-10")
    for i,r in enumerate(db["Icable"]):
        if root(r["FromBus"]) not in reachable: continue
        n=float(r["No/Ph"]); length=float(r["Length"])/1000
        audit.require(n>0 and length>0,"Invalid cable geometry")
        c=float(r["YPos"])/(2*math.pi*float(case["Freq"]))*1e9*n
        r1=float(r["RPos"])/n; x1=float(r["XPos"])/n
        dss(f'New Line.c{i} phases=3 bus1={busname(r["FromBus"])} bus2={busname(r["ToBus"])} length={length} units=km R1={r1} X1={x1} C1={c} R0={r1} X0={x1} C0={c}')
    for i,r in enumerate(db["IXFMR2"]):
        if root(r["FromBus"]) not in reachable: continue
        audit.require(r["Conn"].strip()=="D/Y", "Unexpected transformer connection")
        z=float(r["PosZ"]); xr=float(r["PosX/R"]); rp=z/math.sqrt(1+xr*xr); xp=rp*xr
        # Physical D/Y maintained. Only magnitudes compared; LF exports 0-degree
        # phase shift, so no assertion about relative HV/LV phase displacement.
        dss(f'New Transformer.t{i} phases=3 windings=2 buses=[{busname(r["FromBus"])} {busname(r["ToBus"])}] conns=[delta wye] kVs=[{r["PrimkV"]} {r["SeckV"]}] kVAs=[{r["MVA"]*1000} {r["MVA"]*1000}] xhl={xp} %Rs=[{rp/2} {rp/2}] %noloadloss={r["NoLoadkW"]/(r["MVA"]*1000)*100} %imag={r["NoLoadIPos"]} ppm_antifloat=0')
        for w,key in ((1,"Prim%Tap"),(2,"Sec%Tap")):
            dss(f'Edit Transformer.t{i} wdg={w} tap={1+float(r[key])/100}')
    for i,(b,r) in enumerate(buses.items()):
        if root(b) not in reachable: continue
        audit.require(abs(r["GenericMW"])+abs(r["GenericMvar"])+abs(r["ConstIMW"])+abs(r["ConstIMvar"])<1e-9,"Unsupported load category")
        for category,model in (("Mtr",1),("Stat",2)):
            p=float(r[category+"MW"])*1000;q=float(r[category+"Mvar"])*1000
            if abs(p)+abs(q)<1e-10:continue
            dss(f'New Load.l{i}_{category} bus1={busname(b)} phases=3 conn=wye kV={r["NomlkV"]} kW={p} kvar={q} model={model} Vminpu=0.1 Vmaxpu=2')
    dss("Set VoltageBases=[22 0.4]")
    dss("CalcVoltageBases")
    dss("Set maxiterations=99 tolerance=1e-9 controlmode=off")
    solved=core.ejecutar_flujo_potencia()
    audit.require(solved["convergio"],"OpenDSS did not converge")
    compared={}
    for r in references:
        b=r["IDFrom"]
        if b not in buses or root(b) not in reachable or float(r["VoltMag"])<=0:continue
        dss.Circuit.SetActiveBus(busname(b))
        values=dss.Bus.puVmagAngle()[0::2]
        v=sum(values)/len(values)
        ref=float(r["VoltMag"])/100
        compared[b]={"source_pu":ref,"calculated_pu":v,"abs_error_pu":abs(v-ref)}
    audit.require(len(compared)>200,"Incomplete bus comparison")
    worst=max(compared,key=lambda b:compared[b]["abs_error_pu"])
    report={"schema":"BRNO_LF_EXPLORATORY_REPLAY_V1",
        "status":"RESEARCH_ONLY_LOAD_MODEL_SEMANTICS_UNCONFIRMED",
        "archive_sha256":facts["archive"]["sha256"],"report_sha256":facts["archive"]["members"]["Untitled.LF1S"],
        "case":{k:case[k] for k in ("ID","Config","Revision","Freq","LoadCat")},
        "engine":"OpenDSS","engine_version":dss.Basic.Version(),
        "converged":True,"electrical_calculation_performed":True,
        "installation_validation_closed":False,"field_validation_performed":False,
        "reference_outputs_used_as_inputs":False,
        "hypotheses":["IBus.MtrMW/Mvar treated as constant PQ", "IBus.StatMW/Mvar treated as constant impedance (including compensation)",
          "Exported IConnect zero-impedance branches merged as ideal closed contacts","Utility fixed-terminal swing source; not source Thevenin impedance"],
        "not_compared":["HV/LV phase angles","ampacity","short circuit","protection","machine decay","ground faults"],
        "input_buses":len(buses),"compared_buses":len(compared),"excluded_unloaded_buses":[r["IDBus"] for r in outside],
        "ideal_ties":tie_rows,"maximum_voltage_error_pu":compared[worst]["abs_error_pu"],
        "worst_bus":worst,"voltages":compared,"total_power_kw_kvar":[-x for x in dss.Circuit.TotalPower()],
        "losses_kw_kvar":[x/1000 for x in dss.Circuit.Losses()]}
    output=Path("outputs/brno-lf-replay");output.mkdir(parents=True,exist_ok=False)
    (output/"comparison.json").write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf8")
    print("BRNO_LF_REPLAY="+json.dumps({k:v for k,v in report.items() if k not in ("voltages","engine_version")},allow_nan=False))
if __name__=="__main__":main()
