"""P12A — contrato fail-closed para estudios de motores y arranque.

P12A NO ejecuta dinámica ni flujo. Define una entrada explícita y sector-neutral
para preparar futuros estudios de arranque en manufactura, agua, HVAC,
hospitales, data centers, oil & gas, minería y otras instalaciones industriales.

Principios:
- no se deriva silenciosamente corriente nominal, LRC, torque o inercia;
- el método de arranque es explícito;
- STARTING_VOLTAGE_DIP y ACCELERATION_TIME tienen requisitos distintos;
- VFD no se trata como DOL reducido;
- professional_emission permanece False.
"""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any

SCHEMA = "MCP_ELECTRICO_P12A_MOTOR_STARTING_INPUT_V1"
STATUS_READY = "READY_FOR_MOTOR_STARTING_MODEL"
STATUS_BLOCKED = "BLOCKED_MISSING_MOTOR_STARTING_INPUTS"

SUPPORTED_STUDIES = {
    "STARTING_VOLTAGE_DIP",
    "ACCELERATION_TIME",
}
SUPPORTED_MOTOR_TYPES = {
    "INDUCTION_SQUIRREL_CAGE",
}
SUPPORTED_STARTERS = {
    "DOL",
    "STAR_DELTA",
    "SOFT_STARTER",
    "VFD",
}
SUPPORTED_LOAD_TORQUE_MODELS = {
    "CONSTANT_TORQUE",
    "QUADRATIC_TORQUE",
    "LINEAR_TORQUE",
    "EXPLICIT_POINTS",
}


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


def _fraction(value: Any) -> bool:
    number = _number(value)
    return number is not None and 0 < number <= 1


def _issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def obtener_contrato_p12a() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "purpose": "PRE_MOTOR_STARTING_MODEL_ADMISSION",
        "supported_studies": sorted(SUPPORTED_STUDIES),
        "supported_motor_types": sorted(SUPPORTED_MOTOR_TYPES),
        "supported_starters": sorted(SUPPORTED_STARTERS),
        "electrical_calculation_performed": False,
        "dynamic_simulation_performed": False,
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "professional_emission": False,
    }


