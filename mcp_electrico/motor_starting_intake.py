"""P13A — contrato fail-closed para motores y estudios de arranque.

P12 es una extensión transversal del producto y no depende de una industria
específica. Puede usarse en manufactura, agua/saneamiento, HVAC, hospitales,
data centers, oil & gas, minería u otras instalaciones con motores.

P13A NO ejecuta flujo ni arranque. Valida que el modelo base P8 sea admisible
y que cada motor/estudio tenga datos explícitos suficientes para una futura
aproximación estática de demanda de arranque equivalente.

Principios:
- no se deriva la corriente de arranque desde el método de arranque;
- no se inventa factor de corriente, factor de potencia ni criterio de tensión;
- la presencia de una carga de marcha en el modelo base se declara;
- un estudio referencia exactamente un motor;
- no hay mutación, dispatch automático ni emisión profesional.
"""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any

from . import real_pilot_intake

SCHEMA = "MCP_ELECTRICO_P13A_MOTOR_STARTING_INTAKE_V1"
STATUS_READY = "READY_FOR_STATIC_MOTOR_STARTING_BUILD"
STATUS_BLOCKED = "BLOCKED_MOTOR_STARTING_INPUTS"

STUDY_TYPE = "STATIC_MOTOR_STARTING_VOLTAGE_DIP"
ALLOWED_STARTING_METHODS = {
    "DOL",
    "STAR_DELTA",
    "AUTOTRANSFORMER",
    "SOFT_STARTER",
    "VFD",
    "OTHER_EXPLICIT",
}
ALLOWED_CONNECTIONS = {"wye", "delta"}


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _positive(value: Any) -> bool:
    number = _number(value)
    return number is not None and number > 0


def _issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _motor_id(raw: Any) -> str:
    text = str(raw or "").strip()
    if text and "." not in text:
        text = f"Motor.{text}"
    return text


def _load_id(raw: Any) -> str:
    text = str(raw or "").strip()
    if text and "." not in text:
        text = f"Load.{text}"
    return text


def _base_topology(base_model: dict[str, Any]) -> tuple[set[str], dict[str, dict[str, Any]]]:
    topology = base_model.get("topology") or {}
    buses = {str(item).strip() for item in topology.get("buses") or [] if str(item).strip()}
    loads: dict[str, dict[str, Any]] = {}
    for item in topology.get("loads") or []:
        if not isinstance(item, dict):
            continue
        identifier = _load_id(item.get("id"))
        if identifier:
            loads[identifier.lower()] = item
    return buses, loads


def obtener_contrato_p13a() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "purpose": "MOTOR_STARTING_STATIC_INPUT_ADMISSION",
        "industry_scope": "CROSS_INDUSTRY",
        "supported_study_type": STUDY_TYPE,
        "supported_starting_methods": sorted(ALLOWED_STARTING_METHODS),
        "electrical_calculation_performed": False,
        "model_mutation_performed": False,
        "automatic_starting_current_derivation": False,
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
        "note": (
            "P13A valida datos para una aproximación estática futura de demanda de arranque. "
            "No calcula tiempo de aceleración, torque dinámico ni estabilidad."
        ),
    }


