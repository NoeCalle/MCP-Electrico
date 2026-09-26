"""P13C — perfiles explícitos de arranque como estados estáticos independientes.

P13C extiende P13B con una secuencia declarada de puntos (tiempo, corriente y
factor de potencia). El tiempo solo ordena los puntos: OpenDSS no avanza reloj,
no interpola y no integra dinámica. Cada punto se resuelve en un NewContext
nuevo para impedir que el estado algebraico de un punto contamine al siguiente.
"""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any

from . import motor_starting_intake, motor_starting_static

SCHEMA_CONTRACT = "MCP_ELECTRICO_P13C_MOTOR_STARTING_PROFILE_CONTRACT_V1"
SCHEMA_EXECUTION = "MCP_ELECTRICO_P13C_MOTOR_STARTING_PROFILE_EXECUTION_V1"

STATUS_READY = "READY_FOR_STATIC_STARTING_PROFILE"
STATUS_BLOCKED = "BLOCKED_STARTING_PROFILE_INPUTS"
STATUS_COMPLETED = "STATIC_STARTING_PROFILE_COMPLETED"
STATUS_PARTIAL = "STATIC_STARTING_PROFILE_PARTIAL"

CURRENT_BASIS = "SUPPLY_LINE_RMS_AT_RATED_VOLTAGE"
PF_BASIS = "FUNDAMENTAL_DISPLACEMENT"
PROFILE_SEMANTICS = "DECLARED_STATIC_OPERATING_POINTS_ORDERED_BY_TIME"


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


def obtener_contrato_p13c() -> dict[str, Any]:
    return {
        "schema": SCHEMA_CONTRACT,
        "purpose": "EXPLICIT_STATIC_MOTOR_STARTING_PROFILE",
        "industry_scope": "CROSS_INDUSTRY",
        "profile_semantics": PROFILE_SEMANTICS,
        "current_basis": CURRENT_BASIS,
        "power_factor_basis": PF_BASIS,
        "point_isolation": "FRESH_OPENDSS_NEW_CONTEXT_PER_POINT",
        "elapsed_time_used_by_solver": False,
        "interpolation": False,
        "dynamic_integration": False,
        "automatic_profile_generation": False,
        "automatic_starting_current_derivation": False,
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
    }


def _study_map(intake: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id") or "").lower(): item
        for item in intake.get("studies") or []
        if str(item.get("id") or "").strip()
    }


def _motor_map(intake: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id") or "").lower(): item
        for item in intake.get("motors") or []
        if str(item.get("id") or "").strip()
    }