def _starter_issues(starter: dict[str, Any], path: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    starter_type = str(starter.get("type") or "").strip().upper()
    if starter_type not in SUPPORTED_STARTERS:
        issues.append(_issue(
            "P12A_S001",
            f"{path}.type",
            "Método de arranque no soportado por P12A.",
        ))
        return issues

    if starter_type == "DOL":
        if not _positive(starter.get("locked_rotor_current_ratio")):
            issues.append(_issue(
                "P12A_S010",
                f"{path}.locked_rotor_current_ratio",
                "DOL requiere relación de corriente de rotor bloqueado explícita.",
            ))
        if not _fraction(starter.get("starting_power_factor")):
            issues.append(_issue(
                "P12A_S011",
                f"{path}.starting_power_factor",
                "DOL requiere factor de potencia de arranque explícito en (0,1].",
            ))

    elif starter_type == "STAR_DELTA":
        if not _positive(starter.get("locked_rotor_current_ratio_delta")):
            issues.append(_issue(
                "P12A_S020",
                f"{path}.locked_rotor_current_ratio_delta",
                "STAR_DELTA requiere LRC en conexión delta explícita.",
            ))
        if not _fraction(starter.get("starting_power_factor")):
            issues.append(_issue(
                "P12A_S021",
                f"{path}.starting_power_factor",
                "STAR_DELTA requiere factor de potencia de arranque explícito.",
            ))
        transition = str(starter.get("transition") or "").strip().upper()
        if transition not in {"OPEN", "CLOSED"}:
            issues.append(_issue(
                "P12A_S022",
                f"{path}.transition",
                "STAR_DELTA requiere transition=OPEN o CLOSED.",
            ))

    elif starter_type == "SOFT_STARTER":
        if not _positive(starter.get("current_limit_pu")):
            issues.append(_issue(
                "P12A_S030",
                f"{path}.current_limit_pu",
                "SOFT_STARTER requiere current_limit_pu explícito.",
            ))
        if not _positive(starter.get("ramp_time_s")):
            issues.append(_issue(
                "P12A_S031",
                f"{path}.ramp_time_s",
                "SOFT_STARTER requiere ramp_time_s explícito.",
            ))
        if not _fraction(starter.get("input_power_factor")):
            issues.append(_issue(
                "P12A_S032",
                f"{path}.input_power_factor",
                "SOFT_STARTER requiere input_power_factor explícito.",
            ))

    elif starter_type == "VFD":
        for key in ("drive_rating_kw", "input_current_limit_a"):
            if not _positive(starter.get(key)):
                issues.append(_issue(
                    "P12A_S040",
                    f"{path}.{key}",
                    f"VFD requiere {key} explícito.",
                ))
        if not _fraction(starter.get("input_power_factor")):
            issues.append(_issue(
                "P12A_S041",
                f"{path}.input_power_factor",
                "VFD requiere input_power_factor explícito.",
            ))
        control = str(starter.get("control_mode") or "").strip().upper()
        if control not in {"V_HZ", "VECTOR", "DTC", "OTHER_EXPLICIT"}:
            issues.append(_issue(
                "P12A_S042",
                f"{path}.control_mode",
                "VFD requiere control_mode explícito y soportado.",
            ))

    return issues


def _mechanical_issues(
    motor: dict[str, Any],
    requested_studies: set[str],
    path: str,
) -> list[dict[str, str]]:
    if "ACCELERATION_TIME" not in requested_studies:
        return []

    issues: list[dict[str, str]] = []
    mechanical = motor.get("mechanical")
    if not isinstance(mechanical, dict):
        return [_issue(
            "P12A_M001",
            f"{path}.mechanical",
            "ACCELERATION_TIME requiere bloque mechanical explícito.",
        )]

    if not _positive(mechanical.get("motor_inertia_kg_m2")):
        issues.append(_issue(
            "P12A_M002",
            f"{path}.mechanical.motor_inertia_kg_m2",
            "Se requiere inercia del motor explícita.",
        ))
    if not _positive(mechanical.get("load_inertia_kg_m2")):
        issues.append(_issue(
            "P12A_M003",
            f"{path}.mechanical.load_inertia_kg_m2",
            "Se requiere inercia de la carga explícita.",
        ))

    model = str(mechanical.get("load_torque_model") or "").strip().upper()
    if model not in SUPPORTED_LOAD_TORQUE_MODELS:
        issues.append(_issue(
            "P12A_M004",
            f"{path}.mechanical.load_torque_model",
            "Modelo de torque de carga no soportado.",
        ))
    elif model == "EXPLICIT_POINTS":
        points = mechanical.get("load_torque_points")
        if not isinstance(points, list) or len(points) < 2:
            issues.append(_issue(
                "P12A_M005",
                f"{path}.mechanical.load_torque_points",
                "EXPLICIT_POINTS requiere al menos dos puntos speed_pu/torque_pu.",
            ))
        else:
            previous_speed: float | None = None
            for j, point in enumerate(points):
                ppath = f"{path}.mechanical.load_torque_points[{j}]"
                if not isinstance(point, dict):
                    issues.append(_issue("P12A_M006", ppath, "Cada punto debe ser un objeto."))
                    continue
                speed = _number(point.get("speed_pu"))
                torque = _number(point.get("torque_pu"))
                if speed is None or not 0 <= speed <= 1:
                    issues.append(_issue(
                        "P12A_M007",
                        f"{ppath}.speed_pu",
                        "speed_pu debe estar entre 0 y 1.",
                    ))
                elif previous_speed is not None and speed <= previous_speed:
                    issues.append(_issue(
                        "P12A_M008",
                        f"{ppath}.speed_pu",
                        "Los puntos deben tener speed_pu estrictamente creciente.",
                    ))
                if speed is not None:
                    previous_speed = speed
                if torque is None or torque < 0:
                    issues.append(_issue(
                        "P12A_M009",
                        f"{ppath}.torque_pu",
                        "torque_pu debe ser numérico y no negativo.",
                    ))

    return issues


def evaluar_admision(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("payload debe ser dict.")

    requested_raw = payload.get("requested_studies") or []
    requested = list(dict.fromkeys(
        str(item).strip().upper()
        for item in requested_raw
        if str(item).strip()
    ))
    requested_set = set(requested)
    issues: list[dict[str, str]] = []

    if not requested:
        issues.append(_issue(
            "P12A_001",
            "requested_studies",
            "Debe declararse al menos un estudio de arranque.",
        ))
    for study in requested:
        if study not in SUPPORTED_STUDIES:
            issues.append(_issue(
                "P12A_002",
                "requested_studies",
                f"Estudio no soportado: {study}.",
            ))

    project = payload.get("project") or {}
    for key in ("id", "name", "source_reference"):
        if not _present(project.get(key)):
            issues.append(_issue(
                "P12A_010",
                f"project.{key}",
                f"project.{key} es requerido.",
            ))

    system = payload.get("system") or {}
    if not _positive(system.get("frequency_hz")):
        issues.append(_issue(
            "P12A_020",
            "system.frequency_hz",
            "La frecuencia del sistema debe ser explícita y mayor que cero.",
        ))

    motors = payload.get("motors")
    if not isinstance(motors, list) or not motors:
        issues.append(_issue(
            "P12A_030",
            "motors",
            "Se requiere al menos un motor estructurado.",
        ))
        motors = []

    seen: set[str] = set()
    normalized_motors: list[dict[str, Any]] = []
    for i, motor in enumerate(motors):
        path = f"motors[{i}]"
        if not isinstance(motor, dict):
            issues.append(_issue("P12A_031", path, "Cada motor debe ser un objeto."))
            continue

        motor_id = str(motor.get("id") or "").strip()
        if not motor_id:
            issues.append(_issue("P12A_032", f"{path}.id", "Motor requiere id explícito."))
        elif motor_id.lower() in seen:
            issues.append(_issue("P12A_033", f"{path}.id", "ID de motor duplicado."))
        else:
            seen.add(motor_id.lower())

        for key in ("bus", "source_reference"):
            if not _present(motor.get(key)):
                issues.append(_issue(
                    "P12A_034",
                    f"{path}.{key}",
                    f"Motor requiere {key} explícito.",
                ))

        phases = _number(motor.get("phases"))
        if phases != 3:
            issues.append(_issue(
                "P12A_035",
                f"{path}.phases",
                "P12A-v1 limita estudios de arranque a motores trifásicos.",
            ))

        for key in ("rated_kw", "rated_kv_ll", "rated_current_a"):
            if not _positive(motor.get(key)):
                issues.append(_issue(
                    "P12A_036",
                    f"{path}.{key}",
                    f"Motor requiere {key} explícito >0.",
                ))

        if not _fraction(motor.get("efficiency_pu")):
            issues.append(_issue(
                "P12A_037",
                f"{path}.efficiency_pu",
                "efficiency_pu debe estar en (0,1].",
            ))
        if not _fraction(motor.get("rated_power_factor")):
            issues.append(_issue(
                "P12A_038",
                f"{path}.rated_power_factor",
                "rated_power_factor debe estar en (0,1].",
            ))

        motor_type = str(motor.get("motor_type") or "").strip().upper()
        if motor_type not in SUPPORTED_MOTOR_TYPES:
            issues.append(_issue(
                "P12A_039",
                f"{path}.motor_type",
                "P12A-v1 soporta únicamente motor de inducción jaula de ardilla.",
            ))

        starter = motor.get("starter")
        if not isinstance(starter, dict):
            issues.append(_issue(
                "P12A_040",
                f"{path}.starter",
                "Se requiere bloque starter explícito.",
            ))
        else:
            issues.extend(_starter_issues(starter, f"{path}.starter"))

        issues.extend(_mechanical_issues(motor, requested_set, path))

        normalized_motors.append({
            "id": motor_id,
            "bus": str(motor.get("bus") or "").strip(),
            "motor_type": motor_type,
            "starter_type": (
                str((starter or {}).get("type") or "").strip().upper()
                if isinstance(starter, dict)
                else None
            ),
        })

    ready = not issues and bool(requested) and bool(normalized_motors)
    return {
        "schema": SCHEMA,
        "admission_status": STATUS_READY if ready else STATUS_BLOCKED,
        "ready_for_motor_starting_model": ready,
        "requested_studies": requested,
        "motors": normalized_motors,
        "issues": deepcopy(issues),
        "issue_count": len(issues),
        "electrical_calculation_performed": False,
        "dynamic_simulation_performed": False,
        "model_mutation_performed": False,
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "professional_emission": False,
        "note": (
            "P12A valida datos de entrada para motores y arranque. "
            "No calcula corriente de arranque, caída de tensión ni tiempo de aceleración."
        ),
    }