def evaluar_admision_motor(manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise TypeError("manifest debe ser dict.")

    payload = deepcopy(manifest)
    issues: list[dict[str, str]] = []

    project = payload.get("project") or {}
    for key in ("id", "name", "source_reference"):
        if not _present(project.get(key)):
            issues.append(_issue("P13A001", f"project.{key}", f"project.{key} es requerido."))

    base_model = payload.get("base_model")
    if not isinstance(base_model, dict):
        issues.append(_issue("P13A010", "base_model", "Se requiere un manifiesto base P8 estructurado."))
        base_admission = None
        buses: set[str] = set()
        loads: dict[str, dict[str, Any]] = {}
    else:
        base_admission = real_pilot_intake.evaluar_admision(base_model)
        if base_admission.get("ready_to_build_model") is not True:
            issues.append(_issue(
                "P13A011",
                "base_model",
                "El modelo base P8 debe estar READY_TO_BUILD_MODEL antes de admitir un estudio de motor.",
            ))
        buses, loads = _base_topology(base_model)
        source = base_model.get("source") or {}
        for key in ("scc_max_mva", "x_r_max"):
            if not _present(source.get(key)):
                issues.append(_issue(
                    "P13A012",
                    f"base_model.source.{key}",
                    "El estudio de arranque requiere una impedancia positiva-secuencia explícita de la fuente; no se usa el default del Vsource.",
                ))
            elif not _positive(source.get(key)):
                issues.append(_issue(
                    "P13A013",
                    f"base_model.source.{key}",
                    f"{key} debe ser finito y mayor que cero.",
                ))

    motors = payload.get("motors")
    if not isinstance(motors, list) or not motors:
        issues.append(_issue("P13A020", "motors", "Se requiere al menos un motor explícito."))
        motors = []

    normalized_motors: list[dict[str, Any]] = []
    seen_motors: set[str] = set()
    for index, raw in enumerate(motors):
        path = f"motors[{index}]"
        if not isinstance(raw, dict):
            issues.append(_issue("P13A021", path, "Cada motor debe ser un objeto estructurado."))
            continue

        identifier = _motor_id(raw.get("id"))
        if not identifier:
            issues.append(_issue("P13A022", f"{path}.id", "El motor requiere id."))
        elif identifier.lower() in seen_motors:
            issues.append(_issue("P13A023", f"{path}.id", "No se permiten motores duplicados."))
        else:
            seen_motors.add(identifier.lower())

        for key in (
            "bus",
            "phases",
            "kv_ll",
            "connection",
            "rated_output_kw",
            "starting_method",
            "starting_current_a",
            "starting_power_factor",
            "starting_data_reference",
        ):
            if not _present(raw.get(key)):
                issues.append(_issue("P13A024", f"{path}.{key}", f"Dato de motor requerido: {key}."))

        bus = str(raw.get("bus") or "").strip()
        if bus and buses and bus not in buses:
            issues.append(_issue("P13A025", f"{path}.bus", "La barra del motor no existe en base_model.topology.buses."))

        phases = _number(raw.get("phases"))
        if phases is not None and phases != 3:
            issues.append(_issue(
                "P13A026",
                f"{path}.phases",
                "P13 v1 limita el estudio estático de arranque a motores trifásicos.",
            ))

        for key in ("kv_ll", "rated_output_kw", "starting_current_a"):
            if _present(raw.get(key)) and not _positive(raw.get(key)):
                issues.append(_issue("P13A027", f"{path}.{key}", f"{key} debe ser finito y mayor que cero."))

        connection = str(raw.get("connection") or "").strip().lower()
        if connection and connection not in ALLOWED_CONNECTIONS:
            issues.append(_issue("P13A028", f"{path}.connection", "connection debe ser wye o delta."))

        method = str(raw.get("starting_method") or "").strip().upper()
        if method and method not in ALLOWED_STARTING_METHODS:
            issues.append(_issue(
                "P13A029",
                f"{path}.starting_method",
                "Método de arranque no soportado por el contrato P13A.",
            ))

        pf = _number(raw.get("starting_power_factor"))
        if pf is not None and not (0 < pf <= 1):
            issues.append(_issue(
                "P13A030",
                f"{path}.starting_power_factor",
                "starting_power_factor debe cumplir 0 < PF <= 1.",
            ))

        included = raw.get("base_model_includes_running_motor")
        if not isinstance(included, bool):
            issues.append(_issue(
                "P13A031",
                f"{path}.base_model_includes_running_motor",
                "Debe declararse explícitamente si el modelo base ya contiene la carga de marcha del motor.",
            ))
        running = _load_id(raw.get("running_load_element_id"))
        if included is True:
            if not running:
                issues.append(_issue(
                    "P13A032",
                    f"{path}.running_load_element_id",
                    "Si el modelo incluye la carga de marcha, debe identificarse exactamente el Load.* a reemplazar durante el arranque.",
                ))
            elif loads and running.lower() not in loads:
                issues.append(_issue(
                    "P13A033",
                    f"{path}.running_load_element_id",
                    "running_load_element_id no existe en base_model.topology.loads.",
                ))
            else:
                declared_load = loads.get(running.lower()) or {}
                load_bus = str(declared_load.get("bus") or "").strip()
                if bus and load_bus and load_bus != bus:
                    issues.append(_issue(
                        "P13A034",
                        f"{path}.running_load_element_id",
                        "La carga de marcha declarada no está conectada en la misma barra del motor.",
                    ))
        elif included is False and running:
            issues.append(_issue(
                "P13A035",
                f"{path}.running_load_element_id",
                "No declare running_load_element_id si base_model_includes_running_motor=false.",
            ))

        normalized_motors.append({
            "id": identifier,
            "bus": bus,
            "phases": int(phases) if phases is not None and phases.is_integer() else raw.get("phases"),
            "kv_ll": _number(raw.get("kv_ll")),
            "connection": connection,
            "rated_output_kw": _number(raw.get("rated_output_kw")),
            "starting_method": method,
            "starting_current_a": _number(raw.get("starting_current_a")),
            "starting_power_factor": pf,
            "starting_data_reference": str(raw.get("starting_data_reference") or "").strip(),
            "base_model_includes_running_motor": included,
            "running_load_element_id": running or None,
        })

    studies = payload.get("studies")
    if not isinstance(studies, list) or not studies:
        issues.append(_issue("P13A040", "studies", "Se requiere al menos un estudio de arranque."))
        studies = []

    study_ids: set[str] = set()
    referenced_motors = {item["id"].lower() for item in normalized_motors if item.get("id")}
    normalized_studies: list[dict[str, Any]] = []
    for index, raw in enumerate(studies):
        path = f"studies[{index}]"
        if not isinstance(raw, dict):
            issues.append(_issue("P13A041", path, "Cada estudio debe ser un objeto estructurado."))
            continue
        for key in ("id", "motor_id", "study_type", "minimum_terminal_voltage_pu", "criterion_reference"):
            if not _present(raw.get(key)):
                issues.append(_issue("P13A042", f"{path}.{key}", f"Dato de estudio requerido: {key}."))

        sid = str(raw.get("id") or "").strip()
        if sid:
            if sid.lower() in study_ids:
                issues.append(_issue("P13A043", f"{path}.id", "ID de estudio duplicado."))
            study_ids.add(sid.lower())

        motor_id = _motor_id(raw.get("motor_id"))
        if motor_id and motor_id.lower() not in referenced_motors:
            issues.append(_issue("P13A044", f"{path}.motor_id", "El estudio referencia un motor inexistente."))

        study_type = str(raw.get("study_type") or "").strip().upper()
        if study_type and study_type != STUDY_TYPE:
            issues.append(_issue(
                "P13A045",
                f"{path}.study_type",
                f"P13A solo admite {STUDY_TYPE}.",
            ))

        minimum = _number(raw.get("minimum_terminal_voltage_pu"))
        if minimum is not None and not (0 < minimum <= 1):
            issues.append(_issue(
                "P13A046",
                f"{path}.minimum_terminal_voltage_pu",
                "El criterio de tensión debe cumplir 0 < pu <= 1.",
            ))

        normalized_studies.append({
            "id": sid,
            "motor_id": motor_id,
            "study_type": study_type,
            "minimum_terminal_voltage_pu": minimum,
            "criterion_reference": str(raw.get("criterion_reference") or "").strip(),
        })

    ready = not issues and bool(normalized_motors) and bool(normalized_studies)
    return {
        "schema": SCHEMA,
        "intake_status": STATUS_READY if ready else STATUS_BLOCKED,
        "ready_for_static_starting_build": ready,
        "issues": issues,
        "issue_count": len(issues),
        "project": deepcopy(project),
        "base_model_admission": deepcopy(base_admission),
        "motors": normalized_motors,
        "studies": normalized_studies,
        "industry_scope": "CROSS_INDUSTRY",
        "electrical_calculation_performed": False,
        "model_mutation_performed": False,
        "automatic_starting_current_derivation": False,
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
        "note": (
            "READY solo significa que los datos explícitos permiten construir después "
            "una aproximación estática de demanda de arranque equivalente. No implica cálculo dinámico "
            "de aceleración ni conformidad con un criterio normativo universal."
        ),
    }
