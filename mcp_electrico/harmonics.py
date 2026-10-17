"""Explicit balanced harmonic studies using native OpenDSS, with isolated contexts.

The adapter validates inputs and reads phasors; it implements no network solver.
Integer non-triplen spectra and positive-sequence impedance scans are distinct.
"""
from copy import deepcopy
import hashlib
from html import escape
import json
from math import isfinite, sqrt
from pathlib import Path

import numpy as np
from opendssdirect import dss
from . import reactive_compensation as rc
from . import module_qualification

SCHEMA = "MCP_ELECTRICO_HARMONICS_V1"


def contract():
    return {
        "schema": SCHEMA, "engine": "OpenDSS",
        "qualification": module_qualification.get("harmonics"),
        "scope": "BALANCED_3PH_NONTRIPLEN_LOAD_SPECTRA_AND_POSITIVE_SEQUENCE_SCAN",
        "frequency_model": "CONSTANT_R_LINEAR_X_NO_SKIN_EFFECT",
        "source_spectrum": "FUNDAMENTAL_ONLY",
        "load_admittance": "EXPLICIT_SERIES_PARALLEL_RL_FROM_NOMINAL_PQ",
        "thd": "TRUNCATED_TO_DECLARED_INTEGER_ORDERS_REFERRED_TO_SOLVED_FUNDAMENTAL",
        "scan": "ONE_AMP_POSITIVE_SEQUENCE_DRIVING_POINT_NO_HARMONIC_LOAD_INJECTIONS",
        "scan_peaks": "SAMPLED_LOCAL_MAXIMA_NOT_CERTIFIED_RESONANCE_FREQUENCIES",
        "not_supported": ["triplen_or_zero_sequence", "unbalance", "interharmonic_emissions",
                          "background_voltage_harmonics", "frequency_dependent_skin_effect",
                          "detuned_filters", "automatic_IEEE519_compliance", "switching_transients"],
        "physical_solver_owned_by_mcp": False, "automatic_defaults": False,
        "parent_model_mutated": False, "professional_emission": False,
    }


