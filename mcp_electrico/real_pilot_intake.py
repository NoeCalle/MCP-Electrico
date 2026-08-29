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


def _get(data: dict[str, Any], path: str) -> Any:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _issue(code: str, path: str, message: str, scope: str = "BASE_MODEL") -> dict[str, str]:
    return {"code": code, "path": path, "message": message, "scope": scope}


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
            "P8B verifica presencia y trazabilidad de entradas. La suficiencia eléctrica "
            "final sigue siendo evaluada por los gates P2/P3/P4/P5 después de construir el modelo."
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
    return issues


def _positive_sequence_issues(manifest: dict[str, Any], scope: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for code, path, message in (
        ("P8B_SC01", "source.scc_max_mva", "Scc3 MAX explícita de la red aguas arriba."),
        ("P8B_SC02", "source.x_r_max", "X/R MAX explícito de la red aguas arriba."),
        ("P8B_SC03", "source.scc_min_mva", "Scc3 MIN explícita para escenario mínimo."),
        ("P8B_SC04", "source.x_r_min", "X/R MIN explícito para escenario mínimo."),
    ):
        if not _present(_get(manifest, path)):
            issues.append(_issue(code, path, message, scope))

    for i, trafo in enumerate(_get(manifest, "topology.transformers") or []):
        for key in ("id", "bus_hv", "bus_lv", "kva", "kv_hv", "kv_lv", "uk_percent", "vector_group"):
            if not _present(trafo.get(key)):
                issues.append(_issue("P8B_SC10", f"topology.transformers[{i}].{key}", f"Dato P2 de transformador requerido: {key}.", scope))
        if not (_present(trafo.get("x_r")) or _present(trafo.get("load_loss_kw"))):
            issues.append(_issue("P8B_SC11", f"topology.transformers[{i}]", "Se requiere X/R o pérdidas de carga trazables para separar R/X.", scope))

    for i, line in enumerate(_get(manifest, "topology.lines") or []):
        for key in ("id", "bus1", "bus2", "length_km", "r1_ohm_km", "x1_ohm_km"):
            if not _present(line.get(key)):
                issues.append(_issue("P8B_SC20", f"topology.lines[{i}].{key}", f"Dato de secuencia positiva requerido: {key}.", scope))
        if scope == "IEC60909_3PH_MAX_MIN" and not _present(line.get("endtemp_min_c")):
            issues.append(_issue("P8B_SC21", f"topology.lines[{i}].endtemp_min_c", "Temperatura final explícita para cálculo MIN; no se inventa.", scope))
    return issues


def _ground_issues(manifest: dict[str, Any], scope: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for code, path in (
        ("P8B_Z001", "zero_sequence.source.r0_max_ohm"),
        ("P8B_Z002", "zero_sequence.source.x0_max_ohm"),
        ("P8B_Z003", "zero_sequence.source.r0_min_ohm"),
        ("P8B_Z004", "zero_sequence.source.x0_min_ohm"),
    ):
        if not _present(_get(manifest, path)):
            issues.append(_issue(code, path, "Secuencia cero de fuente requerida para falla a tierra MAX/MIN.", scope))

    lines_z0 = _get(manifest, "zero_sequence.lines") or []
    transformers_z0 = _get(manifest, "zero_sequence.transformers") or []
    if not lines_z0:
        issues.append(_issue("P8B_Z010", "zero_sequence.lines", "R0/X0/C0 explícitos por línea/cable del alcance.", scope))
    else:
        for i, line in enumerate(lines_z0):
            for key in ("id", "r0_ohm_km", "x0_ohm_km", "c0_nf_km"):
                if not _present(line.get(key)):
                    issues.append(_issue("P8B_Z011", f"zero_sequence.lines[{i}].{key}", f"Dato Z0 requerido: {key}.", scope))

    if not transformers_z0:
        issues.append(_issue("P8B_Z020", "zero_sequence.transformers", "Ficha Z0 + neutro/puesta a tierra de transformador requerida.", scope))
    else:
        for i, trafo in enumerate(transformers_z0):
            for key in ("id", "uk0_percent", "ur0_percent", "neutral_side", "neutral_mode"):
                if not _present(trafo.get(key)):
                    issues.append(_issue("P8B_Z021", f"zero_sequence.transformers[{i}].{key}", f"Dato de transformador Z0 requerido: {key}.", scope))
    return issues


def _ampacity_issues(manifest: dict[str, Any], scope: str) -> list[dict[str, str]]:
    records = _get(manifest, "ampacity") or []
    if not records:
        return [_issue("P8B_P301", "ampacity", "Ficha de conductores/instalación/criterio Ib-In-Iz requerida.", scope)]
    issues: list[dict[str, str]] = []
    for i, item in enumerate(records):
        for key in ("element_id", "conductor_code", "ib_a", "in_a", "installation_reference", "ampacity_reference"):
            if not _present(item.get(key)):
                issues.append(_issue("P8B_P302", f"ampacity[{i}].{key}", f"Entrada P3 requerida: {key}.", scope))
    return issues


def _protection_issues(manifest: dict[str, Any], scope: str) -> list[dict[str, str]]:
    devices = _get(manifest, "protection.devices") or []
    datasets = _get(manifest, "protection.tcc_datasets") or []
    issues: list[dict[str, str]] = []
    if not devices:
        issues.append(_issue("P8B_P501", "protection.devices", "Dispositivos de protección y ratings explícitos requeridos.", scope))
    else:
        for i, item in enumerate(devices):
            for key in ("id", "type", "protected_element", "in_a", "ue_kv", "breaking_capacity_ka", "source_reference"):
                if not _present(item.get(key)):
                    issues.append(_issue("P8B_P502", f"protection.devices[{i}].{key}", f"Entrada P5 requerida: {key}.", scope))
    if not datasets:
        issues.append(_issue("P8B_P510", "protection.tcc_datasets", "Curvas/datasets TCC trazables requeridos para coordinación.", scope))
    else:
        for i, item in enumerate(datasets):
            for key in ("dataset_id", "time_semantics", "source_type", "source_reference"):
                if not _present(item.get(key)):
                    issues.append(_issue("P8B_P511", f"protection.tcc_datasets[{i}].{key}", f"Metadata TCC requerida: {key}.", scope))
    return issues


def evaluar_admision(manifest: dict[str, Any]) -> dict[str, Any]:
    """Evalúa un manifiesto de datos reales sin modificar el modelo eléctrico."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest debe ser dict.")

    requested = manifest.get("requested_scope") or []
    normalized = [str(item).strip().upper() for item in requested if str(item).strip()]
    unknown = sorted(set(normalized) - ALLOWED_SCOPE)
    issues = _base_issues(manifest)
    for item in unknown:
        issues.append(_issue("P8B_SCOPE01", "requested_scope", f"Scope no soportado por P8B: {item}.", item))

    readiness: dict[str, Any] = {}
    for scope in normalized:
        scoped: list[dict[str, str]] = []
        if scope in {"IEC60909_3PH_MAX_MIN", "IEC60909_1PH_GROUND_MAX_MIN"}:
            scoped.extend(_positive_sequence_issues(manifest, scope))
        if scope == "IEC60909_1PH_GROUND_MAX_MIN":
            scoped.extend(_ground_issues(manifest, scope))
        if scope == "AMPACITY":
            scoped.extend(_ampacity_issues(manifest, scope))
        if scope == "PROTECTION_TCC":
            scoped.extend(_protection_issues(manifest, scope))
        readiness[scope] = {
            "status": "INPUTS_PRESENT" if not scoped else "MISSING_INPUTS",
            "missing": deepcopy(scoped),
            "engineering_execution_claim": False,
        }
        issues.extend(scoped)

    ready = not issues and bool(normalized)
    return {
        "schema": SCHEMA,
        "intake_status": STATUS_READY if ready else STATUS_BLOCKED,
        "ready_to_build_model": ready,
        "requested_scope": normalized,
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
            "INPUTS_PRESENT solo significa que P8B encontró los campos declarados. "
            "P2/P3/P4/P5 deben validar coherencia, alcance y aptitud después de modelar."
        ),
    }
