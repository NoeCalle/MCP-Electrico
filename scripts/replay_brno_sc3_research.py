"""Research-only SC3 replay from pinned Brno SI1S physical inputs.
Uses pandapower only. It neither fits inputs to results nor claims MCP admission.
Aggregated motors retain declared apparent power and locked-rotor impedance;
PP's pn_mech=Sn, cos_phi=eta=1 is a numerical parameterization, not a nameplate.
"""
import json
import math
from pathlib import Path
import sqlite3
import sys
import tempfile
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandapower as pp
from pandapower.shortcircuit import calc_sc
import audit_brno_industrial_archive as audit

def main():
    facts=json.loads(audit.FACTS.read_text(encoding="utf8"))
    data=audit.download(facts["archive"])
    with tempfile.TemporaryDirectory() as temp:
        archive_path=Path(temp)/"source.zip";archive_path.write_bytes(data)
        with zipfile.ZipFile(archive_path) as archive:
            matches=[i for i in archive.infolist() if i.filename.endswith("/Untitled.SI1S")]
            audit.require(len(matches)==1,"Ambiguous report")
            blob=archive.read(matches[0])
            audit.require(audit.sha256(blob)==facts["archive"]["members"]["Untitled.SI1S"],"Report changed")
            target=Path(temp)/"report.sqlite";target.write_bytes(blob)
        con=sqlite3.connect(target.resolve().as_uri()+"?mode=ro&immutable=1",uri=True);con.row_factory=sqlite3.Row
        con.execute("PRAGMA trusted_schema=OFF")
        tables={name:[dict(r) for r in con.execute('SELECT * FROM "'+name+'"')]
                for name in ("IBus","IConnect","Icable","IXFMR2","IUtility","ILump","ISynGen","ISCStudyCase","SCIEC3ph","SCIEC3phSum")}
        con.close()
    buses={r["IDBus"]:r for r in tables["IBus"]}
    parent={b:b for b in buses}
    def root(b):
        while parent[b]!=b:
            parent[b]=parent[parent[b]];b=parent[b]
        return b
    known={r["ID"] for t in ("Icable","IXFMR2") for r in tables[t]}
    merged=[]
    for r in tables["IConnect"]:
        if r["ID"] in known:continue
        audit.require(r["From"] in buses and r["ToSec"] in buses,"Unknown endpoints")
        audit.require(r["R"]==r["X"]==0,"Unmapped nonzero connection")
        audit.require(abs(buses[r["From"]]["NomlkV"]-buses[r["ToSec"]]["NomlkV"])<1e-5,"Tie voltage mismatch")
        parent[root(r["ToSec"])]=root(r["From"]);merged.append(r["ID"])
    adjacency={root(b):set() for b in buses}
    for r in tables["IConnect"]:
        a,b=root(r["From"]),root(r["ToSec"]);adjacency[a].add(b);adjacency[b].add(a)
    audit.require(len(tables["IUtility"])==1,"Requires one utility")
    utility=tables["IUtility"][0];case=tables["ISCStudyCase"][0]
    reachable=set();stack=[root(utility["ConnectedBus"])]
    while stack:
        b=stack.pop()
        if b in reachable:continue
        reachable.add(b);stack.extend(adjacency[b]-reachable)
    excluded_gens=[r["ID"] for r in tables["ISynGen"] if root(r["ConnectedBus"]) not in reachable]
    audit.require(len(excluded_gens)==len(tables["ISynGen"]),"Connected synchronous generator requires another projection")
    net=pp.create_empty_network(sn_mva=100.,f_hz=float(case["Freq"]))
    busmap={b:pp.create_bus(net,vn_kv=float(buses[b]["NomlkV"]),name=b) for b in sorted(reachable)}
    def index(b):return busmap[root(b)]
    source_c=float(case["CFact3"])
    z100=complex(utility["RPos100MVA"],utility["XPos100MVA"])/100
    physical_scc=100/abs(z100)
    audit.require(abs(physical_scc/float(utility["MVA3ph"])-1)<1e-5,"Utility MVA/impedance inconsistent")
    # PP s_sc includes cHV; preserve the exported physical positive-sequence Z.
    source_mva=source_c*physical_scc
    pp.create_ext_grid(net,index(utility["ConnectedBus"]),s_sc_max_mva=source_mva,
        rx_max=z100.real/z100.imag,name=utility["ID"])
    for r in tables["Icable"]:
        if root(r["FromBus"]) not in reachable:continue
        audit.require(r["TempOp"]==20,"SC report does not prescribe R20")
        pp.create_line_from_parameters(net,index(r["FromBus"]),index(r["ToBus"]),
            length_km=float(r["Length"])/1000,r_ohm_per_km=float(r["RPos"]),
            x_ohm_per_km=float(r["XPos"]),c_nf_per_km=0.,max_i_ka=1.,
            parallel=int(r["No/Ph"]),name=r["ID"])
    for r in tables["IXFMR2"]:
        if root(r["FromBus"]) not in reachable:continue
        audit.require(r["Conn"].strip()=="D/Y" and float(r["Prim%Tap"])==float(r["Sec%Tap"])==0,"Unsupported transformer projection")
        vkr=float(r["PosZ"])/math.sqrt(1+float(r["PosX/R"])**2)
        pp.create_transformer_from_parameters(net,index(r["FromBus"]),index(r["ToBus"]),
            sn_mva=float(r["MVA"]),vn_hv_kv=float(r["PrimkV"]),vn_lv_kv=float(r["SeckV"]),
            vk_percent=float(r["PosZ"]),vkr_percent=vkr,pfe_kw=float(r["NoLoadkW"]),
            i0_percent=float(r["NoLoadIPos"]),shift_degree=30.,vector_group="Dyn",name=r["ID"])
    groups=[]
    for r in tables["ILump"]:
        if root(r["ConnectedBus"]) not in reachable:continue
        share=float(r["MTR%"])/100
        if share==0:continue
        audit.require(0<share<=1 and abs(float(r["MTR%"])+float(r["Stat%"])-100)<1e-5,"Unsupported motor fraction")
        sn=float(r["kVA"])/1000*share
        resistance=float(r["R"]);reactance=float(r["XppIEC"])
        audit.require(sn>0 and resistance>=0 and reactance>0,"Missing group impedance")
        lrc=100/math.hypot(resistance,reactance);rx=resistance/reactance
        pp.create_motor(net,index(r["ConnectedBus"]),pn_mech_mw=sn,cos_phi=1.,
            efficiency_percent=100.,cos_phi_n=1.,efficiency_n_percent=100.,
            vn_kv=float(r["KV"]),lrc_pu=lrc,rx=rx,name=r["ID"])
        groups.append({"id":r["ID"],"bus":r["ConnectedBus"],"rated_group_sn_mva":sn,
            "r_percent":resistance,"x_percent":reactance,"lrc_from_impedance_pu":lrc,
            "z_ohm":float(r["KV"])**2/sn*complex(resistance,reactance).__abs__()/100})
    initial={}
    for r in tables["SCIEC3ph"]:
        if str(r["ToBus"]).strip()=="Total" and r["FromBus"]==r["FaultedBus"]:
            audit.require(r["FaultedBus"] not in initial,"Duplicate initial-current reference")
            initial[r["FaultedBus"]]={"current_ka":float(r["kAMag"]),"c":float(r["CFactor"])}
    audit.require(initial,"No initial-current references")
    for b,ref in initial.items():
        audit.require(root(b) in reachable,"Reference outside utility-connected component")
        matches=[r for r in tables["SCIEC3phSum"] if r["FaultedBus"]==b and r["DeviceID"]==b]
        audit.require(len(matches)==1 and abs(matches[0]["IPPk"]-ref["current_ka"])<1e-5,"Initial-current fields disagree")
        audit.require(abs(ref["c"]-1.05)<1e-5,"This projection requires cLV=1.05")
    # The 6% LV-tolerance option in pinned PP selects cmax=1.05.
    calc_sc(net,bus=sorted({index(b) for b in initial}),case="max",fault="3ph",
        ip=False,ith=False,lv_tol_percent=6,check_connectivity=True,use_pre_fault_voltage=False)
    comparison=[]
    for b,ref in initial.items():
        actual=float(net.res_bus_sc.at[index(b),"ikss_ka"])
        audit.require(math.isfinite(actual) and actual>0,"Invalid calculated current")
        comparison.append({"bus":b,"reference_ka":ref["current_ka"],"calculated_ka":actual,
            "relative_error":abs(actual/ref["current_ka"]-1)})
    output=Path("outputs/brno-sc3-research");output.mkdir(parents=True,exist_ok=False)
    summary={"schema":"BRNO_SC3_RESEARCH_REPLAY_V1","status":"RESEARCH_ONLY_AGGREGATE_MACHINE_AND_SOURCE_SEMANTICS_UNCONFIRMED",
        "backend":"pandapower","backend_version":pp.__version__,"archive_sha256":facts["archive"]["sha256"],
        "report_sha256":facts["archive"]["members"]["Untitled.SI1S"],
        "input_bus_count":len(buses),"utility_component_bus_count":sum(root(b) in reachable for b in buses),
        "compared_fault_buses":len(comparison),"motor_groups":len(groups),"excluded_generator_islands":excluded_gens,
        "merged_zero_impedance_connections":merged,"source_voltage_factor":source_c,
        "lv_voltage_factor":1.05,"source_physical_scc_mva":physical_scc,"pp_source_scc_mva":source_mva,
        "reference_outputs_used_as_inputs":False,"operating_kw_used_as_nameplate_power":False,
        "equivalent_parameters_are_individual_motor_nameplates":False,
        "machine_mapping":"Sn=kVA*MTR_fraction; Zlr=(R+jXppIEC)% on group Sn; PP pn=Sn/eta=1/cosphi=1 numerical equivalent only",
        "comparison":comparison,"max_relative_error":max(r["relative_error"] for r in comparison),
        "electrical_calculation_performed":True,"mcp_p4_execution_performed":False,
        "minimum_case_reproduced":False,"ith_reproduced":False,"ground_fault_reproduced":False,
        "installation_validation_closed":False,"field_validation_performed":False}
    (output/"comparison.json").write_text(json.dumps(summary,indent=2,allow_nan=False),encoding="utf8")
    (output/"motor-groups.json").write_text(json.dumps(groups,indent=2,allow_nan=False),encoding="utf8")
    print("BRNO_SC3_REPLAY="+json.dumps(summary,allow_nan=False))
if __name__=="__main__":main()
