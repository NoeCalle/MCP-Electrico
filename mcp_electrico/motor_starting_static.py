"""P13B — estudio estático de arranque de motor en OpenDSS aislado.

P13B consume exclusivamente entradas admitidas por P13A y resuelve dos estados
balanceados de régimen estacionario: pre-arranque con el motor apagado y
arranque con una impedancia equivalente derivada de corriente/PF explícitos.

La red base se construye directamente dentro de dss.NewContext(). Ni readiness
ni ejecución materializan, resuelven o exportan el circuito DSS padre.

No se modelan aceleración, torque, deslizamiento transitorio, control interno de
star-delta/soft starter/VFD, armónicos ni formas de onda.
"""

from __future__ import annotations

from copy import deepcopy
from math import isfinite, sqrt
import re
from typing import Any

from opendssdirect import dss

from . import motor_starting_intake, professional_data, workspace_state

SCHEMA_READINESS = "MCP_ELECTRICO_P13B_MOTOR_STARTING_READINESS_V1"
SCHEMA_EXECUTION = "MCP_ELECTRICO_P13B_MOTOR_STARTING_STATIC_V1"

STATUS_BLOCKED_INTAKE = "BLOCKED_BY_P13A_INTAKE"
STATUS_BLOCKED_DEFAULTS = "BLOCKED_BY_BASE_ENGINE_DEFAULTS"
STATUS_BLOCKED_BUILD = "BLOCKED_BY_ISOLATED_BASE_BUILD"
STATUS_READY = "READY_FOR_STATIC_MOTOR_STARTING"
STATUS_COMPLETED = "STATIC_MOTOR_STARTING_COMPLETED"
STATUS_PARTIAL = "STATIC_MOTOR_STARTING_PARTIAL"

ENGINE = "OpenDSS"
ISOLATION_MODE = "OPENDSS_NEW_CONTEXT"
MODEL = "EQUIVALENT_STARTING_IMPEDANCE"
LOAD_MODEL = 2
MODEL_VMIN_PU = 0.01
MODEL_VMAX_PU = 2.0

_SAFE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_TAP_FIELDS = ("tap_side", "tap_neutral", "tap_min", "tap_max", "tap_step_percent", "tap_pos")


def _issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _element_name(identifier: Any, expected_class: str) -> str:
    raw = str(identifier or "").strip()
    if "." in raw:
        kind, name = raw.split(".", 1)
        if kind.lower() != expected_class.lower():
            raise ValueError(f"{raw!r} debe pertenecer a {expected_class}.*")
    else:
        name = raw
    if not name or not _SAFE_NAME.fullmatch(name):
        raise ValueError(
            f"nombre OpenDSS no soportado: {raw!r}; use letras, números, '_' o '-' sin espacios"
        )
    return name


def _circuit_name(project_id: Any) -> str:
    raw = str(project_id or "motor_starting").strip()
    safe = re.sub(r"[^A-Za-z0-9_]+", "_", raw).strip("_") or "motor_starting"
    if safe[0].isdigit():
        safe = f"p_{safe}"
    return f"p13b_{safe[:48]}"


def _parent_signature() -> dict[str, Any]:
    try:
        circuit = str(dss.Circuit.Name() or "")
    except Exception:
        circuit = ""
    try:
        elements = sorted(str(item) for item in dss.Circuit.AllElementNames()) if circuit else []
    except Exception:
        elements = []
    return {
        "circuit": circuit,
        "elements": elements,
        "workspace": deepcopy(workspace_state.status()),
    }


def _motor_map(intake: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id") or "").lower(): item
        for item in intake.get("motors") or []
        if str(item.get("id") or "").strip()
    }


