"""Q12A: source audit and explicitly conditional industrial diagnostic models.

No production import or new operating solver. PYPOWER is a qualification oracle.
Passing translation tests NEVER promotes the incomplete thesis reference.
"""
from copy import deepcopy
import json
from math import sqrt
from pathlib import Path

from scripts.published_feeder_reference import BOUNDARY

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "examples/qualification/unam_industrial_2017.json"
VARIANTS = ("tables", "diagram_lengths", "figure_reactance", "diagram_and_figure")
TOLERANCES = {"voltage_pu_abs":.0002, "loss_kw_abs":.05, "loss_kvar_abs":.05,
              "branch_current_a_abs":.05, "branch_kw_abs":.05, "branch_kvar_abs":.05}


def load_facts():
    return json.loads(FACTS.read_text(encoding="utf8"))


def alias(bus):
    return "BUS-08" if bus == "BUS-09" else bus


def audit(facts):
    findings = []
    for line in facts["lines"]:
        if "diagram_id" in line and line["diagram_id"] != line["id"]:
            findings.append({"id":"NEW_FEEDER_IDENTIFIER","severity":"INPUT_RECONCILIATION_REQUIRED",
                "table_id":line["id"],"diagram_id":line["diagram_id"],"pages":[48,105],
                "diagnostic_choice":"Use the table's new-load application and its CP08 identifier; retain the discrepancy"})
        if "diagram_length_m" in line and line["length_m"] != line["diagram_length_m"]:
            findings.append({"id":"LENGTH_"+line["id"],"severity":"REFERENCE_CONFLICT",
                "table_m":line["length_m"],"diagram_m":line["diagram_length_m"],"pages":[48,53,105]})
    t = next(t for t in facts["transformers"] if t["id"] == "SE01")
    findings.append({"id":"SE01_REACTANCE","severity":"REFERENCE_CONFLICT",
        "table_x_pu_100mva":t["table_x_pu_100mva"],"figure_x_pu_100mva":t["figure_x_pu_100mva"],
        "pages":[54,65,70,105]})
    loss_row = facts["etap_new_transformer_terminals"]
    r_own_pu = t["uk_percent"]/100/sqrt(1+t["xr"]**2)
    r_lv_ohm = r_own_pu*t["kv_lv"]**2/(t["kva"]/1000)
    findings.append({"id":"NEW_TRANSFORMER_LOSS_INPUTS","severity":"INPUT_RECONCILIATION_REQUIRED",
        "published_terminal_loss_kw":loss_row["sending_kw"]-loss_row["receiving_kw"],
        "table_series_copper_loss_at_published_current_kw":3*loss_row["lv_current_a"]**2*r_lv_ohm/1000,
        "conditions":"Balanced nominal ratio; excitation excluded. Actual tap and ETAP inputs still required.",
        "resolution":"Do not infer replacement R from the desired ETAP result", "pages":[54,103,105]})
    z = facts["zero_sequence_audit"]
    findings.append({"id":"TABLE613_ZERO_SEQUENCE_LABEL","severity":"REFERENCE_CONFLICT",
        "development_z0":[z["development_z0_r_pu"],z["development_z0_x_pu"]],
        "table_labeled_z0":[z["table613_labeled_z0_r_pu"],z["table613_labeled_z0_x_pu"]],
        "recomputed_z0_plus_2z1":[z["development_z0_r_pu"]+2*z["z1_r_pu"],z["development_z0_x_pu"]+2*z["z1_x_pu"]],
        "resolution":"Table values equal Z0+Z1+Z2, not Z0 alone; no automatic source projection", "pages":z["pages"]})
    # A common Sbase does not make the voltage base identical across a transformer.
    lv = next(line for line in facts["lines"] if line["id"] == "CP09")
    findings.append({"id":"LV_IMPEDANCE_BASE","severity":"UNIT_RECONCILIATION_REQUIRED",
        "sbase_mva":100.,"mv_zbase_ohm":23.**2/100.,"lv_zbase_ohm":.46**2/100.,
        "voltage_base_ratio_squared":(23/.46)**2,"cp09_correct_local_r_pu":lv["r_ohm"]/(.46**2/100.),
        "cp09_using_23kv_base_r_pu":lv["r_ohm"]/(23.**2/100.),"pages":[52,65,105]})
    by_id = {line["id"]:line for line in facts["lines"]}
    for row in facts["etap_lv_line_terminals"]:
        # Diagnostic only: shunts, input temperature and parallel sets are unknown.
        # This does not fit R into a model or assert that ETAP solved incorrectly.
        r_from_loss = (row["sending_kw"]-row["receiving_kw"])*1000/(3*row["current_a"]**2)
        findings.append({"id":"PF_SC_INPUT_COMPARISON_"+row["id"],"severity":"INPUT_RECONCILIATION_REQUIRED",
            "sc_table_r_ohm":by_id[row["id"]]["r_ohm"],"pf_loss_implied_r_ohm":r_from_loss,
            "ratio":r_from_loss/by_id[row["id"]]["r_ohm"],"pages":[103,105],
            "note":"Loss-derived diagnostic is NOT adopted as cable input"})
    return {"status":"BLOCKED_FULL_REFERENCE_QUALIFICATION","can_claim_complete_reference":False,
        "can_claim_etap_parity":False,"findings":findings,
        "missing":deepcopy(facts["missing_for_full_reference"]),
        "short_circuit_comparison":"IEEE_ANSI_REFERENCE_NOT_IEC60909_PARITY",
        "professional_emission":False}


