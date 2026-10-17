"""Q11 published IEEE4 facts and independent balanced transformer oracle.

Not imported by the server. CSVs are IEEE results transcribed by Power Grid
Model contributors, pinned at 4cb5f85c7e361bd68243036ca255d2100ed0a937.
"""
from copy import deepcopy
import csv
from math import acos, tan, sqrt
from pathlib import Path

from scripts.published_feeder_reference import BOUNDARY

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "examples/qualification/ieee4"
PIN = "4cb5f85c7e361bd68243036ca255d2100ed0a937"
UPSTREAM = f"https://github.com/PowerGridModel/power-grid-model-io/blob/{PIN}/_network_data_generation/ieee_4_node/"
TOLERANCES = {"voltage_v_abs": 5., "voltage_angle_deg_abs": 1., "current_a_abs": 5., "current_angle_deg_abs": 1.5}


def ieee_manifest(direction="down", connection="ynyn", loading="balanced"):
    assert direction in ("down", "up") and connection in ("ynyn", "dyn") and loading in ("balanced", "unbalanced")
    secondary = 4.16 if direction == "down" else 24.9
    ref = UPSTREAM + f"results_step_{direction}_{loading}_loading.csv"
    wires = {r["wire_type"]: r for r in csv.DictReader((DATA / "wire_data_ieee_4_node.csv").open())}
    lines = []
    for i, (a, b, feet, wire) in enumerate((("n1", "n2", 2000, "3-wire" if connection == "dyn" else "4-wire"),
                                          ("n3", "n4", 2500, "4-wire")), 1):
        w = wires[wire]
        matrices = {}
        for kind in ("r", "x"):
            matrices[kind + "_ohm_km"] = [[float(w[f"{kind}_{v}"])/1.609344 for v in row]
                for row in (("aa", "ba", "ca"), ("ba", "bb", "cb"), ("ca", "cb", "cc"))]
        matrices.update(c_nf_km=[[0., 0., 0.] for _ in range(3)], source_reference=UPSTREAM+"wire_data_ieee_4_node.csv")
        lines.append({"id":f"Line.l{i}", "bus1":a, "bus2":b, "phases":3, "length_km":feet*.0003048,
                      "phase_impedance":matrices, "source_reference":ref})
    # The labels HV/LV remain physical even when supplied from the LV side.
    if direction == "down":
        hv, lv, kh, kl, vg = "n2", "n3", 12.47, secondary, "Dyn1" if connection == "dyn" else "Yy0"
    else:
        hv, lv, kh, kl, vg = "n3", "n2", secondary, 12.47, "Yd1" if connection == "dyn" else "Yy0"
    trafo = {"id":"Transformer.t1", "bus_hv":hv, "bus_lv":lv, "kva":6000., "kv_hv":kh, "kv_lv":kl,
             "uk_percent":sqrt(1+36), "x_r":6., "vector_group":vg, "load_loss_kw":60.,
             "no_load_loss_kw":0., "i0_percent":0., "source_reference":ref}
    powers = [1800.]*3 if loading == "balanced" else [1275.,1800.,2375.]
    factors = [.9]*3 if loading == "balanced" else [.85,.9,.95]
    loads = [{"id":f"Load.p{i}", "bus":"n4", "nodes":[i,0], "phases":1, "kv":secondary/sqrt(3),
              "kw":p, "kvar":p*tan(acos(pf)), "model":1, "connection":"wye", "vminpu":.5, "vmaxpu":1.5,
              "source_reference":ref} for i,(p,pf) in enumerate(zip(powers,factors),1)]
    return {"project":{"id":f"ieee4_{direction}_{connection}_{loading}", "name":"Published IEEE four-node feeder", "source_reference":ref},
            "source":{"bus":"n1", "kv_ll":12.47, "frequency_hz":60., "pu":1., "angle_deg":0.,
                      "source_reference":ref, "power_flow_boundary":deepcopy(BOUNDARY)},
            "requested_scope":["POWER_FLOW"], "topology":{"buses":["n1","n2","n3","n4"],
            "transformers":[trafo], "lines":lines, "loads":loads},
            "qualification_conventions":{"neutral":"Kron-reduced line neutral; solid grounded wye transformer; no explicit neutral voltage qualification",
                "shunt":"Zero line capacitance and transformer excitation, as in published benchmark model",
                "tap":"Nominal fixed tap, no automatic regulator", "faults":"PF source is not utility SCC data"}}