def _base_load_map(base_model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in (base_model.get("topology") or {}).get("loads") or []:
        if not isinstance(item, dict):
            continue
        identifier = str(item.get("id") or "").strip()
        if identifier and "." not in identifier:
            identifier = f"Load.{identifier}"
        if identifier:
            result[identifier.lower()] = item
    return result


def _assign_bus_base(
    bases: dict[str, float],
    bus: Any,
    kv_ll: Any,
    *,
    path: str,
    issues: list[dict[str, str]],
) -> bool:
    name = str(bus or "").split(".")[0].strip()
    value = _number(kv_ll)
    if not name or value is None or value <= 0:
        return False
    key = name.lower()
    previous = bases.get(key)
    if previous is not None and abs(previous - value) > max(1e-9, 1e-6 * max(previous, value)):
        issues.append(_issue(
            "P13B020",
            path,
            f"La barra {name} recibe tensiones nominales incompatibles: {previous} kV y {value} kV.",
        ))
        return False
    bases[key] = value
    return previous is None


def _derive_bus_bases(
    base_model: dict[str, Any],
    motors: list[dict[str, Any]],
) -> tuple[dict[str, float], list[dict[str, str]]]:
    issues: list[dict[str, str]] = []
    bases: dict[str, float] = {}
    source = base_model.get("source") or {}
    topology = base_model.get("topology") or {}

    _assign_bus_base(
        bases, source.get("bus"), source.get("kv_ll"),
        path="base_model.source.kv_ll", issues=issues,
    )
    for i, item in enumerate(topology.get("transformers") or []):
        if not isinstance(item, dict):
            continue
        _assign_bus_base(
            bases, item.get("bus_hv"), item.get("kv_hv"),
            path=f"base_model.topology.transformers[{i}].kv_hv", issues=issues,
        )
        _assign_bus_base(
            bases, item.get("bus_lv"), item.get("kv_lv"),
            path=f"base_model.topology.transformers[{i}].kv_lv", issues=issues,
        )
    for i, item in enumerate(topology.get("loads") or []):
        if isinstance(item, dict):
            _assign_bus_base(
                bases, item.get("bus"), item.get("kv"),
                path=f"base_model.topology.loads[{i}].kv", issues=issues,
            )
    for i, motor in enumerate(motors):
        _assign_bus_base(
            bases, motor.get("bus"), motor.get("kv_ll"),
            path=f"motors[{i}].kv_ll", issues=issues,
        )

    lines = [item for item in topology.get("lines") or [] if isinstance(item, dict)]
    changed = True
    while changed:
        changed = False
        for item in lines:
            a = str(item.get("bus1") or "").split(".")[0].strip().lower()
            b = str(item.get("bus2") or "").split(".")[0].strip().lower()
            if a in bases and b and b not in bases:
                bases[b] = bases[a]
                changed = True
            elif b in bases and a and a not in bases:
                bases[a] = bases[b]
                changed = True
            elif a in bases and b in bases and abs(bases[a] - bases[b]) > max(
                1e-9, 1e-6 * max(bases[a], bases[b])
            ):
                issues.append(_issue(
                    "P13B021",
                    "base_model.topology.lines",
                    f"Una línea pasiva conecta barras con bases nominales distintas: {a}={bases[a]} kV, {b}={bases[b]} kV.",
                ))

    for bus in topology.get("buses") or []:
        key = str(bus).strip().lower()
        if key and key not in bases:
            issues.append(_issue(
                "P13B022",
                "base_model.topology.buses",
                f"No se pudo determinar una base kVLL explícita para la barra {bus}.",
            ))
    return bases, issues


def _preflight_base(
    base_model: dict[str, Any],
    motors: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], dict[str, float]]:
    issues: list[dict[str, str]] = []
    source = base_model.get("source") or {}
    topology = base_model.get("topology") or {}

    required_source = ("frequency_hz", "pu", "angle_deg", "scc_max_mva", "x_r_max")
    for key in required_source:
        if not _present(source.get(key)):
            issues.append(_issue(
                "P13B001",
                f"base_model.source.{key}",
                f"P13B requiere {key} explícito; no retiene el default de OpenDSS.",
            ))
    for key in ("frequency_hz", "pu", "scc_max_mva", "x_r_max"):
        value = _number(source.get(key))
        if _present(source.get(key)) and (value is None or value <= 0):
            issues.append(_issue(
                "P13B002", f"base_model.source.{key}", f"{key} debe ser finito y mayor que cero."
            ))
    if _present(source.get("angle_deg")) and _number(source.get("angle_deg")) is None:
        issues.append(_issue("P13B003", "base_model.source.angle_deg", "angle_deg debe ser finito."))

    for i, item in enumerate(topology.get("transformers") or []):
        if not isinstance(item, dict):
            continue
        try:
            _element_name(item.get("id"), "Transformer")
        except ValueError as exc:
            issues.append(_issue("P13B004", f"base_model.topology.transformers[{i}].id", str(exc)))
        for key in ("no_load_loss_kw", "i0_percent"):
            if not _present(item.get(key)):
                issues.append(_issue(
                    "P13B005",
                    f"base_model.topology.transformers[{i}].{key}",
                    f"P13B requiere {key} explícito para no retener defaults del motor.",
                ))
        declared = [key for key in _TAP_FIELDS if _present(item.get(key))]
        if len(declared) != len(_TAP_FIELDS):
            issues.append(_issue(
                "P13B006",
                f"base_model.topology.transformers[{i}]",
                "P13B exige tap_side, tap_neutral, tap_min, tap_max, tap_step_percent y tap_pos explícitos.",
            ))

    for i, item in enumerate(topology.get("lines") or []):
        if not isinstance(item, dict):
            continue
        try:
            _element_name(item.get("id"), "Line")
        except ValueError as exc:
            issues.append(_issue("P13B007", f"base_model.topology.lines[{i}].id", str(exc)))
        if not _present(item.get("c1_nf_km")):
            issues.append(_issue(
                "P13B008",
                f"base_model.topology.lines[{i}].c1_nf_km",
                "P13B requiere C1 explícita; no conserva el valor interno de OpenDSS.",
            ))
        elif _number(item.get("c1_nf_km")) is None or float(item["c1_nf_km"]) < 0:
            issues.append(_issue(
                "P13B009",
                f"base_model.topology.lines[{i}].c1_nf_km",
                "c1_nf_km debe ser finita y no negativa.",
            ))

    for i, item in enumerate(topology.get("loads") or []):
        if not isinstance(item, dict):
            continue
        try:
            _element_name(item.get("id"), "Load")
        except ValueError as exc:
            issues.append(_issue("P13B010", f"base_model.topology.loads[{i}].id", str(exc)))
        connection = str(item.get("connection") or "").strip().lower()
        if connection not in {"wye", "delta"}:
            issues.append(_issue(
                "P13B011",
                f"base_model.topology.loads[{i}].connection",
                "P13B requiere connection=wye/delta explícita.",
            ))
        model = _number(item.get("model"))
        if model is None or int(model) != model or int(model) not in range(1, 9):
            issues.append(_issue(
                "P13B012",
                f"base_model.topology.loads[{i}].model",
                "P13B requiere OpenDSS Load.Model explícito entre 1 y 8.",
            ))

    bases, base_issues = _derive_bus_bases(base_model, motors)
    issues.extend(base_issues)
    return issues, bases


