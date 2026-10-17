"""Explicit three-phase PF matrices and load nodes; native OpenDSS physics."""
from math import isfinite

import numpy as np
from opendssdirect import dss


def validate(manifest):
    issues = []
    def issue(path, message):
        issues.append({"code": "PHASEPF001", "path": path, "message": message})
    topology = manifest.get("topology") or {}
    for i, line in enumerate(topology.get("lines") or []):
        if not isinstance(line, dict) or "phase_impedance" not in line:
            continue
        path = f"topology.lines[{i}].phase_impedance"
        data = line["phase_impedance"]
        if not isinstance(data, dict) or set(data) != {"r_ohm_km", "x_ohm_km", "c_nf_km", "source_reference"}:
            issue(path, "Declare R/X/C matrices and source_reference explicitly.")
            continue
        if line.get("phases") != 3 or isinstance(line.get("phases"), bool):
            issue(path, "Only three-phase matrices are supported.")
        if any(key in line for key in ("r1_ohm_km", "x1_ohm_km", "c1_nf_km")):
            issue(path, "Choose phase matrices or sequence parameters, never both.")
        if not isinstance(data["source_reference"], str) or not data["source_reference"].strip():
            issue(path, "Nonempty source reference required.")
        for key in ("r_ohm_km", "x_ohm_km", "c_nf_km"):
            rows = data[key]
            valid = (isinstance(rows, list) and len(rows) == 3 and all(
                isinstance(row, list) and len(row) == 3 and all(
                    type(v) in (int, float) and isfinite(v) for v in row) for row in rows))
            if not valid:
                issue(path + "." + key, "Finite numeric 3x3 matrix required.")
                continue
            matrix = np.array(rows)
            if not np.allclose(matrix, matrix.T, rtol=0, atol=1e-12):
                issue(path + "." + key, "Symmetric matrix required.")
            elif np.linalg.eigvalsh(matrix).min() < -1e-12:
                issue(path + "." + key, "Passive positive-semidefinite matrix required.")
        if not (manifest.get("source") or {}).get("power_flow_boundary"):
            issue(path, "v1 phase input requires an explicit PF-only boundary; no fault projection.")
    for i, load in enumerate(topology.get("loads") or []):
        if not isinstance(load, dict) or "nodes" not in load:
            continue
        nodes = load["nodes"]
        if (type(load.get("phases")) is not int or load.get("phases") != 1 or load.get("connection") != "wye" or
            not isinstance(nodes, list) or len(nodes) != 2 or
            type(nodes[0]) is not int or nodes[0] not in (1, 2, 3) or
            type(nodes[1]) is not int or nodes[1] != 0):
            issue(f"topology.loads[{i}].nodes", "v1 supports a single-phase wye load [phase 1..3, 0] only.")
    return issues


def create_line(name, line):
    """Create directly from matrices, without sequence placeholders."""
    data = line["phase_impedance"]
    fields = []
    for native, key in (("Rmatrix", "r_ohm_km"), ("Xmatrix", "x_ohm_km"), ("Cmatrix", "c_nf_km")):
        triangle = " | ".join(" ".join(str(v) for v in row[:i+1]) for i, row in enumerate(data[key]))
        fields.append(f"{native}=[{triangle}]")
    dss(f"New Line.{name} Bus1={line['bus1']} Bus2={line['bus2']} Phases=3 "
        f"Length={line['length_km']} Units=km " + " ".join(fields))
    from . import core
    core._inherit_line_voltage_base(line["bus1"], line["bus2"])


def load_bus(load):
    return load["bus"] + ("." + ".".join(map(str, load["nodes"])) if "nodes" in load else "")
