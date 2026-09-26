"""P13C — perfiles explícitos de arranque evaluados como puntos estáticos.

P13C extiende P13B sin afirmar dinámica electromecánica. Un perfil es una
secuencia temporal declarada de corriente supply-side RMS y factor de potencia
de desplazamiento fundamental. Cada punto se resuelve algebraicamente en
OpenDSS; el tiempo ordena los puntos pero no integra aceleración ni torque.

Reglas:
- el perfil referencia un estudio P13A existente;
- el primer punto debe estar en t=0 y coincidir con I/PF iniciales P13A;
- los tiempos deben ser estrictamente crecientes;
- no hay interpolación, derivación de corriente ni síntesis de rampas;
- la ejecución ocurre en dss.NewContext() y preserva el contexto padre.
"""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from opendssdirect import dss

from . import core, motor_starting_intake, motor_starting_static, workspace_state

SCHEMA_CONTRACT = "MCP_ELECTRICO_P13C_MOTOR_STARTING_PROFILE_CONTRACT_V1"
SCHEMA_EXECUTION = "MCP_ELECTRICO_P13C_MOTOR_STARTING_PROFILE_EXECUTION_V1"

STATUS_READY = "READY_FOR_STATIC_STARTING_PROFILE"
STATUS_BLOCKED = "BLOCKED_STARTING_PROFILE_INPUTS"
STATUS_COMPLETED = "STATIC_STARTING_PROFILE_COMPLETED"
STATUS_PARTIAL = "STATIC_STARTING_PROFILE_PARTIAL"