def _source_rx(source: dict[str, Any]) -> tuple[float, float]:
    kv_ll = float(source["kv_ll"])
    scc_mva = float(source["scc_max_mva"])
    x_r = float(source["x_r_max"])
    z1 = kv_ll * kv_ll / scc_mva
    r1 = z1 / sqrt(1.0 + x_r * x_r)
    return r1, r1 * x_r


def _build_isolated_base(
    base_model: dict[str, Any],
    motors: list[dict[str, Any]],
    bus_bases: dict[str, float],
) -> tuple[Any, dict[str, Any]]:
    source = base_model["source"]
    topology = base_model["topology"]
    engine = dss.NewContext()
    engine.Basic.AllowChangeDir(False)
    engine("Clear")

    circuit_name = _circuit_name((base_model.get("project") or {}).get("id"))
    engine(
        f"New Circuit.{circuit_name} basekv={float(source['kv_ll'])} "
        f"Frequency={float(source['frequency_hz'])}"
    )
    r1, x1 = _source_rx(source)
    engine(
        f"Edit Vsource.source Bus1={source['bus']} BasekV={float(source['kv_ll'])} "
        f"pu={float(source['pu'])} angle={float(source['angle_deg'])} R1={r1} X1={x1}"
    )

    for item in topology.get("transformers") or []:
        name = _element_name(item["id"], "Transformer")
        vg = professional_data._parse_vector_group(str(item["vector_group"]))
        series = professional_data._series_impedance(
            float(item["kva"]),
            float(item["uk_percent"]),
            float(item["x_r"]) if _present(item.get("x_r")) else None,
            float(item["load_loss_kw"]) if _present(item.get("load_loss_kw")) else None,
        )
        tap = professional_data._tap_data(
            str(item["tap_side"]),
            int(item["tap_neutral"]),
            int(item["tap_min"]),
            int(item["tap_max"]),
            float(item["tap_step_percent"]),
            int(item["tap_pos"]),
        )
        r_half = series["r_percent_total"] / 2.0
        hv_tap = tap["tap_pu"] if tap["side"] == "hv" else 1.0
        lv_tap = tap["tap_pu"] if tap["side"] == "lv" else 1.0
        parts = [
            f"New Transformer.{name}",
            "Phases=3",
            "Windings=2",
            f"Buses=[{item['bus_hv']},{item['bus_lv']}]",
            f"Conns=[{vg['hv_connection']},{vg['lv_connection']}]",
            f"kVs=[{float(item['kv_hv'])},{float(item['kv_lv'])}]",
            f"kVAs=[{float(item['kva'])},{float(item['kva'])}]",
            f"%Rs=[{r_half},{r_half}]",
            f"XHL={series['x_percent']}",
            f"Taps=[{hv_tap},{lv_tap}]",
            f"%Noloadloss={float(item['no_load_loss_kw']) / float(item['kva']) * 100.0}",
            f"%imag={float(item['i0_percent'])}",
        ]
        if vg["lead_lag_opendss"]:
            parts.append(f"LeadLag={vg['lead_lag_opendss']}")
        engine(" ".join(parts))
        wdg = 1 if tap["side"] == "hv" else 2
        min_pu = 1.0 + (tap["min"] - tap["neutral"]) * tap["step_percent"] / 100.0
        max_pu = 1.0 + (tap["max"] - tap["neutral"]) * tap["step_percent"] / 100.0
        engine(
            f"Edit Transformer.{name} Wdg={wdg} MinTap={min_pu} MaxTap={max_pu} "
            f"NumTaps={int(tap['max'] - tap['min'])} Tap={tap['tap_pu']}"
        )

    for item in topology.get("lines") or []:
        name = _element_name(item["id"], "Line")
        engine(
            f"New Line.{name} Bus1={item['bus1']} Bus2={item['bus2']} "
            f"Length={float(item['length_km'])} Units=km Phases={int(float(item['phases']))} "
            f"R1={float(item['r1_ohm_km'])} X1={float(item['x1_ohm_km'])} "
            f"C1={float(item['c1_nf_km'])}"
        )

    for item in topology.get("loads") or []:
        name = _element_name(item["id"], "Load")
        engine(
            f"New Load.{name} Bus1={item['bus']} Phases={int(float(item['phases']))} "
            f"kV={float(item['kv'])} kW={float(item['kw'])} kvar={float(item['kvar'])} "
            f"Conn={str(item['connection']).lower()} Model={int(float(item['model']))}"
        )

    levels = sorted({float(value) for value in bus_bases.values()}, reverse=True)
    engine("Set VoltageBases=[" + ",".join(str(value) for value in levels) + "]")
    engine("CalcVoltageBases")
    for bus, kv_ll in sorted(bus_bases.items()):
        engine(f"SetkVBase Bus={bus} kVLL={kv_ll}")

    evidence = {
        "circuit": str(engine.Circuit.Name() or ""),
        "buses": sorted(str(item) for item in engine.Circuit.AllBusNames()),
        "transformers": sorted(f"Transformer.{item}" for item in engine.Transformers.AllNames()),
        "lines": sorted(f"Line.{item}" for item in engine.Lines.AllNames()),
        "loads": sorted(f"Load.{item}" for item in engine.Loads.AllNames()),
        "engine_defaults_retained": [],
        "engine_defaults_retained_count": 0,
        "solve_performed": False,
        "isolation_mode": ISOLATION_MODE,
    }
    return engine, evidence


