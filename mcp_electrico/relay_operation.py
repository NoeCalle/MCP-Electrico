"""Explicit constant-current operation of native pandapower OCRelay objects.

Uses the native deserialization/evaluation path, not automatic setting design.
The local tables carry declared primary RMS measurements, not a solved grid.
"""
from copy import deepcopy
import hashlib
from html import escape
import inspect
import json
from math import isfinite
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pandapower as pp
from pandapower.protection.protection_devices.ocrelay import OCRelay
from . import module_qualification, motor_starting_static as network

SCHEMA = "MCP_ELECTRICO_RELAY_OPERATION_V1"
ENGINE_VERSION = "3.5.4"
CURVES = ("standard_inverse", "very_inverse", "extremely_inverse", "long_inverse")
SETTING_FIELDS = {
    "DTOC": {"pickup_primary_a", "high_set_primary_a", "delay_s", "high_set_delay_s"},
    "IDMT": {"pickup_primary_a", "curve_type", "time_multiplier", "additive_delay_s"},
    "IDTOC": {"inverse_pickup_primary_a", "pickup_primary_a", "high_set_primary_a", "delay_s",
              "high_set_delay_s", "curve_type", "time_multiplier", "additive_delay_s"},
}


def contract():
    return {
        "schema": SCHEMA, "engine": "pandapower.OCRelay", "required_engine_version": ENGINE_VERSION,
        "qualification": module_qualification.get("relay_operation"),
        "scope": "DTOC_IDMT_IDTOC_EXPLICIT_SETTINGS_CONSTANT_PRIMARY_RMS_CURRENT_POINTS",
        "native_path": "OCRelay.from_dict -> _select_k_alpha -> protection_function -> status_to_net",
        "current_basis": "PRIMARY_RMS_A_CONVERTED_TO_NATIVE_KA",
        "current_time_model": "CONSTANT_RMS_OVER_OPERATING_TIME",
        "threshold_comparison": "STRICT_GREATER_THAN_NATIVE_PANDAPOWER",
        "relay_time_semantics": "NATIVE_RELAY_OPERATION_DELAY_NOT_TOTAL_FAULT_CLEARING",
        "total_clearing_time": "RELAY_TIME_PLUS_EXPLICIT_BREAKER_DELAY_THROUGH_ARC_EXTINCTION",
        "current_provenance_required": True, "automatic_settings": False,
        "network_short_circuit_calculated": False, "network_recalculated_after_trip": False,
        "not_supported": ["time_varying_current_integration", "CT_saturation_or_secondary_waveforms",
                          "directional_or_earth_fault_elements", "manufacturer_relay_qualification",
                          "automatic_selectivity_claim", "breaker_failure_or_reclosing", "automatic_P4_current_binding"],
        "physical_solver_owned_by_mcp": False, "parent_model_mutated": False,
        "professional_emission": False,
    }


