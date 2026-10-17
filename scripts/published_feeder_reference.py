"""Independent validation oracle; never imported by server or an operating route."""
from copy import deepcopy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = {"model": "QUASI_IDEAL_SLACK", "base_mva": 10.0, "r_pu": 1e-8, "x_pu": 1e-8,
            "tolerance": 1e-10, "max_iterations": 100,
            "source_reference": "Numerical fixed-voltage PF slack approximation; NOT utility SC data"}
TOLERANCES = {"voltage_pu_abs": .0002, "loss_kw_abs": .05, "loss_kvar_abs": .05,
              "branch_current_a_abs": .05, "branch_power_kw_abs": .05,
              "branch_power_kvar_abs": .05, "voltage_drop_pct_abs": .03}


def load_case(name):
    return json.loads((ROOT/f"examples/qualification/{name}_matpower81.json").read_text(encoding="utf8"))


def reference(case, load_factor=1.0):
    import numpy as np
    from pypower.api import ppoption, runpf
    bus, branch, gen = [np.array(case[name], dtype=float) for name in ("bus", "branch", "gen")]
    bus[:, 2:4] *= load_factor/1000.
    branch[:, 2:4] /= bus[0, 9]**2/case["base_mva"]
    solved, success = runpf({"version": "2", "baseMVA": case["base_mva"], "bus": bus, "branch": branch, "gen": gen},
                            ppoption(PF_ALG=1, PF_TOL=1e-11, PF_MAX_IT=100, VERBOSE=0, OUT_ALL=0))
    if not success:
        raise RuntimeError("Independent AC Newton reference did not converge")
    rows = {}
    for i, original in enumerate(case["branch"]):
        if int(original[10]) != 1:
            continue
        row = solved["branch"][i]
        fbus, tbus = int(row[0]), int(row[1])
        vfrom, vto = solved["bus"][fbus-1,7], solved["bus"][tbus-1,7]
        rows[f"Line.b{i+1}"] = {"from": fbus, "to": tbus,
            "p_kw": float(row[13]*1000), "q_kvar": float(row[14]*1000),
            "current_a": float(abs(complex(row[13], row[14]))*1000/(3**.5*vfrom*bus[fbus-1,9])),
            "drop_pct": float((vfrom-vto)/vfrom*100)}
    return {"engine": "PYPOWER", "algorithm": "AC_NEWTON", "load_factor": load_factor,
            "voltages_pu": {f"n{int(row[0])}": float(row[7]) for row in solved["bus"]},
            "loss_kw": float(sum(solved["branch"][:,13]+solved["branch"][:,15])*1000),
            "loss_kvar": float(sum(solved["branch"][:,14]+solved["branch"][:,16])*1000),
            "branches": rows}


def manifest(case, load_factor=1.0, explicit_boundary=True):
    kv, provenance = case["bus"][0][9], case["source_url"]
    source = {"bus": "n1", "kv_ll": kv, "frequency_hz": 60., "pu": 1., "angle_deg": 0.,
              "source_reference": provenance}
    if explicit_boundary:
        source["power_flow_boundary"] = deepcopy(BOUNDARY)
    loads = []
    for row in case["bus"]:
        if not (row[2] or row[3]):
            continue
        load = {"id": f"Load.c{int(row[0])}", "bus": f"n{int(row[0])}", "phases": 3, "kv": kv,
                "kw": row[2]*load_factor, "kvar": row[3]*load_factor,
                "connection": "wye", "model": 1, "critical": True, "source_reference": provenance}
        if explicit_boundary:
            load.update(vminpu=.5, vmaxpu=1.5)
        loads.append(load)
    return {"project": {"id": case["case"]+"_external", "name": case["case"]+" published feeder",
                        "source_reference": provenance},
            "requested_scope": ["POWER_FLOW", "VOLTAGE_DROP"], "source": source,
            "topology": {"buses": [f"n{int(row[0])}" for row in case["bus"]], "transformers": [], "transformers_declared_absent": True,
                "lines": [{"id": f"Line.b{i+1}", "bus1": f"n{int(row[0])}", "bus2": f"n{int(row[1])}",
                           "phases": 3, "length_km": 1., "r1_ohm_km": row[2], "x1_ohm_km": row[3],
                           "c1_nf_km": 0., "source_reference": provenance}
                          for i,row in enumerate(case["branch"]) if int(row[10]) == 1], "loads": loads},
            "qualification_conventions": {
                "frequency": "60 Hz convention; impedances supplied directly in ohms",
                "length": "Unit-length equivalent segments; NOT physical line lengths",
                "load_connection": "Balanced wye equivalent of positive-sequence PQ data",
                "critical": "All test loads require supply for this test; NOT published customer classifications",
                "load_factor": load_factor, "published_original_loads": load_factor == 1.,
                "ratings": "Not provided; ampacity/loading conformity NOT evaluated",
                "short_circuit": "No utility SCC/XR/Z0; PF slack is NOT a fault equivalent"}}


def disconnected_loads(case, branch_index):
    adjacency = {int(row[0]): set() for row in case["bus"]}
    for i, row in enumerate(case["branch"]):
        if i == branch_index or int(row[10]) != 1:
            continue
        a,b = int(row[0]), int(row[1])
        adjacency[a].add(b); adjacency[b].add(a)
    reached, pending = {1}, [1]
    while pending:
        for other in adjacency[pending.pop()]:
            if other not in reached:
                reached.add(other); pending.append(other)
    return sorted(f"c{int(row[0])}" for row in case["bus"] if (row[2] or row[3]) and int(row[0]) not in reached)


def compare(flow, detail, drops, expected):
    if not flow.get("convergio"):
        return {"passed": False, "reason": "OpenDSS did not converge"}
    if set(flow["voltajes_por_bus"]) != set(expected["voltages_pu"]):
        raise AssertionError("Bus inventory mismatch")
    if {row["id"] for row in detail["alimentadores"]} != set(expected["branches"]):
        raise AssertionError("Branch inventory mismatch")
    errors = {
        "voltage_pu_abs": max(abs(value-expected["voltages_pu"][bus])
                              for bus,row in flow["voltajes_por_bus"].items() for value in row["voltajes_pu"]),
        "loss_kw_abs": abs(flow["perdidas_totales_kw"]-expected["loss_kw"]),
        "loss_kvar_abs": abs(flow["perdidas_totales_kvar"]-expected["loss_kvar"])}
    for key, refkey, actualkey in (("branch_current_a_abs", "current_a", "corriente_max_a"),
                                 ("branch_power_kw_abs", "p_kw", "flujo_kw_terminal1"),
                                 ("branch_power_kvar_abs", "q_kvar", "flujo_kvar_terminal1")):
        errors[key] = max(abs(row[actualkey]-expected["branches"][row["id"]][refkey]) for row in detail["alimentadores"])
    errors["voltage_drop_pct_abs"] = max(abs(row["caida_evaluada_pct"]-max(0,expected["branches"][row["id"]]["drop_pct"]))
                                       for row in drops["alimentadores"])
    return {"errors": errors, "tolerances": deepcopy(TOLERANCES),
            "passed": all(value <= TOLERANCES[key] for key,value in errors.items())}