def validate(package):
    issues = []

    def issue(path, message):
        issues.append({"path": path, "message": message})

    def obj(value, path, fields):
        if not isinstance(value, dict):
            issue(path, "object required")
            return {}
        if set(value) != set(fields):
            issue(path, "exact explicit fields required: " + ", ".join(sorted(fields)))
        return value

    def number(value, path, low, high):
        if type(value) not in (int, float):
            issue(path, "finite explicit number required")
            return False
        try:
            valid = isfinite(value) and low <= value <= high
        except OverflowError:
            valid = False
        if not valid:
            issue(path, "number outside supported range")
        return valid

    def reference(value, path):
        if not isinstance(value, str) or not value.strip():
            issue(path, "source reference required")

    def rows(value, path, maximum, nonempty=False):
        if not isinstance(value, list) or len(value) > maximum or (nonempty and not value):
            issue(path, "explicit bounded list required")
            return []
        return value

    root = obj(package, "study", {"schema", "id", "source_reference", "base_model", "banks",
                                  "load_harmonics", "orders", "scan", "criteria", "options"})
    if root.get("schema") != SCHEMA:
        issue("schema", SCHEMA + " required")
    reference(root.get("id"), "id")
    reference(root.get("source_reference"), "source_reference")
    base_issues, bases = rc.validate_base_network(root.get("base_model"))
    issues.extend(base_issues)
    base = root.get("base_model") if isinstance(root.get("base_model"), dict) else {}
    source = base.get("source") if isinstance(base.get("source"), dict) else {}
    if type(source.get("frequency_hz")) not in (int, float) or source.get("frequency_hz") not in (50, 60):
        issue("base_model.source.frequency_hz", "verified 50 or 60 Hz required")
    topo = base.get("topology") if isinstance(base.get("topology"), dict) else {}
    loads = topo.get("loads") if isinstance(topo.get("loads"), list) else []
    loads = {item["id"]: item for item in loads if isinstance(item, dict) and isinstance(item.get("id"), str)}
    declared = rows(root.get("orders"), "orders", 32, True)
    if any(type(h) is not int or not 2 <= h <= 50 or h % 3 == 0 for h in declared):
        issue("orders", "unique ascending integer orders 2..50 excluding triplen required")
    elif declared != sorted(set(declared)):
        issue("orders", "unique ascending orders required")
    records = rows(root.get("load_harmonics"), "load_harmonics", 200, True)
    seen = set()
    for i, raw in enumerate(records):
        path = f"load_harmonics[{i}]"
        item = obj(raw, path, {"load_id", "series_rl_percent", "spectrum", "source_reference"})
        key = item.get("load_id")
        if not isinstance(key, str) or key not in loads or key in seen:
            issue(path + ".load_id", "exactly one entry for every load required")
        else:
            seen.add(key)
        number(item.get("series_rl_percent"), path + ".series_rl_percent", 0, 100)
        reference(item.get("source_reference"), path + ".source_reference")
        spectrum = rows(item.get("spectrum"), path + ".spectrum", 32)
        orders = []
        for j, point in enumerate(spectrum):
            point = obj(point, path + f".spectrum[{j}]", {"order", "percent", "angle_deg"})
            order = point.get("order")
            if type(order) is not int or order not in declared:
                issue(path, "spectrum orders must belong to declared non-triplen orders")
            orders.append(str(order))
            number(point.get("percent"), path + ".percent", 0, 1000)
            number(point.get("angle_deg"), path + ".angle_deg", -360, 360)
        if len(orders) != len(set(orders)):
            issue(path, "duplicate spectrum order")
    if seen != set(loads):
        issue("load_harmonics", "classify every load, including explicit empty spectra for linear loads")
    banks = rows(root.get("banks"), "banks", 16)
    bank_ids = set()
    for i, raw in enumerate(banks):
        path = f"banks[{i}]"
        item = obj(raw, path, {"id", "bus", "kv_ll", "kvar", "connection", "enabled", "source_reference"})
        key = item.get("id")
        if not isinstance(key, str) or not rc.SAFE.fullmatch(key) or key.casefold() in bank_ids:
            issue(path + ".id", "safe unique bank identifier required")
        else:
            bank_ids.add(key.casefold())
        if not isinstance(item.get("bus"), str) or item.get("bus") not in bases:
            issue(path + ".bus", "declared network bus required")
        if (number(item.get("kv_ll"), path + ".kv_ll", .01, 1000)
                and isinstance(item.get("bus"), str) and item["bus"] in bases):
            if abs(item["kv_ll"] - bases[item["bus"]]) > 1e-6:
                issue(path + ".kv_ll", "bank rating must match bus voltage in V1")
        number(item.get("kvar"), path + ".kvar", .001, 1e7)
        if item.get("connection") not in ("wye", "delta"):
            issue(path + ".connection", "wye/delta required")
        if type(item.get("enabled")) is not bool:
            issue(path + ".enabled", "explicit boolean required")
        reference(item.get("source_reference"), path + ".source_reference")
    scan = obj(root.get("scan"), "scan", {"buses", "orders", "sequence", "source_reference"})
    scan_buses = rows(scan.get("buses"), "scan.buses", 8)
    if any(not isinstance(bus, str) or bus not in bases for bus in scan_buses):
        issue("scan.buses", "declared buses required")
    if len(set(str(v) for v in scan_buses)) != len(scan_buses):
        issue("scan.buses", "unique buses required")
    scan_orders = rows(scan.get("orders"), "scan.orders", 500)
    valid_scan = all(number(h, "scan.orders", 1.01, 50) for h in scan_orders)
    if valid_scan and scan_orders != sorted(set(scan_orders)):
        issue("scan.orders", "unique ascending scan orders required")
    if bool(scan_buses) != bool(scan_orders) or (scan_orders and len(scan_orders) < 3):
        issue("scan", "declare buses and at least three scan points together, or both empty")
    if scan.get("sequence") != "positive":
        issue("scan.sequence", "only positive-sequence driving-point scans supported")
    reference(scan.get("source_reference"), "scan.source_reference")
    criteria = obj(root.get("criteria"), "criteria", {"maximum_voltage_thd_percent", "source_reference"})
    number(criteria.get("maximum_voltage_thd_percent"), "criteria.maximum_voltage_thd_percent", 0, 1000)
    reference(criteria.get("source_reference"), "criteria.source_reference")
    options = obj(root.get("options"), "options", {"frequency_model", "neglect_load_y", "solver_tolerance",
                                                        "max_iterations", "kcl_tolerance_a"})
    if options.get("frequency_model") != "CONSTANT_R_LINEAR_X_NO_SKIN_EFFECT":
        issue("options.frequency_model", "explicit supported approximation required")
    if options.get("neglect_load_y") is not False:
        issue("options.neglect_load_y", "False required: preserve explicitly declared load damping")
    number(options.get("solver_tolerance"), "options.solver_tolerance", 1e-12, 1e-4)
    number(options.get("kcl_tolerance_a"), "options.kcl_tolerance_a", 1e-9, .01)
    if type(options.get("max_iterations")) is not int or not 2 <= options["max_iterations"] <= 1000:
        issue("options.max_iterations", "integer 2..1000 required")
    # Passive RL damping excludes negative reactance, generation and zero-sized loads.
    for key, load in loads.items():
        if type(load.get("kw")) in (int, float) and load["kw"] <= 0:
            issue(key, "strictly positive load kW required")
        if type(load.get("kvar")) in (int, float) and load["kvar"] < 0:
            issue(key, "capacitive demand must be represented as an explicit bank")
    return {"schema": SCHEMA, "ready_for_execution": not issues, "issues": issues,
            "bus_bases_kv_ll": bases, "electrical_calculation_performed": False,
            "automatic_defaults": False, "professional_emission": False}


