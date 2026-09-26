"""P13D — secuencias explícitas de varios motores como estados estáticos.

P13D combina perfiles P13C sin convertirlos en una simulación dinámica. Cada
paso de secuencia se reconstruye desde el mismo netlist base y declara el estado
de cada motor participante: OFF, RUNNING o STARTING_PROFILE_POINT.

No existe transición implícita entre pasos, interpolación temporal, selección
automática de motor, generación de perfiles ni integración electromecánica.
"""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from opendssdirect import dss

from . import (
    core,
    motor_starting_profiles,
    motor_starting_static,
    workspace_state,
)

SCHEMA_CONTRACT = "MCP_ELECTRICO_P13D_MOTOR_SEQUENCE_CONTRACT_V1"
SCHEMA_EXECUTION = "MCP_ELECTRICO_P13D_MOTOR_SEQUENCE_EXECUTION_V1"

STATUS_READY = "READY_FOR_STATIC_MOTOR_SEQUENCE"
STATUS_BLOCKED = "BLOCKED_MOTOR_SEQUENCE_INPUTS"
STATUS_COMPLETED = "STATIC_MOTOR_SEQUENCE_COMPLETED"
STATUS_PARTIAL = "STATIC_MOTOR_SEQUENCE_PARTIAL"

STATE_OFF = "OFF"
STATE_RUNNING = "RUNNING"
STATE_STARTING = "STARTING_PROFILE_POINT"
ALLOWED_STATES = {STATE_OFF, STATE_RUNNING, STATE_STARTING}


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


def _issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def obtener_contrato_p13d() -> dict[str, Any]:
    return {
        "schema": SCHEMA_CONTRACT,
        "purpose": "EXPLICIT_MULTI_MOTOR_STATIC_STARTING_SEQUENCE",
        "industry_scope": "CROSS_INDUSTRY",
        "allowed_motor_states": sorted(ALLOWED_STATES),
        "step_semantics": "INDEPENDENT_STATIC_STATE_REBUILT_FROM_BASE_MODEL",
        "minimum_motors_per_sequence": 2,
        "interpolation": False,
        "dynamic_integration": False,
        "automatic_motor_selection": False,
        "automatic_start_order": False,
        "automatic_profile_generation": False,
        "automatic_starting_current_derivation": False,
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
    }


