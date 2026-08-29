"""P8C3C — readiness post-build del primer proyecto real.

Construye el modelo mediante P8C3B y, sin ejecutar estudios, determina qué
alcances solicitados tienen datos suficientes para una futura ejecución
controlada.

Principios:
- MODEL_BUILT no implica STUDY_READY;
- OpenDSS sigue siendo el backend por defecto para flujo/caída de tensión;
- P4 usa explícitamente pandapower y sus gates existentes;
- P3/P5 permanecen bloqueados hasta que un bloque posterior materialice sus
  entradas reales; P8C3C no crea conductores ni protecciones;
- no se llama a Solve, runpp ni calc_sc;
- no hay cross-check, dispatch automático ni emisión profesional.
"""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any

from . import (
    iec60909,
    iec60909_single_phase_ground,
    pandapower_engine,
    real_model_materializer,
    workspace_state,
)

SCHEMA = "MCP_ELECTRICO_P8C3C_ENGINE_READINESS_V1"
STATUS_READY = "READY_FOR_CONTROLLED_EXECUTION"
STATUS_PARTIAL = "PARTIALLY_READY"
STATUS_BLOCKED = "BLOCKED"
SCOPE_READY = "READY"
SCOPE_BLOCKED = "BLOCKED"

POWER_FLOW = "POWER_FLOW"
VOLTAGE_DROP = "VOLTAGE_DROP"
AMPACITY = "AMPACITY"
SC_3PH = "IEC60909_3PH_MAX_MIN"
SC_1PH = "IEC60909_1PH_GROUND_MAX_MIN"
PROTECTION = "PROTECTION_TCC"


