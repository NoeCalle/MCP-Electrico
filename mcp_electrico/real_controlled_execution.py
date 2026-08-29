"""P8D1 — primera ejecución controlada del manifiesto real.

P8C5 demuestra que el modelo y sus bindings están listos. P8D1 es el primer
bloque que ejecuta estudios del piloto real, pero mantiene una secuencia fija y
trazable: OpenDSS para P1, P3 explícito y pandapower para P4. P5 queda fuera de
este bloque porque el manifiesto todavía no declara qué bus/caso/corriente de
falla debe vincularse a cada dispositivo.

No existe despacho automático de motores, cross-check ni emisión profesional.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import (
    ampacity,
    iec60909_single_phase_ground,
    iec60909_suite,
    real_integrated_readiness,
    studies,
    workspace_state,
)

SCHEMA = "MCP_ELECTRICO_P8D1_CONTROLLED_EXECUTION_V1"
STATUS_BLOCKED = "BLOCKED_BY_READINESS"
STATUS_COMPLETED = "CONTROLLED_EXECUTION_COMPLETED"
STATUS_COMPLETED_P5_PENDING = "CONTROLLED_EXECUTION_COMPLETED_WITH_P5_PENDING"

POWER_FLOW = "POWER_FLOW"
VOLTAGE_DROP = "VOLTAGE_DROP"
AMPACITY = "AMPACITY"
SC_3PH = "IEC60909_3PH_MAX_MIN"
SC_1PH = "IEC60909_1PH_GROUND_MAX_MIN"
PROTECTION = "PROTECTION_TCC"

EXECUTABLE_SCOPES = {POWER_FLOW, VOLTAGE_DROP, AMPACITY, SC_3PH, SC_1PH}


def _requested(manifest: dict[str, Any]) -> list[str]:
    return [
        str(value).strip().upper()
        for value in manifest.get("requested_scope") or []
        if str(value).strip()
    ]


def _temperature_map(manifest: dict[str, Any]) -> dict[str, float]:
    result: dict[str, float] = {}
    for item in (manifest.get("topology") or {}).get("lines") or []:
        if not isinstance(item, dict):
            continue
        identifier = str(item.get("id") or "").strip()
        value = item.get("endtemp_min_c")
        if identifier and value is not None:
            result[identifier] = float(value)
    return result


def _fault_buses(manifest: dict[str, Any]) -> list[str]:
    return [
        str(value).strip()
        for value in (manifest.get("study_inputs") or {}).get("short_circuit_buses") or []
        if str(value).strip()
    ]


def _record_flow(flow: dict[str, Any], action: str) -> None:
    workspace_state.record_solution(flow["powerflow"], "powerflow", action=action)
    workspace_state.record_study("flow", flow, action=f"{action}:detail")


def _execute_power_flow() -> dict[str, Any]:
    flow = studies.analizar_flujo_operacion()
    _record_flow(flow, "p8d1_power_flow")
    return flow


def _execute_voltage_drop(manifest: dict[str, Any]) -> dict[str, Any]:
    limit_pct = float((manifest.get("study_inputs") or {})["voltage_drop_limit_pct"])
    raw = studies.analizar_caida_tension(limit_pct)
    flow = raw["flow"]
    _record_flow(flow, "p8d1_voltage_drop:resolve")
    result = {key: deepcopy(value) for key, value in raw.items() if key != "flow"}
    workspace_state.record_study("voltage_drop", result, action="p8d1_voltage_drop")
    return result


def _execute_ampacity() -> dict[str, Any]:
    result = ampacity.evaluar_todos()
    workspace_state.record_study("ampacity", result, action="p8d1_ampacity")
    return result


def _execute_3ph(manifest: dict[str, Any]) -> dict[str, Any]:
    temperatures = _temperature_map(manifest)
    buses = _fault_buses(manifest)
    targets: list[dict[str, Any]] = []
    for bus in buses:
        pair = iec60909_suite.ejecutar_3ph_max_min(
            bus,
            line_endtemp_degree_c=temperatures,
            calcular_ip_ith=False,
        )
        targets.append({"bus": bus, "result": pair})

    aggregate = {
        "schema": "MCP_ELECTRICO_P8D1_IEC60909_3PH_TARGETS_V1",
        "fault": "3ph",
        "targets": targets,
        "target_count": len(targets),
        "automatic_target_selection": False,
        "professional_emission": False,
    }
    # V4 histórico consume el schema por-bus. Para un único target se conserva
    # exactamente esa forma; con varios targets no se elige uno silenciosamente.
    if len(targets) == 1:
        workspace_state.record_study(
            "iec60909_3ph", targets[0]["result"], action="p8d1_iec60909_3ph"
        )
    else:
        workspace_state.record_study(
            "iec60909_3ph_targets", aggregate, action="p8d1_iec60909_3ph_targets"
        )
    return aggregate


def _execute_1ph_ground(manifest: dict[str, Any]) -> dict[str, Any]:
    temperatures = _temperature_map(manifest)
    targets: list[dict[str, Any]] = []
    for bus in _fault_buses(manifest):
        maximum = iec60909_single_phase_ground.ejecutar_1ph_ground(bus, "max")
        minimum = iec60909_single_phase_ground.ejecutar_1ph_ground(
            bus,
            "min",
            line_endtemp_degree_c=temperatures,
        )
        pair = {
            "schema": "MCP_ELECTRICO_P8D1_1PH_GROUND_PAIR_V1",
            "bus": bus,
            "max": maximum,
            "min": minimum,
            "professional_emission": False,
        }
        targets.append({"bus": bus, "result": pair})

    aggregate = {
        "schema": "MCP_ELECTRICO_P8D1_IEC60909_1PH_GROUND_TARGETS_V1",
        "fault": "1ph-ground",
        "targets": targets,
        "target_count": len(targets),
        "automatic_target_selection": False,
        "professional_emission": False,
    }
    if len(targets) == 1:
        workspace_state.record_study(
            "iec60909_1ph_ground",
            targets[0]["result"],
            action="p8d1_iec60909_1ph_ground",
        )
    else:
        workspace_state.record_study(
            "iec60909_1ph_ground_targets",
            aggregate,
            action="p8d1_iec60909_1ph_ground_targets",
        )
    return aggregate


def ejecutar_controlado(manifest: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta P1/P3/P4 solo después de un readiness P8C5 completamente verde."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest debe ser dict.")

    requested = _requested(manifest)
    readiness = real_integrated_readiness.evaluar_readiness_integral(deepcopy(manifest))
    revision_before = workspace_state.status().get("model_revision")

    if readiness.get("readiness_status") != real_integrated_readiness.STATUS_READY:
        return {
            "schema": SCHEMA,
            "execution_status": STATUS_BLOCKED,
            "requested_scopes": requested,
            "executed_scopes": [],
            "pending_scopes": requested,
            "readiness": readiness,
            "results": {},
            "model_revision": revision_before,
            "workspace_studies": [],
            "electrical_calculation_performed": False,
            "ampacity_calculation_performed": False,
            "short_circuit_calculation_performed": False,
            "protection_calculation_performed": False,
            "automatic_dispatch": False,
            "crosscheck": False,
            "professional_emission": False,
            "next_gate": "P8C5_READINESS_REPAIR",
        }

    results: dict[str, Any] = {}
    executed: list[str] = []

    # Secuencia deliberadamente fija. No se selecciona motor dinámicamente.
    if POWER_FLOW in requested:
        results[POWER_FLOW] = _execute_power_flow()
        executed.append(POWER_FLOW)

    if VOLTAGE_DROP in requested:
        results[VOLTAGE_DROP] = _execute_voltage_drop(manifest)
        executed.append(VOLTAGE_DROP)

    if AMPACITY in requested:
        results[AMPACITY] = _execute_ampacity()
        executed.append(AMPACITY)

    if SC_3PH in requested:
        results[SC_3PH] = _execute_3ph(manifest)
        executed.append(SC_3PH)

    if SC_1PH in requested:
        results[SC_1PH] = _execute_1ph_ground(manifest)
        executed.append(SC_1PH)

    pending: list[str] = []
    if PROTECTION in requested:
        pending.append(PROTECTION)
        results[PROTECTION] = {
            "status": "PENDING_P8D2_EXPLICIT_FAULT_BINDING",
            "reason": (
                "P8D1 no elige qué bus/caso/corriente IEC 60909 alimenta cada dispositivo P5. "
                "Ese vínculo debe declararse explícitamente antes de evaluar TCC/capacidad de corte."
            ),
            "protection_calculation_performed": False,
            "automatic_fault_binding": False,
            "professional_emission": False,
        }

    unknown = [scope for scope in requested if scope not in EXECUTABLE_SCOPES | {PROTECTION}]
    pending.extend(unknown)

    status = workspace_state.status()
    revision_after = status.get("model_revision")
    if revision_after != revision_before:
        raise RuntimeError(
            "P8D1EXEC001: la ejecución modificó model_revision; los estudios no pueden promoverse como vigentes."
        )

    execution_status = STATUS_COMPLETED_P5_PENDING if pending else STATUS_COMPLETED
    return {
        "schema": SCHEMA,
        "execution_status": execution_status,
        "requested_scopes": requested,
        "executed_scopes": executed,
        "pending_scopes": pending,
        "readiness": readiness,
        "results": results,
        "model_revision": revision_after,
        "workspace_studies": sorted(status.get("studies", {}).keys()),
        "electrical_calculation_performed": bool(executed),
        "ampacity_calculation_performed": AMPACITY in executed,
        "short_circuit_calculation_performed": SC_3PH in executed or SC_1PH in executed,
        "protection_calculation_performed": False,
        "automatic_dispatch": False,
        "engine_policy": {
            POWER_FLOW: "OpenDSS",
            VOLTAGE_DROP: "OpenDSS",
            AMPACITY: "P3_MCP",
            SC_3PH: "pandapower_explicit_IEC60909",
            SC_1PH: "pandapower_explicit_IEC60909_Z0",
            PROTECTION: "PENDING_P8D2",
        },
        "automatic_fault_binding": False,
        "crosscheck": False,
        "professional_emission": False,
        "next_gate": (
            "P8D2_EXPLICIT_P5_FAULT_BINDING" if PROTECTION in pending else "P8E_WORKSPACE_AND_DOSSIER"
        ),
    }
