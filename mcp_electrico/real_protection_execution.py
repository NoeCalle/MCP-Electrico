"""P8D2 — binding explícito de resultados P4 hacia ejecución P5.

P8D2 no selecciona una falla, barra, caso ni magnitud automáticamente. Cada
protección debe declarar de forma inequívoca qué resultado P4 ya ejecutado
alimenta su evaluación. El bloque reutiliza la ejecución P8D1 de la misma
corrida y no relanza un cortocircuito diferente dentro de P5.

Alcance inicial:
- capacidad de corte P5C con semántica propia de breaker/fuse;
- evaluación TCC y promoción a clearing time P5D cuando el dataset numérico
  real está dentro de dominio y usa TOTAL_CLEARING_TIME;
- soportabilidad térmica P5C únicamente cuando el binding aporta k, sección y
  sus procedencias explícitas;
- sin dispatch automático, sin fault binding automático, sin cross-check y sin
  emisión profesional.
"""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any

from . import (
    protection_checks,
    protection_clearing_time,
    protection_data,
    real_controlled_execution,
    workspace_state,
)

SCHEMA = "MCP_ELECTRICO_P8D2_PROTECTION_EXECUTION_V1"
STATUS_BLOCKED_BINDING = "BLOCKED_BY_EXPLICIT_FAULT_BINDING"
STATUS_BLOCKED_P8D1 = "BLOCKED_BY_P8D1_EXECUTION"
STATUS_PARTIAL = "PROTECTION_EXECUTION_PARTIAL_TCC_NOT_READY"
STATUS_COMPLETED = "PROTECTION_EXECUTION_COMPLETED"

PROTECTION_SCOPE = "PROTECTION_TCC"
SC_3PH = real_controlled_execution.SC_3PH
SC_1PH = real_controlled_execution.SC_1PH
_ALLOWED_FAULT_TYPES = {"3ph", "1ph-ground"}
_ALLOWED_CASES = {"max", "min"}
_ALLOWED_CURRENT_QUANTITIES = {"ikss_ka"}


def _issue(code: str, message: str, *, path: str | None = None, device_id: str | None = None) -> dict[str, Any]:
    return {"code": code, "message": message, "path": path, "device_id": device_id}


def _positive(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) and number > 0 else None


def _device_key(raw: Any) -> str:
    value = str(raw or "").strip()
    if value.lower().startswith("protection."):
        value = value.split(".", 1)[1]
    return value.lower()


def _normalize_fault_type(raw: Any) -> str:
    value = str(raw or "").strip().lower().replace("_", "-")
    aliases = {
        "3ph": "3ph",
        "3-phase": "3ph",
        "3phase": "3ph",
        "1ph-ground": "1ph-ground",
        "1phground": "1ph-ground",
        "1ph-g": "1ph-ground",
        "single-phase-ground": "1ph-ground",
    }
    return aliases.get(value, value)