def validar_perfiles(
    manifest: dict[str, Any],
    profile_package: dict[str, Any],
) -> dict[str, Any]:
    """Valida el profile package sin construir ni resolver un modelo eléctrico."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest debe ser dict.")
    if not isinstance(profile_package, dict):
        raise TypeError("profile_package debe ser dict.")

    intake = motor_starting_intake.evaluar_admision_motor(deepcopy(manifest))
    issues: list[dict[str, str]] = []
    if intake.get("ready_for_static_starting_build") is not True:
        issues.append(_issue(
            "P13C001",
            "manifest",
            "P13C requiere que P13A esté READY antes de admitir perfiles.",
        ))

    project_id = str((manifest.get("project") or {}).get("id") or "").strip()
    package_project = str(profile_package.get("project_id") or "").strip()
    if not package_project:
        issues.append(_issue("P13C002", "profile_package.project_id", "project_id es requerido."))
    elif project_id and package_project != project_id:
        issues.append(_issue(
            "P13C003",
            "profile_package.project_id",
            "El profile package debe pertenecer al mismo proyecto P13.",
        ))

    package_reference = str(profile_package.get("source_reference") or "").strip()
    if not package_reference:
        issues.append(_issue(
            "P13C004",
            "profile_package.source_reference",
            "El paquete de perfiles requiere procedencia explícita.",
        ))

    profiles = profile_package.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        issues.append(_issue(
            "P13C005",
            "profile_package.profiles",
            "Se requiere al menos un perfil explícito.",
        ))
        profiles = []

    studies = _study_map(intake)
    motors = _motor_map(intake)
    normalized: list[dict[str, Any]] = []
    seen_profile_ids: set[str] = set()
    seen_studies: set[str] = set()

    for i, raw in enumerate(profiles):
        path = f"profile_package.profiles[{i}]"
        if not isinstance(raw, dict):
            issues.append(_issue("P13C006", path, "Cada perfil debe ser un objeto estructurado."))
            continue

        profile_id = str(raw.get("id") or "").strip()
        study_id = str(raw.get("study_id") or "").strip()
        profile_reference = str(raw.get("profile_reference") or "").strip()
        current_basis = str(raw.get("current_basis") or "").strip().upper()
        pf_basis = str(raw.get("power_factor_basis") or "").strip().upper()

        if not profile_id:
            issues.append(_issue("P13C007", f"{path}.id", "El perfil requiere id."))
        elif profile_id.lower() in seen_profile_ids:
            issues.append(_issue("P13C008", f"{path}.id", "ID de perfil duplicado."))
        else:
            seen_profile_ids.add(profile_id.lower())

        study = None
        if not study_id:
            issues.append(_issue("P13C009", f"{path}.study_id", "study_id es requerido."))
        else:
            study = studies.get(study_id.lower())
            if study is None:
                issues.append(_issue(
                    "P13C010",
                    f"{path}.study_id",
                    "El perfil referencia un estudio P13A inexistente.",
                ))
            if study_id.lower() in seen_studies:
                issues.append(_issue(
                    "P13C011",
                    f"{path}.study_id",
                    "P13C v1 admite un solo perfil por estudio.",
                ))
            seen_studies.add(study_id.lower())

        if not profile_reference:
            issues.append(_issue(
                "P13C012",
                f"{path}.profile_reference",
                "El perfil requiere referencia explícita.",
            ))

        if current_basis != CURRENT_BASIS:
            issues.append(_issue(
                "P13C013",
                f"{path}.current_basis",
                f"current_basis debe ser {CURRENT_BASIS}.",
            ))
        if pf_basis != PF_BASIS:
            issues.append(_issue(
                "P13C014",
                f"{path}.power_factor_basis",
                f"power_factor_basis debe ser {PF_BASIS}.",
            ))

        points = raw.get("points")
        if not isinstance(points, list) or len(points) < 2:
            issues.append(_issue(
                "P13C015",
                f"{path}.points",
                "Un perfil requiere al menos dos puntos explícitos.",
            ))
            points = []

        normalized_points: list[dict[str, Any]] = []
        previous_time: float | None = None
        seen_point_ids: set[str] = set()
        for j, point in enumerate(points):
            ppath = f"{path}.points[{j}]"
            if not isinstance(point, dict):
                issues.append(_issue("P13C016", ppath, "Cada punto debe ser un objeto."))
                continue

            point_id = str(point.get("id") or "").strip()
            elapsed = _number(point.get("elapsed_time_s"))
            current = _number(point.get("starting_current_a"))
            pf = _number(point.get("starting_power_factor"))

            if not point_id:
                issues.append(_issue("P13C017", f"{ppath}.id", "Cada punto requiere id."))
            elif point_id.lower() in seen_point_ids:
                issues.append(_issue(
                    "P13C018", f"{ppath}.id", "ID de punto duplicado dentro del perfil."
                ))
            else:
                seen_point_ids.add(point_id.lower())

            if elapsed is None or elapsed < 0:
                issues.append(_issue(
                    "P13C019",
                    f"{ppath}.elapsed_time_s",
                    "elapsed_time_s debe ser finito y >=0.",
                ))
            elif previous_time is not None and elapsed <= previous_time:
                issues.append(_issue(
                    "P13C020",
                    f"{ppath}.elapsed_time_s",
                    "Los tiempos deben ser estrictamente crecientes.",
                ))
            if elapsed is not None and elapsed >= 0:
                previous_time = elapsed

            if not _positive(current):
                issues.append(_issue(
                    "P13C021",
                    f"{ppath}.starting_current_a",
                    "starting_current_a debe ser finito y >0.",
                ))
            if pf is None or not (0 < pf <= 1):
                issues.append(_issue(
                    "P13C022",
                    f"{ppath}.starting_power_factor",
                    "starting_power_factor debe cumplir 0 < PF <= 1.",
                ))

            normalized_points.append({
                "id": point_id,
                "elapsed_time_s": elapsed,
                "starting_current_a": current,
                "starting_power_factor": pf,
            })

        motor = None
        if study is not None:
            motor = motors.get(str(study.get("motor_id") or "").lower())

        if normalized_points:
            first = normalized_points[0]
            if first.get("elapsed_time_s") != 0.0:
                issues.append(_issue(
                    "P13C023",
                    f"{path}.points[0].elapsed_time_s",
                    "El primer punto del perfil debe estar en t=0.",
                ))
            if motor is not None:
                if current_basis != str(motor.get("starting_current_basis") or "").upper():
                    issues.append(_issue(
                        "P13C024",
                        f"{path}.current_basis",
                        "La base de corriente del perfil debe coincidir con la del motor P13A.",
                    ))
                if pf_basis != str(motor.get("starting_power_factor_basis") or "").upper():
                    issues.append(_issue(
                        "P13C025",
                        f"{path}.power_factor_basis",
                        "La base de PF del perfil debe coincidir con la del motor P13A.",
                    ))
                actual_i = first.get("starting_current_a")
                actual_pf = first.get("starting_power_factor")
                if actual_i is None or abs(float(actual_i) - float(motor["starting_current_a"])) > 1e-9:
                    issues.append(_issue(
                        "P13C026",
                        f"{path}.points[0].starting_current_a",
                        "El primer punto debe coincidir con starting_current_a de P13A.",
                    ))
                if actual_pf is None or abs(float(actual_pf) - float(motor["starting_power_factor"])) > 1e-12:
                    issues.append(_issue(
                        "P13C027",
                        f"{path}.points[0].starting_power_factor",
                        "El primer punto debe coincidir con starting_power_factor de P13A.",
                    ))

        normalized.append({
            "id": profile_id,
            "study_id": study_id,
            "profile_reference": profile_reference,
            "current_basis": current_basis,
            "power_factor_basis": pf_basis,
            "points": normalized_points,
        })

    ready = not issues and bool(normalized)
    return {
        "schema": SCHEMA_CONTRACT,
        "validation_status": STATUS_READY if ready else STATUS_BLOCKED,
        "ready_for_execution": ready,
        "issues": issues,
        "issue_count": len(issues),
        "profiles": normalized,
        "p13a": intake,
        "electrical_calculation_performed": False,
        "motor_starting_calculation_performed": False,
        "elapsed_time_used_by_solver": False,
        "interpolation_performed": False,
        "dynamic_integration_performed": False,
        "automatic_profile_generation": False,
        "automatic_starting_current_derivation": False,
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
    }


def _point_demand(motor: dict[str, Any], point: dict[str, Any]) -> dict[str, float]:
    local = dict(motor)
    local["starting_current_a"] = float(point["starting_current_a"])
    local["starting_power_factor"] = float(point["starting_power_factor"])
    return motor_starting_static._equivalent_starting_demand(local)


def _disable_running_load(engine: Any, motor: dict[str, Any]) -> str | None:
    running = str(motor.get("running_load_element_id") or "").strip()
    if motor.get("base_model_includes_running_motor") is True and running:
        if not engine.Circuit.SetActiveElement(running):
            raise RuntimeError(f"running load no encontrado en contexto aislado: {running}")
        engine(f"Edit {running} Enabled=No")
        return running
    return None


def _pre_start_state(
    *,
    base_model: dict[str, Any],
    motors: list[dict[str, Any]],
    bus_bases: dict[str, float],
    motor: dict[str, Any],
) -> dict[str, Any]:
    engine, _ = motor_starting_static._build_isolated_base(base_model, motors, bus_bases)
    running = _disable_running_load(engine, motor)
    engine("Solve")
    converged = bool(engine.Solution.Converged())
    voltages = motor_starting_static._bus_voltage_pu(engine, motor["bus"])
    return {
        "converged": converged,
        "voltage_pu_by_phase": voltages,
        "minimum_voltage_pu": min(voltages) if voltages else None,
        "running_load_disabled": running,
    }


def _execute_point(
    *,
    base_model: dict[str, Any],
    motors: list[dict[str, Any]],
    bus_bases: dict[str, float],
    motor: dict[str, Any],
    study: dict[str, Any],
    profile: dict[str, Any],
    point: dict[str, Any],
    pre_start_min_voltage_pu: float,
) -> dict[str, Any]:
    engine, _ = motor_starting_static._build_isolated_base(base_model, motors, bus_bases)
    _disable_running_load(engine, motor)

    demand = _point_demand(motor, point)
    load_name = (
        "p13c_"
        + motor_starting_static._safe_element_suffix(profile["id"])
        + "_"
        + motor_starting_static._safe_element_suffix(point["id"])
    )
    engine(
        " ".join([
            f"New Load.{load_name}",
            f"Bus1={motor['bus']}",
            "Phases=3",
            f"kV={float(motor['kv_ll'])}",
            f"kW={demand['active_kw_at_rated_voltage']}",
            f"kvar={demand['reactive_kvar_at_rated_voltage']}",
            f"Conn={motor['connection']}",
            f"Model={motor_starting_static.LOAD_MODEL}",
            "Status=Fixed",
            f"Vminpu={motor_starting_static.MODEL_VMIN_PU}",
            f"Vmaxpu={motor_starting_static.MODEL_VMAX_PU}",
        ])
    )
    engine("Solve")
    converged = bool(engine.Solution.Converged())
    voltages = motor_starting_static._bus_voltage_pu(engine, motor["bus"])
    if not converged or not voltages:
        return {
            **deepcopy(point),
            "ok": False,
            "status": "POINT_SOLUTION_NOT_READY",
            "starting_demand": demand,
            "elapsed_time_used_by_solver": False,
            "professional_emission": False,
        }

    minimum = min(voltages)
    dip_pu = pre_start_min_voltage_pu - minimum
    dip_pct = (
        dip_pu / pre_start_min_voltage_pu * 100.0
        if pre_start_min_voltage_pu > 0
        else None
    )
    criterion = float(study["minimum_terminal_voltage_pu"])
    passed = minimum >= criterion
    return {
        **deepcopy(point),
        "ok": True,
        "status": "PASS" if passed else "FAIL",
        "voltage_pu_by_phase": voltages,
        "minimum_voltage_pu": minimum,
        "voltage_dip_pu": dip_pu,
        "voltage_dip_pct": dip_pct,
        "starting_demand": demand,
        "criterion_passed": passed,
        "elapsed_time_used_by_solver": False,
        "isolated_context_per_point": True,
        "professional_emission": False,
    }


def _execute_profile(
    *,
    base_model: dict[str, Any],
    motors: list[dict[str, Any]],
    bus_bases: dict[str, float],
    motor: dict[str, Any],
    study: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    pre = _pre_start_state(
        base_model=base_model,
        motors=motors,
        bus_bases=bus_bases,
        motor=motor,
    )
    if not pre["converged"] or not pre["voltage_pu_by_phase"]:
        return {
            "profile_id": profile["id"],
            "study_id": study["id"],
            "motor_id": motor["id"],
            "status": "PRE_START_SOLUTION_NOT_READY",
            "ok": False,
            "professional_emission": False,
        }

    point_results = [
        _execute_point(
            base_model=base_model,
            motors=motors,
            bus_bases=bus_bases,
            motor=motor,
            study=study,
            profile=profile,
            point=point,
            pre_start_min_voltage_pu=float(pre["minimum_voltage_pu"]),
        )
        for point in profile["points"]
    ]

    valid_points = [item for item in point_results if item.get("ok") is True]
    all_solved = len(valid_points) == len(point_results) and bool(point_results)
    worst = min(valid_points, key=lambda item: item["minimum_voltage_pu"]) if valid_points else None
    criterion = float(study["minimum_terminal_voltage_pu"])
    all_pass = all_solved and all(
        item["minimum_voltage_pu"] >= criterion for item in valid_points
    )

    return {
        "profile_id": profile["id"],
        "study_id": study["id"],
        "motor_id": motor["id"],
        "status": "PASS" if all_pass else ("FAIL" if all_solved else "PARTIAL"),
        "ok": all_solved,
        "engine": "OpenDSS",
        "isolation_mode": motor_starting_static.ISOLATION_MODE,
        "method": "DECLARED_STATIC_PROFILE_POINTS",
        "profile_reference": profile["profile_reference"],
        "current_basis": profile["current_basis"],
        "power_factor_basis": profile["power_factor_basis"],
        "pre_start_converged": pre["converged"],
        "pre_start_voltage_pu_by_phase": pre["voltage_pu_by_phase"],
        "pre_start_min_voltage_pu": pre["minimum_voltage_pu"],
        "running_load_disabled": pre["running_load_disabled"],
        "points": point_results,
        "worst_point": deepcopy(worst),
        "criterion": {
            "minimum_terminal_voltage_pu": criterion,
            "reference": study["criterion_reference"],
            "all_points_pass": all_pass,
            "universal_normative_claim": False,
        },
        "profile_semantics": PROFILE_SEMANTICS,
        "elapsed_time_used_by_solver": False,
        "interpolation_performed": False,
        "dynamic_integration_performed": False,
        "torque_calculation_performed": False,
        "automatic_profile_generation": False,
        "automatic_starting_current_derivation": False,
        "professional_emission": False,
    }


def ejecutar_perfiles(
    manifest: dict[str, Any],
    profile_package: dict[str, Any],
) -> dict[str, Any]:
    """Ejecuta cada punto como estado algebraico independiente y aislado."""
    parent_before = motor_starting_static._parent_signature()
    validation = validar_perfiles(deepcopy(manifest), deepcopy(profile_package))
    if validation.get("ready_for_execution") is not True:
        parent_after = motor_starting_static._parent_signature()
        return {
            "schema": SCHEMA_EXECUTION,
            "execution_status": "BLOCKED_BY_P13C_VALIDATION",
            "validation": validation,
            "results": [],
            "parent_context_mutated": parent_after != parent_before,
            "electrical_calculation_performed": False,
            "motor_starting_calculation_performed": False,
            "elapsed_time_used_by_solver": False,
            "interpolation_performed": False,
            "dynamic_integration_performed": False,
            "professional_emission": False,
        }

    readiness = motor_starting_static.evaluar_readiness(deepcopy(manifest))
    if readiness.get("ready_for_execution") is not True:
        parent_after = motor_starting_static._parent_signature()
        return {
            "schema": SCHEMA_EXECUTION,
            "execution_status": "BLOCKED_BY_P13B_READINESS",
            "validation": validation,
            "p13b_readiness": readiness,
            "results": [],
            "parent_context_mutated": parent_after != parent_before,
            "electrical_calculation_performed": False,
            "motor_starting_calculation_performed": False,
            "elapsed_time_used_by_solver": False,
            "interpolation_performed": False,
            "dynamic_integration_performed": False,
            "professional_emission": False,
        }

    intake = validation["p13a"]
    motors = deepcopy(intake.get("motors") or [])
    motor_map = _motor_map(intake)
    study_map = _study_map(intake)
    base_model = deepcopy(manifest["base_model"])
    preflight, bus_bases = motor_starting_static._preflight_base(base_model, motors)
    if preflight:
        raise RuntimeError("P13CEXEC000: readiness y ejecución discrepan en preflight.")

    results: list[dict[str, Any]] = []
    for profile in validation["profiles"]:
        study = study_map[profile["study_id"].lower()]
        motor = motor_map[str(study["motor_id"]).lower()]
        results.append(_execute_profile(
            base_model=base_model,
            motors=motors,
            bus_bases=bus_bases,
            motor=motor,
            study=study,
            profile=profile,
        ))

    parent_after = motor_starting_static._parent_signature()
    if parent_after != parent_before:
        raise RuntimeError(
            "P13CEXEC001: perfiles aislados modificaron el contexto DSS/Workspace padre."
        )

    all_ok = bool(results) and all(item.get("ok") is True for item in results)
    return {
        "schema": SCHEMA_EXECUTION,
        "execution_status": STATUS_COMPLETED if all_ok else STATUS_PARTIAL,
        "validation": validation,
        "p13b_readiness": readiness,
        "results": results,
        "profile_count": len(results),
        "engine": "OpenDSS",
        "isolation_mode": motor_starting_static.ISOLATION_MODE,
        "point_isolation": "FRESH_OPENDSS_NEW_CONTEXT_PER_POINT",
        "parent_context_mutated": False,
        "parent_workspace_mutated": False,
        "electrical_calculation_performed": bool(results),
        "motor_starting_calculation_performed": bool(results),
        "elapsed_time_used_by_solver": False,
        "interpolation_performed": False,
        "dynamic_integration_performed": False,
        "torque_calculation_performed": False,
        "automatic_profile_generation": False,
        "automatic_starting_current_derivation": False,
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
    }
