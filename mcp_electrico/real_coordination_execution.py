"""Optional P8 temporal ranges bound to the current execution's P4 MIN/MAX.

No fault is selected or solved here. Preflight is pure and can be used by
intake before mutating a model. Evaluation reuses the P5E curve envelope.
"""
from __future__ import annotations

from copy import deepcopy
import json
from math import isfinite

SCHEMA = "MCP_ELECTRICO_P8_COORDINATION_RANGES_V1"
_FIELDS = {"id", "downstream_device_id", "upstream_device_id",
           "upstream_to_downstream_ratio", "required_margin_s",
           "relationship_source_reference", "currents_source_reference", "current_bounds"}
_BOUND_FIELDS = {"fault_bus", "fault_type", "case", "current_quantity", "operating_voltage_kv"}
_SCOPES = {"3ph": "IEC60909_3PH_MAX_MIN", "1ph-ground": "IEC60909_1PH_GROUND_MAX_MIN"}


def _key(value):
    return str(value or "").strip().lower().removeprefix("protection.")


def _number(value, zero=False):
    try:
        return type(value) in (int, float) and isfinite(value) and (value >= 0 if zero else value > 0)
    except OverflowError:
        return False


def preflight(manifest):
    """Validate the explicit optional request; never assume topology or ratio."""
    protection = manifest.get("protection")
    if protection is None:
        return [], []
    issues = []
    def issue(path, message):
        issues.append({"code": "P8CR_INPUT", "path": path, "message": message, "scope": "PROTECTION_TCC"})
    if not isinstance(protection, dict):
        issue("protection", "protection debe ser un objeto.")
        return [], issues
    if "coordination_ranges" not in protection:
        return [], []
    raw = protection["coordination_ranges"]
    if not isinstance(raw, list):
        issue("protection.coordination_ranges", "Debe ser una lista explícita, no null.")
        return [], issues
    requested = manifest.get("requested_scope") or []
    scopes = {str(s).strip().upper() for s in requested} if isinstance(requested, list) else set()
    if raw and "PROTECTION_TCC" not in scopes:
        issue("requested_scope", "Los rangos requieren PROTECTION_TCC.")
    devices = protection.get("devices")
    declared = {_key(d.get("id")) for d in devices if isinstance(d, dict)} if isinstance(devices, list) else set()
    inputs = manifest.get("study_inputs") or {}
    buses = {str(b).strip().lower() for b in (inputs.get("short_circuit_buses") or [])} if isinstance(inputs, dict) else set()
    seen = set()
    for index, item in enumerate(raw):
        path = f"protection.coordination_ranges[{index}]"
        if not isinstance(item, dict):
            issue(path, "El rango debe ser un objeto.")
            continue
        if set(item) != _FIELDS:
            issue(path, "Campos faltantes o desconocidos: " + ", ".join(sorted(set(item) ^ _FIELDS)))
        for field in ("id", "downstream_device_id", "upstream_device_id",
                      "relationship_source_reference", "currents_source_reference"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                issue(f"{path}.{field}", "Se requiere texto explícito y no vacío.")
        rid = str(item.get("id") or "").strip().lower()
        if rid in seen:
            issue(f"{path}.id", "Identificador de rango duplicado.")
        seen.add(rid)
        down, up = _key(item.get("downstream_device_id")), _key(item.get("upstream_device_id"))
        if down == up or not {down, up} <= declared:
            issue(path, "Se requieren dos dispositivos distintos declarados en este manifiesto.")
        for field, zero in (("upstream_to_downstream_ratio", False), ("required_margin_s", True)):
            if not _number(item.get(field), zero):
                issue(f"{path}.{field}", "Valor numérico finito y positivo; solo el margen admite cero.")
        bounds = item.get("current_bounds")
        if not isinstance(bounds, dict) or set(bounds) != {"minimum", "maximum"}:
            issue(f"{path}.current_bounds", "Declare exactamente minimum y maximum.")
            continue
        for name, case in (("minimum", "min"), ("maximum", "max")):
            bound = bounds[name]
            bp = f"{path}.current_bounds.{name}"
            if not isinstance(bound, dict):
                issue(bp, "El límite debe ser una referencia P4 estructurada.")
                continue
            if set(bound) != _BOUND_FIELDS:
                issue(bp, "Campos de referencia P4 faltantes o desconocidos.")
            fault_type = bound.get("fault_type")
            if not isinstance(fault_type, str) or fault_type not in _SCOPES or _SCOPES.get(fault_type) not in scopes:
                issue(bp, "El tipo de falla requiere su scope P4 explícito: 3ph o 1ph-ground.")
            if bound.get("case") != case or bound.get("current_quantity") != "ikss_ka":
                issue(bp, "Se requiere el caso MIN/MAX correspondiente y la magnitud ikss_ka.")
            if not isinstance(bound.get("fault_bus"), str) or bound["fault_bus"].strip().lower() not in buses:
                issue(bp, "La barra debe estar declarada en short_circuit_buses.")
            if not _number(bound.get("operating_voltage_kv")):
                issue(bp, "La tensión de operación debe ser explícita, finita y positiva.")
        low, high = bounds["minimum"], bounds["maximum"]
        if isinstance(low, dict) and isinstance(high, dict):
            if (str(low.get("fault_bus", "")).strip().lower() != str(high.get("fault_bus", "")).strip().lower()
                    or low.get("fault_type") != high.get("fault_type")
                    or low.get("operating_voltage_kv") != high.get("operating_voltage_kv")):
                issue(f"{path}.current_bounds", "Ambos límites deben referir a la misma barra, falla y tensión.")
    return deepcopy(raw) if not issues else [], issues


def _usable_result(result, request, provenance):
    """Reject a successful-looking result for another pair, range or criterion."""
    if not isinstance(result, dict):
        return False
    worst, currents, relation = (result.get("worst_case") or {}, result.get("currents") or {},
                                 result.get("relationship") or {})
    margin = worst.get("conservative_margin_s")
    low, high = (provenance[name]["fault_current_ka"] * 1000 for name in ("minimum", "maximum"))
    ratio, required = request["upstream_to_downstream_ratio"], request["required_margin_s"]
    return (
        result.get("resultados_validos") is True and result.get("full_requested_range_evaluated") is True
        and result.get("status") in {"PASS", "FAIL"}
        and type(margin) in (int, float) and isfinite(margin)
        and result.get("required_margin_s") == required
        and result["status"] == ("PASS" if margin >= required else "FAIL")
        and currents.get("downstream_min_a") == low and currents.get("downstream_max_a") == high
        and currents.get("upstream_to_downstream_ratio") == ratio
        and _key(relation.get("downstream_device")) == _key(request["downstream_device_id"])
        and _key(relation.get("upstream_device")) == _key(request["upstream_device_id"])
        and _number(worst.get("downstream_current_a"))
        and low <= worst["downstream_current_a"] <= high
        and _number(worst.get("upstream_current_a"))
        and worst["upstream_current_a"] == worst["downstream_current_a"] * ratio
        and _number(worst.get("upstream_time_min_s")) and _number(worst.get("downstream_time_max_s"))
        and margin == worst["upstream_time_min_s"] - worst["downstream_time_max_s"]
    )


def evaluate(requests, execution, resolve_fault, *, device_checks_ready=True):
    """Resolve both bounds from P8D1 and invoke one P5E postprocessor per range."""
    from . import execution_quality, protection_coordination_range
    rows, invocations = [], 0
    for request in requests:
        provenance, issues = {}, []
        result = None
        if not device_checks_ready:
            issues.append({"code": "P8CR_DEVICE_CHECKS", "message": "Las comprobaciones P5 de dispositivos no están completas."})
        else:
            for name in ("minimum", "maximum"):
                binding = {**request["current_bounds"][name],
                           "device_id": request["downstream_device_id"],
                           "source_reference": request["currents_source_reference"]}
                fault, errors = resolve_fault(execution, binding)
                if errors or fault is None:
                    issues.extend(errors or [{"code": "P8CR_FAULT_MISSING", "message": "Referencia P4 no resuelta."}])
                else:
                    provenance[name] = fault
        if not issues:
            try:
                invocations += 1
                result = protection_coordination_range.evaluar_coordinacion_intervalo(
                    request["downstream_device_id"], request["upstream_device_id"],
                    provenance["minimum"]["fault_current_ka"] * 1000,
                    provenance["maximum"]["fault_current_ka"] * 1000,
                    request["upstream_to_downstream_ratio"], request["required_margin_s"],
                    request["relationship_source_reference"], request["currents_source_reference"])
                json.dumps(result, allow_nan=False)
                usable = _usable_result(result, request, provenance)
                if not usable:
                    issues.append({"code": "P8CR_RANGE_NOT_READY", "message": "El rango P5E no tiene un resultado válido y completo."})
            except Exception as exc:
                issues.append({"code": "P8CR_EVALUATION_FAILED", "message": f"{type(exc).__name__}: {exc}"})
        rows.append({
            "range_id": request["id"], "request": deepcopy(request),
            "result": execution_quality.diagnostic_payload(result),
            "result_usable": not issues,
            "issues": issues, "p4_provenance": provenance,
            "model_revision": execution.get("model_revision"),
            "manifest_sha256": execution.get("manifest_sha256"),
            "p4_recalculation_inside_p5": False,
        })
    ready = all(r["result_usable"] for r in rows)
    status = ("NOT_REQUESTED" if not requests else "NOT_EVALUABLE" if not ready
              else "FAIL" if any(r["result"]["status"] == "FAIL" for r in rows) else "PASS")
    return {
        "schema": SCHEMA, "status": status, "requested_count": len(requests),
        "all_requested_ranges_evaluated": ready, "calculation_performed": invocations > 0,
        "executor_invocation_count": invocations,
        "model_revision": execution.get("model_revision"), "manifest_sha256": execution.get("manifest_sha256"),
        "ranges": rows, "p4_results_reused": True, "p4_recalculation_inside_p5": False,
        "selectivity_integral_evaluated": False, "professional_emission": False,
    }


def assessment_checks(summary):
    return [{"device_id": row["request"]["downstream_device_id"], "range_id": row["range_id"],
             "check": "temporal_coordination_range", "status": (row["result"].get("status", "NOT_EVALUABLE") if isinstance(row["result"], dict) else "NOT_EVALUABLE"),
             "result_usable": row["result_usable"]}
            for row in summary["ranges"]]