def _spectrum(engine, name, orders, percents, angles):
    array = lambda values: "[" + ",".join(str(v) for v in values) + "]"
    engine(f"New Spectrum.{name} NumHarm={len(orders)} Harmonic={array(orders)} "
           f"%Mag={array(percents)} Angle={array(angles)}")


def _build(package, scan=False):
    base = package["base_model"]
    bases = rc.network._derive_bus_bases(base, [])[0]
    engine, _ = rc.network._build_isolated_base(base, [], bases)
    f = base["source"]["frequency_hz"]
    _spectrum(engine, "h_fundamental", [1], [100], [0])
    engine(f"Edit Vsource.source BaseFreq={f} Frequency={f} Model=Thevenin Spectrum=h_fundamental")
    for kind, group in (("Line", "lines"), ("Transformer", "transformers"), ("Load", "loads")):
        for item in base["topology"][group]:
            name = rc.network._element_name(item["id"], kind)
            engine(f"Edit {kind}.{name} BaseFreq={f}")
            if kind == "Line":
                engine(f"Edit Line.{name} Rg=0 Xg=0")
            elif kind == "Transformer":
                engine(f"Edit Transformer.{name} XRConst=No ppm_Antifloat=0")
            else:
                engine(f"Edit Load.{name} Vminpu={item['vminpu']} Vmaxpu={item['vmaxpu']}")
    for i, item in enumerate(package["load_harmonics"]):
        points = [] if scan else item["spectrum"]
        _spectrum(engine, f"h_load_{i}", [1] + [p["order"] for p in points],
                  [100] + [p["percent"] for p in points], [0] + [p["angle_deg"] for p in points])
        name = rc.network._element_name(item["load_id"], "Load")
        engine(f"Edit Load.{name} Spectrum=h_load_{i} %SeriesRL={item['series_rl_percent']} puXHarm=0 XRHarm=6")
    for item in package["banks"]:
        engine(f"New Capacitor.h_{item['id']} Bus1={item['bus']} Bus2={item['bus']}.0.0.0 Phases=3 "
               f"Conn={item['connection']} kV={item['kv_ll']} kvar={item['kvar']} BaseFreq={f} "
               f"NumSteps=1 R=[0] XL=[0] States=[{int(item['enabled'])}]")
    opt = package["options"]
    engine(f"Set Mode=Snapshot ControlMode=Off Frequency={f} LoadMult=1 NeglectLoadY=No "
           f"Algorithm=Normal Tolerance={opt['solver_tolerance']} MaxIterations={opt['max_iterations']}")
    engine.Solution.Solve()
    if not engine.Solution.Converged():
        raise ValueError("FUNDAMENTAL_NONCONVERGENCE")
    for item in base["topology"]["loads"]:
        values = rc.network._bus_voltage_pu(engine, item["bus"])
        if item["model"] == 1 and not all(item["vminpu"] < v < item["vmaxpu"] for v in values):
            raise ValueError("FUNDAMENTAL_LOAD_MODEL_FALLBACK: " + item["id"])
    return engine


def _phasors(raw):
    values = [complex(a, b) for a, b in zip(raw[::2], raw[1::2])]
    if not values or any(not isfinite(v.real) or not isfinite(v.imag) for v in values):
        raise ValueError("NONFINITE_OR_EMPTY_ENGINE_PHASORS")
    return values


