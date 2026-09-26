"""P12B — estudio estático de arranque de motor en contexto OpenDSS aislado.

P12B consume el contrato P12A y calcula únicamente el impacto estático inicial
sobre la tensión usando una impedancia equivalente derivada de corriente de
arranque y factor de potencia explícitos.

No calcula aceleración, torque, deslizamiento, tiempo de arranque ni control
interno de soft starters/VFD. El método de arranque no genera parámetros
eléctricos: la red ve exclusivamente los datos de arranque declarados.

La ejecución del estado de arranque ocurre en dss.NewContext(). El modelo
padre se materializa una vez para producir el netlist base, pero cada estudio
temporal se resuelve en un contexto DSS independiente.
"""

from __future__ import annotations

from copy import deepcopy
from math import sqrt
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from typing import Any

from opendssdirect import dss

from . import (
    core,
    motor_starting_intake,
    real_model_materializer,
    workspace_state,
)

SCHEMA_READINESS = "MCP_ELECTRICO_P12B_MOTOR_STARTING_READINESS_V1"
SCHEMA_EXECUTION = "MCP_ELECTRICO_P12B_MOTOR_STARTING_STATIC_V1"

STATUS_BLOCKED_INTAKE = "BLOCKED_BY_P12A_INTAKE"
STATUS_BLOCKED_BASE = "BLOCKED_BY_BASE_MODEL"
STATUS_BLOCKED_DEFAULTS = "BLOCKED_BY_BASE_ENGINE_DEFAULTS"
STATUS_READY = "READY_FOR_STATIC_MOTOR_STARTING"
STATUS_COMPLETED = "STATIC_MOTOR_STARTING_COMPLETED"
STATUS_PARTIAL = "STATIC_MOTOR_STARTING_PARTIAL"

ENGINE = "OpenDSS"
MODEL = "EQUIVALENT_STARTING_IMPEDANCE"
LOAD_MODEL = 2
MODEL_VMIN_PU = 0.01
MODEL_VMAX_PU = 2.0


def _issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


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


def _bus_voltage_pu(engine: Any, bus: str) -> list[float]:
    if not engine.Circuit.SetActiveBus(str(bus)):
        return []
    raw = engine.Bus.puVmagAngle()
    return [float(value) for value in raw[0::2]]