def expected_ieee(direction, connection, loading):
    path = DATA / f"results_step_{direction}_{loading}_loading.csv"
    return next(r for r in csv.DictReader(path.open()) if r["Connection"] == connection)


def compare_ieee(flow, detail, direction, connection, loading):
    import cmath
    expected = expected_ieee(direction, connection, loading)
    errors = dict.fromkeys(TOLERANCES, 0.)
    def check(actual, token, magkey, anglekey):
        mag, angle = map(float, token.split("/"))
        errors[magkey] = max(errors[magkey], abs(abs(actual)-mag))
        errors[anglekey] = max(errors[anglekey], abs((cmath.phase(actual)*180/3.141592653589793-angle+180)%360-180))
    assert flow["convergio"] and set(flow["voltajes_por_bus"]) == {"n1","n2","n3","n4"}
    for node in (2,3,4):
        row = flow["voltajes_por_bus"][f"n{node}"]
        assert row["nodes"] == [1,2,3]
        v = [cmath.rect(m, a*3.141592653589793/180) for m,a in zip(row["voltajes_ln_v"],row["angulos_ln_deg"])]
        if node == 2 and connection == "dyn":
            v = [v[0]-v[1], v[1]-v[2], v[2]-v[0]]
        for phase,actual in zip("abc",v):
            check(actual, expected[f"V_{node}_{phase}"], "voltage_v_abs", "voltage_angle_deg_abs")
    feeders = {r["id"].lower():r for r in detail["alimentadores"]}
    for line, branch in ((1,"12"),(2,"34")):
        row = feeders[f"line.l{line}"]
        for phase, mag, angle in zip("abc", row["corrientes_terminal1_a"][:3], row["angulos_corriente_terminal1_deg"][:3]):
            check(cmath.rect(mag,angle*3.141592653589793/180),expected[f"I_{branch}_{phase}"],"current_a_abs","current_angle_deg_abs")
    return {"errors":errors, "tolerances":deepcopy(TOLERANCES), "passed":all(v<=TOLERANCES[k] for k,v in errors.items())}


def tap_manifest(group="Dyn11", side="hv", position=0, excitation=False):
    """Controlled integration variant, NOT a published customer project."""
    data = ieee_manifest()
    data["project"]["id"] = f"tap_{group}_{side}_{position}_{excitation}"
    data["project"]["name"] = "Controlled balanced transformer integration check"
    t = data["topology"]["transformers"][0]
    t.update(vector_group=group, tap_side=side, tap_neutral=0, tap_min=-4, tap_max=4,
             tap_step_percent=2.5, tap_pos=position, no_load_loss_kw=6. if excitation else 0.,
             i0_percent=.5 if excitation else 0., source_reference="Explicit qualification variant, not nameplate data")
    # Transposed equivalent line, so an independent positive-sequence AC Newton
    # solution is applicable. These are controlled values, not IEEE4 matrices.
    for line in data["topology"]["lines"]:
        line.pop("phase_impedance")
        line.update(r1_ohm_km=.3, x1_ohm_km=.4, c1_nf_km=0., source_reference="Controlled transposed line")
    for load in data["topology"]["loads"]:
        load["kw"] *= .5
        load["kvar"] *= .5
    data["qualification_conventions"] = {"case":"Controlled balanced variant; not original IEEE4",
        "shunt":"Transformer excitation is represented at winding 2 with an explicit P0/I0",
        "neutral":"Balanced operation only", "tap":"Fixed tap positions, no automatic controller"}
    return data


