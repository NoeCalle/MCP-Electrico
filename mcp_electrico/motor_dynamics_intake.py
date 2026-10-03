"""P13F1: physical data admission for future dynamic backend qualification.

This module does not initialize a solver, materialize a machine or integrate
time. Complete input data never enables dynamic execution by itself.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from math import isclose, isfinite, pi
from typing import Any

from . import motor_starting_intake

SCHEMA = "MCP_ELECTRICO_P13F_DYNAMIC_PACKAGE_V1"
RESULT_SCHEMA = "MCP_ELECTRICO_P13F1_DYNAMIC_ADMISSION_V1"
SCOPE = "BALANCED_THREE_PHASE_SQUIRREL_CAGE_DOL"
MAXIMUM_STEPS = 200_000
MAXIMUM_POLE_PAIRS = 64

ELECTRICAL_FIELDS = {
    "parameter_basis", "pole_pairs", "frequency_hz", "stator_resistance_ohm",
    "rotor_resistance_ohm", "stator_leakage_inductance_h",
    "rotor_leakage_inductance_h", "magnetizing_inductance_h",
    "stator_temperature_k", "rotor_temperature_k", "temperature_model",
    "saturation_model", "core_loss_model", "stray_loss_model", "source_reference",
}
MECHANICAL_FIELDS = {
    "inertia_basis", "motor_inertia_kg_m2", "load_inertia_kg_m2",
    "viscous_damping_nm_s_per_rad", "load_curve", "curve_interpolation",
    "curve_extrapolation", "source_reference",
}


def manifest_sha256(manifest: dict) -> str:
    payload = json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def obtener_contrato_p13f() -> dict:
    return {
        "schema": RESULT_SCHEMA, "package_schema": SCHEMA, "scope": SCOPE,
        "phase": "P13F1_PHYSICAL_INPUT_PREPARATION",
        "electrical_parameter_basis": "PER_PHASE_STATOR_REFERRED_SI",
        "electrical_fields": sorted(ELECTRICAL_FIELDS),
        "mechanical_fields": sorted(MECHANICAL_FIELDS),
        "initialization": "DEENERGIZED_AT_REST",
        "maximum_time_steps": MAXIMUM_STEPS,
        "maximum_pole_pairs": MAXIMUM_POLE_PAIRS,
        "selected_backend": "OPENMODELICA_MSL_4_0_0", "backend_implemented": True,
        "execution_contract_tool": "obtener_contrato_dinamica_modelica", "legacy_execution_schema_retired": True,
        "ready_for_execution": False, "dynamic_integration_performed": False,
        "electrical_calculation_performed": False, "model_mutation_performed": False,
        "automatic_defaults": False, "automatic_dispatch": False,
        "professional_emission": False,
        "execution_blockers": ["EXECUTION_OPTIONS_AND_CALIBRATION_REQUIRED", "ACTUAL_GRID_AND_ENERGY_VERIFICATION_REQUIRED"],
    }


def evaluar_admision_dinamica(manifest: dict, paquete_dinamico: dict) -> dict:
    """Validate proposed SI machine inputs and their binding to a P13 manifest."""
    issues: list[dict[str, str]] = []

    def issue(code: str, path: str, message: str) -> None:
        issues.append({"code": code, "path": path, "message": message})

    def obj(value: Any, path: str, allowed: set[str]) -> dict:
        if not isinstance(value, dict):
            issue("P13F002", path, "Se requiere un objeto estructurado.")
            return {}
        for key in value:
            if key not in allowed:
                issue("P13F003", f"{path}.{key}", "Campo no reconocido en esta versión del contrato.")
        return value

    def number(value: Any, path: str, *, zero: bool = False) -> float | None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            issue("P13F004", path, "Se requiere un número SI explícito y finito.")
            return None
        try:
            result = float(value)
        except (ValueError, OverflowError):
            result = float("nan")
        if not isfinite(result) or (result < 0 if zero else result <= 0):
            issue("P13F004", path, "Valor fuera del dominio físico admitido.")
            return None
        return result

    def text(value: Any, path: str) -> str:
        if not isinstance(value, str) or not value.strip():
            issue("P13F005", path, "Se requiere texto explícito con procedencia o identidad.")
            return ""
        return value.strip()

    def choice(value: Any, expected: str, path: str) -> None:
        if value != expected:
            issue("P13F006", path, f"El alcance preparado requiere {expected}.")

    base = None
    digest = None
    if not isinstance(manifest, dict):
        issue("P13F001", "manifest", "Se requiere el manifiesto P13 estructurado.")
    else:
        try:
            digest = manifest_sha256(manifest)
            base = motor_starting_intake.evaluar_admision_motor(manifest)
        except (TypeError, ValueError, AttributeError, OverflowError):
            issue("P13F001", "manifest", "Manifiesto P13 mal formado o no serializable como JSON finito.")
        if base is not None and not base.get("ready_for_static_starting_build"):
            issue("P13F010", "manifest", "El intake P13A debe estar admitido.")

    package = obj(paquete_dinamico, "package", {
        "schema", "project_id", "manifest_sha256", "scope", "motors",
        "simulation", "studies", "source_reference",
    })
    choice(package.get("schema"), SCHEMA, "package.schema")
    choice(package.get("scope"), SCOPE, "package.scope")
    text(package.get("source_reference"), "package.source_reference")
    project_id = text(package.get("project_id"), "package.project_id")
    if base and project_id != (manifest.get("project") or {}).get("id"):
        issue("P13F011", "package.project_id", "El paquete debe pertenecer al proyecto P13 recibido.")
    if not digest or package.get("manifest_sha256") != digest:
        issue("P13F012", "package.manifest_sha256", "El SHA-256 canónico debe corresponder al manifiesto recibido.")

    simulation = obj(package.get("simulation"), "package.simulation", {
        "time_grid", "duration_s", "time_step_s", "maximum_steps", "source_reference",
    })
    choice(simulation.get("time_grid"), "FIXED_STEP", "package.simulation.time_grid")
    duration = number(simulation.get("duration_s"), "package.simulation.duration_s")
    step = number(simulation.get("time_step_s"), "package.simulation.time_step_s")
    limit = simulation.get("maximum_steps")
    if type(limit) is not int or not 1 <= limit <= MAXIMUM_STEPS:
        issue("P13F020", "package.simulation.maximum_steps", "Límite entero explícito fuera de rango.")
    if duration is not None and step is not None:
        count = duration / step
        if (not isfinite(count) or count < 1 or count > MAXIMUM_STEPS
                or not isclose(count, round(count), rel_tol=0, abs_tol=1e-8)
                or (type(limit) is int and round(count) > limit)):
            issue("P13F021", "package.simulation", "La duración debe definir pasos enteros dentro del límite declarado.")
    text(simulation.get("source_reference"), "package.simulation.source_reference")

    base_motors = {item["id"].lower(): item for item in (base or {}).get("motors", [])}
    source_frequency = None
    if isinstance(manifest, dict):
        base_model = manifest.get("base_model")
        if isinstance(base_model, dict) and isinstance(base_model.get("source"), dict):
            source_frequency = base_model["source"].get("frequency_hz")
    models = package.get("motors")
    if not isinstance(models, list) or not models:
        issue("P13F030", "package.motors", "Se requiere al menos un modelo físico.")
        models = []
    seen: set[str] = set()
    derived = []
    for index, raw in enumerate(models):
        path = f"package.motors[{index}]"
        model = obj(raw, path, {"motor_id", "machine_type", "electrical", "mechanical", "initial_state", "source_reference"})
        identifier = text(model.get("motor_id"), f"{path}.motor_id")
        key = identifier.lower()
        if key in seen:
            issue("P13F031", f"{path}.motor_id", "Modelo físico duplicado.")
        seen.add(key)
        parent = base_motors.get(key)
        if parent is None:
            issue("P13F032", f"{path}.motor_id", "Referencia a un motor P13 inexistente.")
        elif parent.get("starting_method") != "DOL" or parent.get("phases") != 3:
            issue("P13F033", f"{path}.motor_id", "La preparación inicial admite únicamente DOL trifásico.")
        choice(model.get("machine_type"), "SQUIRREL_CAGE_INDUCTION", f"{path}.machine_type")
        text(model.get("source_reference"), f"{path}.source_reference")
        electric = obj(model.get("electrical"), f"{path}.electrical", ELECTRICAL_FIELDS)
        choice(electric.get("parameter_basis"), "PER_PHASE_STATOR_REFERRED_SI", f"{path}.electrical.parameter_basis")
        poles = electric.get("pole_pairs")
        valid_poles = type(poles) is int and 1 <= poles <= MAXIMUM_POLE_PAIRS
        if not valid_poles:
            issue("P13F034", f"{path}.electrical.pole_pairs", "Pares de polos enteros fuera del alcance preparado (1..64).")
        frequency = number(electric.get("frequency_hz"), f"{path}.electrical.frequency_hz")
        if frequency is not None and frequency != source_frequency:
            issue("P13F035", f"{path}.electrical.frequency_hz", "La frecuencia debe coincidir con la red base explícita.")
        for field in ELECTRICAL_FIELDS - {"parameter_basis", "pole_pairs", "frequency_hz", "temperature_model", "saturation_model", "core_loss_model", "stray_loss_model", "source_reference"}:
            number(electric.get(field), f"{path}.electrical.{field}")
        for field, expected in {
            "temperature_model": "FIXED_AT_DECLARED_OPERATING_TEMPERATURE",
            "saturation_model": "LINEAR_EXPLICIT", "core_loss_model": "EXCLUDED_EXPLICIT",
            "stray_loss_model": "EXCLUDED_EXPLICIT",
        }.items():
            choice(electric.get(field), expected, f"{path}.electrical.{field}")
        text(electric.get("source_reference"), f"{path}.electrical.source_reference")

        mechanical = obj(model.get("mechanical"), f"{path}.mechanical", MECHANICAL_FIELDS)
        choice(mechanical.get("inertia_basis"), "MOTOR_SHAFT_SI", f"{path}.mechanical.inertia_basis")
        number(mechanical.get("motor_inertia_kg_m2"), f"{path}.mechanical.motor_inertia_kg_m2")
        number(mechanical.get("load_inertia_kg_m2"), f"{path}.mechanical.load_inertia_kg_m2", zero=True)
        number(mechanical.get("viscous_damping_nm_s_per_rad"), f"{path}.mechanical.viscous_damping_nm_s_per_rad", zero=True)
        choice(mechanical.get("curve_interpolation"), "LINEAR_EXPLICIT", f"{path}.mechanical.curve_interpolation")
        choice(mechanical.get("curve_extrapolation"), "BLOCK", f"{path}.mechanical.curve_extrapolation")
        text(mechanical.get("source_reference"), f"{path}.mechanical.source_reference")
        points = mechanical.get("load_curve")
        if not isinstance(points, list) or len(points) < 2:
            issue("P13F040", f"{path}.mechanical.load_curve", "La curva requiere al menos dos puntos explícitos.")
            points = []
        speeds = []
        for j, point in enumerate(points):
            pp = f"{path}.mechanical.load_curve[{j}]"
            point = obj(point, pp, {"speed_rad_s", "torque_nm"})
            speed = number(point.get("speed_rad_s"), f"{pp}.speed_rad_s", zero=True)
            number(point.get("torque_nm"), f"{pp}.torque_nm", zero=True)
            if speed is not None:
                speeds.append(speed)
        synchronous_speed = 2 * pi * frequency / poles if frequency and valid_poles else None
        if speeds and (speeds[0] != 0 or any(b <= a for a, b in zip(speeds, speeds[1:]))
                       or (synchronous_speed and speeds[-1] < synchronous_speed)):
            issue("P13F041", f"{path}.mechanical.load_curve", "Velocidades estrictamente crecientes desde cero y cobertura hasta velocidad síncrona.")
        initial = obj(model.get("initial_state"), f"{path}.initial_state", {"mode", "speed_rad_s", "source_reference"})
        choice(initial.get("mode"), "DEENERGIZED_AT_REST", f"{path}.initial_state.mode")
        initial_speed = number(initial.get("speed_rad_s"), f"{path}.initial_state.speed_rad_s", zero=True)
        if initial_speed is not None and initial_speed != 0:
            issue("P13F042", f"{path}.initial_state.speed_rad_s", "La inicialización preparada exige reposo explícito.")
        text(initial.get("source_reference"), f"{path}.initial_state.source_reference")
        derived.append({"motor_id": identifier, "synchronous_speed_rad_s": synchronous_speed})

    studies = package.get("studies")
    if not isinstance(studies, list) or not studies:
        issue("P13F050", "package.studies", "Se requiere un objetivo dinámico explícito.")
        studies = []
    study_ids = set()
    referenced = set()
    for index, raw in enumerate(studies):
        path = f"package.studies[{index}]"
        study = obj(raw, path, {"id", "motor_id", "target_speed_fraction", "maximum_acceleration_time_s", "minimum_terminal_voltage_pu", "criterion_reference"})
        sid = text(study.get("id"), f"{path}.id").lower()
        if sid in study_ids:
            issue("P13F051", f"{path}.id", "ID de estudio duplicado.")
        study_ids.add(sid)
        motor_id = text(study.get("motor_id"), f"{path}.motor_id").lower()
        referenced.add(motor_id)
        if motor_id not in seen:
            issue("P13F052", f"{path}.motor_id", "El estudio requiere un modelo físico declarado.")
        target = number(study.get("target_speed_fraction"), f"{path}.target_speed_fraction")
        minimum = number(study.get("minimum_terminal_voltage_pu"), f"{path}.minimum_terminal_voltage_pu")
        deadline = number(study.get("maximum_acceleration_time_s"), f"{path}.maximum_acceleration_time_s")
        if (target is not None and target >= 1) or (minimum is not None and minimum > 1):
            issue("P13F053", path, "El objetivo debe estar debajo de velocidad síncrona y la tensión mínima no puede superar 1 pu.")
        if deadline is not None and duration is not None and deadline > duration:
            issue("P13F054", f"{path}.maximum_acceleration_time_s", "El tiempo permitido debe estar dentro de la ventana simulada.")
        text(study.get("criterion_reference"), f"{path}.criterion_reference")
    if seen - referenced:
        issue("P13F055", "package.studies", "Cada modelo físico requiere un estudio explícito.")

    # Order is deterministic for audit/replay, including fields collected from sets.
    issues.sort(key=lambda item: (item["path"], item["code"]))
    ready = not issues
    return {
        **obtener_contrato_p13f(), "data_ready": ready,
        "admission_status": "READY_FOR_DYNAMIC_BACKEND_QUALIFICATION" if ready else "BLOCKED_DYNAMIC_INPUTS",
        "ready_for_dynamic_backend_qualification": ready, "issues": issues,
        "manifest_sha256": digest, "p13a_admitted": bool(base and base.get("ready_for_static_starting_build")),
        "derived_kinematic_values": derived if ready else [],
        "accepted_package": deepcopy(package) if ready else None,
    }
