"""Explicit native Daily/Yearly LoadShape studies, without a second solver."""
from copy import deepcopy
import csv
import hashlib
from html import escape
import json
from math import isfinite
from pathlib import Path

from opendssdirect import dss
from . import reactive_compensation as rc, module_qualification

SCHEMA = "MCP_ELECTRICO_TIME_SERIES_V1"


def contract():
    return {
        "schema": SCHEMA, "engine": "OpenDSS", "qualification": module_qualification.get("time_series"),
        "scope": "BALANCED_PASSIVE_3PH_NATIVE_DAILY_YEARLY_EXPLICIT_P_Q_MULTIPLIERS",
        "profile_semantics": "ONE_POINT_PER_SOLVED_INTERVAL_END_NO_NORMALIZATION_USEACTUAL_FALSE",
        "daily_cycle_hours": 24, "yearly_wrap": False,
        "energy_integration": "RECTANGULAR_INTERVAL_END_POWER_TIMES_EXPLICIT_STEP_HOURS",
        "timeline": "ELAPSED_HOURS_STARTING_AT_ZERO_NOT_A_CALENDAR_OR_TIMEZONE",
        "not_supported": ["unbalance", "generation_or_storage", "automatic_regulator_or_capacitor_control",
                          "switching_topology", "EMT", "motor_acceleration", "automatic_tariffs",
                          "irregular_or_missing_profile_points", "implicit_annual_extrapolation"],
        "physical_solver_owned_by_mcp": False, "parent_model_mutated": False,
        "automatic_defaults": False, "professional_emission": False,
    }


