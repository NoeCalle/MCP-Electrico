"""Validate result usability, separately from whether a design passes criteria.

This module performs no electrical calculation and never repairs solver output.
The declared manifest defines which feeders, buses and cases must be present.
"""
from __future__ import annotations

import json
from math import isfinite


def positive(value):
    return type(value) in (int, float) and isfinite(value) and value > 0


def diagnostic_payload(value):
    """Keep rejected output inspectable without leaking NaN into MCP/JSON."""
    if isinstance(value, float) and not isfinite(value):
        return {"invalid_numeric": str(value)}
    if isinstance(value, dict):
        return {str(k): diagnostic_payload(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [diagnostic_payload(v) for v in value]
    if value is None or type(value) in (str, int, float, bool):
        return value
    return {"unsupported_type": type(value).__name__}


def scope_issues(scope, result, manifest):
    issues = []

    def require(condition, path, message):
        if not condition:
            issues.append({"code": "EXECUTION_RESULT_INVALID", "scope": scope,
                           "path": path, "message": message})

    if not isinstance(result, dict):
        require(False, "result", "El ejecutor no devolvió un objeto de resultados.")
        return issues
    try:
        json.dumps(result, allow_nan=False)
    except (TypeError, ValueError):
        require(False, "result", "Resultado no serializable o con NaN/Infinity.")
        return issues
    require(result.get("resultados_validos") is not False and result.get("ok") is not False,
            "result", "El ejecutor declaró el resultado inválido.")
    if scope in {"POWER_FLOW", "VOLTAGE_DROP"}:
        require(result.get("convergio") is True, "convergio", "El flujo no confirmó convergencia.")
        if scope == "POWER_FLOW":
            pf = result.get("powerflow")
            require(isinstance(pf, dict) and pf.get("convergio") is True
                    and pf.get("resultados_validos") is not False,
                    "powerflow", "La solución base no es válida.")
        require(isinstance(result.get("buses"), list) and bool(result["buses"]),
                "buses", "No hay resultados de barras.")
        if scope == "VOLTAGE_DROP":
            rows = result.get("alimentadores")
            expected = {str(r["id"]).lower() for r in manifest["topology"]["lines"]}
            actual = [str(r.get("id", "")).lower() for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []
            require(bool(expected) and len(actual) == len(expected) and set(actual) == expected,
                    "alimentadores", "Faltan alimentadores o hay resultados duplicados/inesperados.")
            require(isinstance(rows, list) and all(isinstance(r, dict)
                    and type(r.get("caida_evaluada_pct")) in (int, float)
                    and r.get("estado_criterio") in {"OK", "EXCEDE"} for r in rows),
                    "alimentadores", "Caída no evaluable; EXCEDE sí es un resultado de diseño válido.")
    elif scope == "AMPACITY":
        rows = result.get("alimentadores")
        expected = {str(r["element_id"]).lower() for r in manifest.get("ampacity", [])}
        actual = [str(r.get("element", "")).lower() for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []
        require(bool(expected) and len(actual) == len(expected) and set(actual) == expected,
                "alimentadores", "Cobertura P3 distinta de los perfiles declarados.")
        require(result.get("status") in {"CUMPLE", "NO_CUMPLE"}, "status", "Ampacidad sin datos suficientes.")
        require(isinstance(rows, list) and all(isinstance(r, dict)
                and r.get("status") in {"CUMPLE", "NO_CUMPLE"}
                and all(positive((r.get("values") or {}).get(k)) for k in ("ib_a", "in_a", "iz_a")) for r in rows),
                "alimentadores", "P3 incompleto; NO_CUMPLE sí es un resultado de diseño válido.")
    elif scope in {"IEC60909_3PH_MAX_MIN", "IEC60909_1PH_GROUND_MAX_MIN"}:
        rows = result.get("targets")
        expected = {str(b).lower() for b in manifest["study_inputs"]["short_circuit_buses"]}
        actual = [str(r.get("bus", "")).lower() for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []
        require(bool(expected) and len(actual) == len(expected) and set(actual) == expected,
                "targets", "Faltan barras o hay targets duplicados/inesperados.")
        for target in rows if isinstance(rows, list) else []:
            if not isinstance(target, dict):
                require(False, "targets", "Target no estructurado.")
                continue
            pair = target.get("result")
            if not isinstance(pair, dict):
                require(False, "targets.result", "Par MAX/MIN no estructurado.")
                continue
            scenarios = pair.get("scenarios", {}) if scope == "IEC60909_3PH_MAX_MIN" else pair
            for case in ("max", "min"):
                atomic = scenarios.get(case) if isinstance(scenarios, dict) else None
                good = isinstance(atomic, dict) and atomic.get("ok") is True
                require(good, f"targets.{target.get('bus')}.{case}", "Caso MAX/MIN ausente o fallido.")
                if good:
                    require(str(atomic.get("bus", "")).lower() == str(target.get("bus", "")).lower()
                            and atomic.get("case") == case and positive((atomic.get("results") or {}).get("ikss_ka")),
                            f"targets.{target.get('bus')}.{case}", "Identidad de barra/caso o corriente inválida.")
    else:
        require(False, "scope", "No hay contrato de calidad para este estudio.")
    return issues


def protection_assessment(devices):
    """A genuine FAIL remains usable evidence; a missing check never becomes PASS."""
    checks, incomplete = [], []
    for device in devices:
        for kind in ("breaking_capacity", "clearing_time", "thermal_check"):
            result = device.get(kind) or {}
            status = result.get("status")
            requested = kind != "thermal_check" or device.get("binding", {}).get("thermal_check") is not None
            if not requested:
                continue
            usable = status == "CLEARING_TIME_READY" if kind == "clearing_time" else status in {"PASS", "FAIL"}
            if kind == "clearing_time" and usable:
                usable = positive((result.get("clearing_time") or {}).get("conservative_time_s"))
            try:
                json.dumps(result, allow_nan=False)
            except (TypeError, ValueError):
                usable = False
            check = {"device_id": device.get("device_id"), "check": kind,
                     "status": status, "result_usable": usable}
            checks.append(check)
            if not usable:
                incomplete.append(check)
    complete = bool(devices) and bool(checks) and not incomplete
    return {"all_requested_checks_evaluated": complete,
            "status": "NOT_EVALUABLE" if not complete else ("FAIL" if any(c["status"] == "FAIL" for c in checks) else "PASS"),
            "scope": "DECLARED_DEVICE_CHECKS_ONLY_NOT_INSTALLATION_APPROVAL",
            "checks": checks, "incomplete_checks": incomplete,
            "selectivity_integral_evaluated": False, "professional_emission": False}


def project_assessment(execution):
    """Expose failed design criteria without converting them into solver errors."""
    base = execution.get("p8d1_execution") or {}
    results = base.get("results") or {}
    checks = []
    for scope, field, passing in (
        ("VOLTAGE_DROP", "estado_criterio", "OK"),
        ("AMPACITY", "status", "CUMPLE"),
    ):
        for row in (results.get(scope) or {}).get("alimentadores", []):
            checks.append({"scope": scope, "element": row.get("id") or row.get("element"),
                           "status": row.get(field), "passed": row.get(field) == passing})
    for check in (execution.get("design_assessment") or {}).get("checks", []):
        if check["check"] != "clearing_time":
            checks.append({"scope": ("TEMPORAL_COORDINATION_RANGE" if check["check"] == "temporal_coordination_range" else "PROTECTION_TCC"),
                           "element": check.get("range_id") or check["device_id"],
                           "status": check["status"], "passed": check["status"] == "PASS"})
    return {"schema": "MCP_ELECTRICO_DECLARED_DESIGN_CHECKS_V1",
            "status": ("NOT_EVALUABLE" if execution.get("resultados_validos") is not True or not checks
                       else "DECLARED_CHECKS_FAILED" if any(not c["passed"] for c in checks)
                       else "DECLARED_CHECKS_PASSED"),
            "calculation_valid": execution.get("resultados_validos") is True,
            "scope": "REQUESTED_CHECKS_ONLY_NOT_FULL_INSTALLATION_COMPLIANCE",
            "model_revision": execution.get("model_revision"),
            "manifest_sha256": execution.get("manifest_sha256"), "checks": checks,
            "unassessed": ["full_selectivity", "protection_sensitivity_over_all_faults",
                           "full_standard_conformance", "field_validation"],
            "installation_validation_closed": False, "professional_emission": False}