def validate(package):
    issues = []

    def issue(path, text):
        issues.append({"path": path, "message": text})

    def obj(raw, path, fields):
        if not isinstance(raw, dict):
            issue(path, "explicit object required")
            return {}
        if set(raw) != set(fields):
            issue(path, "exact explicit fields required: " + ", ".join(sorted(fields)))
        return raw

    def number(value, path, low, high, strict=False):
        try:
            valid = type(value) in (int, float) and isfinite(value) and (low < value if strict else low <= value) and value <= high
        except OverflowError:
            valid = False
        if not valid:
            issue(path, "finite explicit number outside supported range")
        return valid

    def reference(value, path):
        if not isinstance(value, str) or not value.strip():
            issue(path, "source reference required")

    def rows(value, path, maximum):
        if not isinstance(value, list) or not 1 <= len(value) <= maximum:
            issue(path, "bounded explicit nonempty list required")
            return []
        return value

    root = obj(package, "study", {"schema", "id", "source_reference", "current_time_model", "relays", "cases"})
    if root.get("schema") != SCHEMA:
        issue("schema", SCHEMA + " required")
    reference(root.get("id"), "id")
    reference(root.get("source_reference"), "source_reference")
    if root.get("current_time_model") != "CONSTANT_RMS_OVER_OPERATING_TIME":
        issue("current_time_model", "explicit constant-current assumption required")
    relays = rows(root.get("relays"), "relays", 64)
    ids = set()
    folded = set()
    for i, raw in enumerate(relays):
        path = f"relays[{i}]"
        item = obj(raw, path, {"id", "protected_element_reference", "type", "settings", "breaker", "source_reference"})
        key = item.get("id")
        if not isinstance(key, str) or not key.strip() or key.casefold() in folded:
            issue(path + ".id", "case-insensitive unique nonempty identifier required")
        else:
            ids.add(key)
            folded.add(key.casefold())
        reference(item.get("protected_element_reference"), path + ".protected_element_reference")
        reference(item.get("source_reference"), path + ".source_reference")
        kind = item.get("type")
        if not isinstance(kind, str) or kind not in SETTING_FIELDS:
            issue(path + ".type", "DTOC/IDMT/IDTOC required")
            fields = set()
        else:
            fields = SETTING_FIELDS[kind]
        settings = obj(item.get("settings"), path + ".settings", fields)
        for field in fields:
            value = settings.get(field)
            if field == "curve_type":
                if value not in CURVES:
                    issue(path + ".settings.curve_type", "explicit native inverse curve required")
            elif field.endswith("_primary_a"):
                number(value, path + ".settings." + field, 0, 1e9, strict=True)
            elif field == "time_multiplier":
                number(value, path + ".settings." + field, 0, 100, strict=True)
            else:
                number(value, path + ".settings." + field, 0, 86400)
        thresholds = ("inverse_pickup_primary_a", "pickup_primary_a", "high_set_primary_a") if kind == "IDTOC" else (
            ("pickup_primary_a", "high_set_primary_a") if kind == "DTOC" else ())
        if thresholds and all(type(settings.get(k)) in (int,float) for k in thresholds):
            values = [settings[k] for k in thresholds]
            if not all(a < b for a,b in zip(values, values[1:])):
                issue(path + ".settings", "strictly increasing stage pickup currents required")
        breaker = obj(item.get("breaker"), path + ".breaker", {"clearing_delay_s", "source_reference"})
        if breaker.get("clearing_delay_s") is not None:
            number(breaker["clearing_delay_s"], path + ".breaker.clearing_delay_s", 0, 3600)
        reference(breaker.get("source_reference"), path + ".breaker.source_reference")
    cases = rows(root.get("cases"), "cases", 128)
    case_ids = set()
    for i, raw in enumerate(cases):
        path = f"cases[{i}]"
        item = obj(raw, path, {"id", "scenario", "currents", "expectations", "source_reference"})
        key = item.get("id")
        if not isinstance(key, str) or not key.strip() or key.casefold() in case_ids:
            issue(path + ".id", "unique case identifier required")
        else:
            case_ids.add(key.casefold())
        if item.get("scenario") not in ("sc", "pp"):
            issue(path + ".scenario", "sc or pp measurement-table semantics required")
        reference(item.get("source_reference"), path + ".source_reference")
        currents = obj(item.get("currents"), path + ".currents", ids)
        expectations = obj(item.get("expectations"), path + ".expectations", ids)
        for relay_id in ids:
            current = obj(currents.get(relay_id), path + ".currents." + relay_id, {"primary_rms_a", "source_reference"})
            number(current.get("primary_rms_a"), path + ".currents." + relay_id, 0, 1e9)
            reference(current.get("source_reference"), path + ".currents." + relay_id + ".source_reference")
            criterion = obj(expectations.get(relay_id), path + ".expectations." + relay_id,
                            {"trip", "maximum_relay_time_s", "maximum_total_clearing_time_s", "source_reference"})
            if type(criterion.get("trip")) is not bool:
                issue(path + ".expectations." + relay_id, "explicit expected trip boolean required")
            for field in ("maximum_relay_time_s", "maximum_total_clearing_time_s"):
                if criterion.get(field) is not None:
                    number(criterion[field], path + ".expectations." + relay_id + "." + field, 0, 1e9)
                    if criterion.get("trip") is False:
                        issue(path + ".expectations." + relay_id, "time deadlines do not apply to an expected non-trip")
            reference(criterion.get("source_reference"), path + ".expectations." + relay_id + ".source_reference")
    return {"schema": SCHEMA, "ready_for_execution": not issues, "issues": issues,
            "electrical_calculation_performed": False, "automatic_settings": False, "professional_emission": False}


