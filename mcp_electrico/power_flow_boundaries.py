"""Explicit PF-only slack and PQ intervals using native OpenDSS properties."""
from math import isfinite
from opendssdirect import dss

FIELDS = {"model", "base_mva", "r_pu", "x_pu", "tolerance", "max_iterations", "source_reference"}


def _finite(value):
    return type(value) in (int, float) and isfinite(value)


def validate(manifest):
    issues = []
    def issue(path, message):
        issues.append({"code": "PFBND001", "path": path, "message": message})
    source = manifest.get("source") or {}
    boundary = source.get("power_flow_boundary")
    if "power_flow_boundary" in source:
        if not isinstance(boundary, dict) or set(boundary) != FIELDS:
            issue("source.power_flow_boundary", "Explicit quasi-ideal PF boundary fields required.")
        else:
            if boundary["model"] != "QUASI_IDEAL_SLACK":
                issue("source.power_flow_boundary.model", "Only QUASI_IDEAL_SLACK supported.")
            if not _finite(boundary["base_mva"]) or boundary["base_mva"] <= 0:
                issue("source.power_flow_boundary.base_mva", "Finite positive base MVA required.")
            for key in ("r_pu", "x_pu"):
                if not _finite(boundary[key]) or not 0 < boundary[key] <= .001:
                    issue("source.power_flow_boundary."+key, "Finite positive quasi-ideal impedance <= .001 pu required.")
            if not _finite(boundary["tolerance"]) or not 0 < boundary["tolerance"] <= .001:
                issue("source.power_flow_boundary.tolerance", "Explicit finite positive tolerance <= .001 required.")
            if type(boundary["max_iterations"]) is not int or not 1 <= boundary["max_iterations"] <= 1000:
                issue("source.power_flow_boundary.max_iterations", "Integer 1..1000 required.")
            if not isinstance(boundary["source_reference"], str) or not boundary["source_reference"].strip():
                issue("source.power_flow_boundary.source_reference", "Source reference required.")
        if set(manifest.get("requested_scope") or []) - {"POWER_FLOW", "VOLTAGE_DROP"}:
            issue("requested_scope", "PF-only boundary does not supply fault/ampacity/protection inputs.")
        if any(source.get(key) is not None for key in ("scc_max_mva", "x_r_max", "scc_min_mva", "x_r_min")):
            issue("source", "Do not combine PF-only boundary with utility SC data.")
    for i, load in enumerate((manifest.get("topology") or {}).get("loads") or []):
        if not isinstance(load, dict):
            continue
        if "vminpu" in load or "vmaxpu" in load:
            low, high = load.get("vminpu"), load.get("vmaxpu")
            if not (_finite(low) and _finite(high) and 0 < low < high):
                issue(f"topology.loads[{i}]", "Declare finite explicit 0 < vminpu < vmaxpu together.")
    return issues


def apply_source(source):
    boundary = source.get("power_flow_boundary")
    if boundary is not None:
        dss(f"Edit Vsource.source BaseMVA={boundary['base_mva']} Model=Ideal "
            f"puZideal=[{boundary['r_pu']},{boundary['x_pu']}]")
        dss(f"Set tolerance={boundary['tolerance']} maxiterations={boundary['max_iterations']}")


def load_edits(load):
    return [f"Vminpu={load['vminpu']}", f"Vmaxpu={load['vmaxpu']}"] if "vminpu" in load else []
