"""P8B — admisión fail-closed de datos para el primer piloto real.

Esta capa NO construye el modelo, NO calcula ingeniería y NO completa valores
faltantes. Solo revisa que un paquete de entrada declare la información mínima
antes de transferirla a P2/P3/P4/P5 y al workspace.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

SCHEMA = "MCP_ELECTRICO_P8B_REAL_PILOT_INTAKE_V1"
STATUS_READY = "READY_TO_BUILD_MODEL"
STATUS_BLOCKED = "BLOCKED_MISSING_INPUTS"

ALLOWED_SCOPE = {
    "POWER_FLOW",
    "VOLTAGE_DROP",
    "AMPACITY",
    "IEC60909_3PH_MAX_MIN",
    "IEC60909_1PH_GROUND_MAX_MIN",
    "PROTECTION_TCC",
}


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
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _positive(value: Any) -> bool:
    return _number(value) and float(value) > 0


def _nonnegative(value: Any) -> bool:
    return _number(value) and float(value) >= 0


def _get(data: dict[str, Any], path: str) -> Any:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _issue(code: str, path: str, message: str, scope: str = "BASE_MODEL") -> dict[str, str]:
    return {"code": code, "path": path, "message": message, "scope": scope}


def _topology_ids(manifest: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    topology = manifest.get("topology") or {}
    for collection in ("transformers", "lines", "loads"):
        for item in topology.get(collection) or []:
            if isinstance(item, dict) and _present(item.get("id")):
                result.add(str(item["id"]).strip())
    return result


def obtener_contrato_p8b() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "purpose": "PRE_MODEL_REAL_PROJECT_INPUT_ADMISSION",
        "allowed_scope": sorted(ALLOWED_SCOPE),
        "electrical_calculation": False,
        "model_mutation": False,
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
        "note": (
            "P8B verifica presencia, trazabilidad y plausibilidad básica de entradas. "
            "La suficiencia eléctrica final sigue siendo evaluada por los gates P2/P3/P4/P5 después de construir el modelo."
        ),
    }


def _base_issues(manifest: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    required = {
        "project.id": "Identificador del proyecto real.",
        "project.name": "Nombre del proyecto/subestación.",
        "project.source_reference": "Referencia del expediente/plano/fuente de datos.",
        "source.kv_ll": "Tensión nominal LL de la red aguas arriba.",
        "topology.buses": "Lista explícita de barras.",
        "topology.transformers": "Transformadores del alcance.",
        "topology.lines": "Líneas/cables del alcance.",
        "topology.loads": "Cargas del alcance.",
    }
    for index, (path, message) in enumerate(required.items(), start=1):
        if not _present(_get(manifest, path)):
            issues.append(_issue(f"P8B_BASE_{index:02d}", path, message))
    if _present(_get(manifest, "source.kv_ll")) and not _positive(_get(manifest, "source.kv_ll")):
        issues.append(_issue("P8B_BASE_09", "source.kv_ll", "La tensión nominal LL debe ser numérica y mayor que cero."))
    return issues


def _topology_issues(manifest: dict[str, Any]) -> list[dict[str, str]]:
    """Comprueba que el modelo base tenga datos suficientes para poder construirse.

    P8B sigue sin compilar OpenDSS ni mutar el modelo. Esta validación evita que
    POWER_FLOW/VOLTAGE_DROP queden verdes solo porque las listas no están vacías.
    """
    issues: list[dict[str, str]] = []
    topology = manifest.get("topology") or {}
    buses_raw = topology.get("buses") or []
    buses = [str(item).strip() for item in buses_raw if _present(item)]
    bus_set = set(buses)

    if len(buses) != len(buses_raw):
        issues.append(_issue("P8B_TOPO01", "topology.buses", "Cada barra debe tener un identificador no vacío."))
    if len(bus_set) != len(buses):
        issues.append(_issue("P8B_TOPO02", "topology.buses", "Los identificadores de barra deben ser únicos."))

    seen_ids: set[str] = set()

    for i, trafo in enumerate(topology.get("transformers") or []):
        if not isinstance(trafo, dict):
            issues.append(_issue("P8B_TOPO10", f"topology.transformers[{i}]", "Cada transformador debe ser un objeto estructurado."))
            continue
        for key in ("id", "bus_hv", "bus_lv", "kva", "kv_hv", "kv_lv", "uk_percent", "vector_group"):
            if not _present(trafo.get(key)):
                issues.append(_issue("P8B_TOPO11", f"topology.transformers[{i}].{key}", f"Dato de transformador requerido para construir el modelo: {key}."))
        for key in ("kva", "kv_hv", "kv_lv", "uk_percent"):
            if _present(trafo.get(key)) and not _positive(trafo.get(key)):
                issues.append(_issue("P8B_TOPO12", f"topology.transformers[{i}].{key}", f"{key} debe ser numérico y mayor que cero."))
        if not (_present(trafo.get("x_r")) or _present(trafo.get("load_loss_kw"))):
            issues.append(_issue("P8B_TOPO13", f"topology.transformers[{i}]", "Se requiere X/R o pérdidas de carga trazables para separar R/X."))
        elif _present(trafo.get("x_r")) and not _positive(trafo.get("x_r")):
            issues.append(_issue("P8B_TOPO14", f"topology.transformers[{i}].x_r", "X/R debe ser numérico y mayor que cero."))
        elif _present(trafo.get("load_loss_kw")) and not _nonnegative(trafo.get("load_loss_kw")):
            issues.append(_issue("P8B_TOPO15", f"topology.transformers[{i}].load_loss_kw", "Las pérdidas de carga no pueden ser negativas."))
        for key in ("bus_hv", "bus_lv"):
            if _present(trafo.get(key)) and str(trafo[key]).strip() not in bus_set:
                issues.append(_issue("P8B_TOPO16", f"topology.transformers[{i}].{key}", "La barra referenciada no existe en topology.buses."))
        if _present(trafo.get("id")):
            identifier = str(trafo["id"]).strip()
            if identifier in seen_ids:
                issues.append(_issue("P8B_TOPO17", f"topology.transformers[{i}].id", "El ID de elemento debe ser único en la topología."))
            seen_ids.add(identifier)

    for i, line in enumerate(topology.get("lines") or []):
        if not isinstance(line, dict):
            issues.append(_issue("P8B_TOPO20", f"topology.lines[{i}]", "Cada línea/cable debe ser un objeto estructurado."))
            continue
        for key in ("id", "bus1", "bus2", "phases", "length_km", "r1_ohm_km", "x1_ohm_km"):
            if not _present(line.get(key)):
                issues.append(_issue("P8B_TOPO21", f"topology.lines[{i}].{key}", f"Dato de línea requerido para construir el modelo: {key}."))
        if _present(line.get("phases")) and not _positive(line.get("phases")):
            issues.append(_issue("P8B_TOPO22", f"topology.lines[{i}].phases", "phases debe ser numérico y mayor que cero."))
        if _present(line.get("length_km")) and not _positive(line.get("length_km")):
            issues.append(_issue("P8B_TOPO23", f"topology.lines[{i}].length_km", "La longitud debe ser numérica y mayor que cero."))
        for key in ("r1_ohm_km", "x1_ohm_km"):
            if _present(line.get(key)) and not _nonnegative(line.get(key)):
                issues.append(_issue("P8B_TOPO24", f"topology.lines[{i}].{key}", f"{key} no puede ser negativo en el alcance pasivo P8B."))
        for key in ("bus1", "bus2"):
            if _present(line.get(key)) and str(line[key]).strip() not in bus_set:
                issues.append(_issue("P8B_TOPO25", f"topology.lines[{i}].{key}", "La barra referenciada no existe en topology.buses."))
        if _present(line.get("id")):
            identifier = str(line["id"]).strip()
            if identifier in seen_ids:
                issues.append(_issue("P8B_TOPO26", f"topology.lines[{i}].id", "El ID de elemento debe ser único en la topología."))
            seen_ids.add(identifier)

    for i, load in enumerate(topology.get("loads") or []):
        if not isinstance(load, dict):
            issues.append(_issue("P8B_TOPO30", f"topology.loads[{i}]", "Cada carga debe ser un objeto estructurado."))
            continue
        for key in ("id", "bus", "phases", "kv", "kw", "kvar"):
            if not _present(load.get(key)):
                issues.append(_issue("P8B_TOPO31", f"topology.loads[{i}].{key}", f"Dato de carga requerido para construir el modelo: {key}."))
        if _present(load.get("phases")) and not _positive(load.get("phases")):
            issues.append(_issue("P8B_TOPO32", f"topology.loads[{i}].phases", "phases debe ser numérico y mayor que cero."))
        if _present(load.get("kv")) and not _positive(load.get("kv")):
            issues.append(_issue("P8B_TOPO33", f"topology.loads[{i}].kv", "La tensión de carga debe ser numérica y mayor que cero."))
        if _present(load.get("kw")) and not _nonnegative(load.get("kw")):
            issues.append(_issue("P8B_TOPO34", f"topology.loads[{i}].kw", "kW no puede ser negativo en el alcance de carga pasiva P8B."))
        if _present(load.get("kvar")) and not _number(load.get("kvar")):
            issues.append(_issue("P8B_TOPO35", f"topology.loads[{i}].kvar", "kvar debe ser numérico; puede ser positivo o negativo."))
        if _present(load.get("bus")) and str(load["bus"]).strip() not in bus_set:
            issues.append(_issue("P8B_TOPO36", f"topology.loads[{i}].bus", "La barra referenciada no existe en topology.buses."))
        if _present(load.get("id")):
            identifier = str(load["id"]).strip()
            if identifier in seen_ids:
                issues.append(_issue("P8B_TOPO37", f"topology.loads[{i}].id", "El ID de elemento debe ser único en la topología."))
            seen_ids.add(identifier)

    return issues


def _short_circuit_issues(manifest: dict[str, Any], scope: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    source_fields = (
        ("P8B_SC01", "source.scc_max_mva", "Scc3 MAX explícita de la red aguas arriba."),
        ("P8B_SC02", "source.x_r_max", "X/R MAX explícito de la red aguas arriba."),
        ("P8B_SC03", "source.scc_min_mva", "Scc3 MIN explícita para escenario mínimo."),
        ("P8B_SC04", "source.x_r_min", "X/R MIN explícito para escenario mínimo."),
    )
    for code, path, message in source_fields:
        value = _get(manifest, path)
        if not _present(value):
            issues.append(_issue(code, path, message, scope))
        elif not _positive(value):
            issues.append(_issue(f"{code}V", path, f"{message} El valor debe ser numérico y mayor que cero.", scope))

    for i, line in enumerate(_get(manifest, "topology.lines") or []):
        if not isinstance(line, dict):
            continue
        if not _present(line.get("endtemp_min_c")):
            issues.append(_issue("P8B_SC21", f"topology.lines[{i}].endtemp_min_c", "Temperatura final explícita para cálculo MIN; no se inventa.", scope))
        elif not _positive(line.get("endtemp_min_c")):
            issues.append(_issue("P8B_SC24", f"topology.lines[{i}].endtemp_min_c", "La temperatura final MIN debe ser numérica y mayor que cero.", scope))
    return issues


def _ground_issues(manifest: dict[str, Any], scope: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for code, path in (
        ("P8B_Z001", "zero_sequence.source.r0_max_ohm"),
        ("P8B_Z002", "zero_sequence.source.x0_max_ohm"),
        ("P8B_Z003", "zero_sequence.source.r0_min_ohm"),
        ("P8B_Z004", "zero_sequence.source.x0_min_ohm"),
    ):
        value = _get(manifest, path)
        if not _present(value):
            issues.append(_issue(code, path, "Secuencia cero de fuente requerida para falla a tierra MAX/MIN.", scope))
        elif not _nonnegative(value):
            issues.append(_issue(f"{code}V", path, "La impedancia de secuencia cero no puede ser negativa en el alcance pasivo P8B.", scope))

    topology = manifest.get("topology") or {}
    known_line_ids = {
        str(item.get("id")).strip()
        for item in topology.get("lines") or []
        if isinstance(item, dict) and _present(item.get("id"))
    }
    known_transformer_ids = {
        str(item.get("id")).strip()
        for item in topology.get("transformers") or []
        if isinstance(item, dict) and _present(item.get("id"))
    }

    lines_z0 = _get(manifest, "zero_sequence.lines") or []
    transformers_z0 = _get(manifest, "zero_sequence.transformers") or []
    if not lines_z0:
        issues.append(_issue("P8B_Z010", "zero_sequence.lines", "R0/X0/C0 explícitos por línea/cable del alcance.", scope))
    else:
        seen: set[str] = set()
        for i, line in enumerate(lines_z0):
            if not isinstance(line, dict):
                issues.append(_issue("P8B_Z011", f"zero_sequence.lines[{i}]", "La ficha Z0 de línea debe ser un objeto estructurado.", scope))
                continue
            for key in ("id", "r0_ohm_km", "x0_ohm_km", "c0_nf_km"):
                if not _present(line.get(key)):
                    issues.append(_issue("P8B_Z011", f"zero_sequence.lines[{i}].{key}", f"Dato Z0 requerido: {key}.", scope))
            for key in ("r0_ohm_km", "x0_ohm_km", "c0_nf_km"):
                if _present(line.get(key)) and not _nonnegative(line.get(key)):
                    issues.append(_issue("P8B_Z012", f"zero_sequence.lines[{i}].{key}", f"{key} no puede ser negativo.", scope))
            if _present(line.get("id")):
                identifier = str(line["id"]).strip()
                if identifier not in known_line_ids:
                    issues.append(_issue("P8B_Z013", f"zero_sequence.lines[{i}].id", "La ficha Z0 debe referenciar una línea existente de topology.lines.", scope))
                if identifier in seen:
                    issues.append(_issue("P8B_Z014", f"zero_sequence.lines[{i}].id", "No se permiten fichas Z0 duplicadas para la misma línea.", scope))
                seen.add(identifier)

    if not transformers_z0:
        issues.append(_issue("P8B_Z020", "zero_sequence.transformers", "Ficha Z0 + neutro/puesta a tierra de transformador requerida.", scope))
    else:
        seen_t: set[str] = set()
        for i, trafo in enumerate(transformers_z0):
            if not isinstance(trafo, dict):
                issues.append(_issue("P8B_Z021", f"zero_sequence.transformers[{i}]", "La ficha Z0 de transformador debe ser un objeto estructurado.", scope))
                continue
            for key in ("id", "uk0_percent", "ur0_percent", "neutral_side", "neutral_mode"):
                if not _present(trafo.get(key)):
                    issues.append(_issue("P8B_Z021", f"zero_sequence.transformers[{i}].{key}", f"Dato de transformador Z0 requerido: {key}.", scope))
            for key in ("uk0_percent", "ur0_percent"):
                if _present(trafo.get(key)) and not _nonnegative(trafo.get(key)):
                    issues.append(_issue("P8B_Z022", f"zero_sequence.transformers[{i}].{key}", f"{key} no puede ser negativo.", scope))
            if _present(trafo.get("id")):
                identifier = str(trafo["id"]).strip()
                if identifier not in known_transformer_ids:
                    issues.append(_issue("P8B_Z023", f"zero_sequence.transformers[{i}].id", "La ficha Z0 debe referenciar un transformador existente de topology.transformers.", scope))
                if identifier in seen_t:
                    issues.append(_issue("P8B_Z024", f"zero_sequence.transformers[{i}].id", "No se permiten fichas Z0 duplicadas para el mismo transformador.", scope))
                seen_t.add(identifier)
    return issues


def _ampacity_issues(manifest: dict[str, Any], scope: str) -> list[dict[str, str]]:
    records = _get(manifest, "ampacity") or []
    if not records:
        return [_issue("P8B_P301", "ampacity", "Ficha de conductores/instalación/criterio Ib-In-Iz requerida.", scope)]
    issues: list[dict[str, str]] = []
    known_ids = _topology_ids(manifest)
    for i, item in enumerate(records):
        if not isinstance(item, dict):
            issues.append(_issue("P8B_P302", f"ampacity[{i}]", "La ficha P3 debe ser un objeto estructurado.", scope))
            continue
        for key in ("element_id", "conductor_code", "ib_a", "in_a", "installation_reference", "ampacity_reference"):
            if not _present(item.get(key)):
                issues.append(_issue("P8B_P302", f"ampacity[{i}].{key}", f"Entrada P3 requerida: {key}.", scope))
        for key in ("ib_a", "in_a"):
            if _present(item.get(key)) and not _positive(item.get(key)):
                issues.append(_issue("P8B_P303", f"ampacity[{i}].{key}", f"{key} debe ser numérico y mayor que cero.", scope))
        if _present(item.get("element_id")) and str(item["element_id"]).strip() not in known_ids:
            issues.append(_issue("P8B_P304", f"ampacity[{i}].element_id", "La ficha P3 debe referenciar un elemento existente de la topología.", scope))
    return issues


def _protection_issues(manifest: dict[str, Any], scope: str) -> list[dict[str, str]]:
    devices = _get(manifest, "protection.devices") or []
    datasets = _get(manifest, "protection.tcc_datasets") or []
    issues: list[dict[str, str]] = []
    known_ids = _topology_ids(manifest)
    if not devices:
        issues.append(_issue("P8B_P501", "protection.devices", "Dispositivos de protección y ratings explícitos requeridos.", scope))
    else:
        for i, item in enumerate(devices):
            if not isinstance(item, dict):
                issues.append(_issue("P8B_P502", f"protection.devices[{i}]", "El dispositivo P5 debe ser un objeto estructurado.", scope))
                continue
            for key in ("id", "type", "protected_element", "in_a", "ue_kv", "breaking_capacity_ka", "source_reference"):
                if not _present(item.get(key)):
                    issues.append(_issue("P8B_P502", f"protection.devices[{i}].{key}", f"Entrada P5 requerida: {key}.", scope))
            for key in ("in_a", "ue_kv", "breaking_capacity_ka"):
                if _present(item.get(key)) and not _positive(item.get(key)):
                    issues.append(_issue("P8B_P503", f"protection.devices[{i}].{key}", f"{key} debe ser numérico y mayor que cero.", scope))
            if _present(item.get("protected_element")) and str(item["protected_element"]).strip() not in known_ids:
                issues.append(_issue("P8B_P504", f"protection.devices[{i}].protected_element", "El dispositivo debe referenciar un elemento existente de la topología.", scope))
    if not datasets:
        issues.append(_issue("P8B_P510", "protection.tcc_datasets", "Curvas/datasets TCC trazables requeridos para coordinación.", scope))
    else:
        for i, item in enumerate(datasets):
            if not isinstance(item, dict):
                issues.append(_issue("P8B_P511", f"protection.tcc_datasets[{i}]", "El dataset TCC debe ser un objeto estructurado.", scope))
                continue
            for key in ("dataset_id", "time_semantics", "source_type", "source_reference"):
                if not _present(item.get(key)):
                    issues.append(_issue("P8B_P511", f"protection.tcc_datasets[{i}].{key}", f"Metadata TCC requerida: {key}.", scope))
    return issues


def evaluar_admision(manifest: dict[str, Any]) -> dict[str, Any]:
    """Evalúa un manifiesto de datos reales sin modificar el modelo eléctrico."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest debe ser dict.")

    requested = manifest.get("requested_scope") or []
    normalized = list(dict.fromkeys(str(item).strip().upper() for item in requested if str(item).strip()))
    common_issues = _base_issues(manifest) + _topology_issues(manifest)
    issues = deepcopy(common_issues)

    if not normalized:
        issues.append(_issue("P8B_SCOPE00", "requested_scope", "Debe declararse al menos un estudio/alcance solicitado."))

    readiness: dict[str, Any] = {}
    for scope in normalized:
        scoped: list[dict[str, str]] = []
        if scope not in ALLOWED_SCOPE:
            scoped.append(_issue("P8B_SCOPE01", "requested_scope", f"Scope no soportado por P8B: {scope}.", scope))
        else:
            if scope in {"IEC60909_3PH_MAX_MIN", "IEC60909_1PH_GROUND_MAX_MIN"}:
                scoped.extend(_short_circuit_issues(manifest, scope))
            if scope == "IEC60909_1PH_GROUND_MAX_MIN":
                scoped.extend(_ground_issues(manifest, scope))
            if scope == "AMPACITY":
                scoped.extend(_ampacity_issues(manifest, scope))
            if scope == "PROTECTION_TCC":
                scoped.extend(_protection_issues(manifest, scope))

        effective = deepcopy(common_issues) + deepcopy(scoped)
        readiness[scope] = {
            "status": "INPUTS_PRESENT" if not effective else "MISSING_INPUTS",
            "missing": effective,
            "engineering_execution_claim": False,
        }
        issues.extend(scoped)

    ready = not issues and bool(normalized)
    return {
        "schema": SCHEMA,
        "intake_status": STATUS_READY if ready else STATUS_BLOCKED,
        "ready_to_build_model": ready,
        "requested_scope": normalized,
        "base_model_readiness": {
            "status": "INPUTS_PRESENT" if not common_issues else "MISSING_INPUTS",
            "missing": deepcopy(common_issues),
        },
        "study_input_readiness": readiness,
        "issues": deepcopy(issues),
        "issue_count": len(issues),
        "electrical_calculation_performed": False,
        "model_mutation_performed": False,
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
        "note": (
            "INPUTS_PRESENT solo significa que P8B encontró campos declarados y plausibilidad básica. "
            "P2/P3/P4/P5 deben validar coherencia, alcance y aptitud después de modelar."
        ),
    }