def validate(package):
    issues = []

    def issue(path, message):
        issues.append({"path": path, "message": message})

    def obj(raw, path, fields):
        if not isinstance(raw, dict):
            issue(path, "explicit object required")
            return {}
        if set(raw) != set(fields):
            issue(path, "exact explicit fields required: " + ", ".join(sorted(fields)))
        return raw

    def number(value, path, low, high):
        try:
            valid = type(value) in (int, float) and isfinite(value) and low <= value <= high
        except OverflowError:
            valid = False
        if not valid:
            issue(path, "finite number outside supported range")
        return valid

    def reference(value, path):
        if not isinstance(value, str) or not value.strip():
            issue(path, "source reference required")

    root = obj(package, "study", {"schema", "id", "source_reference", "base_model", "timeline",
                                  "load_profiles", "criteria", "options"})
    if root.get("schema") != SCHEMA:
        issue("schema", SCHEMA + " required")
    reference(root.get("id"), "id")
    reference(root.get("source_reference"), "source_reference")
    base_issues, bases = rc.validate_base_network(root.get("base_model"))
    issues.extend(base_issues)
    base = root.get("base_model") if isinstance(root.get("base_model"), dict) else {}
    source = base.get("source") if isinstance(base.get("source"), dict) else {}
    if type(source.get("frequency_hz")) not in (int, float) or source.get("frequency_hz") not in (50, 60):
        issue("base_model.source.frequency_hz", "50 or 60 Hz required")
    topo = base.get("topology") if isinstance(base.get("topology"), dict) else {}
    loads = topo.get("loads") if isinstance(topo.get("loads"), list) else []
    load_ids = {r["id"] for r in loads if isinstance(r, dict) and isinstance(r.get("id"), str)}
    timeline = obj(root.get("timeline"), "timeline", {"mode", "start_hour", "step_hours", "steps",
                                                       "repeat_daily_profile", "energy_integration", "source_reference"})
    mode = timeline.get("mode")
    if mode not in ("daily", "yearly"):
        issue("timeline.mode", "native daily/yearly required")
    if type(timeline.get("start_hour")) not in (int, float) or timeline.get("start_hour") != 0:
        issue("timeline.start_hour", "explicit zero required; no calendar offset in V1")
    good_step = number(timeline.get("step_hours"), "timeline.step_hours", 1/60, 24)
    steps = timeline.get("steps")
    good_count = type(steps) is int and 1 <= steps <= 35136
    if not good_count:
        issue("timeline.steps", "integer 1..35136 required")
    repeat = timeline.get("repeat_daily_profile")
    if type(repeat) is not bool:
        issue("timeline.repeat_daily_profile", "explicit boolean required")
    if mode == "yearly" and repeat is not False:
        issue("timeline.repeat_daily_profile", "yearly profiles cannot wrap")
    if timeline.get("energy_integration") != "RECTANGULAR_INTERVAL_END":
        issue("timeline.energy_integration", "explicit interval-end rectangular integration required")
    reference(timeline.get("source_reference"), "timeline.source_reference")
    expected_points = None
    if good_step and good_count:
        step = timeline["step_hours"]
        if mode == "daily":
            daily_count = 24/step
            if abs(daily_count-round(daily_count)) > 1e-8:
                issue("timeline.step_hours", "step must divide 24 hours exactly")
            else:
                expected_points = round(daily_count)
                if steps > expected_points and repeat is not True:
                    issue("timeline.repeat_daily_profile", "explicit repeat required beyond one day")
        elif mode == "yearly":
            expected_points = steps
        if steps*step > 8784+1e-8:
            issue("timeline", "maximum declared horizon is 8784 hours")
        lines = topo.get("lines") if isinstance(topo.get("lines"), list) else []
        transformers = topo.get("transformers") if isinstance(topo.get("transformers"), list) else []
        if steps*(len(bases)+len(loads)+len(lines)+len(transformers)) > 2_000_000:
            issue("timeline.steps", "study output exceeds bounded V1 size")
    profiles = root.get("load_profiles")
    if not isinstance(profiles, list) or not 1 <= len(profiles) <= 200:
        issue("load_profiles", "explicit bounded nonempty list required")
        profiles = []
    seen = set()
    for i, raw in enumerate(profiles):
        path = f"load_profiles[{i}]"
        item = obj(raw, path, {"load_id", "p_multipliers", "q_multipliers", "source_reference"})
        key = item.get("load_id")
        if not isinstance(key, str) or key not in load_ids or key in seen:
            issue(path + ".load_id", "exactly one profile for every declared load required")
        else:
            seen.add(key)
        for field in ("p_multipliers", "q_multipliers"):
            values = item.get(field)
            if not isinstance(values, list) or not 1 <= len(values) <= 35136:
                issue(path + "." + field, "explicit bounded multiplier array required")
                continue
            if expected_points is not None and len(values) != expected_points:
                issue(path + "." + field, f"exactly {expected_points} declared points required")
            for j, value in enumerate(values):
                number(value, path + f".{field}[{j}]", 0, 10)
        reference(item.get("source_reference"), path + ".source_reference")
    if seen != load_ids:
        issue("load_profiles", "every load needs independent explicit P and Q arrays")
    criteria = obj(root.get("criteria"), "criteria", {"voltage_min_pu", "voltage_max_pu",
                    "maximum_line_loading_pct", "maximum_transformer_loading_pct", "source_reference"})
    for key in ("voltage_min_pu", "voltage_max_pu"):
        number(criteria.get(key), "criteria."+key, .01, 2)
    if all(type(criteria.get(k)) in (int, float) for k in ("voltage_min_pu", "voltage_max_pu")):
        if criteria["voltage_min_pu"] >= criteria["voltage_max_pu"]:
            issue("criteria", "increasing voltage bounds required")
    for key in ("maximum_line_loading_pct", "maximum_transformer_loading_pct"):
        number(criteria.get(key), "criteria."+key, .01, 1000)
    reference(criteria.get("source_reference"), "criteria.source_reference")
    options = obj(root.get("options"), "options", {"solver_tolerance", "max_iterations",
                        "active_balance_tolerance_kw", "reactive_balance_tolerance_kvar"})
    number(options.get("solver_tolerance"), "options.solver_tolerance", 1e-12, 1e-4)
    for key in ("active_balance_tolerance_kw", "reactive_balance_tolerance_kvar"):
        number(options.get(key), "options."+key, 1e-9, .01)
    if type(options.get("max_iterations")) is not int or not 1 <= options["max_iterations"] <= 1000:
        issue("options.max_iterations", "integer 1..1000 required")
    return {"schema": SCHEMA, "ready_for_execution": not issues, "issues": issues,
            "bus_bases_kv_ll": bases, "electrical_calculation_performed": False,
            "automatic_defaults": False, "professional_emission": False}