def manifest(facts, variant="tables", diagnostic=True):
    assert variant in VARIANTS
    ref = facts["source_url"]
    # Use safe names and merge the ideal closed breaker, not a fictitious cable.
    name = lambda bus: alias(bus).lower().replace("-", "_")
    buses = sorted({name(b) for line in facts["lines"] for b in (line["from"],line["to"])} |
                   {name(b) for t in facts["transformers"] for b in (t["hv_bus"],t["lv_bus"])})
    lines = []
    for row in facts["lines"]:
        length = row["diagram_length_m"] if variant in ("diagram_lengths","diagram_and_figure") and "diagram_length_m" in row else row["length_m"]
        original_km = row["length_m"]/1000
        lines.append({"id":"Line."+row["id"].lower(),"bus1":name(row["from"]),"bus2":name(row["to"]),
            "phases":3,"length_km":length/1000,"r1_ohm_km":row["r_ohm"]/original_km,
            "x1_ohm_km":row["x_ohm"]/original_km,"c1_nf_km":0. if diagnostic else None,"source_reference":ref})
    transformers = []
    for row in facts["transformers"]:
        uk, xr = row["uk_percent"], row["xr"]
        if row["id"] == "SE01" and variant in ("figure_reactance","diagram_and_figure"):
            # Preserve both published alternatives; do not pick the best-fitting one.
            r, x = row["table_r_pu_100mva"], row["figure_x_pu_100mva"]
            uk, xr = abs(complex(r,x))*row["kva"]/1000, x/r
        transformers.append({"id":"Transformer."+row["id"].lower(),"bus_hv":name(row["hv_bus"]),"bus_lv":name(row["lv_bus"]),
            "kva":row["kva"],"kv_hv":row["kv_hv"],"kv_lv":row["kv_lv"],"uk_percent":uk,"x_r":xr,
            "vector_group":"Dyn11" if diagnostic else None,"no_load_loss_kw":0. if diagnostic else None,
            "i0_percent":0. if diagnostic else None,"source_reference":ref})
    loads = [{"id":"Load."+name(row["bus"]),"bus":name(row["bus"]),"phases":3,"kv":.46,
              "kw":row["kw"],"kvar":row["kvar"],"connection":"wye","model":1,
              "vminpu":.5,"vmaxpu":1.5,"source_reference":ref} for row in facts["loads"]]
    source = {"bus":"bus_01","kv_ll":23.,"frequency_hz":60.,"pu":1.,"angle_deg":0.,"source_reference":ref}
    if diagnostic:
        source["power_flow_boundary"] = deepcopy(BOUNDARY)
    else:
        source.update(scc_max_mva=facts["source"]["scc3_mva"],x_r_max=facts["source"]["xr3"])
    return {"project":{"id":"UNAM2017_"+variant+("_DIAGNOSTIC" if diagnostic else "_INCOMPLETE"),
                "name":"Conditional industrial diagnostic; NOT a qualified real installation","source_reference":ref},
            "requested_scope":["POWER_FLOW","VOLTAGE_DROP"],"source":source,
            "topology":{"buses":buses,"lines":lines,"transformers":transformers,"loads":loads},
            "qualification_status":"DIAGNOSTIC_ONLY" if diagnostic else "UNRESOLVED_SOURCE_INPUTS",
            "source_reference_admitted":False,"qualification_conventions":deepcopy(facts["diagnostic_assumptions"]) if diagnostic else {}}