def _safe_element_suffix(raw: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", str(raw or "").strip())
    text = text.strip("_")
    return text or "motor_start"


def _equivalent_starting_demand(motor: dict[str, Any]) -> dict[str, float]:
    kv_ll = float(motor["kv_ll"])
    current_a = float(motor["starting_current_a"])
    pf = float(motor["starting_power_factor"])
    apparent_kva = sqrt(3.0) * kv_ll * current_a
    active_kw = apparent_kva * pf
    reactive_kvar = apparent_kva * sqrt(max(1.0 - pf * pf, 0.0))
    return {
        "apparent_kva": apparent_kva,
        "active_kw": active_kw,
        "reactive_kvar": reactive_kvar,
    }


def evaluar_readiness(manifest: dict[str, Any]) -> dict[str, Any]:
    """Materializa el modelo base sin Solve y verifica el gate P12B."""
    intake = motor_starting_intake.evaluar_admision_motor(deepcopy(manifest))
    base = {
        "schema": SCHEMA_READINESS,
        "industry_scope": "CROSS_INDUSTRY",
        "engine": ENGINE,
        "method": MODEL,
        "electrical_calculation_performed": False,
        "motor_starting_calculation_performed": False,
        "dynamic_acceleration_calculation_performed": False,
        "automatic_starting_current_derivation": False,
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
    }
    if intake.get("ready_for_static_starting_build") is not True:
        return {
            **base,
            "readiness_status": STATUS_BLOCKED_INTAKE,
            "ready_for_execution": False,
            "issues": deepcopy(intake.get("issues") or []),
            "p12a": intake,
        }

    base_model = deepcopy(manifest["base_model"])
    materialized = real_model_materializer.materializar_modelo(base_model)
    if materialized.get("materializer_status") != real_model_materializer.STATUS_BUILT:
        return {
            **base,
            "readiness_status": STATUS_BLOCKED_BASE,
            "ready_for_execution": False,
            "issues": deepcopy(materialized.get("issues") or []),
            "p12a": intake,
            "base_model": materialized,
        }

    retained = deepcopy(materialized.get("engine_defaults_retained") or [])
    if retained:
        return {
            **base,
            "readiness_status": STATUS_BLOCKED_DEFAULTS,
            "ready_for_execution": False,
            "issues": [
                _issue(
                    "P12B001",
                    str(item.get("path") or "base_model"),
                    "P12B requiere cerrar defaults retenidos relevantes antes del estudio: "
                    + str(item.get("note") or ""),
                )
                for item in retained
            ],
            "p12a": intake,
            "base_model": materialized,
        }

    issues: list[dict[str, str]] = []
    loads = _base_load_map(base_model)
    for index, motor in enumerate(intake.get("motors") or []):
        running = str(motor.get("running_load_element_id") or "").lower()
        if motor.get("base_model_includes_running_motor") is True and running:
            load = loads.get(running)
            if not load:
                issues.append(_issue(
                    "P12B010",
                    f"motors[{index}].running_load_element_id",
                    "La carga de marcha no existe después de normalizar el modelo base.",
                ))
                continue
            if int(float(load.get("phases") or 0)) != int(motor["phases"]):
                issues.append(_issue(
                    "P12B011",
                    f"motors[{index}].running_load_element_id",
                    "La carga de marcha y el motor deben tener el mismo número de fases.",
                ))
            if abs(float(load.get("kv") or 0.0) - float(motor["kv_ll"])) > 1e-9:
                issues.append(_issue(
                    "P12B012",
                    f"motors[{index}].running_load_element_id",
                    "La tensión de la carga de marcha no coincide con kv_ll del motor.",
                ))

    return {
        **base,
        "readiness_status": STATUS_READY if not issues else STATUS_BLOCKED_BASE,
        "ready_for_execution": not issues,
        "issues": issues,
        "p12a": intake,
        "base_model": materialized,
        "study_count": len(intake.get("studies") or []),
        "note": (
            "P12B readiness materializa el modelo base pero no ejecuta Solve. "
            "La simulación temporal de arranque se hará en contextos OpenDSS aislados."
        ),
    }


def _execute_one(
    *,
    master_file: Path,
    motor: dict[str, Any],
    study: dict[str, Any],
) -> dict[str, Any]:
    engine = dss.NewContext()
    engine.Basic.AllowChangeDir(False)
    engine("Clear")
    engine(f'Redirect "{master_file}"')

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
        engine(f"Edit {running} enabled=no")

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
    load_name = "p12_" + _safe_element_suffix(study["id"])
    engine(
        " ".join([
            f"New Load.{load_name}",
            f"Bus1={motor['bus']}",
            "Phases=3",
            f"kV={float(motor['kv_ll'])}",
            f"kW={demand['active_kw']}",
            f"kvar={demand['reactive_kvar']}",
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
    dip_pct = ((pre_min - start_min) / pre_min * 100.0) if pre_min > 0 else None
    criterion = float(study["minimum_terminal_voltage_pu"])
    passed = start_min >= criterion

    return {
        "study_id": study["id"],
        "motor_id": motor["id"],
        "status": "PASS" if passed else "FAIL",
        "ok": True,
        "engine": ENGINE,
        "method": MODEL,
        "starting_method_metadata": motor["starting_method"],
        "starting_data_reference": motor["starting_data_reference"],
        "pre_start_motor_state": "OFF",
        "running_load_disabled": running or None,
        "pre_start_converged": pre_converged,
        "starting_converged": start_converged,
        "pre_start_voltage_pu_by_phase": pre_voltages,
        "starting_voltage_pu_by_phase": start_voltages,
        "pre_start_min_voltage_pu": pre_min,
        "starting_min_voltage_pu": start_min,
        "voltage_dip_pct": dip_pct,
        "starting_demand": demand,
        "equivalent_load_model": {
            "opendss_load_model": LOAD_MODEL,
            "semantics": "CONSTANT_IMPEDANCE_EQUIVALENT_FROM_EXPLICIT_START_CURRENT_AND_PF",
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
    """Ejecuta todos los estudios P12A en contextos DSS independientes."""
    readiness = evaluar_readiness(deepcopy(manifest))
    if readiness.get("ready_for_execution") is not True:
        return {
            "schema": SCHEMA_EXECUTION,
            "execution_status": "BLOCKED_BY_P12B_READINESS",
            "readiness": readiness,
            "results": [],
            "electrical_calculation_performed": False,
            "motor_starting_calculation_performed": False,
            "dynamic_acceleration_calculation_performed": False,
            "automatic_starting_current_derivation": False,
            "automatic_dispatch": False,
            "crosscheck": False,
            "professional_emission": False,
        }

    intake = readiness["p12a"]
    motors = _motor_map(intake)
    parent_circuit_before = str(dss.Circuit.Name() or "")
    parent_workspace_before = deepcopy(workspace_state.status())

    results: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="mcp_electrico_p12b_") as temp:
        netlist_dir = Path(temp) / "base_netlist"
        netlist = core.obtener_netlist(str(netlist_dir))
        master_name = str(netlist.get("archivo_master") or "")
        if not master_name:
            return {
                "schema": SCHEMA_EXECUTION,
                "execution_status": "BASE_NETLIST_EXPORT_FAILED",
                "readiness": readiness,
                "results": [],
                "electrical_calculation_performed": False,
                "motor_starting_calculation_performed": False,
                "professional_emission": False,
            }
        master_file = Path(netlist["directorio"]) / master_name

        for study in intake.get("studies") or []:
            motor = motors[str(study["motor_id"]).lower()]
            results.append(_execute_one(master_file=master_file, motor=motor, study=study))

    parent_circuit_after = str(dss.Circuit.Name() or "")
    parent_workspace_after = deepcopy(workspace_state.status())
    parent_preserved = (
        parent_circuit_after == parent_circuit_before
        and parent_workspace_after == parent_workspace_before
    )

    if not parent_preserved:
        raise RuntimeError(
            "P12BEXEC001: la ejecución aislada de arranque modificó el contexto DSS/Workspace padre."
        )

    all_ok = bool(results) and all(item.get("ok") is True for item in results)
    return {
        "schema": SCHEMA_EXECUTION,
        "execution_status": STATUS_COMPLETED if all_ok else STATUS_PARTIAL,
        "readiness": readiness,
        "results": results,
        "study_count": len(results),
        "engine": ENGINE,
        "method": MODEL,
        "parent_circuit": parent_circuit_after,
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
            "P12B es una aproximación estática de impacto de red. "
            "No representa la trayectoria electromecánica completa del motor."
        ),
    }