def balanced_reference(data):
    """Build Newton input from manifest facts, never from native solver results."""
    import numpy as np
    from pypower.api import runpf, ppoption
    topo = data["topology"]
    buses = topo["buses"]
    t = topo["transformers"][0]
    bus = np.zeros((len(buses),13))
    bus[:,0] = np.arange(1,len(buses)+1)
    bus[:,1] = 1
    bus[0,1] = 3
    bus[:,6] = 1
    bus[:,7] = 1
    bus[:,9] = [12.47,12.47,4.16,4.16]
    bus[:,10] = 1
    bus[:,11:13] = [1.5,.5]
    for load in topo["loads"]:
        bus[buses.index(load["bus"]),2:4] += np.array([load["kw"],load["kvar"]])/1000
    base = 6.
    branches = []
    for line in topo["lines"]:
        a,b = buses.index(line["bus1"]), buses.index(line["bus2"])
        zbase = bus[a,9]**2/base
        branches.append([a+1,b+1,line["length_km"]*line["r1_ohm_km"]/zbase,
            line["length_km"]*line["x1_ohm_km"]/zbase,0,0,0,0,0,0,1,-360,360])
    a,b = buses.index(t["bus_hv"]),buses.index(t["bus_lv"])
    tap = 1+(t["tap_pos"]-t["tap_neutral"])*t["tap_step_percent"]/100
    ht,lt = (tap,1.) if t["tap_side"]=="hv" else (1.,tap)
    r = t["load_loss_kw"]/t["kva"]
    x = sqrt((t["uk_percent"]/100)**2-r*r)
    clock = 11 if t["vector_group"].endswith("11") else (1 if t["vector_group"].endswith("1") else 0)
    shift = -30 if clock==11 else (30 if clock==1 else 0)
    branches.append([a+1,b+1,r*lt*lt,x*lt*lt,0,0,0,0,ht/lt,shift,1,-360,360])
    p0 = t["no_load_loss_kw"]
    q0 = sqrt((t["i0_percent"]/100*t["kva"])**2-p0*p0)
    bus[b,4:6] = [p0/1000/lt**2,-q0/1000/lt**2]
    gen = np.zeros((1,21)); gen[0,:10] = [1,0,0,100,-100,1,base,1,100,-100]
    result,ok = runpf({"version":"2","baseMVA":base,"bus":bus,"gen":gen,"branch":np.array(branches)},
        ppoption(PF_ALG=1,PF_TOL=1e-11,PF_MAX_IT=100,VERBOSE=0,OUT_ALL=0))
    assert ok, "Independent Newton reference did not converge"
    return {"engine":"PYPOWER AC Newton", "voltages_pu":dict(zip(buses,map(float,result["bus"][:,7]))),
            "angles_deg":dict(zip(buses,map(float,result["bus"][:,8]))),
            "loss_kw":float((result["gen"][:,1].sum()-bus[:,2].sum())*1000),
            "loss_kvar":float((result["gen"][:,2].sum()-bus[:,3].sum())*1000)}


def compare_balanced(flow, ref):
    assert flow["convergio"]
    errors = {"voltage_pu_abs":0., "angle_deg_abs":0.,
        "loss_kw_abs":abs(flow["perdidas_totales_kw"]-ref["loss_kw"]),
        "loss_kvar_abs":abs(flow["perdidas_totales_kvar"]-ref["loss_kvar"])}
    tolerances = {"voltage_pu_abs":.0002,"angle_deg_abs":.01,"loss_kw_abs":.05,"loss_kvar_abs":.05}
    for bus,row in flow["voltajes_por_bus"].items():
        errors["voltage_pu_abs"] = max(errors["voltage_pu_abs"],*(abs(v-ref["voltages_pu"][bus]) for v in row["voltajes_pu"]))
        errors["angle_deg_abs"] = max(errors["angle_deg_abs"],abs((row["angulos_ln_deg"][0]-ref["angles_deg"][bus]+180)%360-180))
    return {"passed":all(v<=tolerances[k] for k,v in errors.items()), "errors":errors, "tolerances":tolerances}