def reference(facts, variant):
    """Independent positive-sequence Newton model built directly from source facts."""
    import numpy as np
    from pypower.api import ppoption, runpf
    labels = sorted({alias(k) for k in facts["etap_voltages_pct"]})
    indices = {label:i for i,label in enumerate(labels)}
    lv = {alias(t["lv_bus"]) for t in facts["transformers"]} | {"BUS-10","BUS-13","BUS-14"}
    bus = np.zeros((len(labels),13))
    bus[:,0] = np.arange(1,len(labels)+1); bus[:,1] = 1
    bus[indices["BUS-01"],1] = 3
    bus[:,6] = 1; bus[:,7] = 1; bus[:,9] = [.46 if b in lv else 23. for b in labels]
    bus[:,10] = 1; bus[:,11:13] = [1.5,.5]
    for load in facts["loads"]:
        bus[indices[load["bus"]],2:4] += np.array([load["kw"],load["kvar"]])/1000
    branches, ids = [], []
    for line in facts["lines"]:
        a,b = indices[alias(line["from"])],indices[alias(line["to"])]
        length_ratio = line.get("diagram_length_m",line["length_m"])/line["length_m"] if variant in ("diagram_lengths","diagram_and_figure") else 1.
        zbase = line["kv_ll"]**2/100
        branches.append([a+1,b+1,line["r_ohm"]*length_ratio/zbase,line["x_ohm"]*length_ratio/zbase,0,0,0,0,0,0,1,-360,360])
        ids.append("Line."+line["id"].lower())
    for t in facts["transformers"]:
        a,b = indices[t["hv_bus"]],indices[t["lv_bus"]]
        r = t["uk_percent"]/100/sqrt(1+t["xr"]**2)*100000/t["kva"]
        x = r*t["xr"]
        if t["id"] == "SE01" and variant in ("figure_reactance","diagram_and_figure"):
            r,x = t["table_r_pu_100mva"],t["figure_x_pu_100mva"]
        branches.append([a+1,b+1,r,x,0,0,0,0,1,-30,1,-360,360])
        ids.append("Transformer."+t["id"].lower())
    gen = np.zeros((1,21)); gen[0,:10] = [indices["BUS-01"]+1,0,0,100,-100,1,100,1,100,-100]
    solved,ok = runpf({"version":"2","baseMVA":100.,"bus":bus,"gen":gen,"branch":np.array(branches)},
        ppoption(PF_ALG=1,PF_TOL=1e-11,PF_MAX_IT=100,VERBOSE=0,OUT_ALL=0))
    assert ok,"Independent Newton reference did not converge"
    line_results = {}
    for i,line in enumerate(facts["lines"]):
        row = solved["branch"][i]
        current = abs(complex(row[13],row[14]))*1000/(sqrt(3)*solved["bus"][indices[alias(line["from"])] ,7]*line["kv_ll"])
        line_results[ids[i]] = {"kw":float(row[13]*1000),"kvar":float(row[14]*1000),"current_a":float(current)}
    return {"engine":"PYPOWER AC Newton; diagnostic only","voltages_pu":{b.lower().replace("-","_"):float(solved["bus"][i,7]) for i,b in enumerate(labels)},
        "loss_kw":float((solved["gen"][:,1].sum()-bus[:,2].sum())*1000),
        "loss_kvar":float((solved["gen"][:,2].sum()-bus[:,3].sum())*1000),"lines":line_results}


def compare_translation(flow, detail, expected):
    assert flow["convergio"]
    assert set(flow["voltajes_por_bus"]) == set(expected["voltages_pu"])
    errors = {"voltage_pu_abs":max(abs(v-expected["voltages_pu"][b]) for b,row in flow["voltajes_por_bus"].items() for v in row["voltajes_pu"]),
        "loss_kw_abs":abs(flow["perdidas_totales_kw"]-expected["loss_kw"]),"loss_kvar_abs":abs(flow["perdidas_totales_kvar"]-expected["loss_kvar"])}
    assert {r["id"] for r in detail["alimentadores"]} == set(expected["lines"])
    for metric,key,native in (("branch_current_a_abs","current_a","corriente_max_a"),("branch_kw_abs","kw","flujo_kw_terminal1"),("branch_kvar_abs","kvar","flujo_kvar_terminal1")):
        errors[metric] = max(abs(row[native]-expected["lines"][row["id"]][key]) for row in detail["alimentadores"])
    return {"translation_passed":all(v<=TOLERANCES[k] for k,v in errors.items()),"errors":errors,"tolerances":deepcopy(TOLERANCES),
            "complete_real_project_qualified":False,"etap_parity_qualified":False}


def compare_published(flow, facts):
    differences = {b:100*sum(flow["voltajes_por_bus"][alias(b).lower().replace("-","_")]["voltajes_pu"])/3-v
                   for b,v in facts["etap_voltages_pct"].items()}
    return {"status":"DIAGNOSTIC_NOT_ACCEPTANCE","voltage_difference_percentage_points":differences,
        "max_abs_voltage_difference_pp":max(map(abs,differences.values())),
        "etap_printed_losses_kw":facts["etap_source_power"]["kw"]-sum(v["kw"] for v in facts["loads"]),
        "diagnostic_opendss_losses_kw":flow["perdidas_totales_kw"],"can_claim_etap_parity":False}
