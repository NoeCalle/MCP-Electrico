"""P12 — escenarios operativos y contingencias explícitas multiindustria.

P12 no está ligado a una industria concreta. Su contrato inicial permite declarar
cambios topológicos explícitos y verificar continuidad de servicio sobre un
modelo ya soportado por P8/P10.

Reglas v1:
- no se seleccionan contingencias automáticamente;
- no se infieren maniobras;
- no hay load shedding automático;
- solo se abren/cierran Line.* y Transformer.* ya existentes;
- cada escenario reconstruye el modelo base y restaura exactamente su estado;
- la continuidad de servicio usa umbrales de tensión declarados por el usuario;
- no hay emisión profesional.
"""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any

from opendssdirect import dss

from . import core, real_model_materializer, workspace_state

SCHEMA = "MCP_ELECTRICO_P12_OPERATING_SCENARIOS_V1"
STATUS_READY = "READY_FOR_SCENARIO_EXECUTION"
STATUS_BLOCKED = "BLOCKED_SCENARIO_INPUTS"
EXECUTION_COMPLETED = "SCENARIO_SET_EXECUTION_COMPLETED"
EXECUTION_BLOCKED = "SCENARIO_SET_EXECUTION_BLOCKED"
SCENARIO_PASS = "PASS"
SCENARIO_FAIL = "FAIL"

_ALLOWED_PURPOSES = {
    "CONTINGENCY",
    "MAINTENANCE",
    "ALTERNATE_CONFIGURATION",
    "OPERATING_MODE",
    "EMERGENCY",
}
_ALLOWED_ACTIONS = {"OPEN_ELEMENT", "CLOSE_ELEMENT"}
_ALLOWED_SWITCHABLE_PREFIXES = ("line.", "transformer.")


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if isfinite(result) else None


def _issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _topology_index(manifest: dict[str, Any]) -> tuple[set[str], dict[str, dict[str, Any]]]:
    topology = manifest.get("topology") or {}
    switchable: set[str] = set()
    loads: dict[str, dict[str, Any]] = {}

    for collection in ("lines", "transformers"):
        for item in topology.get(collection) or []:
            if isinstance(item, dict) and _present(item.get("id")):
                switchable.add(str(item["id"]).strip())

    for item in topology.get("loads") or []:
        if isinstance(item, dict) and _present(item.get("id")):
            loads[str(item["id"]).strip()] = item

    return switchable, loads