def _motor_map(profile_validation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    intake = profile_validation.get("p13a") or {}
    return {
        str(item.get("id") or "").lower(): item
        for item in intake.get("motors") or []
        if str(item.get("id") or "").strip()
    }


def _study_map(profile_validation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    intake = profile_validation.get("p13a") or {}
    return {
        str(item.get("id") or "").lower(): item
        for item in intake.get("studies") or []
        if str(item.get("id") or "").strip()
    }


def _profile_map(profile_validation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id") or "").lower(): item
        for item in profile_validation.get("profiles") or []
        if str(item.get("id") or "").strip()
    }


def _profile_motor_id(
    profile: dict[str, Any],
    studies: dict[str, dict[str, Any]],
) -> str | None:
    study = studies.get(str(profile.get("study_id") or "").lower())
    if not study:
        return None
    return str(study.get("motor_id") or "").strip() or None


def validar_secuencias(
    manifest: dict[str, Any],
    profile_package: dict[str, Any],
    sequence_package: dict[str, Any],
) -> dict[str, Any]:
    """Valida secuencias multi-motor sin materializar ni resolver la red."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest debe ser dict.")
    if not isinstance(profile_package, dict):
        raise TypeError("profile_package debe ser dict.")
    if not isinstance(sequence_package, dict):
        raise TypeError("sequence_package debe ser dict.")

    profile_validation = motor_starting_profiles.validar_perfiles(
        deepcopy(manifest),
        deepcopy(profile_package),
    )
    issues: list[dict[str, str]] = []
    if profile_validation.get("ready_for_execution") is not True:
        issues.append(_issue(
            "P13D001",
            "profile_package",
            "P13D requiere perfiles P13C válidos antes de admitir una secuencia.",
        ))

    project_id = str((manifest.get("project") or {}).get("id") or "").strip()
    package_project = str(sequence_package.get("project_id") or "").strip()
    if not package_project:
        issues.append(_issue("P13D002", "sequence_package.project_id", "project_id es requerido."))
    elif project_id and package_project != project_id:
        issues.append(_issue(
            "P13D003",
            "sequence_package.project_id",
            "La secuencia debe pertenecer al mismo proyecto P13.",
        ))

    source_reference = str(sequence_package.get("source_reference") or "").strip()
    if not source_reference:
        issues.append(_issue(
            "P13D004",
            "sequence_package.source_reference",
            "El paquete de secuencias requiere procedencia explícita.",
        ))

    sequences = sequence_package.get("sequences")
    if not isinstance(sequences, list) or not sequences:
        issues.append(_issue(
            "P13D005",
            "sequence_package.sequences",
            "Se requiere al menos una secuencia explícita.",
        ))
        sequences = []

    motors = _motor_map(profile_validation)
    studies = _study_map(profile_validation)
    profiles = _profile_map(profile_validation)

    profile_for_motor: dict[str, str] = {}
    for key, profile in profiles.items():
        motor_id = _profile_motor_id(profile, studies)
        if motor_id:
            profile_for_motor[motor_id.lower()] = key

    normalized_sequences: list[dict[str, Any]] = []
    seen_sequence_ids: set[str] = set()

    for i, raw in enumerate(sequences):
        path = f"sequence_package.sequences[{i}]"
        if not isinstance(raw, dict):
            issues.append(_issue("P13D006", path, "Cada secuencia debe ser un objeto estructurado."))
            continue

        sequence_id = str(raw.get("id") or "").strip()
        reference = str(raw.get("sequence_reference") or "").strip()
        motor_ids_raw = raw.get("motor_ids")
        steps = raw.get("steps")

        if not sequence_id:
            issues.append(_issue("P13D007", f"{path}.id", "La secuencia requiere id."))
        elif sequence_id.lower() in seen_sequence_ids:
            issues.append(_issue("P13D008", f"{path}.id", "ID de secuencia duplicado."))
        else:
            seen_sequence_ids.add(sequence_id.lower())

        if not reference:
            issues.append(_issue(
                "P13D009",
                f"{path}.sequence_reference",
                "La secuencia requiere referencia explícita.",
            ))

        if not isinstance(motor_ids_raw, list) or len(motor_ids_raw) < 2:
            issues.append(_issue(
                "P13D010",
                f"{path}.motor_ids",
                "P13D requiere al menos dos motores explícitos por secuencia.",
            ))
            motor_ids_raw = []

        motor_ids = [str(item or "").strip() for item in motor_ids_raw]
        motor_keys = [item.lower() for item in motor_ids if item]
        if len(motor_keys) != len(motor_ids_raw) or len(set(motor_keys)) != len(motor_keys):
            issues.append(_issue(
                "P13D011",
                f"{path}.motor_ids",
                "motor_ids debe contener IDs no vacíos y únicos.",
            ))

        for j, motor_id in enumerate(motor_ids):
            key = motor_id.lower()
            motor = motors.get(key)
            if motor is None:
                issues.append(_issue(
                    "P13D012",
                    f"{path}.motor_ids[{j}]",
                    "El motor no existe en P13A.",
                ))
                continue
            if motor.get("base_model_includes_running_motor") is not True:
                issues.append(_issue(
                    "P13D013",
                    f"{path}.motor_ids[{j}]",
                    "P13D v1 requiere una carga de marcha Load.* explícita para representar RUNNING.",
                ))
            if key not in profile_for_motor:
                issues.append(_issue(
                    "P13D014",
                    f"{path}.motor_ids[{j}]",
                    "Cada motor de la secuencia requiere un perfil P13C explícito.",
                ))

        if not isinstance(steps, list) or len(steps) < 2:
            issues.append(_issue(
                "P13D015",
                f"{path}.steps",
                "Una secuencia requiere al menos dos pasos explícitos.",
            ))
            steps = []

        normalized_steps: list[dict[str, Any]] = []
        previous_time: float | None = None
        seen_step_ids: set[str] = set()

        for j, step in enumerate(steps):
            spath = f"{path}.steps[{j}]"
            if not isinstance(step, dict):
                issues.append(_issue("P13D016", spath, "Cada paso debe ser un objeto."))
                continue

            step_id = str(step.get("id") or "").strip()
            elapsed = _number(step.get("elapsed_time_s"))
            states = step.get("motor_states")

            if not step_id:
                issues.append(_issue("P13D017", f"{spath}.id", "Cada paso requiere id."))
            elif step_id.lower() in seen_step_ids:
                issues.append(_issue("P13D018", f"{spath}.id", "ID de paso duplicado."))
            else:
                seen_step_ids.add(step_id.lower())

            if elapsed is None or elapsed < 0:
                issues.append(_issue(
                    "P13D019",
                    f"{spath}.elapsed_time_s",
                    "elapsed_time_s debe ser finito y >=0.",
                ))
            elif previous_time is not None and elapsed <= previous_time:
                issues.append(_issue(
                    "P13D020",
                    f"{spath}.elapsed_time_s",
                    "Los tiempos de secuencia deben ser estrictamente crecientes.",
                ))
            if elapsed is not None and elapsed >= 0:
                previous_time = elapsed
            if j == 0 and elapsed is not None and elapsed != 0.0:
                issues.append(_issue(
                    "P13D021",
                    f"{spath}.elapsed_time_s",
                    "El primer paso de la secuencia debe estar en t=0.",
                ))

            if not isinstance(states, list):
                issues.append(_issue(
                    "P13D022",
                    f"{spath}.motor_states",
                    "motor_states debe ser una lista explícita.",
                ))
                states = []

            normalized_states: list[dict[str, Any]] = []
            state_keys: set[str] = set()
            for k, state in enumerate(states):
                mpath = f"{spath}.motor_states[{k}]"
                if not isinstance(state, dict):
                    issues.append(_issue("P13D023", mpath, "Cada estado de motor debe ser un objeto."))
                    continue

                motor_id = str(state.get("motor_id") or "").strip()
                motor_key = motor_id.lower()
                state_name = str(state.get("state") or "").strip().upper()
                profile_id = str(state.get("profile_id") or "").strip()
                point_id = str(state.get("point_id") or "").strip()

                if not motor_id or motor_key not in motor_keys:
                    issues.append(_issue(
                        "P13D024",
                        f"{mpath}.motor_id",
                        "motor_id debe pertenecer a motor_ids de la secuencia.",
                    ))
                elif motor_key in state_keys:
                    issues.append(_issue(
                        "P13D025",
                        f"{mpath}.motor_id",
                        "Cada motor debe aparecer exactamente una vez por paso.",
                    ))
                else:
                    state_keys.add(motor_key)

                if state_name not in ALLOWED_STATES:
                    issues.append(_issue(
                        "P13D026",
                        f"{mpath}.state",
                        "state debe ser OFF, RUNNING o STARTING_PROFILE_POINT.",
                    ))

                normalized_profile = None
                normalized_point = None
                if state_name == STATE_STARTING:
                    if not profile_id or not point_id:
                        issues.append(_issue(
                            "P13D027",
                            mpath,
                            "STARTING_PROFILE_POINT requiere profile_id y point_id.",
                        ))
                    else:
                        profile = profiles.get(profile_id.lower())
                        if profile is None:
                            issues.append(_issue(
                                "P13D028",
                                f"{mpath}.profile_id",
                                "profile_id no existe en P13C.",
                            ))
                        else:
                            expected_motor = _profile_motor_id(profile, studies)
                            if not expected_motor or expected_motor.lower() != motor_key:
                                issues.append(_issue(
                                    "P13D029",
                                    f"{mpath}.profile_id",
                                    "El perfil no pertenece al motor declarado en este estado.",
                                ))
                            points = {
                                str(item.get("id") or "").lower(): item
                                for item in profile.get("points") or []
                            }
                            point = points.get(point_id.lower())
                            if point is None:
                                issues.append(_issue(
                                    "P13D030",
                                    f"{mpath}.point_id",
                                    "point_id no existe dentro del perfil.",
                                ))
                            else:
                                normalized_profile = profile_id
                                normalized_point = deepcopy(point)
                elif profile_id or point_id:
                    issues.append(_issue(
                        "P13D031",
                        mpath,
                        "OFF/RUNNING no admite profile_id ni point_id.",
                    ))

                normalized_states.append({
                    "motor_id": motor_id,
                    "state": state_name,
                    "profile_id": normalized_profile,
                    "point_id": point_id if normalized_point is not None else None,
                    "point": normalized_point,
                })

            missing_states = sorted(set(motor_keys) - state_keys)
            extra_states = sorted(state_keys - set(motor_keys))
            if missing_states or extra_states or len(state_keys) != len(motor_keys):
                issues.append(_issue(
                    "P13D032",
                    f"{spath}.motor_states",
                    "Cada paso debe declarar exactamente un estado para cada motor de la secuencia.",
                ))

            normalized_steps.append({
                "id": step_id,
                "elapsed_time_s": elapsed,
                "motor_states": normalized_states,
            })

        normalized_sequences.append({
            "id": sequence_id,
            "sequence_reference": reference,
            "motor_ids": motor_ids,
            "steps": normalized_steps,
        })

    ready = not issues and bool(normalized_sequences)
    return {
        "schema": SCHEMA_CONTRACT,
        "validation_status": STATUS_READY if ready else STATUS_BLOCKED,
        "ready_for_execution": ready,
        "issues": issues,
        "issue_count": len(issues),
        "sequences": normalized_sequences,
        "p13c": profile_validation,
        "electrical_calculation_performed": False,
        "motor_starting_calculation_performed": False,
        "dynamic_integration_performed": False,
        "automatic_motor_selection": False,
        "automatic_start_order": False,
        "automatic_profile_generation": False,
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
    }


def _starting_demand(motor: dict[str, Any], point: dict[str, Any]) -> dict[str, float]:
    local = dict(motor)
    local["starting_current_a"] = float(point["starting_current_a"])
    local["starting_power_factor"] = float(point["starting_power_factor"])
    return motor_starting_static._equivalent_starting_demand(local)


def _execute_step(
    *,
    master_file: Path,
    step: dict[str, Any],
    motors: dict[str, dict[str, Any]],
    studies: dict[str, dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    engine = dss.NewContext()
    engine.Basic.AllowChangeDir(False)
    engine("Clear")
    engine(f'Redirect "{master_file}"')

    criterion_evaluations: list[dict[str, Any]] = []
    applied_states: list[dict[str, Any]] = []

    for state in step["motor_states"]:
        motor = motors[state["motor_id"].lower()]
        running = str(motor.get("running_load_element_id") or "").strip()
        if running and not engine.Circuit.SetActiveElement(running):
            return {
                "step_id": step["id"],
                "elapsed_time_s": step["elapsed_time_s"],
                "status": "RUNNING_LOAD_NOT_FOUND",
                "ok": False,
                "motor_id": motor["id"],
                "professional_emission": False,
            }

        if state["state"] in {STATE_OFF, STATE_STARTING}:
            engine(f"Edit {running} enabled=no")
        elif state["state"] == STATE_RUNNING:
            engine(f"Edit {running} enabled=yes")

        applied = {
            "motor_id": motor["id"],
            "state": state["state"],
            "running_load_element_id": running,
            "profile_id": state.get("profile_id"),
            "point_id": state.get("point_id"),
        }

        if state["state"] == STATE_STARTING:
            profile = profiles[str(state["profile_id"]).lower()]
            study = studies[str(profile["study_id"]).lower()]
            point = state["point"]
            demand = _starting_demand(motor, point)
            suffix = motor_starting_static._safe_element_suffix(
                f"{step['id']}_{motor['id']}"
            )
            engine(
                " ".join([
                    f"New Load.p13d_{suffix}",
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
            applied["starting_demand"] = demand
            applied["starting_current_a"] = point["starting_current_a"]
            applied["starting_power_factor"] = point["starting_power_factor"]
            applied["criterion"] = {
                "minimum_terminal_voltage_pu": float(study["minimum_terminal_voltage_pu"]),
                "reference": study["criterion_reference"],
            }

        applied_states.append(applied)

    engine("Solve")
    converged = bool(engine.Solution.Converged())
    if not converged:
        return {
            "step_id": step["id"],
            "elapsed_time_s": step["elapsed_time_s"],
            "status": "STEP_SOLUTION_NOT_READY",
            "ok": False,
            "converged": False,
            "applied_states": applied_states,
            "professional_emission": False,
        }

    motor_voltages: list[dict[str, Any]] = []
    for state in step["motor_states"]:
        motor = motors[state["motor_id"].lower()]
        voltages = motor_starting_static._bus_voltage_pu(engine, motor["bus"])
        minimum = min(voltages) if voltages else None
        motor_voltages.append({
            "motor_id": motor["id"],
            "state": state["state"],
            "bus": motor["bus"],
            "voltage_pu_by_phase": voltages,
            "minimum_voltage_pu": minimum,
        })

        if state["state"] == STATE_STARTING:
            profile = profiles[str(state["profile_id"]).lower()]
            study = studies[str(profile["study_id"]).lower()]
            criterion = float(study["minimum_terminal_voltage_pu"])
            passed = minimum is not None and minimum >= criterion
            criterion_evaluations.append({
                "motor_id": motor["id"],
                "study_id": study["id"],
                "profile_id": state["profile_id"],
                "point_id": state["point_id"],
                "minimum_voltage_pu": minimum,
                "criterion_minimum_voltage_pu": criterion,
                "margin_pu": (minimum - criterion) if minimum is not None else None,
                "passed": passed,
                "reference": study["criterion_reference"],
            })

    applicable = bool(criterion_evaluations)
    all_pass = applicable and all(item["passed"] for item in criterion_evaluations)
    any_fail = any(not item["passed"] for item in criterion_evaluations)
    status = "FAIL" if any_fail else ("PASS" if all_pass else "OBSERVED")

    minima = [
        item["minimum_voltage_pu"]
        for item in motor_voltages
        if item["minimum_voltage_pu"] is not None
    ]

    return {
        "step_id": step["id"],
        "elapsed_time_s": step["elapsed_time_s"],
        "status": status,
        "ok": True,
        "converged": True,
        "applied_states": applied_states,
        "motor_terminal_voltages": motor_voltages,
        "minimum_participant_voltage_pu": min(minima) if minima else None,
        "criterion_evaluations": criterion_evaluations,
        "criterion_status": (
            "PASS" if all_pass else ("FAIL" if any_fail else "NOT_APPLICABLE")
        ),
        "interpolation_performed": False,
        "dynamic_integration_performed": False,
        "professional_emission": False,
    }


def ejecutar_secuencias(
    manifest: dict[str, Any],
    profile_package: dict[str, Any],
    sequence_package: dict[str, Any],
) -> dict[str, Any]:
    validation = validar_secuencias(
        deepcopy(manifest),
        deepcopy(profile_package),
        deepcopy(sequence_package),
    )
    if validation.get("ready_for_execution") is not True:
        return {
            "schema": SCHEMA_EXECUTION,
            "execution_status": "BLOCKED_BY_P13D_VALIDATION",
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

    p13c = validation["p13c"]
    motors = _motor_map(p13c)
    studies = _study_map(p13c)
    profiles = _profile_map(p13c)

    parent_circuit_before = str(dss.Circuit.Name() or "")
    parent_workspace_before = deepcopy(workspace_state.status())

    sequence_results: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="mcp_electrico_p13d_") as temp:
        netlist = core.obtener_netlist(str(Path(temp) / "base_netlist"))
        master = Path(netlist["directorio"]) / str(netlist.get("archivo_master") or "")
        if not master.is_file():
            return {
                "schema": SCHEMA_EXECUTION,
                "execution_status": "BASE_NETLIST_EXPORT_FAILED",
                "validation": validation,
                "results": [],
                "electrical_calculation_performed": False,
                "motor_starting_calculation_performed": False,
                "professional_emission": False,
            }

        for sequence in validation["sequences"]:
            steps = [
                _execute_step(
                    master_file=master,
                    step=step,
                    motors=motors,
                    studies=studies,
                    profiles=profiles,
                )
                for step in sequence["steps"]
            ]
            solved = bool(steps) and all(item.get("ok") is True for item in steps)
            any_fail = any(item.get("criterion_status") == "FAIL" for item in steps)
            applicable = [
                evaluation
                for step in steps
                for evaluation in step.get("criterion_evaluations") or []
            ]
            worst = (
                min(
                    applicable,
                    key=lambda item: (
                        item["margin_pu"]
                        if item.get("margin_pu") is not None
                        else float("inf")
                    ),
                )
                if applicable
                else None
            )
            sequence_results.append({
                "sequence_id": sequence["id"],
                "sequence_reference": sequence["sequence_reference"],
                "status": (
                    "PARTIAL" if not solved else ("FAIL" if any_fail else "PASS")
                ),
                "ok": solved,
                "motor_ids": sequence["motor_ids"],
                "steps": steps,
                "worst_starting_criterion": deepcopy(worst),
                "static_state_rebuild_per_step": True,
                "interpolation_performed": False,
                "dynamic_integration_performed": False,
                "automatic_motor_selection": False,
                "automatic_start_order": False,
                "professional_emission": False,
            })

    parent_circuit_after = str(dss.Circuit.Name() or "")
    parent_workspace_after = deepcopy(workspace_state.status())
    if (
        parent_circuit_after != parent_circuit_before
        or parent_workspace_after != parent_workspace_before
    ):
        raise RuntimeError(
            "P13DEXEC001: la ejecución aislada de secuencias modificó el contexto DSS/Workspace padre."
        )

    all_solved = bool(sequence_results) and all(
        item.get("ok") is True for item in sequence_results
    )
    return {
        "schema": SCHEMA_EXECUTION,
        "execution_status": STATUS_COMPLETED if all_solved else STATUS_PARTIAL,
        "validation": validation,
        "p13b_readiness": readiness,
        "results": sequence_results,
        "sequence_count": len(sequence_results),
        "parent_context_mutated": False,
        "parent_workspace_mutated": False,
        "electrical_calculation_performed": bool(sequence_results),
        "motor_starting_calculation_performed": bool(sequence_results),
        "static_state_rebuild_per_step": True,
        "interpolation_performed": False,
        "dynamic_integration_performed": False,
        "torque_calculation_performed": False,
        "automatic_motor_selection": False,
        "automatic_start_order": False,
        "automatic_profile_generation": False,
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
    }
