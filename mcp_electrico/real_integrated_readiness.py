"""P8C5 — readiness integral del primer proyecto real, sin ejecución.

P8C5 materializa una sola vez hasta la capa más alta solicitada y luego evalúa
readiness sobre el modelo activo. No vuelve a llamar P8C3C.evaluar_readiness()
porque esa función reconstruye el modelo y borraría P3/P5 recién materializados.

Capas:
- P8C3B: OpenDSS/P2/Z0;
- P8C4A: conductor real + P3;
- P8C4B: dispositivos P5A + datasets P5B;
- P8C5: readiness por scope, sin Solve/evaluar/calc_sc.
"""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any

from . import (
    ampacity,
    conductor_library,
    protection_data,
    real_engineering_materializer,
    real_model_materializer,
    real_model_readiness,
    real_protection_materializer,
    workspace_state,
)

SCHEMA = "MCP_ELECTRICO_P8C5_INTEGRATED_READINESS_V1"
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


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _same_number(left: Any, right: Any, tol: float = 1e-9) -> bool:
    a, b = _number(left), _number(right)
    return a is not None and b is not None and abs(a - b) <= tol


def _requested(manifest: dict[str, Any]) -> list[str]:
    return [
        str(item).strip().upper()
        for item in manifest.get("requested_scope") or []
        if str(item).strip()
    ]


def _materialize_once(manifest: dict[str, Any], requested: list[str]) -> tuple[str, bool, dict[str, Any], dict[str, Any]]:
    """Materializa la capa más alta una sola vez y devuelve P8C3B base."""
    requested_set = set(requested)
    if PROTECTION in requested_set:
        root = real_protection_materializer.materializar_protecciones(deepcopy(manifest))
        ok = root.get("protection_materializer_status") == real_protection_materializer.STATUS_MATERIALIZED
        engineering = root.get("engineering") or {}
        model = engineering.get("model") or {}
        return "P8C4B", ok, root, model

    if AMPACITY in requested_set:
        root = real_engineering_materializer.materializar_datos_ingenieria(deepcopy(manifest))
        ok = root.get("p3_materialized") is True
        model = root.get("model") or {}
        return "P8C4A", ok, root, model

    root = real_model_materializer.materializar_modelo(deepcopy(manifest))
    ok = root.get("materializer_status") == real_model_materializer.STATUS_BUILT
    return "P8C3B", ok, root, root


def _scope_blocked_by_materialization(scope: str, layer: str, root: dict[str, Any]) -> dict[str, Any]:
    issues = deepcopy(root.get("issues") or [])
    return {
        "status": SCOPE_BLOCKED,
        "backend": None,
        "issues": [_issue(
            "P8C5M001",
            f"La capa requerida {layer} no quedó materializada; no se inspecciona readiness sobre estado previo.",
            path="materialization",
            element=scope,
        )] + issues,
        "calculation_performed": False,
    }