def _meters(engine, package):
    buses = []
    for bus in package["base_model"]["topology"]["buses"]:
        if engine.Circuit.SetActiveBus(bus) < 0:
            raise ValueError("MISSING_ENGINE_BUS: " + bus)
        nodes = engine.Bus.Nodes()
        voltage = dict(zip(nodes, _phasors(engine.Bus.Voltages())))
        if not {1, 2, 3} <= set(voltage):
            raise ValueError("MISSING_THREE_PHASE_NODES: " + bus)
        phase = [voltage[n] for n in (1, 2, 3)]
        buses.append({"bus": bus, "voltage_ln_v": [abs(v) for v in phase],
                      "voltage_phasors_v": [[v.real, v.imag] for v in phase]})
    elements = []
    for name in engine.Circuit.AllElementNames():
        engine.Circuit.SetActiveElement(name)
        if not engine.CktElement.Enabled():
            continue
        currents = _phasors(engine.CktElement.Currents())
        n = engine.CktElement.NumConductors()
        # Load.GetCurrents in this backend does not expose the full Norton
        # shunt contribution in harmonic mode. Publish PD terminal meters only.
        if name.lower().startswith(("line.", "transformer.", "capacitor.")):
            elements.append({"id": name, "terminal_phase_currents_a": [
                [abs(v) for v in currents[t*n:t*n+3]] for t in range(engine.CktElement.NumTerminals())]})
    voltage = np.asarray(_phasors(engine.Circuit.YNodeVArray()))
    residuals = -np.asarray(_phasors(engine.Circuit.YCurrents()))
    data, indices, indptr = engine.YMatrix.getYsparse()
    for col, value in enumerate(voltage):
        lo, hi = indptr[col:col+2]
        np.add.at(residuals, indices[lo:hi], data[lo:hi]*value)
    residual = float(max(abs(residuals)))
    if residual > package["options"]["kcl_tolerance_a"]:
        raise ValueError(f"ENGINE_KCL_RESIDUAL_EXCEEDED: {residual}")
    return {"buses": buses, "elements": elements, "maximum_kcl_residual_a": residual}


def _solve_order(engine, order, frequency):
    engine(f"Set Harmonics=[{order}]")
    engine.Solution.Solve()
    if not engine.Solution.Converged() or abs(engine.Solution.Frequency() - order*frequency) > 1e-6:
        raise ValueError("HARMONIC_SOLUTION_INVALID_OR_WRONG_FREQUENCY")


def _run(package):
    frequency = package["base_model"]["source"]["frequency_hz"]
    engine = _build(package)
    fundamental = _meters(engine, package)
    engine("Set Mode=Harmonic")
    harmonics = []
    for order in package["orders"]:
        _solve_order(engine, order, frequency)
        harmonics.append({"order": order, "frequency_hz": frequency*order, **_meters(engine, package)})
    thd = []
    for i, bus in enumerate(fundamental["buses"]):
        denominators = bus["voltage_ln_v"]
        if min(denominators) <= 1e-6:
            raise ValueError("FUNDAMENTAL_VOLTAGE_TOO_SMALL_FOR_THD")
        values = [100*sqrt(sum(h["buses"][i]["voltage_ln_v"][p]**2 for h in harmonics))/denominators[p]
                  for p in range(3)]
        thd.append({"bus": bus["bus"], "voltage_thd_percent": values,
                    "passed_declared_criterion": max(values) <= package["criteria"]["maximum_voltage_thd_percent"]})
    scans = []
    for bus in package["scan"]["buses"]:
        engine = _build(package, scan=True)
        engine("Set Mode=Harmonic")
        orders = package["scan"]["orders"]
        _spectrum(engine, "h_scan", [1]+orders, [0]+[100]*len(orders), [0]*(1+len(orders)))
        engine(f"New Isource.h_probe Bus1={bus}.1.2.3 Bus2={bus}.0.0.0 Phases=3 Amps=1 Angle=0 "
               f"Frequency={frequency} BaseFreq={frequency} ScanType=Positive Sequence=Positive Spectrum=h_scan")
        points = []
        for order in orders:
            _solve_order(engine, order, frequency)
            metrics = _meters(engine, package)
            values = next(v for v in metrics["buses"] if v["bus"] == bus)["voltage_phasors_v"]
            engine.Circuit.SetActiveElement("Isource.h_probe")
            injection = -_phasors(engine.CktElement.Currents())[0]
            if abs(injection) < .999999 or abs(injection) > 1.000001:
                raise ValueError("SCAN_PROBE_CURRENT_NOT_ONE_AMP")
            impedance = complex(*values[0])/injection
            points.append({"order": order, "frequency_hz": frequency*order,
                           "r_ohm": impedance.real, "x_ohm": impedance.imag, "z_ohm": abs(impedance),
                           "maximum_kcl_residual_a": metrics["maximum_kcl_residual_a"]})
        peaks = [points[i] for i in range(1, len(points)-1)
                 if points[i]["z_ohm"] > points[i-1]["z_ohm"] and points[i]["z_ohm"] > points[i+1]["z_ohm"]]
        scans.append({"bus": bus, "sequence": "positive", "points": points,
                      "sampled_local_peaks": peaks, "peak_interpretation": contract()["scan_peaks"]})
    return {"fundamental": fundamental, "harmonics": harmonics, "voltage_thd": thd, "scans": scans,
            "criteria": {"evaluated": True, "passed": all(v["passed_declared_criterion"] for v in thd),
                         "source_reference": package["criteria"]["source_reference"]}}