def _binding_preflight(manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    protection = manifest.get("protection") or {}
    devices = protection.get("devices") or []
    bindings = protection.get("fault_bindings") or []
    issues: list[dict[str, Any]] = []

    if PROTECTION_SCOPE not in {
        str(scope).strip().upper() for scope in manifest.get("requested_scope") or []
    }:
        issues.append(_issue(
            "P8D2B001",
            "P8D2 requiere PROTECTION_TCC dentro de requested_scope.",
            path="requested_scope",
        ))

    if not isinstance(devices, list) or not devices:
        issues.append(_issue("P8D2B002", "No hay dispositivos P5 declarados.", path="protection.devices"))
        return [], issues
    if not isinstance(bindings, list) or not bindings:
        issues.append(_issue(
            "P8D2B003",
            "PROTECTION_TCC requiere protection.fault_bindings explícito; no se selecciona una falla automáticamente.",
            path="protection.fault_bindings",
        ))
        return [], issues

    declared: dict[str, str] = {}
    for index, device in enumerate(devices):
        if not isinstance(device, dict):
            issues.append(_issue("P8D2B004", "Dispositivo P5 no estructurado.", path=f"protection.devices[{index}]"))
            continue
        raw = str(device.get("id") or "").strip()
        key = _device_key(raw)
        if not key:
            issues.append(_issue("P8D2B005", "Dispositivo sin id.", path=f"protection.devices[{index}].id"))
            continue
        declared[key] = raw

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, binding in enumerate(bindings):
        path = f"protection.fault_bindings[{index}]"
        if not isinstance(binding, dict):
            issues.append(_issue("P8D2B006", "Binding de falla no estructurado.", path=path))
            continue

        device_raw = str(binding.get("device_id") or "").strip()
        key = _device_key(device_raw)
        if not key:
            issues.append(_issue("P8D2B007", "device_id es obligatorio.", path=f"{path}.device_id"))
            continue
        if key not in declared:
            issues.append(_issue(
                "P8D2B008",
                "El binding referencia un dispositivo que no existe en protection.devices.",
                path=f"{path}.device_id",
                device_id=device_raw,
            ))
        if key in seen:
            issues.append(_issue(
                "P8D2B009",
                "P8D2 v1 admite exactamente un binding de falla por dispositivo; no se elige entre alternativas.",
                path=path,
                device_id=device_raw,
            ))
        seen.add(key)

        bus = str(binding.get("fault_bus") or "").strip()
        fault_type = _normalize_fault_type(binding.get("fault_type"))
        case = str(binding.get("case") or "").strip().lower()
        quantity = str(binding.get("current_quantity") or "").strip().lower()
        voltage = _positive(binding.get("operating_voltage_kv"))
        reference = str(binding.get("source_reference") or "").strip()

        if not bus:
            issues.append(_issue("P8D2B010", "fault_bus es obligatorio.", path=f"{path}.fault_bus", device_id=device_raw))
        if fault_type not in _ALLOWED_FAULT_TYPES:
            issues.append(_issue(
                "P8D2B011",
                "fault_type debe ser 3ph o 1ph-ground.",
                path=f"{path}.fault_type",
                device_id=device_raw,
            ))
        if case not in _ALLOWED_CASES:
            issues.append(_issue("P8D2B012", "case debe ser max o min.", path=f"{path}.case", device_id=device_raw))
        if quantity not in _ALLOWED_CURRENT_QUANTITIES:
            issues.append(_issue(
                "P8D2B013",
                "P8D2 v1 consume únicamente current_quantity=ikss_ka; no se sustituye otra magnitud.",
                path=f"{path}.current_quantity",
                device_id=device_raw,
            ))
        if voltage is None:
            issues.append(_issue(
                "P8D2B014",
                "operating_voltage_kv debe ser explícita, finita y >0.",
                path=f"{path}.operating_voltage_kv",
                device_id=device_raw,
            ))
        if not reference:
            issues.append(_issue(
                "P8D2B015",
                "source_reference del binding es obligatorio para trazabilidad.",
                path=f"{path}.source_reference",
                device_id=device_raw,
            ))

        thermal = binding.get("thermal_check")
        thermal_norm = None
        if thermal is not None:
            if not isinstance(thermal, dict):
                issues.append(_issue("P8D2B020", "thermal_check debe ser un objeto.", path=f"{path}.thermal_check", device_id=device_raw))
            else:
                section = _positive(thermal.get("section_mm2"))
                k_value = _positive(thermal.get("k_a_sqrt_s_per_mm2"))
                k_reference = str(thermal.get("k_source_reference") or "").strip()
                section_reference = str(thermal.get("section_source_reference") or "").strip()
                if section is None:
                    issues.append(_issue("P8D2B021", "thermal_check.section_mm2 debe ser >0.", path=f"{path}.thermal_check.section_mm2", device_id=device_raw))
                if k_value is None:
                    issues.append(_issue("P8D2B022", "thermal_check.k_a_sqrt_s_per_mm2 debe ser >0.", path=f"{path}.thermal_check.k_a_sqrt_s_per_mm2", device_id=device_raw))
                if not k_reference:
                    issues.append(_issue("P8D2B023", "thermal_check requiere k_source_reference.", path=f"{path}.thermal_check.k_source_reference", device_id=device_raw))
                if not section_reference:
                    issues.append(_issue("P8D2B024", "thermal_check requiere section_source_reference.", path=f"{path}.thermal_check.section_source_reference", device_id=device_raw))
                thermal_norm = {
                    "section_mm2": section,
                    "k_a_sqrt_s_per_mm2": k_value,
                    "k_source_reference": k_reference,
                    "section_source_reference": section_reference,
                }

        normalized.append({
            "device_id": declared.get(key, device_raw),
            "device_key": key,
            "fault_bus": bus,
            "fault_type": fault_type,
            "case": case,
            "current_quantity": quantity,
            "operating_voltage_kv": voltage,
            "source_reference": reference,
            "thermal_check": thermal_norm,
        })

    missing = sorted(set(declared) - seen)
    for key in missing:
        issues.append(_issue(
            "P8D2B016",
            "Cada dispositivo P5 requiere exactamente un binding de falla explícito.",
            path="protection.fault_bindings",
            device_id=declared[key],
        ))

    return normalized, issues


def _targets_for(execution: dict[str, Any], fault_type: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if fault_type == "3ph":
        scope = SC_3PH
    else:
        scope = SC_1PH
    aggregate = (execution.get("results") or {}).get(scope)
    if not isinstance(aggregate, dict):
        return None, [_issue(
            "P8D2R001",
            f"El resultado P8D1 no contiene el scope P4 requerido: {scope}.",
            path=f"results.{scope}",
        )]
    return aggregate, []


def _resolve_fault_result(execution: dict[str, Any], binding: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    aggregate, issues = _targets_for(execution, binding["fault_type"])
    if issues or aggregate is None:
        return None, issues

    bus = binding["fault_bus"].lower()
    matches = [
        item for item in aggregate.get("targets") or []
        if str(item.get("bus") or "").strip().lower() == bus
    ]
    if len(matches) != 1:
        return None, [_issue(
            "P8D2R002",
            "fault_bus no identifica exactamente un target P4 ya ejecutado; no se selecciona otra barra.",
            device_id=binding["device_id"],
        )]

    target = matches[0]
    pair = target.get("result") or {}
    if binding["fault_type"] == "3ph":
        atomic = (pair.get("scenarios") or {}).get(binding["case"])
    else:
        atomic = pair.get(binding["case"])
    if not isinstance(atomic, dict):
        return None, [_issue(
            "P8D2R003",
            "El caso MAX/MIN declarado no existe dentro del target P4 ejecutado.",
            device_id=binding["device_id"],
        )]
    if atomic.get("ok") is not True:
        return None, [_issue(
            "P8D2R004",
            "El resultado P4 seleccionado no está calculado satisfactoriamente; P5 no consume una falla inválida.",
            device_id=binding["device_id"],
        )]

    result_bus = str(atomic.get("bus") or "").strip().lower()
    if result_bus != bus:
        return None, [_issue(
            "P8D2R005",
            "La barra canónica del resultado P4 no coincide con fault_bus del binding.",
            device_id=binding["device_id"],
        )]
    result_case = str(atomic.get("case") or "").strip().lower()
    if result_case != binding["case"]:
        return None, [_issue(
            "P8D2R006",
            "El case del resultado P4 no coincide con el binding explícito.",
            device_id=binding["device_id"],
        )]

    current = _positive((atomic.get("results") or {}).get(binding["current_quantity"]))
    if current is None:
        return None, [_issue(
            "P8D2R007",
            "La magnitud de corriente solicitada no existe o no es positiva en el resultado P4 seleccionado.",
            device_id=binding["device_id"],
        )]

    atomic_vn = _positive(atomic.get("vn_kv"))
    if atomic_vn is not None and abs(atomic_vn - float(binding["operating_voltage_kv"])) > 1e-9:
        return None, [_issue(
            "P8D2R008",
            "operating_voltage_kv del binding no coincide con vn_kv del resultado 3F seleccionado.",
            device_id=binding["device_id"],
        )]

    return {
        "fault_current_ka": current,
        "fault_bus": str(atomic.get("bus")),
        "fault_type": binding["fault_type"],
        "case": binding["case"],
        "current_quantity": binding["current_quantity"],
        "operating_voltage_kv": float(binding["operating_voltage_kv"]),
        "aggregate_schema": aggregate.get("schema"),
        "pair_schema": pair.get("schema"),
        "atomic_schema": atomic.get("schema"),
        "engine": deepcopy(atomic.get("engine")),
        "target_standard": deepcopy(atomic.get("target_standard")),
        "p4_input_projection": deepcopy(atomic.get("input_projection") or atomic.get("inputs")),
        "binding_source_reference": binding["source_reference"],
        "automatic_target_selection": False,
    }, []


def _evaluate_device(binding: dict[str, Any], fault: dict[str, Any]) -> dict[str, Any]:
    device = protection_data.obtener_dispositivo(binding["device_id"])
    if not device:
        return {
            "device_id": binding["device_id"],
            "status": "DEVICE_NOT_FOUND_AFTER_P8D1",
            "issues": [_issue("P8D2P001", "El dispositivo no quedó materializado por P8D1/P8C5.", device_id=binding["device_id"])],
            "professional_emission": False,
        }

    source_text = (
        f"P8D2 explicit binding {binding['source_reference']} | "
        f"P4 {fault['atomic_schema']} {fault['fault_type']} {fault['case']} {fault['fault_bus']} {fault['current_quantity']}"
    )
    breaking = protection_checks.evaluar_capacidad_corte(
        device["id"],
        fault["fault_current_ka"],
        fault["operating_voltage_kv"],
        source_text,
        tipo_falla=fault["fault_type"],
        escenario=fault["case"],
    )

    clearing = protection_clearing_time.evaluar_tiempo_despeje(
        device["id"],
        fault["fault_current_ka"] * 1000.0,
    )

    thermal: dict[str, Any]
    thermal_request = binding.get("thermal_check")
    if thermal_request is None:
        thermal = {
            "status": "NOT_REQUESTED",
            "calculation_performed": False,
            "automatic_defaults": False,
            "professional_emission": False,
        }
    elif clearing.get("status") != "CLEARING_TIME_READY":
        thermal = {
            "status": "NOT_READY_CLEARING_TIME_REQUIRED",
            "calculation_performed": False,
            "clearing_time_status": clearing.get("status"),
            "automatic_defaults": False,
            "professional_emission": False,
        }
    else:
        clearing_time = float((clearing.get("clearing_time") or {})["conservative_time_s"])
        time_source = (
            f"P5D dataset={clearing.get('dataset_id')} curve={clearing.get('curve_id')} "
            f"semantics={clearing.get('time_semantics')} field=conservative_time_s"
        )
        thermal = protection_checks.evaluar_soportabilidad_termica_conductor(
            device["protected_element"],
            fault["fault_current_ka"],
            clearing_time,
            float(thermal_request["section_mm2"]),
            float(thermal_request["k_a_sqrt_s_per_mm2"]),
            thermal_request["k_source_reference"],
            time_source,
            thermal_request["section_source_reference"],
        )

    return {
        "device_id": device["id"],
        "device_type": device["device_type"],
        "protected_element": device["protected_element"],
        "binding": deepcopy(binding),
        "fault_provenance": deepcopy(fault),
        "breaking_capacity": breaking,
        "clearing_time": clearing,
        "thermal_check": thermal,
        "fault_binding_explicit": True,
        "automatic_fault_binding": False,
        "professional_emission": False,
    }


def ejecutar_protecciones(manifest: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta P5 consumiendo únicamente resultados P4 ligados explícitamente."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest debe ser dict.")

    bindings, binding_issues = _binding_preflight(deepcopy(manifest))
    if binding_issues:
        blocked_workspace = workspace_state.reset_for_circuit("p8d2_binding_preflight_blocked")
        return {
            "schema": SCHEMA,
            "execution_status": STATUS_BLOCKED_BINDING,
            "issues": binding_issues,
            "bindings": bindings,
            "p8d1_execution": None,
            "device_results": [],
            "model_revision": blocked_workspace.get("model_revision"),
            "workspace_study_recorded": False,
            "electrical_calculation_performed": False,
            "protection_calculation_performed": False,
            "tcc_evaluation_performed": False,
            "automatic_dispatch": False,
            "automatic_fault_binding": False,
            "crosscheck": False,
            "professional_emission": False,
            "next_gate": "P8D2_REPAIR_EXPLICIT_FAULT_BINDING",
        }

    execution = real_controlled_execution.ejecutar_controlado(deepcopy(manifest))
    if execution.get("execution_status") != real_controlled_execution.STATUS_COMPLETED_P5_PENDING:
        return {
            "schema": SCHEMA,
            "execution_status": STATUS_BLOCKED_P8D1,
            "issues": [_issue(
                "P8D2E001",
                "P8D1 no terminó con P5 explícitamente pendiente; P8D2 no consume resultados incompletos.",
            )],
            "bindings": bindings,
            "p8d1_execution": execution,
            "device_results": [],
            "model_revision": execution.get("model_revision"),
            "workspace_study_recorded": False,
            "electrical_calculation_performed": bool(execution.get("electrical_calculation_performed")),
            "protection_calculation_performed": False,
            "tcc_evaluation_performed": False,
            "automatic_dispatch": False,
            "automatic_fault_binding": False,
            "crosscheck": False,
            "professional_emission": False,
            "next_gate": "P8D1_REPAIR_BEFORE_P8D2",
        }

    resolution_issues: list[dict[str, Any]] = []
    resolved: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for binding in bindings:
        fault, issues = _resolve_fault_result(execution, binding)
        if issues or fault is None:
            resolution_issues.extend(issues)
        else:
            resolved.append((binding, fault))

    if resolution_issues:
        return {
            "schema": SCHEMA,
            "execution_status": STATUS_BLOCKED_BINDING,
            "issues": resolution_issues,
            "bindings": bindings,
            "p8d1_execution": execution,
            "device_results": [],
            "model_revision": execution.get("model_revision"),
            "workspace_study_recorded": False,
            "electrical_calculation_performed": True,
            "protection_calculation_performed": False,
            "tcc_evaluation_performed": False,
            "automatic_dispatch": False,
            "automatic_fault_binding": False,
            "crosscheck": False,
            "professional_emission": False,
            "next_gate": "P8D2_REPAIR_EXPLICIT_FAULT_BINDING",
        }

    revision_before = workspace_state.status().get("model_revision")
    if revision_before != execution.get("model_revision"):
        raise RuntimeError("P8D2EXEC001: model_revision cambió entre P8D1 y P8D2.")

    device_results = [_evaluate_device(binding, fault) for binding, fault in resolved]
    clearing_ready = all(
        (item.get("clearing_time") or {}).get("status") == "CLEARING_TIME_READY"
        for item in device_results
    )
    execution_status = STATUS_COMPLETED if clearing_ready else STATUS_PARTIAL

    aggregate = {
        "schema": "MCP_ELECTRICO_P8D2_PROTECTION_RESULTS_V1",
        "execution_status": execution_status,
        "model_revision": revision_before,
        "devices": deepcopy(device_results),
        "device_count": len(device_results),
        "all_clearing_times_ready": clearing_ready,
        "p4_results_reused": True,
        "p4_recalculation_inside_p5": False,
        "automatic_fault_binding": False,
        "professional_emission": False,
    }

    workspace_recorded = False
    if clearing_ready:
        workspace_state.record_study("protection_tcc", aggregate, action="p8d2_protection_tcc")
        workspace_recorded = True

    revision_after = workspace_state.status().get("model_revision")
    if revision_after != revision_before:
        raise RuntimeError("P8D2EXEC002: P5 modificó model_revision; los resultados no pueden promoverse.")

    return {
        "schema": SCHEMA,
        "execution_status": execution_status,
        "issues": [],
        "bindings": bindings,
        "p8d1_execution": execution,
        "device_results": device_results,
        "model_revision": revision_after,
        "workspace_study_recorded": workspace_recorded,
        "workspace_study": "protection_tcc" if workspace_recorded else None,
        "electrical_calculation_performed": True,
        "protection_calculation_performed": True,
        "tcc_evaluation_performed": True,
        "p4_results_reused": True,
        "p4_recalculation_inside_p5": False,
        "automatic_dispatch": False,
        "automatic_fault_binding": False,
        "crosscheck": False,
        "professional_emission": False,
        "next_gate": "P8E_WORKSPACE_AND_DOSSIER" if clearing_ready else "P8D2_TCC_REPAIR",
    }