CURRENT_BASIS = "SUPPLY_LINE_RMS_AT_RATED_VOLTAGE"
PF_BASIS = "FUNDAMENTAL_DISPLACEMENT"


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
        "profile_semantics": "DECLARED_STATIC_OPERATING_POINTS_ORDERED_BY_TIME",
        "current_basis": CURRENT_BASIS,
        "power_factor_basis": PF_BASIS,
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
    """Valida perfiles sin Solve ni materialización del modelo eléctrico."""
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
            "P13C requiere que el contrato P13A esté READY antes de admitir perfiles.",
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

    reference = str(profile_package.get("source_reference") or "").strip()
    if not reference:
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

        if not profile_id:
            issues.append(_issue("P13C007", f"{path}.id", "El perfil requiere id."))
        elif profile_id.lower() in seen_profile_ids:
            issues.append(_issue("P13C008", f"{path}.id", "ID de perfil duplicado."))
        else:
            seen_profile_ids.add(profile_id.lower())

        if not study_id:
            issues.append(_issue("P13C009", f"{path}.study_id", "study_id es requerido."))
            study = None
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

        points = raw.get("points")
        if not isinstance(points, list) or len(points) < 2:
            issues.append(_issue(
                "P13C013",
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
                issues.append(_issue("P13C014", ppath, "Cada punto debe ser un objeto."))
                continue

            point_id = str(point.get("id") or "").strip()
            elapsed = _number(point.get("elapsed_time_s"))
            current = _number(point.get("starting_current_a"))
            pf = _number(point.get("starting_power_factor"))

            if not point_id:
                issues.append(_issue("P13C015", f"{ppath}.id", "Cada punto requiere id."))
            elif point_id.lower() in seen_point_ids:
                issues.append(_issue("P13C023", f"{ppath}.id", "ID de punto duplicado dentro del perfil."))
            else:
                seen_point_ids.add(point_id.lower())
            if elapsed is None or elapsed < 0:
                issues.append(_issue(
                    "P13C016",
                    f"{ppath}.elapsed_time_s",
                    "elapsed_time_s debe ser finito y >=0.",
                ))
            elif previous_time is not None and elapsed <= previous_time:
                issues.append(_issue(
                    "P13C017",
                    f"{ppath}.elapsed_time_s",
                    "Los tiempos deben ser estrictamente crecientes.",
                ))
            if elapsed is not None and elapsed >= 0:
                previous_time = elapsed

            if not _positive(current):
                issues.append(_issue(
                    "P13C018",
                    f"{ppath}.starting_current_a",
                    "starting_current_a debe ser >0.",
                ))
            if pf is None or not (0 < pf <= 1):
                issues.append(_issue(
                    "P13C019",
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
                    "P13C020",
                    f"{path}.points[0].elapsed_time_s",
                    "El primer punto del perfil debe estar en t=0.",
                ))
            if motor is not None:
                expected_i = float(motor["starting_current_a"])
                expected_pf = float(motor["starting_power_factor"])
                actual_i = first.get("starting_current_a")
                actual_pf = first.get("starting_power_factor")
                if actual_i is None or abs(float(actual_i) - expected_i) > 1e-9:
                    issues.append(_issue(
                        "P13C021",
                        f"{path}.points[0].starting_current_a",
                        "El primer punto debe coincidir con starting_current_a de P13A; no se elige entre dos valores.",
                    ))
                if actual_pf is None or abs(float(actual_pf) - expected_pf) > 1e-12:
                    issues.append(_issue(
                        "P13C022",
                        f"{path}.points[0].starting_power_factor",
                        "El primer punto debe coincidir con starting_power_factor de P13A.",
                    ))

        normalized.append({
            "id": profile_id,
            "study_id": study_id,
            "profile_reference": profile_reference,
            "current_basis": CURRENT_BASIS,
            "power_factor_basis": PF_BASIS,
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
        "dynamic_integration_performed": False,
        "automatic_profile_generation": False,
        "automatic_starting_current_derivation": False,
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
    }


def _load_name(profile_id: str) -> str:
    return "p13c_" + motor_starting_static._safe_element_suffix(profile_id)


def _point_demand(motor: dict[str, Any], point: dict[str, Any]) -> dict[str, float]:
    local = dict(motor)
    local["starting_current_a"] = float(point["starting_current_a"])
    local["starting_power_factor"] = float(point["starting_power_factor"])
    return motor_starting_static._equivalent_starting_demand(local)


def _execute_profile(
    *,
    master_file: Path,
    motor: dict[str, Any],
    study: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    engine = dss.NewContext()
    engine.Basic.AllowChangeDir(False)
    engine("Clear")
    engine(f'Redirect "{master_file}"')

    running = str(motor.get("running_load_element_id") or "").strip()
    if motor.get("base_model_includes_running_motor") is True and running:
        if not engine.Circuit.SetActiveElement(running):
            return {
                "profile_id": profile["id"],
                "study_id": study["id"],
                "motor_id": motor["id"],
                "status": "RUNNING_LOAD_NOT_FOUND_IN_ISOLATED_MODEL",
                "ok": False,
                "professional_emission": False,
            }
        engine(f"Edit {running} enabled=no")

    engine("Solve")
    pre_converged = bool(engine.Solution.Converged())
    pre_voltages = motor_starting_static._bus_voltage_pu(engine, motor["bus"])
    if not pre_converged or not pre_voltages:
        return {
            "profile_id": profile["id"],
            "study_id": study["id"],
            "motor_id": motor["id"],
            "status": "PRE_START_SOLUTION_NOT_READY",
            "ok": False,
            "professional_emission": False,
        }

    name = _load_name(profile["id"])
    point_results: list[dict[str, Any]] = []
    created = False
    for point in profile["points"]:
        demand = _point_demand(motor, point)
        if not created:
            engine(
                " ".join([
                    f"New Load.{name}",
                    f"Bus1={motor['bus']}",
                    "Phases=3",
                    f"kV={float(motor['kv_ll'])}",
                    f"kW={demand['active_kw']}",
                    f"kvar={demand['reactive_kvar']}",
                    f"Conn={motor['connection']}",
                    f"Model={motor_starting_static.LOAD_MODEL}",
                    "Status=Fixed",
                    f"Vminpu={motor_starting_static.MODEL_VMIN_PU}",
                    f"Vmaxpu={motor_starting_static.MODEL_VMAX_PU}",
                ])
            )
            created = True
        else:
            engine(
                f"Edit Load.{name} kW={demand['active_kw']} kvar={demand['reactive_kvar']}"
            )

        engine("Solve")
        converged = bool(engine.Solution.Converged())
        voltages = motor_starting_static._bus_voltage_pu(engine, motor["bus"])
        if not converged or not voltages:
            point_results.append({
                **deepcopy(point),
                "ok": False,
                "status": "POINT_SOLUTION_NOT_READY",
                "starting_demand": demand,
                "professional_emission": False,
            })
            continue

        minimum = min(voltages)
        criterion = float(study["minimum_terminal_voltage_pu"])
        passed = minimum >= criterion
        point_results.append({
            **deepcopy(point),
            "ok": True,
            "status": "PASS" if passed else "FAIL",
            "voltage_pu_by_phase": voltages,
            "minimum_voltage_pu": minimum,
            "starting_demand": demand,
            "criterion_passed": passed,
            "professional_emission": False,
        })

    valid_points = [item for item in point_results if item.get("ok") is True]
    all_solved = len(valid_points) == len(point_results) and bool(point_results)
    worst = min(valid_points, key=lambda item: item["minimum_voltage_pu"]) if valid_points else None
    criterion = float(study["minimum_terminal_voltage_pu"])
    all_pass = all_solved and all(item["minimum_voltage_pu"] >= criterion for item in valid_points)

    return {
        "profile_id": profile["id"],
        "study_id": study["id"],
        "motor_id": motor["id"],
        "status": "PASS" if all_pass else ("FAIL" if all_solved else "PARTIAL"),
        "ok": all_solved,
        "engine": "OpenDSS",
        "method": "DECLARED_STATIC_PROFILE_POINTS",
        "profile_reference": profile["profile_reference"],
        "current_basis": CURRENT_BASIS,
        "power_factor_basis": PF_BASIS,
        "pre_start_converged": pre_converged,
        "pre_start_voltage_pu_by_phase": pre_voltages,
        "pre_start_min_voltage_pu": min(pre_voltages),
        "points": point_results,
        "worst_point": deepcopy(worst),
        "criterion": {
            "minimum_terminal_voltage_pu": criterion,
            "reference": study["criterion_reference"],
            "all_points_pass": all_pass,
            "universal_normative_claim": False,
        },
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
    validation = validar_perfiles(deepcopy(manifest), deepcopy(profile_package))
    if validation.get("ready_for_execution") is not True:
        return {
            "schema": SCHEMA_EXECUTION,
            "execution_status": "BLOCKED_BY_P13C_VALIDATION",
            "validation": validation,
            "results": [],
            "electrical_calculation_performed": False,
            "motor_starting_calculation_performed": False,
            "dynamic_integration_performed": False,
            "professional_emission": False,
        }

    readiness = motor_starting_static.evaluar_readiness(deepcopy(manifest))
    if readiness.get("ready_for_execution") is not True:
        return {
            "schema": SCHEMA_EXECUTION,
            "execution_status": "BLOCKED_BY_P13B_READINESS",
            "validation": validation,
            "p13b_readiness": readiness,
            "results": [],
            "electrical_calculation_performed": False,
            "motor_starting_calculation_performed": False,
            "dynamic_integration_performed": False,
            "professional_emission": False,
        }

    intake = validation["p13a"]
    motors = _motor_map(intake)
    studies = _study_map(intake)

    parent_circuit_before = str(dss.Circuit.Name() or "")
    parent_workspace_before = deepcopy(workspace_state.status())

    results: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="mcp_electrico_p13c_") as temp:
        netlist = core.obtener_netlist(str(Path(temp) / "base_netlist"))
        master = Path(netlist["directorio"]) / str(netlist.get("archivo_master") or "")
        if not master.is_file():
            return {
                "schema": SCHEMA_EXECUTION,
                "execution_status": "BASE_NETLIST_EXPORT_FAILED",
                "validation": validation,
                "p13b_readiness": readiness,
                "results": [],
                "electrical_calculation_performed": False,
                "motor_starting_calculation_performed": False,
                "professional_emission": False,
            }

        for profile in validation["profiles"]:
            study = studies[profile["study_id"].lower()]
            motor = motors[str(study["motor_id"]).lower()]
            results.append(
                _execute_profile(
                    master_file=master,
                    motor=motor,
                    study=study,
                    profile=profile,
                )
            )

    parent_circuit_after = str(dss.Circuit.Name() or "")
    parent_workspace_after = deepcopy(workspace_state.status())
    if (
        parent_circuit_after != parent_circuit_before
        or parent_workspace_after != parent_workspace_before
    ):
        raise RuntimeError(
            "P13CEXEC001: la ejecución aislada de perfiles modificó el contexto DSS/Workspace padre."
        )

    all_ok = bool(results) and all(item.get("ok") is True for item in results)
    return {
        "schema": SCHEMA_EXECUTION,
        "execution_status": STATUS_COMPLETED if all_ok else STATUS_PARTIAL,
        "validation": validation,
        "p13b_readiness": readiness,
        "results": results,
        "profile_count": len(results),
        "parent_context_mutated": False,
        "parent_workspace_mutated": False,
        "electrical_calculation_performed": bool(results),
        "motor_starting_calculation_performed": bool(results),
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