def _build(package):
    native_package = {"base_model": package["base_model"], "banks": [], "options": package["options"]}
    engine, _ = rc._create_engine(native_package, {"load_multiplier": 1})
    timeline = package["timeline"]
    step = timeline["step_hours"]
    for i, profile in enumerate(package["load_profiles"]):
        p = ",".join(str(v) for v in profile["p_multipliers"])
        q = ",".join(str(v) for v in profile["q_multipliers"])
        engine(f"New LoadShape.ts_{i} Npts={len(profile['p_multipliers'])} Interval={step} "
               f"Mult=[{p}] Qmult=[{q}] UseActual=No")
        name = rc.network._element_name(profile["load_id"], "Load")
        engine(f"Edit Load.{name} Status=Variable Daily=ts_{i} Yearly=ts_{i}")
    # Native solution advances once per sample; metrics must never solve again.
    engine(f"Set Mode={timeline['mode']} Number=1 StepSize={step}h Hour=0 Sec=0 Year=0 "
           "ControlMode=Off LoadMult=1 %Growth=0 DemandInterval=No")
    return engine


def _criteria(metrics, criteria):
    if not metrics.get("results_valid"):
        return {"evaluated": False, "passed": False}
    checks = {
        "constant_pq_representation": not metrics["constant_pq_fallback_loads"],
        "bus_voltages": all(b["minimum_pu"] >= criteria["voltage_min_pu"] and
                            b["maximum_pu"] <= criteria["voltage_max_pu"] for b in metrics["buses"]),
        "line_loading": all(v["loading_pct"] <= criteria["maximum_line_loading_pct"] for v in metrics["lines"]),
        "transformer_loading": all(v["loading_pct"] <= criteria["maximum_transformer_loading_pct"] for v in metrics["transformers"]),
    }
    return {"evaluated": True, "passed": all(checks.values()), "checks": checks}