def _bus_voltage_pu(engine: Any, bus: str) -> list[float]:
    if not engine.Circuit.SetActiveBus(str(bus)):
        return []
    raw = engine.Bus.puVmagAngle()
    return [float(value) for value in raw[0::2]]


def _safe_element_suffix(raw: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", str(raw or "").strip()).strip("_")
    return text or "motor_start"


def _equivalent_starting_demand(motor: dict[str, Any]) -> dict[str, float]:
    kv_ll = float(motor["kv_ll"])
    current_a = float(motor["starting_current_a"])
    pf = float(motor["starting_power_factor"])
    apparent_kva = sqrt(3.0) * kv_ll * current_a
    active_kw = apparent_kva * pf
    reactive_kvar = apparent_kva * sqrt(max(1.0 - pf * pf, 0.0))
    return {
        "apparent_kva_at_rated_voltage": apparent_kva,
        "active_kw_at_rated_voltage": active_kw,
        "reactive_kvar_at_rated_voltage": reactive_kvar,
    }


def evaluar_readiness(manifest: dict[str, Any]) -> dict[str, Any]:
    """Valida y construye un modelo aislado sin Solve ni mutación del padre."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest debe ser dict.")

    parent_before = _parent_signature()
    intake = motor_starting_intake.evaluar_admision_motor(deepcopy(manifest))
    base = {
        "schema": SCHEMA_READINESS,
        "industry_scope": "CROSS_INDUSTRY",
        "engine": ENGINE,
        "isolation_mode": ISOLATION_MODE,
        "method": MODEL,
        "electrical_calculation_performed": False,
        "motor_starting_calculation_performed": False,
        "dynamic_acceleration_calculation_performed": False,
        "torque_calculation_performed": False,
        "automatic_starting_current_derivation": False,
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
    }
    if intake.get("ready_for_static_starting_build") is not True:
        parent_after = _parent_signature()
        return {
            **base,
            "readiness_status": STATUS_BLOCKED_INTAKE,
            "ready_for_execution": False,
            "issues": deepcopy(intake.get("issues") or []),
            "p13a": intake,
            "parent_context_mutated": parent_after != parent_before,
        }

    base_model = deepcopy(manifest["base_model"])
    motors = deepcopy(intake.get("motors") or [])
    preflight, bus_bases = _preflight_base(base_model, motors)
    if preflight:
        parent_after = _parent_signature()
        return {
            **base,
            "readiness_status": STATUS_BLOCKED_DEFAULTS,
            "ready_for_execution": False,
            "issues": preflight,
            "p13a": intake,
            "base_model": {
                "materializer_status": "ISOLATED_MODEL_NOT_BUILT",
                "engine_defaults_retained": deepcopy(preflight),
                "engine_defaults_retained_count": len(preflight),
            },
            "parent_context_mutated": parent_after != parent_before,
        }

    try:
        _engine, evidence = _build_isolated_base(base_model, motors, bus_bases)
    except Exception as exc:
        parent_after = _parent_signature()
        return {
            **base,
            "readiness_status": STATUS_BLOCKED_BUILD,
            "ready_for_execution": False,
            "issues": [_issue("P13B090", "base_model", f"{type(exc).__name__}: {exc}")],
            "p13a": intake,
            "parent_context_mutated": parent_after != parent_before,
        }

    issues: list[dict[str, str]] = []
    loads = _base_load_map(base_model)
    for index, motor in enumerate(motors):
        running = str(motor.get("running_load_element_id") or "").lower()
        if motor.get("base_model_includes_running_motor") is True and running:
            load = loads.get(running)
            if load is None:
                issues.append(_issue(
                    "P13B030",
                    f"motors[{index}].running_load_element_id",
                    "La carga de marcha no existe en el modelo base.",
                ))
                continue
            if int(float(load.get("phases") or 0)) != int(motor["phases"]):
                issues.append(_issue(
                    "P13B031",
                    f"motors[{index}].running_load_element_id",
                    "La carga de marcha y el motor deben tener el mismo número de fases.",
                ))
            if abs(float(load.get("kv") or 0.0) - float(motor["kv_ll"])) > 1e-9:
                issues.append(_issue(
                    "P13B032",
                    f"motors[{index}].running_load_element_id",
                    "La tensión de la carga de marcha no coincide con kv_ll del motor.",
                ))

    parent_after = _parent_signature()
    if parent_after != parent_before:
        issues.append(_issue(
            "P13B091",
            "parent_context",
            "Readiness modificó el contexto DSS/Workspace padre; el gate se bloquea.",
        ))

    ready = not issues
    return {
        **base,
        "readiness_status": STATUS_READY if ready else STATUS_BLOCKED_BUILD,
        "ready_for_execution": ready,
        "issues": issues,
        "p13a": intake,
        "base_model": {
            "materializer_status": "ISOLATED_MODEL_BUILT_NOT_EXECUTED",
            **evidence,
        },
        "study_count": len(intake.get("studies") or []),
        "parent_context_mutated": parent_after != parent_before,
        "parent_circuit": parent_after["circuit"],
        "note": (
            "P13B readiness construye el modelo solo en dss.NewContext() y no ejecuta Solve. "
            "El circuito y Workspace globales permanecen fuera de la ruta de materialización."
        ),
    }


def _execute_one(
    *,
    base_model: dict[str, Any],
    bus_bases: dict[str, float],
    motors: list[dict[str, Any]],
    motor: dict[str, Any],
    study: dict[str, Any],
) -> dict[str, Any]:
    engine, _evidence = _build_isolated_base(base_model, motors, bus_bases)

    running = str(motor.get("running_load_element_id") or "").strip()
    if motor.get("base_model_includes_running_motor") is True and running:
        if not engine.Circuit.SetActiveElement(running):
            return {
                "study_id": study["id"],
                "motor_id": motor["id"],
                "status": "RUNNING_LOAD_NOT_FOUND_IN_ISOLATED_MODEL",
                "ok": False,
                "professional_emission": False,
            }
        engine(f"Edit {running} Enabled=No")

    engine("Solve")
    pre_converged = bool(engine.Solution.Converged())
    pre_voltages = _bus_voltage_pu(engine, motor["bus"])
    if not pre_converged or not pre_voltages:
        return {
            "study_id": study["id"],
            "motor_id": motor["id"],
            "status": "PRE_START_SOLUTION_NOT_READY",
            "ok": False,
            "pre_start_converged": pre_converged,
            "pre_start_voltage_pu_by_phase": pre_voltages,
            "professional_emission": False,
        }

    demand = _equivalent_starting_demand(motor)
    load_name = "p13_" + _safe_element_suffix(study["id"])
    engine(
        " ".join([
            f"New Load.{load_name}",
            f"Bus1={motor['bus']}",
            "Phases=3",
            f"kV={float(motor['kv_ll'])}",
            f"kW={demand['active_kw_at_rated_voltage']}",
            f"kvar={demand['reactive_kvar_at_rated_voltage']}",
            f"Conn={motor['connection']}",
            f"Model={LOAD_MODEL}",
            "Status=Fixed",
            f"Vminpu={MODEL_VMIN_PU}",
            f"Vmaxpu={MODEL_VMAX_PU}",
        ])
    )
    engine("Solve")
    start_converged = bool(engine.Solution.Converged())
    start_voltages = _bus_voltage_pu(engine, motor["bus"])
    if not start_converged or not start_voltages:
        return {
            "study_id": study["id"],
            "motor_id": motor["id"],
            "status": "STARTING_SOLUTION_NOT_READY",
            "ok": False,
            "pre_start_converged": pre_converged,
            "starting_converged": start_converged,
            "pre_start_voltage_pu_by_phase": pre_voltages,
            "starting_voltage_pu_by_phase": start_voltages,
            "starting_demand": demand,
            "professional_emission": False,
        }

    pre_min = min(pre_voltages)
    start_min = min(start_voltages)
    dip_pu = pre_min - start_min
    dip_pct = (dip_pu / pre_min * 100.0) if pre_min > 0 else None
    criterion = float(study["minimum_terminal_voltage_pu"])
    passed = start_min >= criterion

    return {
        "study_id": study["id"],
        "motor_id": motor["id"],
        "status": "PASS" if passed else "FAIL",
        "ok": True,
        "engine": ENGINE,
        "isolation_mode": ISOLATION_MODE,
        "method": MODEL,
        "starting_method_metadata": motor["starting_method"],
        "starting_data_reference": motor["starting_data_reference"],
        "starting_current_a_declared": float(motor["starting_current_a"]),
        "starting_current_basis": motor["starting_current_basis"],
        "starting_power_factor_declared": float(motor["starting_power_factor"]),
        "starting_power_factor_basis": motor["starting_power_factor_basis"],
        "pre_start_motor_state": "OFF",
        "running_load_disabled": running or None,
        "pre_start_converged": pre_converged,
        "starting_converged": start_converged,
        "pre_start_voltage_pu_by_phase": pre_voltages,
        "starting_voltage_pu_by_phase": start_voltages,
        "pre_start_min_voltage_pu": pre_min,
        "starting_min_voltage_pu": start_min,
        "voltage_dip_pu": dip_pu,
        "voltage_dip_pct": dip_pct,
        "starting_demand": demand,
        "equivalent_load_model": {
            "opendss_load_model": LOAD_MODEL,
            "semantics": (
                "CONSTANT_IMPEDANCE_EQUIVALENT_FROM_EXPLICIT_SUPPLY_LINE_RMS_CURRENT_"
                "AND_FUNDAMENTAL_DISPLACEMENT_PF"
            ),
            "vminpu": MODEL_VMIN_PU,
            "vmaxpu": MODEL_VMAX_PU,
            "status": "Fixed",
        },
        "criterion": {
            "minimum_terminal_voltage_pu": criterion,
            "reference": study["criterion_reference"],
            "passed": passed,
            "universal_normative_claim": False,
        },
        "dynamic_acceleration_calculation_performed": False,
        "torque_calculation_performed": False,
        "automatic_starting_current_derivation": False,
        "professional_emission": False,
    }


def ejecutar_estudios(manifest: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta estudios P13B independientes sin tocar el contexto DSS padre."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest debe ser dict.")

    parent_before = _parent_signature()
    readiness = evaluar_readiness(deepcopy(manifest))
    if readiness.get("ready_for_execution") is not True:
        parent_after = _parent_signature()
        return {
            "schema": SCHEMA_EXECUTION,
            "execution_status": "BLOCKED_BY_P13B_READINESS",
            "readiness": readiness,
            "results": [],
            "parent_context_mutated_by_starting_execution": parent_after != parent_before,
            "electrical_calculation_performed": False,
            "motor_starting_calculation_performed": False,
            "dynamic_acceleration_calculation_performed": False,
            "torque_calculation_performed": False,
            "automatic_starting_current_derivation": False,
            "automatic_defaults": False,
            "automatic_dispatch": False,
            "crosscheck": False,
            "professional_emission": False,
        }

    intake = readiness["p13a"]
    motors = deepcopy(intake.get("motors") or [])
    motor_map = _motor_map(intake)
    base_model = deepcopy(manifest["base_model"])
    preflight, bus_bases = _preflight_base(base_model, motors)
    if preflight:
        raise RuntimeError("P13BEXEC000: readiness y ejecución discrepan en preflight.")

    results: list[dict[str, Any]] = []
    for study in intake.get("studies") or []:
        motor = motor_map[str(study["motor_id"]).lower()]
        results.append(_execute_one(
            base_model=base_model,
            bus_bases=bus_bases,
            motors=motors,
            motor=motor,
            study=study,
        ))

    parent_after = _parent_signature()
    parent_preserved = parent_after == parent_before
    if not parent_preserved:
        raise RuntimeError(
            "P13BEXEC001: la ejecución aislada modificó el contexto DSS/Workspace padre."
        )

    all_ok = bool(results) and all(item.get("ok") is True for item in results)
    return {
        "schema": SCHEMA_EXECUTION,
        "execution_status": STATUS_COMPLETED if all_ok else STATUS_PARTIAL,
        "readiness": readiness,
        "results": results,
        "study_count": len(results),
        "engine": ENGINE,
        "isolation_mode": ISOLATION_MODE,
        "method": MODEL,
        "parent_circuit": parent_after["circuit"],
        "parent_context_mutated_by_starting_execution": False,
        "parent_workspace_mutated_by_starting_execution": False,
        "electrical_calculation_performed": bool(results),
        "motor_starting_calculation_performed": bool(results),
        "dynamic_acceleration_calculation_performed": False,
        "torque_calculation_performed": False,
        "automatic_starting_current_derivation": False,
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
        "note": (
            "P13B es una aproximación estática de impacto de red mediante impedancia equivalente. "
            "No representa armónicos, formas de onda ni trayectoria electromecánica de aceleración."
        ),
    }
