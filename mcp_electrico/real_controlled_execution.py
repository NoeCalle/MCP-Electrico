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
from hashlib import sha256
import json
from typing import Any

from . import (
    ampacity,
    execution_quality,
    iec60909_single_phase_ground,
    iec60909_suite,
    real_integrated_readiness,
    studies,
    workspace_state,
)

SCHEMA = "MCP_ELECTRICO_P8D1_CONTROLLED_EXECUTION_V1"
STATUS_BLOCKED = "BLOCKED_BY_READINESS"
STATUS_FAILED_RESULT = "CONTROLLED_EXECUTION_FAILED_INVALID_RESULT"
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


def _record_failed_scope(scope, result):
    names = {
        POWER_FLOW: ["powerflow", "flow"], VOLTAGE_DROP: ["powerflow", "flow", "voltage_drop"],
        AMPACITY: ["ampacity"], SC_3PH: ["iec60909_3ph", "iec60909_3ph_targets"],
        SC_1PH: ["iec60909_1ph_ground", "iec60909_1ph_ground_targets"],
    }
    existing = workspace_state.status().get("studies", {})
    for name in names[scope]:
        if name in existing:
            failed = execution_quality.diagnostic_payload(existing[name]["result"])
            failed["resultados_validos"] = False
            workspace_state.record_study(name, failed, action="p8d1_invalid_result")
    workspace_state.record_study("controlled_execution_failure", result, action="p8d1_invalid_result")
    workspace_state.record_electrical_error("P8D1: cálculo inválido; cadena integral detenida.")


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
        blocked_workspace = workspace_state.reset_for_circuit("p8d1_readiness_blocked")
        return {
            "schema": SCHEMA,
            "execution_status": STATUS_BLOCKED,
            "requested_scopes": requested,
            "executed_scopes": [],
            "pending_scopes": requested,
            "readiness": readiness,
            "results": {},
            "model_revision": blocked_workspace.get("model_revision"),
            "workspace_studies": [],
            "electrical_calculation_performed": False,
            "ampacity_calculation_performed": False,
            "short_circuit_calculation_performed": False,
            "protection_calculation_performed": False,
            "automatic_dispatch": False,
            "automatic_fault_binding": False,
            "crosscheck": False,
            "professional_emission": False,
            "next_gate": "P8C5_READINESS_REPAIR",
        }

    results: dict[str, Any] = {}
    executed: list[str] = []

    manifest_sha = sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode("utf8")).hexdigest()
    runners = ((POWER_FLOW, _execute_power_flow),
               (VOLTAGE_DROP, lambda: _execute_voltage_drop(manifest)),
               (AMPACITY, _execute_ampacity),
               (SC_3PH, lambda: _execute_3ph(manifest)),
               (SC_1PH, lambda: _execute_1ph_ground(manifest)))
    for scope, runner in runners:
        if scope not in requested:
            continue
        try:
            raw = runner()
            issues = execution_quality.scope_issues(scope, raw, manifest)
            if workspace_state.status().get("model_revision") != revision_before:
                issues.append({"code": "EXECUTION_REVISION_CHANGED", "scope": scope,
                               "message": "La revisión cambió durante el cálculo."})
        except Exception as exc:
            raw = {"status": "EXECUTOR_EXCEPTION", "error": f"{type(exc).__name__}: {exc}"}
            issues = [{"code": "EXECUTION_EXCEPTION", "scope": scope, "message": raw["error"]}]
        if issues:
            failure = {"scope": scope, "resultados_validos": False, "issues": issues}
            _record_failed_scope(scope, failure)
            return {
                "schema": SCHEMA, "execution_status": STATUS_FAILED_RESULT,
                "resultados_validos": False, "failed_scope": scope,
                "requested_scopes": requested, "executed_scopes": executed,
                "attempted_scopes": executed + [scope],
                "pending_scopes": [s for s in requested if s not in executed],
                "results": results, "failed_result": execution_quality.diagnostic_payload(raw), "issues": issues,
                "readiness": readiness, "manifest_sha256": manifest_sha,
                "model_revision": workspace_state.status().get("model_revision"),
                "workspace_studies": sorted(workspace_state.status().get("studies", {})),
                "electrical_calculation_performed": True,
                "ampacity_calculation_performed": scope == AMPACITY or AMPACITY in executed,
                "short_circuit_calculation_performed": scope in {SC_3PH, SC_1PH} or bool({SC_3PH, SC_1PH} & set(executed)),
                "protection_calculation_performed": False, "automatic_dispatch": False,
                "automatic_fault_binding": False, "crosscheck": False,
                "professional_emission": False, "next_gate": "P8D1_REPAIR_INVALID_RESULT",
            }
        results[scope] = raw
        executed.append(scope)

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
        "resultados_validos": True,
        "manifest_sha256": manifest_sha,
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