def _native_relay(item, index):
    """Hydrate documented native settings without constructor SC/autograding.

    pandapower 3.5.4 DTOC constructor copies I_g into I_gg, and IDTOC time
    construction is list/autograding-oriented. Native from_dict is the safe
    settings-only path; the vendor operation function remains unchanged.
    """
    s = item["settings"]
    state = {"index": index, "switch_index": index, "oc_relay_type": item["type"],
             "activation_parameter": "i_ka", "tripped": False, "in_service": True,
             "I_g": None, "I_gg": None, "I_s": None, "t_g": None, "t_gg": None,
             "tms": None, "t_grade": None, "time_settings": None, "time_grading": None,
             "pickup_current_manual": None, "overload_factor": None, "ct_current_factor": None,
             "safety_factor": None, "inverse_overload_factor": None, "sc_fraction": None,
             "curve_type": s.get("curve_type"), "kwargs": {}}
    if item["type"] in ("DTOC", "IDTOC"):
        state.update(I_g=s["pickup_primary_a"]/1000, I_gg=s["high_set_primary_a"]/1000,
                     t_g=s["delay_s"], t_gg=s["high_set_delay_s"])
    if item["type"] in ("IDMT", "IDTOC"):
        pickup = s["pickup_primary_a"] if item["type"] == "IDMT" else s["inverse_pickup_primary_a"]
        state.update(I_s=pickup/1000, tms=s["time_multiplier"], t_grade=s["additive_delay_s"])
    relay = OCRelay.from_dict(state)
    if item["type"] != "DTOC":
        relay._select_k_alpha()
    return relay


def _point(relay, current_a, scenario):
    relay.reset_device()
    # Explicit measurement tables only: no artificial network or SC calculation.
    index = relay.switch_index
    net = SimpleNamespace(
        res_switch_sc=pd.DataFrame({"ikss_ka": [current_a/1000]}, index=[index]),
        res_switch=pd.DataFrame({"i_ka": [current_a/1000]}, index=[index]),
        switch=pd.DataFrame({"closed": [True]}, index=[index]),
    )
    native = relay.protection_function(net, scenario)
    relay.status_to_net(net)
    tripped = bool(native["trip_melt"])
    value = float(native["trip_melt_time_s"])
    if tripped and (not isfinite(value) or value < 0):
        raise ValueError("NATIVE_RELAY_TIME_INVALID")
    if not tripped and value != float("inf"):
        raise ValueError("NATIVE_NONTRIP_SEMANTICS_CHANGED")
    if bool(net.switch.at[index,"closed"]) == tripped:
        raise ValueError("NATIVE_SWITCH_COMMAND_MISMATCH")
    return {"trip_command": tripped, "relay_operating_time_s": value if tripped else None,
            "native_nontrip_time": None if tripped else "POSITIVE_INFINITY",
            "native_switch_closed_after_command": bool(net.switch.at[index,"closed"])}


def _criteria(row, criterion):
    checks = {"expected_trip": row["trip_command"] == criterion["trip"]}
    unknown = []
    for key, limit_name in (("relay_operating_time_s", "maximum_relay_time_s"),
                            ("total_clearing_time_s", "maximum_total_clearing_time_s")):
        limit = criterion[limit_name]
        if limit is not None:
            if row[key] is None:
                checks[limit_name] = False
                if row["trip_command"]:
                    unknown.append(limit_name)
            else:
                checks[limit_name] = row[key] <= limit
    return {"evaluated": not unknown, "passed": not unknown and all(checks.values()), "checks": checks,
            "not_evaluable": unknown, "source_reference": criterion["source_reference"]}


def _run(package):
    if pp.__version__ != ENGINE_VERSION:
        raise ValueError("UNQUALIFIED_PANDAPOWER_VERSION: " + pp.__version__)
    relays = {item["id"]: _native_relay(item, i) for i,item in enumerate(package["relays"])}
    results = []
    for case in package["cases"]:
        rows = []
        for item in package["relays"]:
            relay_id = item["id"]
            current = case["currents"][relay_id]
            row = {"relay_id": relay_id, "protected_element_reference": item["protected_element_reference"],
                   "primary_rms_a": current["primary_rms_a"], "current_source_reference": current["source_reference"]}
            try:
                row.update(_point(relays[relay_id], current["primary_rms_a"], case["scenario"]), results_valid=True)
                delay = item["breaker"]["clearing_delay_s"]
                row["breaker_clearing_delay_s"] = delay
                row["breaker_source_reference"] = item["breaker"]["source_reference"]
                row["total_clearing_time_s"] = row["relay_operating_time_s"] + delay if row["trip_command"] and delay is not None else None
                row["clearing_time_status"] = ("NO_TRIP" if not row["trip_command"] else
                                               "READY_WITH_EXPLICIT_BREAKER_DELAY" if delay is not None else
                                               "NOT_EVALUABLE_BREAKER_DELAY_MISSING")
                row["criteria"] = _criteria(row, case["expectations"][relay_id])
            except Exception as exc:
                row.update(results_valid=False, error=f"{type(exc).__name__}: {exc}",
                           criteria={"evaluated": False, "passed": False})
            rows.append(row)
        results.append({"id": case["id"], "scenario": case["scenario"], "source_reference": case["source_reference"], "relays": rows})
    flat = [r for c in results for r in c["relays"]]
    return {"results": results, "results_valid": all(r["results_valid"] for r in flat),
            "criteria": {"evaluated": all(r["criteria"]["evaluated"] for r in flat),
                         "passed": all(r["criteria"]["passed"] for r in flat)},
            "evaluated_points": len(flat)}