def _report(package, result):
    body = "<p>Resultados no evaluables: " + escape(result.get("error", "")) + "</p>"
    if result.get("results_valid"):
        rows = "".join("<tr><td>" + escape(row["bus"]) + "</td><td>" +
                       ", ".join(f"{v:.5g}" for v in row["voltage_thd_percent"]) + "</td><td>" +
                       ("CUMPLE" if row["passed_declared_criterion"] else "EXCEDE") + "</td></tr>"
                       for row in result["voltage_thd"])
        body = "<table><tr><th>Barra</th><th>THDv por fase (%)</th><th>Criterio declarado</th></tr>"+rows+"</table>"
        for scan in result["scans"]:
            points = "".join(f"<tr><td>{p['frequency_hz']:.6g}</td><td>{p['z_ohm']:.6g}</td></tr>" for p in scan["points"])
            body += "<h2>Barrido: " + escape(scan["bus"]) + "</h2><table><tr><th>Hz</th><th>|Z| (ohm)</th></tr>"+points+"</table>"
    return '<!doctype html><html lang="es"><meta charset="utf-8"><title>Armónicos</title><style>body{font:15px system-ui;max-width:1000px;margin:30px auto}table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:6px}@media print{body{margin:0}}</style><h1>'+escape(package["id"])+" — Armónicos y barrido de impedancia</h1><p>OpenDSS. THD truncada a los órdenes declarados; tensiones fase-neutro. No se evalúa conformidad IEEE 519. Los máximos del barrido son puntos muestreados que requieren refinamiento.</p><p>Criterio: "+escape(package["criteria"]["source_reference"])+"</p>"+body+"</html>"


def execute(package, output_directory):
    readiness = validate(package)
    if not readiness["ready_for_execution"]:
        return {"status": "BLOCKED_HARMONICS_INPUTS", "readiness": readiness, "results_valid": False}
    folder = Path(output_directory).expanduser().resolve()
    try:
        folder.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        return {"status": "BLOCKED_OUTPUT_DIRECTORY", "results_valid": False, "output_directory": str(folder)}
    parent = rc.network._parent_signature()
    result = {"schema": SCHEMA, "engine": "OpenDSS", "engine_version": dss.Basic.Version(),
              "contract": contract(), "results_valid": False, "professional_emission": False}
    try:
        result.update(_run(deepcopy(package)), results_valid=True, status="HARMONICS_COMPLETED")
    except Exception as exc:
        result.update(status="HARMONICS_INVALID", error=f"{type(exc).__name__}: {exc}",
                      criteria={"evaluated": False, "passed": False})
    result["parent_model_mutated"] = rc.network._parent_signature() != parent
    if result["parent_model_mutated"]:
        result.update(status="HARMONICS_INVALID", results_valid=False, criteria={"evaluated": False, "passed": False})
    for name, value in (("Inputs.json", package), ("Results.json", result)):
        (folder/name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf8")
    (folder/"Informe.html").write_text(_report(package, result), encoding="utf8")
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}
    sources = [Path(__file__), Path(rc.__file__), Path(rc.network.__file__),
               Path(rc.professional_data.__file__), Path(module_qualification.__file__),
               module_qualification.PATH]
    (folder/"Integrity.json").write_text(json.dumps({"files_sha256": hashes,
        "adapter_sources_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}, indent=2), encoding="utf8")
    return {**result, "output_directory": str(folder), "files_sha256": hashes}


def register(mcp):
    @mcp.tool()
    def obtener_contrato_armonicos() -> dict:
        """Alcance de espectros no triplén y barrido de impedancia positivo con OpenDSS."""
        return contract()

    @mcp.tool()
    def validar_armonicos(paquete_estudio: dict) -> dict:
        """Valida red, espectros, amortiguamiento y criterio sin ejecutar cálculos."""
        return validate(paquete_estudio)

    @mcp.tool()
    def ejecutar_armonicos(paquete_estudio: dict, directorio_salida: str) -> dict:
        """Ejecuta OpenDSS aislado; conserva entradas, fasores, informe y hashes."""
        return execute(paquete_estudio, directorio_salida)