def validar_paquete(manifest: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
    """Valida un paquete P12 sin construir ni modificar el modelo."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest debe ser dict.")
    if not isinstance(package, dict):
        raise TypeError("package debe ser dict.")

    issues: list[dict[str, str]] = []
    switchable, loads = _topology_index(manifest)

    project_id = str((manifest.get("project") or {}).get("id") or "").strip()
    declared_project = str(package.get("project_id") or "").strip()
    if not declared_project:
        issues.append(_issue("P12A001", "project_id", "El paquete de escenarios requiere project_id explícito."))
    elif project_id and declared_project != project_id:
        issues.append(_issue("P12A002", "project_id", "project_id no coincide con el manifiesto eléctrico."))

    if not _present(package.get("source_reference")):
        issues.append(_issue("P12A003", "source_reference", "El paquete requiere una referencia de procedencia."))

    scenarios = package.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        issues.append(_issue("P12A004", "scenarios", "Se requiere al menos un escenario explícito."))
        scenarios = []

    seen_scenarios: set[str] = set()
    for i, scenario in enumerate(scenarios):
        path = f"scenarios[{i}]"
        if not isinstance(scenario, dict):
            issues.append(_issue("P12A005", path, "Cada escenario debe ser un objeto estructurado."))
            continue

        sid = str(scenario.get("id") or "").strip()
        if not sid:
            issues.append(_issue("P12A006", f"{path}.id", "El escenario requiere id."))
        elif sid.lower() in seen_scenarios:
            issues.append(_issue("P12A007", f"{path}.id", "No se permiten IDs de escenario duplicados."))
        else:
            seen_scenarios.add(sid.lower())

        for key in ("name", "source_reference"):
            if not _present(scenario.get(key)):
                issues.append(_issue("P12A008", f"{path}.{key}", f"El escenario requiere {key}."))

        purpose = str(scenario.get("purpose") or "").strip().upper()
        if purpose not in _ALLOWED_PURPOSES:
            issues.append(_issue(
                "P12A009",
                f"{path}.purpose",
                "purpose debe ser CONTINGENCY, MAINTENANCE, ALTERNATE_CONFIGURATION, OPERATING_MODE o EMERGENCY.",
            ))

        actions = scenario.get("actions")
        if not isinstance(actions, list) or not actions:
            issues.append(_issue("P12A010", f"{path}.actions", "P12 v1 requiere al menos una maniobra explícita."))
            actions = []

        seen_elements: set[str] = set()
        for j, action in enumerate(actions):
            apath = f"{path}.actions[{j}]"
            if not isinstance(action, dict):
                issues.append(_issue("P12A011", apath, "Cada maniobra debe ser un objeto."))
                continue

            kind = str(action.get("action") or "").strip().upper()
            element = str(action.get("element_id") or "").strip()
            if kind not in _ALLOWED_ACTIONS:
                issues.append(_issue("P12A012", f"{apath}.action", "action debe ser OPEN_ELEMENT o CLOSE_ELEMENT."))
            if not element:
                issues.append(_issue("P12A013", f"{apath}.element_id", "La maniobra requiere element_id."))
            elif not element.lower().startswith(_ALLOWED_SWITCHABLE_PREFIXES):
                issues.append(_issue(
                    "P12A014",
                    f"{apath}.element_id",
                    "P12 v1 limita maniobras a Line.* y Transformer.*.",
                ))
            elif element not in switchable:
                issues.append(_issue("P12A015", f"{apath}.element_id", "El elemento no existe en la topología declarada."))

            if element:
                key = element.lower()
                if key in seen_elements:
                    issues.append(_issue(
                        "P12A016",
                        apath,
                        "Un mismo escenario no puede ordenar dos estados distintos sobre el mismo elemento.",
                    ))
                seen_elements.add(key)

            if not _present(action.get("source_reference")):
                issues.append(_issue("P12A017", f"{apath}.source_reference", "Cada maniobra requiere procedencia explícita."))

        requirements = scenario.get("service_requirements")
        if not isinstance(requirements, dict):
            issues.append(_issue(
                "P12A020",
                f"{path}.service_requirements",
                "service_requirements debe declararse explícitamente.",
            ))
            continue

        if not isinstance(requirements.get("require_powerflow_convergence"), bool):
            issues.append(_issue(
                "P12A021",
                f"{path}.service_requirements.require_powerflow_convergence",
                "Debe declararse true/false; P12 no lo asume.",
            ))

        critical = requirements.get("critical_loads")
        if not isinstance(critical, list):
            issues.append(_issue(
                "P12A022",
                f"{path}.service_requirements.critical_loads",
                "critical_loads debe ser una lista explícita, incluso si está vacía.",
            ))
            critical = []

        seen_loads: set[str] = set()
        for j, item in enumerate(critical):
            cpath = f"{path}.service_requirements.critical_loads[{j}]"
            if not isinstance(item, dict):
                issues.append(_issue("P12A023", cpath, "Cada requisito de carga debe ser un objeto."))
                continue
            load_id = str(item.get("load_id") or "").strip()
            if not load_id:
                issues.append(_issue("P12A024", f"{cpath}.load_id", "load_id es obligatorio."))
            elif load_id not in loads:
                issues.append(_issue("P12A025", f"{cpath}.load_id", "La carga no existe en topology.loads."))
            elif load_id.lower() in seen_loads:
                issues.append(_issue("P12A026", f"{cpath}.load_id", "Carga crítica duplicada en el mismo escenario."))
            else:
                seen_loads.add(load_id.lower())

            vmin = _number(item.get("minimum_voltage_pu"))
            if vmin is None or vmin <= 0 or vmin > 1.2:
                issues.append(_issue(
                    "P12A027",
                    f"{cpath}.minimum_voltage_pu",
                    "minimum_voltage_pu debe ser >0 y <=1.2.",
                ))
            vmax_raw = item.get("maximum_voltage_pu")
            if vmax_raw is not None:
                vmax = _number(vmax_raw)
                if vmax is None or vmax <= 0 or vmax > 1.5:
                    issues.append(_issue(
                        "P12A028",
                        f"{cpath}.maximum_voltage_pu",
                        "maximum_voltage_pu debe ser >0 y <=1.5 cuando se declara.",
                    ))
                elif vmin is not None and vmax < vmin:
                    issues.append(_issue("P12A029", cpath, "maximum_voltage_pu no puede ser menor que minimum_voltage_pu."))

            if not _present(item.get("source_reference")):
                issues.append(_issue("P12A030", f"{cpath}.source_reference", "El criterio de servicio requiere procedencia."))

    ready = not issues and bool(scenarios)
    return {
        "schema": SCHEMA,
        "validation_status": STATUS_READY if ready else STATUS_BLOCKED,
        "ready_for_execution": ready,
        "scenario_count": len(scenarios),
        "issues": issues,
        "issue_count": len(issues),
        "electrical_calculation_performed": False,
        "model_mutation_performed": False,
        "automatic_contingency_selection": False,
        "automatic_switching": False,
        "automatic_load_shedding": False,
        "professional_emission": False,
    }


def _element_open_state(element: str) -> bool:
    if not dss.Circuit.SetActiveElement(element):
        raise ValueError(f"Elemento no encontrado en OpenDSS: {element}")
    return bool(dss.CktElement.IsOpen(1, 0))


def _set_element_state(element: str, *, open_state: bool) -> None:
    command = "Open" if open_state else "Close"
    dss(f"{command} {element} term=1")


def _load_bus_map(manifest: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in (manifest.get("topology") or {}).get("loads") or []:
        if isinstance(item, dict) and _present(item.get("id")) and _present(item.get("bus")):
            result[str(item["id"]).strip()] = str(item["bus"]).strip()
    return result


def _evaluate_service(
    manifest: dict[str, Any],
    scenario: dict[str, Any],
    flow: dict[str, Any],
) -> dict[str, Any]:
    requirements = scenario["service_requirements"]
    load_buses = _load_bus_map(manifest)
    voltage_map = flow.get("voltajes_por_bus") or {}
    checks: list[dict[str, Any]] = []

    for item in requirements.get("critical_loads") or []:
        load_id = str(item["load_id"]).strip()
        bus = load_buses[load_id]
        bus_result = voltage_map.get(bus) or voltage_map.get(bus.lower()) or {}
        values = [float(v) for v in (bus_result.get("voltajes_pu") or [])]
        vmin_actual = min(values) if values else None
        vmax_actual = max(values) if values else None
        minimum = float(item["minimum_voltage_pu"])
        maximum = float(item["maximum_voltage_pu"]) if item.get("maximum_voltage_pu") is not None else None
        min_ok = vmin_actual is not None and vmin_actual >= minimum
        max_ok = maximum is None or (vmax_actual is not None and vmax_actual <= maximum)
        checks.append({
            "load_id": load_id,
            "bus": bus,
            "voltage_pu": values,
            "minimum_voltage_pu": minimum,
            "maximum_voltage_pu": maximum,
            "minimum_ok": min_ok,
            "maximum_ok": max_ok,
            "service_ok": bool(min_ok and max_ok),
            "source_reference": item["source_reference"],
        })

    convergence_required = requirements["require_powerflow_convergence"]
    convergence_ok = bool(flow.get("convergio")) if convergence_required else True
    return {
        "require_powerflow_convergence": convergence_required,
        "powerflow_converged": bool(flow.get("convergio")),
        "convergence_ok": convergence_ok,
        "critical_load_checks": checks,
        "all_critical_loads_ok": all(item["service_ok"] for item in checks),
        "service_requirements_met": convergence_ok and all(item["service_ok"] for item in checks),
    }


def _execute_one(manifest: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    build = real_model_materializer.materializar_modelo(deepcopy(manifest))
    if build.get("materializer_status") != real_model_materializer.STATUS_BUILT:
        return {
            "scenario_id": scenario.get("id"),
            "execution_status": "BLOCKED_BY_BASE_MODEL",
            "issues": deepcopy(build.get("issues") or []),
            "model_restored": False,
            "professional_emission": False,
        }
    if int(build.get("engine_defaults_retained_count") or 0) != 0:
        return {
            "scenario_id": scenario.get("id"),
            "execution_status": "BLOCKED_BY_ENGINE_DEFAULTS",
            "issues": deepcopy(build.get("engine_defaults_retained") or []),
            "model_restored": False,
            "professional_emission": False,
        }

    actions = scenario.get("actions") or []
    initial = {str(item["element_id"]): _element_open_state(str(item["element_id"])) for item in actions}
    revision_before = workspace_state.status().get("model_revision")
    action_results: list[dict[str, Any]] = []
    flow: dict[str, Any] | None = None
    service: dict[str, Any] | None = None
    runtime_error: str | None = None

    try:
        for item in actions:
            element = str(item["element_id"])
            requested_open = str(item["action"]).upper() == "OPEN_ELEMENT"
            _set_element_state(element, open_state=requested_open)
            action_results.append({
                "element_id": element,
                "action": str(item["action"]).upper(),
                "effective_open_state": _element_open_state(element),
                "source_reference": item["source_reference"],
            })

        flow = core.ejecutar_flujo_potencia()
        service = _evaluate_service(manifest, scenario, flow)
    except Exception as exc:
        runtime_error = f"{type(exc).__name__}: {exc}"
    finally:
        for element, open_state in initial.items():
            _set_element_state(element, open_state=open_state)
        dss("Solve")

    restored = all(_element_open_state(element) == open_state for element, open_state in initial.items())
    revision_after = workspace_state.status().get("model_revision")
    restored_converged = bool(dss.Solution.Converged())

    if runtime_error is not None:
        return {
            "scenario_id": scenario.get("id"),
            "execution_status": "SCENARIO_EXECUTION_ERROR",
            "issues": [{"code": "P12B900", "path": "execution", "message": runtime_error}],
            "action_results": action_results,
            "model_restored": restored,
            "restored_powerflow_converged": restored_converged,
            "model_revision_unchanged": revision_before == revision_after,
            "automatic_contingency_selection": False,
            "automatic_switching": False,
            "automatic_load_shedding": False,
            "professional_emission": False,
        }

    assert flow is not None and service is not None
    scenario_status = SCENARIO_PASS if service["service_requirements_met"] else SCENARIO_FAIL
    return {
        "scenario_id": scenario["id"],
        "scenario_name": scenario["name"],
        "purpose": str(scenario["purpose"]).upper(),
        "execution_status": "SCENARIO_EXECUTED",
        "scenario_status": scenario_status,
        "action_results": action_results,
        "power_flow": flow,
        "service": service,
        "model_restored": restored,
        "restored_powerflow_converged": restored_converged,
        "model_revision_unchanged": revision_before == revision_after,
        "explicit_actions_only": True,
        "automatic_contingency_selection": False,
        "automatic_switching": False,
        "automatic_load_shedding": False,
        "crosscheck": False,
        "professional_emission": False,
    }


def ejecutar_paquete(manifest: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta escenarios independientes; cada uno reconstruye y restaura el modelo base."""
    validation = validar_paquete(manifest, package)
    if not validation["ready_for_execution"]:
        return {
            "schema": SCHEMA,
            "execution_status": EXECUTION_BLOCKED,
            "validation": validation,
            "scenario_results": [],
            "electrical_calculation_performed": False,
            "automatic_contingency_selection": False,
            "automatic_switching": False,
            "automatic_load_shedding": False,
            "professional_emission": False,
        }

    results = [_execute_one(manifest, scenario) for scenario in package["scenarios"]]
    executed = [item for item in results if item.get("execution_status") == "SCENARIO_EXECUTED"]
    return {
        "schema": SCHEMA,
        "execution_status": EXECUTION_COMPLETED,
        "validation": validation,
        "scenario_results": results,
        "summary": {
            "total": len(results),
            "executed": len(executed),
            "pass": sum(1 for item in executed if item.get("scenario_status") == SCENARIO_PASS),
            "fail": sum(1 for item in executed if item.get("scenario_status") == SCENARIO_FAIL),
            "blocked_or_error": len(results) - len(executed),
        },
        "scenario_independence": "REBUILD_BASE_BEFORE_EACH_SCENARIO",
        "model_restored_after_each_scenario": all(item.get("model_restored") is True for item in results),
        "electrical_calculation_performed": bool(executed),
        "automatic_contingency_selection": False,
        "automatic_switching": False,
        "automatic_load_shedding": False,
        "crosscheck": False,
        "professional_emission": False,
    }