def _report(package, result):
    rows = []
    def value(raw):
        return "No evaluable / no dispara" if raw is None else f"{raw:.7g}"
    for case in result.get("results", []):
        for r in case["relays"]:
            cells = [escape(case["id"]), escape(r["relay_id"]), value(r["primary_rms_a"])]
            if r["results_valid"]:
                cells += ["DISPARA" if r["trip_command"] else "NO DISPARA", value(r["relay_operating_time_s"]),
                          value(r["breaker_clearing_delay_s"]), value(r["total_clearing_time_s"]),
                          "CUMPLE" if r["criteria"]["passed"] else "EXCEDE / NO EVALUABLE"]
            else:
                cells += ["INVÁLIDO", escape(r["error"]), "", "", "NO EVALUABLE"]
            rows.append("<tr>"+"".join("<td>"+c+"</td>" for c in cells)+"</tr>")
    return ('<!doctype html><html lang="es"><meta charset="utf-8"><title>Actuación de relés</title>'
            '<style>body{font:15px system-ui;margin:30px;max-width:1300px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:6px}@media print{body{margin:0}}</style>'
            '<h1>'+escape(package["id"])+" — Actuación OCRelay</h1><p>Corriente RMS primaria constante. Ajustes explícitos; "
            "modelo genérico nativo de pandapower. El tiempo del relé se separa del retardo total del interruptor hasta extinguir el arco. "
            "No se recalcula una red, no se integra una corriente variable y no se acredita selectividad ni fabricante.</p>"+
            '<table><tr><th>Caso</th><th>Relé</th><th>A primarios</th><th>Orden</th><th>Relé (s)</th><th>Interruptor (s)</th><th>Despeje total (s)</th><th>Criterio declarado</th></tr>'+
            "".join(rows)+"</table></html>")


def execute(package, output_directory):
    readiness = validate(package)
    if not readiness["ready_for_execution"]:
        return {"status": "BLOCKED_RELAY_OPERATION_INPUTS", "readiness": readiness, "results_valid": False}
    folder = Path(output_directory).expanduser().resolve()
    try:
        folder.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        return {"status": "BLOCKED_OUTPUT_DIRECTORY", "results_valid": False}
    parent = network._parent_signature()
    result = {"schema": SCHEMA, "engine": "pandapower.OCRelay", "engine_version": pp.__version__,
              "contract": contract(), "professional_emission": False,
              "network_short_circuit_calculated": False, "network_recalculated_after_trip": False}
    try:
        result.update(_run(deepcopy(package)))
    except Exception as exc:
        result.update(results_valid=False, results=[], error=f"{type(exc).__name__}: {exc}",
                      criteria={"evaluated": False, "passed": False})
    result["parent_model_mutated"] = network._parent_signature() != parent
    if result["parent_model_mutated"]:
        result.update(results_valid=False, criteria={"evaluated": False, "passed": False})
    result["status"] = "RELAY_OPERATION_COMPLETED" if result["results_valid"] else "RELAY_OPERATION_INVALID"
    for name, data in (("Inputs.json", package), ("Results.json", result)):
        (folder/name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf8")
    (folder/"Informe.html").write_text(_report(package, result), encoding="utf8")
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}
    sources = [Path(__file__), Path(inspect.getsourcefile(OCRelay)), Path(network.__file__), module_qualification.PATH]
    (folder/"Integrity.json").write_text(json.dumps({"files_sha256": hashes,
        "adapter_and_native_sources_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}, indent=2), encoding="utf8")
    return {**result, "output_directory": str(folder), "files_sha256": hashes}


def register(mcp):
    @mcp.tool()
    def obtener_contrato_actuacion_reles() -> dict:
        """Alcance OCRelay nativo: DTOC/IDMT/IDTOC y separación de tiempos relé/interruptor."""
        return contract()

    @mcp.tool()
    def validar_actuacion_reles(paquete_estudio: dict) -> dict:
        """Valida ajustes, corrientes RMS primarias constantes, procedencia y criterios sin calcular."""
        return validate(paquete_estudio)

    @mcp.tool()
    def ejecutar_actuacion_reles(paquete_estudio: dict, directorio_salida: str) -> dict:
        """Evalúa OCRelay nativos con datos explícitos; conserva resultados, informe y hashes."""
        return execute(paquete_estudio, directorio_salida)