def _ampacity_readiness(manifest: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    records = manifest.get("ampacity") or []

    for index, declared in enumerate(records):
        if not isinstance(declared, dict):
            issues.append(_issue("P8C5P301", "Ficha P3 no estructurada.", path=f"ampacity[{index}]"))
            continue
        element = str(declared.get("element_id") or "").strip()
        assignment = conductor_library.obtener_asignacion(element) if element else None
        profile = ampacity.obtener_condiciones(element) if element else None
        local: list[dict[str, Any]] = []

        if not assignment:
            local.append(_issue("P8C5P302", "No existe asignación P2/P3 vigente para el conductor real.", element=element))
        if not profile:
            local.append(_issue("P8C5P303", "No existe perfil P3 vigente materializado.", element=element))

        if assignment:
            if str(assignment.get("codigo") or "") != str(declared.get("conductor_code") or ""):
                local.append(_issue("P8C5P304", "El código del conductor materializado no coincide con el manifiesto.", element=element))
            if not _same_number(assignment.get("ampacidad_aplicada_a"), declared.get("base_ampacity_a")):
                local.append(_issue("P8C5P305", "Iz_base P2 materializada no coincide con base_ampacity_a del manifiesto.", element=element))

        if profile:
            if str((profile.get("norm") or {}).get("id") or "") != str(declared.get("norm_id") or ""):
                local.append(_issue("P8C5P306", "La referencia normativa P3 materializada no coincide con el manifiesto.", element=element))
            if not _same_number((profile.get("base") or {}).get("ampacity_a"), declared.get("base_ampacity_a")):
                local.append(_issue("P8C5P307", "Iz_base del perfil P3 no coincide con el manifiesto.", element=element))
            if not _same_number((profile.get("design_current") or {}).get("ib_a"), declared.get("ib_a")):
                local.append(_issue("P8C5P308", "Ib materializada no coincide con el manifiesto.", element=element))
            if not _same_number((profile.get("protection") or {}).get("in_a"), declared.get("in_a")):
                local.append(_issue("P8C5P309", "In materializada no coincide con el manifiesto.", element=element))

        # Gate visual/semántico descubierto por el piloto real: la ruta histórica
        # de ampacity rotula cualquier base no normativa como P2_CATALOG. Eso es
        # incorrecto para una asignación PROJECT_DATA y debe corregirse antes de
        # ejecutar/mostrar P3 real en Workspace V3/V5.
        if assignment and profile and str(assignment.get("origen") or "") == "PROJECT_DATA":
            base_origin = str((profile.get("base") or {}).get("origin") or "")
            if base_origin != "P2_PROJECT":
                local.append(_issue(
                    "P8C5P310",
                    "Conductor PROJECT_DATA aún aparece con origen P3 distinto de P2_PROJECT; bloquear ejecución evita rotularlo como CATÁLOGO P2 en V3.",
                    path="ampacity.base.origin",
                    element=element,
                ))

        checks.append({
            "element": element,
            "ready": not local,
            "assignment_origin": (assignment or {}).get("origen"),
            "profile_base_origin": ((profile or {}).get("base") or {}).get("origin"),
            "issues": local,
        })
        issues.extend(local)

    if not records:
        issues.append(_issue("P8C5P311", "AMPACITY fue solicitado pero no hay fichas P3 en el manifiesto.", path="ampacity"))

    return {
        "status": SCOPE_READY if not issues and bool(records) else SCOPE_BLOCKED,
        "backend": "P3",
        "checks": checks,
        "issues": issues,
        "calculation_performed": False,
        "visual_origin_gate": "P2_PROJECT_REQUIRED_FOR_PROJECT_DATA",
    }


def _protection_readiness(manifest: dict[str, Any], requested: list[str]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    devices = ((manifest.get("protection") or {}).get("devices") or [])
    require_p3_match = AMPACITY in set(requested)

    for index, declared in enumerate(devices):
        if not isinstance(declared, dict):
            issues.append(_issue("P8C5P501", "Dispositivo P5 no estructurado.", path=f"protection.devices[{index}]"))
            continue
        device_id = str(declared.get("id") or "").strip()
        readiness = protection_data.evaluar_preparacion(device_id)
        local: list[dict[str, Any]] = []

        if readiness.get("status") == "MISSING_DEVICE":
            local.extend(deepcopy(readiness.get("issues") or []))
        if readiness.get("breaking_capacity_ready") is not True:
            local.append(_issue("P8C5P502", "Rating de capacidad de corte P5 no está listo.", element=device_id))
        if readiness.get("tcc_data_ready") is not True:
            local.append(_issue("P8C5P503", "Dataset TCC numérico no está vinculado/listo.", element=device_id))
        p3_binding = readiness.get("p3_binding") or {}
        if require_p3_match and p3_binding.get("status") != "MATCH":
            local.append(_issue("P8C5P504", "PROTECTION_TCC requiere que In P5 coincida con la ficha P3 materializada.", element=device_id))

        checks.append({
            "device_id": device_id,
            "ready": not local,
            "breaking_capacity_ready": readiness.get("breaking_capacity_ready"),
            "tcc_data_ready": readiness.get("tcc_data_ready"),
            "p3_binding": deepcopy(p3_binding),
            "curve_time_semantics": readiness.get("curve_time_semantics"),
            "issues": local,
        })
        issues.extend(local)

    if not devices:
        issues.append(_issue("P8C5P505", "PROTECTION_TCC fue solicitado pero no hay dispositivos P5.", path="protection.devices"))

    return {
        "status": SCOPE_READY if not issues and bool(devices) else SCOPE_BLOCKED,
        "backend": "P5",
        "checks": checks,
        "issues": issues,
        "calculation_performed": False,
        "tcc_evaluation_performed": False,
    }


def evaluar_readiness_integral(manifest: dict[str, Any]) -> dict[str, Any]:
    """Materializa una vez y evalúa readiness integral sin ejecutar estudios."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest debe ser dict.")

    manifest_copy = deepcopy(manifest)
    requested = _requested(manifest_copy)
    layer, materialized, root, model_materialization = _materialize_once(manifest_copy, requested)
    scopes: dict[str, Any] = {}

    if not materialized:
        for scope in requested:
            scopes[scope] = _scope_blocked_by_materialization(scope, layer, root)
    else:
        pf_issues = real_model_readiness._pf_default_issues(model_materialization)
        for scope in requested:
            if scope == POWER_FLOW:
                scopes[scope] = {
                    "status": SCOPE_READY if not pf_issues else SCOPE_BLOCKED,
                    "backend": "OpenDSS",
                    "issues": deepcopy(pf_issues),
                    "calculation_performed": False,
                }
            elif scope == VOLTAGE_DROP:
                issues = deepcopy(pf_issues) + real_model_readiness._voltage_drop_input_issues(manifest_copy)
                scopes[scope] = {
                    "status": SCOPE_READY if not issues else SCOPE_BLOCKED,
                    "backend": "OpenDSS",
                    "limit_pct": (manifest_copy.get("study_inputs") or {}).get("voltage_drop_limit_pct"),
                    "issues": issues,
                    "calculation_performed": False,
                }
            elif scope == SC_3PH:
                scopes[scope] = real_model_readiness._prep_3ph(manifest_copy, model_materialization)
            elif scope == SC_1PH:
                scopes[scope] = real_model_readiness._prep_1ph(manifest_copy, model_materialization)
            elif scope == AMPACITY:
                scopes[scope] = _ampacity_readiness(manifest_copy)
            elif scope == PROTECTION:
                scopes[scope] = _protection_readiness(manifest_copy, requested)
            else:
                scopes[scope] = {
                    "status": SCOPE_BLOCKED,
                    "backend": None,
                    "issues": [_issue("P8C5X001", f"Scope no reconocido por P8C5: {scope}.")],
                    "calculation_performed": False,
                }

    ready_scopes = [scope for scope, view in scopes.items() if view.get("status") == SCOPE_READY]
    blocked_scopes = [scope for scope, view in scopes.items() if view.get("status") != SCOPE_READY]
    if requested and not blocked_scopes:
        status = STATUS_READY
    elif ready_scopes:
        status = STATUS_PARTIAL
    else:
        status = STATUS_BLOCKED

    workspace = workspace_state.status()
    return {
        "schema": SCHEMA,
        "readiness_status": status,
        "requested_scope": requested,
        "materialization_layer": layer,
        "materialization_ok": materialized,
        "materialization": root,
        "scope_readiness": scopes,
        "ready_scopes": ready_scopes,
        "blocked_scopes": blocked_scopes,
        "all_requested_ready": bool(requested) and not blocked_scopes,
        "workspace_state": workspace.get("state"),
        "workspace_results_current": workspace.get("results_current"),
        "workspace_studies_after_readiness": sorted((workspace.get("studies") or {}).keys()),
        "electrical_calculation_performed": False,
        "power_flow_calculation_performed": False,
        "voltage_drop_calculation_performed": False,
        "ampacity_calculation_performed": False,
        "short_circuit_calculation_performed": False,
        "protection_calculation_performed": False,
        "tcc_evaluation_performed": False,
        "studies_executed": [],
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
        "next_gate": "P8D_CONTROLLED_EXECUTION" if status == STATUS_READY else "RESOLVE_BLOCKERS_BEFORE_P8D",
    }