def _issue(code: str, message: str, *, path: str | None = None, element: str | None = None) -> dict[str, Any]:
    return {"code": code, "message": message, "path": path, "element": element}


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _number(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        return isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _temperature_map(manifest: dict[str, Any]) -> dict[str, float]:
    result: dict[str, float] = {}
    for item in (manifest.get("topology") or {}).get("lines") or []:
        if not isinstance(item, dict):
            continue
        identifier = str(item.get("id") or "").strip()
        value = item.get("endtemp_min_c")
        if identifier and _number(value):
            result[identifier] = float(value)
    return result


def _short_circuit_buses(manifest: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    inputs = manifest.get("study_inputs") or {}
    raw = inputs.get("short_circuit_buses")
    if not isinstance(raw, list) or not raw:
        return [], [_issue(
            "P8C3C101",
            "El alcance IEC 60909 requiere study_inputs.short_circuit_buses explícito y no vacío; no se elige un bus automáticamente.",
            path="study_inputs.short_circuit_buses",
        )]

    buses: list[str] = []
    issues: list[dict[str, Any]] = []
    seen: set[str] = set()
    declared = {str(x).strip().lower() for x in (manifest.get("topology") or {}).get("buses") or [] if str(x).strip()}
    for i, value in enumerate(raw):
        bus = str(value or "").strip()
        if not bus:
            issues.append(_issue("P8C3C102", "Bus de cortocircuito vacío.", path=f"study_inputs.short_circuit_buses[{i}]"))
            continue
        key = bus.lower()
        if key in seen:
            issues.append(_issue("P8C3C103", "Bus de cortocircuito duplicado.", path=f"study_inputs.short_circuit_buses[{i}]", element=bus))
            continue
        seen.add(key)
        if key not in declared:
            issues.append(_issue("P8C3C104", "El bus objetivo no existe en topology.buses.", path=f"study_inputs.short_circuit_buses[{i}]", element=bus))
            continue
        buses.append(bus)
    return buses, issues


def _pf_default_issues(materialization: dict[str, Any]) -> list[dict[str, Any]]:
    """Defaults que deben cerrarse antes de ejecutar flujo/caída en un caso real."""
    issues: list[dict[str, Any]] = []
    for item in materialization.get("engine_defaults_retained") or []:
        issues.append(_issue(
            "P8C3C201",
            "Parámetro del modelo real no declarado; OpenDSS conserva un valor interno y P8C3C no permite ejecutarlo como dato de proyecto.",
            path=str(item.get("path") or "model"),
            element=str(item.get("note") or "") or None,
        ))
    return issues


def _voltage_drop_input_issues(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    value = (manifest.get("study_inputs") or {}).get("voltage_drop_limit_pct")
    if not _present(value):
        return [_issue(
            "P8C3C210",
            "VOLTAGE_DROP requiere study_inputs.voltage_drop_limit_pct explícito; no se usa el 5% de ejemplos como criterio del proyecto.",
            path="study_inputs.voltage_drop_limit_pct",
        )]
    if not _number(value) or float(value) <= 0 or float(value) > 100:
        return [_issue(
            "P8C3C211",
            "voltage_drop_limit_pct debe ser finito, >0 y <=100.",
            path="study_inputs.voltage_drop_limit_pct",
        )]
    return []


def _unknown_tap_issues(materialization: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for item in materialization.get("engine_defaults_retained") or []:
        path = str(item.get("path") or "")
        if path.lower().endswith(".tap"):
            issues.append(_issue(
                "P8C3C220",
                "La posición/rango de tap del transformador no está declarada. P4 no ejecuta el caso real suponiendo tap nominal.",
                path=path,
            ))
    return issues


def _prep_3ph(manifest: dict[str, Any], materialization: dict[str, Any]) -> dict[str, Any]:
    buses, issues = _short_circuit_buses(manifest)
    issues.extend(_unknown_tap_issues(materialization))
    temperatures = _temperature_map(manifest)
    checks: list[dict[str, Any]] = []

    if not issues:
        for bus in buses:
            for case in ("max", "min"):
                prep = iec60909.evaluar_preparacion_3ph(
                    case,
                    bus,
                    line_endtemp_degree_c=temperatures if case == "min" else None,
                    calcular_ip_ith=False,
                )
                checks.append({
                    "bus": bus,
                    "case": case,
                    "ready": bool(prep.get("ready")),
                    "issues": deepcopy(prep.get("issues") or []),
                    "source_projection": deepcopy(prep.get("source_projection")),
                    "line_endtemp_degree_c": deepcopy(prep.get("line_endtemp_degree_c") or {}),
                })
                issues.extend(deepcopy(prep.get("issues") or []))

    return {
        "status": SCOPE_READY if not issues and bool(buses) else SCOPE_BLOCKED,
        "backend": "pandapower",
        "fault": "3ph",
        "cases": ["max", "min"],
        "target_buses": buses,
        "checks": checks,
        "issues": issues,
        "short_circuit_calculation_performed": False,
    }


def _prep_1ph_case(bus: str, case: str, temperatures: dict[str, float]) -> dict[str, Any]:
    """Ejecuta solo proyecciones/gates P4C07; nunca llama calc_sc."""
    issues: list[dict[str, Any]] = []
    compatibility = pandapower_engine.evaluar_compatibilidad()
    if not compatibility.get("compatible"):
        issues.extend(deepcopy(compatibility.get("issues") or []))
        return {
            "bus": bus,
            "case": case,
            "ready": False,
            "issues": issues,
            "pandapower_compatibility": compatibility,
            "projection_preflight_performed": False,
        }

    model = pandapower_engine._collect_active_model()
    bus_names = {str(item.get("name") or "").lower() for item in model.get("buses", [])}
    if bus.lower() not in bus_names:
        issues.append(_issue("P8C3C111", "Bus de falla no encontrado en el modelo pandapower proyectable.", element=bus))

    source_projection, source_issues = iec60909._source_projection(case)
    issues.extend(deepcopy(source_issues))
    normalized_temps, temp_issues = iec60909._line_temperature_map(
        model,
        case,
        temperatures if case == "min" else None,
    )
    issues.extend(deepcopy(temp_issues))

    zero_projection = None
    projection_attempted = False
    if source_projection and not source_issues and not temp_issues:
        try:
            net, line_meta, _trafo_meta = pandapower_engine._build_net(model)
            iec60909._set_source_short_circuit(net, source_projection)
            if case == "min":
                iec60909._set_min_line_temperatures(net, line_meta, normalized_temps)
            projection_attempted = True
            zero_projection = iec60909_single_phase_ground._apply_zero_sequence(net, case)
        except Exception as exc:
            issues.append(_issue(
                "P8C3C112",
                f"Preflight de proyección Z0 P4C07 falló sin ejecutar cortocircuito: {type(exc).__name__}: {exc}",
                element=bus,
            ))

    return {
        "bus": bus,
        "case": case,
        "ready": not issues,
        "issues": issues,
        "source_projection": deepcopy(source_projection),
        "line_endtemp_degree_c": deepcopy(normalized_temps),
        "zero_sequence_projection": deepcopy(zero_projection),
        "pandapower_compatibility": compatibility,
        "projection_preflight_performed": projection_attempted,
        "short_circuit_calculation_performed": False,
    }


def _prep_1ph(manifest: dict[str, Any], materialization: dict[str, Any]) -> dict[str, Any]:
    buses, issues = _short_circuit_buses(manifest)
    issues.extend(_unknown_tap_issues(materialization))
    temperatures = _temperature_map(manifest)
    checks: list[dict[str, Any]] = []

    if not issues:
        for bus in buses:
            for case in ("max", "min"):
                prep = _prep_1ph_case(bus, case, temperatures)
                checks.append(prep)
                issues.extend(deepcopy(prep.get("issues") or []))

    return {
        "status": SCOPE_READY if not issues and bool(buses) else SCOPE_BLOCKED,
        "backend": "pandapower",
        "fault": "1ph-ground",
        "cases": ["max", "min"],
        "target_buses": buses,
        "checks": checks,
        "issues": issues,
        "projection_preflight_only": True,
        "short_circuit_calculation_performed": False,
    }


def _blocked_not_materialized(scope: str) -> dict[str, Any]:
    if scope == AMPACITY:
        return {
            "status": SCOPE_BLOCKED,
            "backend": "P3",
            "issues": [_issue(
                "P8C3C301",
                "Las entradas P3 fueron admitidas por P8B, pero P8C3B deliberadamente no las materializa. Requiere el siguiente gate de binding P3 real.",
                path="ampacity",
            )],
            "calculation_performed": False,
        }
    return {
        "status": SCOPE_BLOCKED,
        "backend": "P5",
        "issues": [_issue(
            "P8C3C501",
            "Las entradas P5/TCC fueron admitidas por P8B, pero todavía no existen dispositivos/curvas numéricas materializados en el modelo real.",
            path="protection",
        )],
        "calculation_performed": False,
    }


def _scope_blocked_by_build(scope: str, materialization: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": SCOPE_BLOCKED,
        "backend": None,
        "issues": [{
            "code": "P8C3C001",
            "message": "El modelo real no alcanzó MODEL_BUILT_NOT_EXECUTED; no se evalúa readiness del estudio.",
            "path": "materialization",
            "element": scope,
        }] + deepcopy(materialization.get("issues") or []),
        "calculation_performed": False,
    }


def evaluar_readiness(manifest: dict[str, Any]) -> dict[str, Any]:
    """Reconstruye el modelo y evalúa readiness por alcance sin ejecutar estudios."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest debe ser dict.")

    materialization = real_model_materializer.materializar_modelo(deepcopy(manifest))
    requested = [str(x).strip().upper() for x in manifest.get("requested_scope") or [] if str(x).strip()]
    scopes: dict[str, Any] = {}

    built = materialization.get("materializer_status") == real_model_materializer.STATUS_BUILT
    if not built:
        for scope in requested:
            scopes[scope] = _scope_blocked_by_build(scope, materialization)
    else:
        pf_issues = _pf_default_issues(materialization)
        for scope in requested:
            if scope == POWER_FLOW:
                scopes[scope] = {
                    "status": SCOPE_READY if not pf_issues else SCOPE_BLOCKED,
                    "backend": "OpenDSS",
                    "issues": deepcopy(pf_issues),
                    "calculation_performed": False,
                }
            elif scope == VOLTAGE_DROP:
                issues = deepcopy(pf_issues) + _voltage_drop_input_issues(manifest)
                scopes[scope] = {
                    "status": SCOPE_READY if not issues else SCOPE_BLOCKED,
                    "backend": "OpenDSS",
                    "limit_pct": (manifest.get("study_inputs") or {}).get("voltage_drop_limit_pct"),
                    "issues": issues,
                    "calculation_performed": False,
                }
            elif scope == SC_3PH:
                scopes[scope] = _prep_3ph(manifest, materialization)
            elif scope == SC_1PH:
                scopes[scope] = _prep_1ph(manifest, materialization)
            elif scope in {AMPACITY, PROTECTION}:
                scopes[scope] = _blocked_not_materialized(scope)
            else:
                scopes[scope] = {
                    "status": SCOPE_BLOCKED,
                    "backend": None,
                    "issues": [_issue("P8C3C900", f"Scope no reconocido por P8C3C: {scope}.")],
                    "calculation_performed": False,
                }

    ready_scopes = [scope for scope, item in scopes.items() if item.get("status") == SCOPE_READY]
    blocked_scopes = [scope for scope, item in scopes.items() if item.get("status") != SCOPE_READY]
    if requested and not blocked_scopes:
        status = STATUS_READY
    elif ready_scopes:
        status = STATUS_PARTIAL
    else:
        status = STATUS_BLOCKED

    return {
        "schema": SCHEMA,
        "readiness_status": status,
        "model_built": built,
        "materialization": {
            "status": materialization.get("materializer_status"),
            "manifest_sha256": materialization.get("manifest_sha256"),
            "materialized_fingerprint_sha256": materialization.get("materialized_fingerprint_sha256"),
            "circuit_name": materialization.get("circuit_name"),
            "engine_defaults_retained_count": materialization.get("engine_defaults_retained_count"),
            "issues": deepcopy(materialization.get("issues") or []),
        },
        "requested_scope": requested,
        "scope_readiness": scopes,
        "ready_scopes": ready_scopes,
        "blocked_scopes": blocked_scopes,
        "all_requested_ready": bool(requested) and not blocked_scopes,
        "electrical_calculation_performed": False,
        "studies_executed": [],
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
        "workspace_studies_after_readiness": sorted((workspace_state.status().get("studies") or {}).keys()),
        "note": (
            "READY significa únicamente que los gates de datos/backend permiten una futura ejecución controlada. "
            "No significa resultado calculado, validación profesional ni conformidad IEC 60909-0:2026."
        ),
    }