def _run(package):
    engine = _build(package)
    step = package["timeline"]["step_hours"]
    native_package = {"base_model": package["base_model"], "banks": [], "options": package["options"]}
    profiles = {p["load_id"]: p for p in package["load_profiles"]}
    results = []
    for index in range(package["timeline"]["steps"]):
        try:
            engine.Solution.Solve()
            hour = engine.Solution.DblHour()
            if abs(hour - (index+1)*step) > 1e-6:
                raise ValueError("NATIVE_TIME_STEP_MISMATCH")
            metrics = rc._measure(engine, native_package, solve=False)
            loads = []
            for load in package["base_model"]["topology"]["loads"] if metrics.get("results_valid") else []:
                profile = profiles[load["id"]]
                point = index % len(profile["p_multipliers"])
                engine.Circuit.SetActiveElement("Load."+rc.network._element_name(load["id"], "Load"))
                p, q = rc._terminal_power(engine)
                if not all(isfinite(v) for v in (p,q)):
                    raise ValueError("NONFINITE_LOAD_POWER")
                loads.append({"id": load["id"], "profile_index": point, "p_multiplier": profile["p_multipliers"][point],
                              "q_multiplier": profile["q_multipliers"][point], "actual_kw": p, "actual_kvar": q})
            row = {"step": index+1, "interval_start_hour": index*step, "interval_end_hour": hour,
                   **metrics, "loads": loads, "criteria": _criteria(metrics, package["criteria"])}
            results.append(row)
            if not metrics["results_valid"]:
                break  # No fabricated continuation after nonconvergence or balance failure.
        except Exception as exc:
            results.append({"step": index+1, "interval_start_hour": index*step,
                            "interval_end_hour": (index+1)*step, "results_valid": False,
                            "error": f"{type(exc).__name__}: {exc}", "criteria": {"evaluated": False, "passed": False}})
            break
    valid = len(results) == package["timeline"]["steps"] and all(r["results_valid"] for r in results)
    summary = {"evaluated": valid}
    if valid:
        peak = max(results, key=lambda r: r["source"]["p_kw"])
        summary.update(
            duration_hours=len(results)*step,
            source_energy_kwh=sum(r["source"]["p_kw"]*step for r in results),
            source_reactive_energy_kvarh=sum(r["source"]["q_kvar"]*step for r in results),
            load_energy_kwh=sum(r["actual_load_kw"]*step for r in results),
            network_loss_energy_kwh=sum(r["network_losses_kw"]*step for r in results),
            peak_source_kw=peak["source"]["p_kw"], peak_source_interval_end_hour=peak["interval_end_hour"],
            minimum_voltage_pu=min(b["minimum_pu"] for r in results for b in r["buses"]),
            maximum_line_loading_pct=max((v["loading_pct"] for r in results for v in r["lines"]), default=None),
            maximum_transformer_loading_pct=max((v["loading_pct"] for r in results for v in r["transformers"]), default=None),
            criteria_passed=all(r["criteria"]["passed"] for r in results),
            violating_steps=[r["step"] for r in results if not r["criteria"]["passed"]],
        )
        summary["active_energy_balance_residual_kwh"] = (
            summary["source_energy_kwh"]-summary["load_energy_kwh"]-summary["network_loss_energy_kwh"])
    return {"results_valid": valid, "requested_steps": package["timeline"]["steps"],
            "completed_valid_steps": sum(r["results_valid"] for r in results), "results": results, "summary": summary}


