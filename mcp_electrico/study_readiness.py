"""Preparación profesional de datos y backend por tipo de estudio.

Esta capa no ejecuta cálculos. Separa tres preguntas que antes podían quedar
mezcladas:

1. ¿Los datos profesionales necesarios para el estudio están completos?
2. ¿El backend seleccionado puede representar hoy esos datos sin supuestos?
3. ¿El módulo del estudio está implementado/maduro para su uso declarado?

La separación permite distinguir ``MISSING_DATA`` de ``ENGINE_NOT_READY`` y
``MODULE_NOT_READY``. Un solver existente nunca convierte por sí solo datos
incompletos en datos aptos.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from opendssdirect import dss

from . import (
    ampacity,
    conductor_library,
    iec60909_contract,
    pandapower_engine,
    professional_data,
    runtime_safety,
    validation_status,
    workspace_state,
    zero_sequence,
)

READY_DATA = "READY_DATA"
MISSING_DATA = "MISSING_DATA"
READY_ENGINE = "READY_ENGINE"
ENGINE_NOT_READY = "ENGINE_NOT_READY"
MODULE_NOT_READY = "MODULE_NOT_READY"
READY_TO_EXECUTE = "READY_TO_EXECUTE"

FAULT_ALIASES = {
    "3f": "three_phase", "3ph": "three_phase", "three_phase": "three_phase",
    "trifasica": "three_phase", "trifásica": "three_phase",
    "2f": "two_phase", "2ph": "two_phase", "two_phase": "two_phase",
    "bifasica": "two_phase", "bifásica": "two_phase", "fase_fase": "two_phase", "phase_phase": "two_phase",
    "1f_t": "single_phase_ground", "1ft": "single_phase_ground", "1ph_ground": "single_phase_ground",
    "single_phase_ground": "single_phase_ground", "monofasica_tierra": "single_phase_ground", "monofásica_tierra": "single_phase_ground",
}

_FAULT_STUDIES = {"short_circuit_exploratory", "iec60909"}
_POSITIVE_SEQUENCE_PROFESSIONAL = {
    "power_flow", "voltage_drop", "short_circuit_exploratory", "iec60909",
    "protection_coordination", "arc_flash_ieee1584",
}


def _item(code: str, message: str, element: str | None = None) -> dict[str, Any]:
    return {"code": code, "message": message, "element": element}


def _fault_type(study: str, value: str | None) -> tuple[str | None, list[dict[str, Any]]]:
    if study not in _FAULT_STUDIES:
        return None, []
    if value is None or not str(value).strip():
        return None, [_item("P2READY010", "Debe especificarse tipo_falla; no se asume 3F silenciosamente.")]
    key = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    normalized = FAULT_ALIASES.get(key)
    if normalized is None:
        return None, [_item(
            "P2READY011",
            "P2 readiness clasifica three_phase, two_phase y single_phase_ground; 2F-T permanece fuera del alcance P4 actual.",
        )]
    return normalized, []


def _positive_sequence_requirements(study: str) -> list[dict[str, Any]]:
    try:
        model = workspace_state.collect_model_snapshot()
    except Exception:
        return [_item("P2READY001", "No existe un circuito activo.")]
    missing: list[dict[str, Any]] = []

    if not model.get("circuit"):
        return [_item("P2READY001", "No existe un circuito activo.")]

    for line in model.get("lines", []):
        element = str(line.get("id") or "Line.?")
        if float(line.get("length") or 0) <= 0:
            missing.append(_item("P2READY101", "Longitud no positiva.", element))
        if float(line.get("r1") or 0) <= 0:
            missing.append(_item("P2READY102", "R1 no positiva o no definida.", element))
        if float(line.get("x1") or 0) < 0:
            missing.append(_item("P2READY103", "X1 negativa.", element))

    for transformer in model.get("transformers", []):
        element = str(transformer.get("id") or "Transformer.?")
        p2 = transformer.get("professional")
        if not p2:
            missing.append(_item("P2READY201", "Transformador sin ficha P2 de %Z/X-R/grupo vectorial/procedencia.", element))
            continue
        sc = p2.get("short_circuit", {})
        vg = p2.get("vector_group", {})
        if float(sc.get("uk_percent") or 0) <= 0:
            missing.append(_item("P2READY202", "Transformador P2 sin uk/%Z válido.", element))
        if float(sc.get("x_r_effective") or 0) <= 0:
            missing.append(_item("P2READY203", "Transformador P2 sin X/R efectivo válido.", element))
        if not vg.get("grupo_vectorial"):
            missing.append(_item("P2READY204", "Transformador P2 sin grupo vectorial.", element))
        if not p2.get("provenance", {}).get("uk_percent", {}).get("reference"):
            missing.append(_item("P2READY205", "Transformador P2 sin procedencia de uk/%Z.", element))
        if study in {"power_flow", "voltage_drop"} and not p2.get("projection", {}).get("opendss", {}).get("complete", True):
            missing.append(_item(
                "P2READY206",
                "Transformador P2 conserva parámetros OpenDSS no respaldados por datos profesionales (p. ej. P0/I0).",
                element,
            ))

    if study in {"short_circuit_exploratory", "iec60909", "protection_coordination", "arc_flash_ieee1584"}:
        source = professional_data.obtener_red_equivalente()
        if not source:
            missing.append(_item("P2READY301", "Falta red equivalente P2 aguas arriba."))
        else:
            active_name = str(source.get("active_scenario") or "")
            active = source.get("scenarios", {}).get(active_name)
            if not active or float(active.get("scc3_mva") or 0) <= 0 or float(active.get("x_r") or 0) <= 0:
                missing.append(_item("P2READY302", "Escenario activo Scc3/X-R incompleto."))
            provenance = source.get("provenance", {})
            if not provenance.get("scc_max_mva", {}).get("reference"):
                missing.append(_item("P2READY303", "Red equivalente sin procedencia documentada para Scc3."))

    return missing


def _ampacity_requirements() -> list[dict[str, Any]]:
    try:
        if not str(dss.Circuit.Name() or ""):
            return [_item("P3READY001", "No existe un circuito activo.")]
    except Exception:
        return [_item("P3READY001", "No existe un circuito activo.")]

    state = ampacity.snapshot()
    profiles = state.get("profiles", [])
    if not profiles:
        return [_item("P3READY010", "No existe ningún perfil P3 de ampacidad configurado.")]

    missing: list[dict[str, Any]] = []
    for profile in profiles:
        element = str(profile.get("element") or "Line.?")
        base = profile.get("base", {})
        correction = profile.get("correction", {})
        protection = profile.get("protection", {})
        design = profile.get("design_current", {})
        norm = profile.get("norm", {})
        route = profile.get("normative_applicability")

        assignment = conductor_library.obtener_asignacion(element)
        if not assignment:
            missing.append(_item("P3READY101", "Falta asignación P2 trazable del conductor.", element))
            continue
        if str(assignment.get("codigo") or "") != str(base.get("conductor_code") or ""):
            missing.append(_item("P3READY102", "El conductor activo ya no coincide con la ficha P3.", element))
        if str(assignment.get("instalacion") or "") != str(base.get("catalog_installation") or ""):
            missing.append(_item("P3READY103", "La instalación activa ya no coincide con la ficha P3.", element))
        if float(base.get("ampacity_a") or 0) <= 0:
            missing.append(_item("P3READY104", "Ampacidad base P2 no disponible.", element))
        if float(protection.get("in_a") or 0) <= 0 or not protection.get("reference"):
            missing.append(_item("P3READY105", "In o su referencia están incompletos.", element))
        if design.get("mode") == "EXPLICIT_DESIGN_CURRENT":
            if float(design.get("ib_a") or 0) <= 0 or not design.get("reference"):
                missing.append(_item("P3READY106", "Ib explícita o su referencia están incompletas.", element))
        elif design.get("mode") != "FLOW_CURRENT_EXPLICITLY_ACCEPTED_AS_IB":
            missing.append(_item("P3READY107", "No existe una fuente válida para Ib.", element))
        if not correction.get("installation_compatibility_reference"):
            missing.append(_item("P3READY108", "Falta referencia de compatibilidad de condiciones de instalación.", element))
        factors = correction.get("factors", [])
        if correction.get("mode") == "EXPLICIT_FACTORS":
            if not factors or any(not item.get("reference") for item in factors):
                missing.append(_item("P3READY109", "Factores de corrección sin trazabilidad completa.", element))
        elif correction.get("mode") != "BASE_CONDITIONS_CONFIRMED":
            missing.append(_item("P3READY110", "Modo de corrección P3 no reconocido.", element))
        if not norm.get("id") or not norm.get("reference_status"):
            missing.append(_item("P3READY111", "Referencia normativa P3 no registrada.", element))

        if route:
            if route.get("missing_parameters"):
                missing.append(_item("P3READY112", "Routing P3A incompleto: " + ", ".join(str(x) for x in route.get("missing_parameters", [])), element))
            if route.get("applicable") is False:
                missing.append(_item("P3READY113", "El perfil P3A vinculado está registrado solo como referencia y no puede resolver aplicabilidad/tablas.", element))
            if route.get("manual_review"):
                missing.append(_item("P3READY114", "El routing P3A conserva revisión manual pendiente: " + " | ".join(str(x) for x in route.get("manual_review", [])), element))
            route_norm = str(route.get("norm_reference_id") or "")
            if route_norm and route_norm != str(norm.get("id") or ""):
                missing.append(_item("P3READY115", "El perfil normativo P3A no coincide con la referencia normativa de la ficha P3.", element))
            required_axes = {str(item.get("axis") or "").strip().lower() for item in route.get("required_axes", []) if item.get("required") and str(item.get("axis") or "").strip()}
            linked_axes = {str(item.get("axis") or "").strip().lower() for item in factors if str(item.get("axis") or "").strip()}
            uncovered = sorted(required_axes - linked_axes)
            if uncovered:
                missing.append(_item("P3READY116", "Ejes P3A sin factor explícito vinculado: " + ", ".join(uncovered), element))
            if required_axes and correction.get("mode") == "BASE_CONDITIONS_CONFIRMED":
                missing.append(_item("P3READY117", "El router P3A exige correcciones y la ficha fue marcada como condición base.", element))

    return missing


def _zero_sequence_requirements(*, iec60909_ground: bool = False) -> list[dict[str, Any]]:
    try:
        model = workspace_state.collect_model_snapshot()
    except Exception:
        return [_item("P2READY001", "No existe un circuito activo.")]
    missing: list[dict[str, Any]] = []
    source = professional_data.obtener_red_equivalente()
    z0_source = zero_sequence.obtener_fuente()

    if not source:
        missing.append(_item("P2READY401", "Falta red equivalente P2 positiva antes de evaluar Z0."))
    else:
        scenario = str(source.get("active_scenario") or "max")
        values = (z0_source or {}).get("scenarios", {}).get(scenario)
        if not values:
            missing.append(_item("P2READY402", f"Falta R0/X0 explícita de fuente para escenario {scenario}."))
        elif iec60909_ground and float(values.get("x0_ohm") or 0) <= 0:
            missing.append(_item("P4READY403", "IEC 60909 1F-T requiere X0 de fuente >0 para proyectar x0x sin aproximación."))

    for line in model.get("lines", []):
        element = str(line.get("id") or "Line.?")
        record = zero_sequence.obtener_linea(element)
        if not record:
            missing.append(_item("P2READY410", "Línea sin R0/X0 explícitos.", element))
        elif iec60909_ground and record.get("c0_nf_km") is None:
            missing.append(_item("P4READY411", "IEC 60909 1F-T requiere C0 explícita; no se supone 0 nF/km.", element))

    for transformer in model.get("transformers", []):
        element = str(transformer.get("id") or "Transformer.?")
        record = zero_sequence.obtener_transformador(element)
        if not record:
            missing.append(_item("P2READY420", "Transformador sin ficha explícita de secuencia cero.", element))
            continue
        neutral = record.get("neutral", {})
        vg = (transformer.get("professional") or {}).get("vector_group", {})
        has_wye = vg.get("hv_connection") == "wye" or vg.get("lv_connection") == "wye"
        if has_wye and neutral.get("side") is None:
            missing.append(_item("P2READY421", "Transformador con devanado wye sin declaración explícita de neutro/puesta a tierra para la ficha Z0.", element))
        if iec60909_ground and not record.get("projection", {}).get("pandapower_ready"):
            missing.append(_item("P4READY422", "Ficha Z0 de transformador no es proyectable a pandapower sin supuestos.", element))

    return missing


def _engine_readiness(study: str, capability: dict[str, Any], fault_type: str | None, allow_experimental: bool) -> dict[str, Any]:
    preferred = str(capability.get("preferred") or "")

    if not capability.get("implemented"):
        return {"status": MODULE_NOT_READY, "engine": preferred or None, "reasons": [_item("P2READY801", "El módulo del estudio todavía no está implementado en el roadmap actual.")]}

    if study == "iec60909" and fault_type:
        fault_scope = iec60909_contract.FAULT_SCOPE.get(fault_type)
        fault_status = (fault_scope or {}).get("status")
        if fault_status != "FOUNDATION_READY":
            return {
                "status": ENGINE_NOT_READY,
                "engine": preferred or None,
                "reasons": [_item("P4READY803", f"IEC 60909 {fault_type} no está habilitada en el alcance P4 actual; fault_scope={fault_status or 'UNDECLARED'}.")],
                "note": "La implementación global de IEC 60909 no habilita automáticamente tipos de falla pendientes.",
            }

    if preferred == "opendss" and study == "short_circuit_exploratory":
        preflight = runtime_safety.evaluar_faultstudy_opendss()
        if preflight.get("professional_context") and not preflight.get("ready"):
            return {
                "status": ENGINE_NOT_READY,
                "engine": "opendss",
                "reasons": deepcopy(preflight.get("reasons", [])),
                "note": "El dato puede ser suficiente para el tipo de falla solicitado, pero la tool FaultStudy profesional actual exige una representación Z0 OpenDSS segura.",
            }
        return {"status": READY_ENGINE, "engine": "opendss", "reasons": []}

    if preferred == "pandapower":
        compatibility = pandapower_engine.evaluar_compatibilidad()
        if not compatibility.get("compatible"):
            return {"status": ENGINE_NOT_READY, "engine": "pandapower", "reasons": deepcopy(compatibility.get("issues", []))}
        if str(compatibility.get("maturity")) == "EXPERIMENTAL" and not allow_experimental:
            return {"status": ENGINE_NOT_READY, "engine": "pandapower", "reasons": [_item("P2READY802", "pandapower permanece EXPERIMENTAL para el alcance actual; requiere habilitación explícita.")]}
        return {"status": READY_ENGINE, "engine": "pandapower", "reasons": []}

    if preferred in {"opendss", "opendss+mcp", "mcp", "mcp+pandapower"}:
        return {"status": READY_ENGINE, "engine": preferred, "reasons": []}

    return {"status": ENGINE_NOT_READY, "engine": preferred or None, "reasons": [_item("P2READY899", "No existe una regla de preparación para el backend preferente declarado.")]}


def evaluar(study: str, capability: dict[str, Any], fault_type: str | None = None, allow_experimental: bool = False) -> dict[str, Any]:
    """Evalúa preparación profesional sin ejecutar el estudio."""
    request_missing: list[dict[str, Any]] = []
    normalized_fault, fault_issues = _fault_type(study, fault_type)
    request_missing.extend(fault_issues)

    data_missing: list[dict[str, Any]] = []
    if study == "ampacity":
        data_missing.extend(_ampacity_requirements())
    elif capability.get("requires_active_model", False) or study in _POSITIVE_SEQUENCE_PROFESSIONAL:
        data_missing.extend(_positive_sequence_requirements(study))

    if study in _FAULT_STUDIES and normalized_fault == "single_phase_ground":
        if not any(item.get("code") == "P2READY001" for item in data_missing):
            data_missing.extend(_zero_sequence_requirements(iec60909_ground=(study == "iec60909")))

    data_status = READY_DATA if not request_missing and not data_missing else MISSING_DATA
    engine = _engine_readiness(study, capability, normalized_fault, allow_experimental)

    module_name = capability.get("module")
    module = None
    if module_name:
        try:
            module = validation_status.get_module_status(str(module_name))
        except KeyError:
            module = None

    if data_status == MISSING_DATA:
        overall = MISSING_DATA
    elif engine["status"] == MODULE_NOT_READY:
        overall = MODULE_NOT_READY
    elif engine["status"] == ENGINE_NOT_READY:
        overall = ENGINE_NOT_READY
    else:
        overall = READY_TO_EXECUTE

    return {
        "schema_version": 1,
        "study": study,
        "fault_type": normalized_fault,
        "data_status": data_status,
        "engine_status": engine["status"],
        "overall_status": overall,
        "selected_engine": engine.get("engine"),
        "request_issues": request_missing,
        "missing_data": data_missing,
        "engine_reasons": deepcopy(engine.get("reasons", [])),
        "engine_note": engine.get("note"),
        "module_status": deepcopy(module),
        "professional_context": True,
        "note": "Preparación de datos/backend no equivale a validación normativa ni sustituye revisión profesional.",
    }