def _render(package, result):
    title = escape(package["id"])
    summary = result.get("summary", {})
    content = "<p>Serie incompleta o inválida: no se calcula energía del horizonte completo.</p>"
    if summary.get("evaluated"):
        content = (f"<p>Energía de fuente: <strong>{summary['source_energy_kwh']:.6g} kWh</strong>. "
                   f"Pérdidas: {summary['network_loss_energy_kwh']:.6g} kWh. "
                   f"Demanda máxima: {summary['peak_source_kw']:.6g} kW.</p>")
        points = [(r["interval_end_hour"], r["source"]["p_kw"]) for r in result["results"]]
        xmax = max(t for t,v in points)
        ymax = max(max(v for t,v in points), 1e-9)
        # Display downsampling only; every interval remains in JSON and CSV.
        stride = max(1, (len(points)+999)//1000)
        selected = points[::stride]
        if selected[-1] != points[-1]:
            selected.append(points[-1])
        coords = " ".join(f"{50+700*t/xmax:.3f},{210-180*v/ymax:.3f}" for t,v in selected)
        content += (f'<svg role="img" aria-label="Potencia activa de fuente por hora transcurrida" viewBox="0 0 800 250">'
                    f'<path d="M50 25V210H750" fill="none" stroke="#888"/>'
                    f'<polyline points="{coords}" fill="none" stroke="#147d92" stroke-width="2"/>'
                    f'<text x="50" y="20">{ymax:.5g} kW</text><text x="640" y="240">{xmax:.5g} h</text></svg>'
                    '<p>Gráfico orientativo: puede reducir muestras para visualizar. Los máximos y energías usan todos los pasos.</p>')
    rows = "".join(f"<tr><td>{r['step']}</td><td>{r['interval_end_hour']:.6g}</td>"+
                   (f"<td>{r['source']['p_kw']:.6g}</td><td>{r['network_losses_kw']:.6g}</td><td>"+
                    ("CUMPLE" if r["criteria"]["passed"] else "EXCEDE")+"</td></tr>" if r.get("results_valid")
                    else '<td colspan="3">NO EVALUABLE</td></tr>') for r in result.get("results", [])[:500])
    return ('<!doctype html><html lang="es"><meta charset="utf-8"><title>Perfiles temporales</title>'
            '<style>body{font:15px system-ui;max-width:1000px;margin:30px auto}svg{width:100%}table{border-collapse:collapse;width:100%}td,th{padding:5px;border:1px solid #bbb}@media print{body{margin:0}}</style>'
            '<h1>'+title+' — Daily/Yearly</h1><p>OpenDSS. Horas transcurridas; potencias evaluadas al fin del intervalo. '
            'Energía mediante suma rectangular P·Δt del periodo declarado. No se extrapola automáticamente a un año.</p>'+
            content+'<p>Criterios: '+escape(package["criteria"]["source_reference"])+
            '</p><table><tr><th>Paso</th><th>Hora final</th><th>Fuente kW</th><th>Pérdidas kW</th><th>Criterio</th></tr>'+rows+
            '</table><p>Tabla limitada a los primeros 500 pasos; Results.json y Series.csv conservan todos los intervalos.</p></html>')


def execute(package, output_directory):
    readiness = validate(package)
    if not readiness["ready_for_execution"]:
        return {"status": "BLOCKED_TIME_SERIES_INPUTS", "readiness": readiness, "results_valid": False}
    folder = Path(output_directory).expanduser().resolve()
    try:
        folder.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        return {"status": "BLOCKED_OUTPUT_DIRECTORY", "results_valid": False}
    parent = rc.network._parent_signature()
    result = {"schema": SCHEMA, "engine": "OpenDSS", "engine_version": dss.Basic.Version(),
              "contract": contract(), "professional_emission": False}
    try:
        result.update(_run(deepcopy(package)))
    except Exception as exc:
        result.update(results_valid=False, results=[], summary={"evaluated": False},
                      error=f"{type(exc).__name__}: {exc}")
    result["parent_model_mutated"] = rc.network._parent_signature() != parent
    if result["parent_model_mutated"]:
        result.update(results_valid=False, summary={"evaluated": False})
    result["status"] = "TIME_SERIES_COMPLETED" if result["results_valid"] else "TIME_SERIES_INVALID"
    for name, data in (("Inputs.json", package), ("Results.json", result)):
        (folder/name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf8")
    with (folder/"Series.csv").open("w", encoding="utf8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["step", "interval_end_hour", "source_kw", "source_kvar", "network_losses_kw", "results_valid", "criteria_passed"])
        for row in result["results"]:
            writer.writerow([row["step"], row["interval_end_hour"], row.get("source", {}).get("p_kw"),
                row.get("source", {}).get("q_kvar"), row.get("network_losses_kw"), row["results_valid"], row["criteria"]["passed"]])
    (folder/"Informe.html").write_text(_render(package, result), encoding="utf8")
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}
    sources = [Path(__file__), Path(rc.__file__), Path(rc.network.__file__), Path(rc.professional_data.__file__),
               Path(module_qualification.__file__), module_qualification.PATH]
    (folder/"Integrity.json").write_text(json.dumps({"files_sha256": hashes,
        "adapter_sources_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}, indent=2), encoding="utf8")
    return {**result, "output_directory": str(folder), "files_sha256": hashes}


def register(mcp):
    @mcp.tool()
    def obtener_contrato_series_temporales() -> dict:
        """Alcance Daily/Yearly: perfiles P/Q explícitos, tiempo y energía sin extrapolación."""
        return contract()

    @mcp.tool()
    def validar_series_temporales(paquete_estudio: dict) -> dict:
        """Valida perfiles completos, periodos y criterios sin resolver ni escribir archivos."""
        return validate(paquete_estudio)

    @mcp.tool()
    def ejecutar_series_temporales(paquete_estudio: dict, directorio_salida: str) -> dict:
        """Ejecuta pasos Daily/Yearly nativos aislados y archiva resultados, CSV, informe y hashes."""
        return execute(paquete_estudio, directorio_salida)
