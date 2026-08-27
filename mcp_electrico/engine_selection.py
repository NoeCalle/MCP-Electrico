"""Selección determinista de backend por tipo de estudio.

Esta capa no ejecuta estudios. Decide qué backend corresponde, qué
alternativas existen, qué requisitos deben cumplirse y si el estudio está
habilitado en la madurez/modelo actuales.

No existe cross-check ni despacho automático en esta versión.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from opendssdirect import dss

from . import model_qa, pandapower_engine, study_readiness, validation_status


CAPABILITY_MATRIX: dict[str, dict[str, Any]] = {
    "power_flow": {
        "preferred": "opendss", "alternatives": ["pandapower"], "module": "power_flow",
        "implemented": True, "professional_emission_candidate": True, "requires_active_model": True,
        "reason": "OpenDSS es el backend principal validado con limitaciones para flujo de potencia.",
        "requirements": ["circuito activo"],
    },
    "voltage_drop": {
        "preferred": "opendss+mcp", "alternatives": [], "module": "voltage_drop",
        "implemented": True, "professional_emission_candidate": True, "requires_active_model": True,
        "reason": "OpenDSS resuelve tensiones y MCP deriva la caída sin redondeo intermedio.",
        "requirements": ["circuito activo", "flujo convergente", "líneas con buses origen/destino"],
    },
    "short_circuit_exploratory": {
        "preferred": "opendss", "alternatives": [], "module": "short_circuit",
        "implemented": True, "professional_emission_candidate": False, "requires_active_model": True,
        "reason": "FaultStudy existe, pero no constituye IEC 60909 formal.",
        "requirements": ["circuito activo", "barra de falla válida", "tipo de falla explícito para readiness profesional"],
    },
    "iec60909": {
        "preferred": "pandapower", "alternatives": [], "module": "short_circuit",
        "implemented": True, "professional_emission_candidate": False, "requires_active_model": True,
        "reason": (
            "P4 implementa experimentalmente IEC 60909 con pandapower para falla 3F max/min; "
            "Ik''/Sk'' tienen benchmark independiente P4C09A e ip/Ith requieren parámetros explícitos. "
            "El alcance completo, la revisión de edición 2026 y la madurez profesional siguen pendientes."
        ),
        "requirements": [
            "P2 suficiente para fuente/líneas/transformadores del alcance 3F",
            "escenario max/min explícito",
            "endtemp_degree explícita por línea en cálculo mínimo",
            "topology y tk_s explícitos cuando se solicitan ip/Ith",
            "permitir_experimental=true para readiness del backend pandapower",
            "secuencia cero validada antes de cualquier falla a tierra",
        ],
    },
    "ampacity": {
        "preferred": "mcp", "alternatives": [], "module": "ampacity",
        "implemented": True, "professional_emission_candidate": False, "requires_active_model": True,
        "reason": "P3-v1 evalúa Ib/In/Iz en la capa MCP con trazabilidad explícita y madurez VALIDATED_WITH_LIMITATIONS.",
        "requirements": [
            "conductor P2 trazable",
            "ampacidad base y condición de instalación",
            "In y su referencia",
            "Ib explícita o uso del flujo aceptado expresamente",
            "factores referenciados o confirmación de condiciones base",
            "norma versionada",
        ],
    },
    "protection_coordination": {
        "preferred": "mcp+pandapower", "alternatives": [], "module": "protection_coordination",
        "implemented": False, "professional_emission_candidate": False, "requires_active_model": True,
        "reason": "P5 combinará datos de falla/protección con reglas MCP y capacidades de pandapower cuando apliquen.",
        "requirements": ["P4 IEC 60909", "curvas/ajustes de protección", "biblioteca de dispositivos"],
    },
    "arc_flash_ieee1584": {
        "preferred": "mcp", "alternatives": [], "module": "arc_flash_ieee1584",
        "implemented": False, "professional_emission_candidate": False, "requires_active_model": True,
        "reason": "IEEE 1584 pertenece a P6 y depende de corriente de arco y tiempo de despeje trazable.",
        "requirements": ["P4 cortocircuito", "P5 tiempo de despeje", "parámetros IEEE 1584"],
    },
    "arc_flash_lee": {
        "preferred": "mcp", "alternatives": [], "module": "arc_flash_lee",
        "implemented": True, "professional_emission_candidate": False, "requires_active_model": False,
        "reason": "Lee permanece solo como método simplificado/educativo.",
        "requirements": ["voltaje", "corriente de falla", "tiempo de despeje", "distancia de trabajo"],
    },
    "harmonics": {
        "preferred": "opendss", "alternatives": [], "module": None,
        "implemented": False, "professional_emission_candidate": False, "requires_active_model": True,
        "reason": "OpenDSS tiene capacidad de armónicos, pero MCP Eléctrico todavía no expone ni valida un estudio profesional de armónicos.",
        "requirements": ["modelos/espectros armónicos", "módulo MCP específico", "benchmarks"],
    },
    "time_series": {
        "preferred": "opendss", "alternatives": [], "module": None,
        "implemented": False, "professional_emission_candidate": False, "requires_active_model": True,
        "reason": "OpenDSS es el candidato preferente para series temporales/distribución, pero el módulo MCP aún no está implementado.",
        "requirements": ["perfiles temporales", "módulo MCP específico", "benchmarks"],
    },
}

ALIASES = {
    "flujo": "power_flow", "flujo_potencia": "power_flow", "powerflow": "power_flow", "power_flow": "power_flow",
    "caida_tension": "voltage_drop", "voltage_drop": "voltage_drop",
    "cortocircuito": "short_circuit_exploratory", "short_circuit": "short_circuit_exploratory", "faultstudy": "short_circuit_exploratory",
    "iec_60909": "iec60909", "iec60909": "iec60909",
    "ampacidad": "ampacity", "ampacity": "ampacity",
    "proteccion": "protection_coordination", "coordinacion_protecciones": "protection_coordination", "protection_coordination": "protection_coordination",
    "arc_flash": "arc_flash_ieee1584", "arc_flash_ieee1584": "arc_flash_ieee1584", "ieee1584": "arc_flash_ieee1584",
    "lee": "arc_flash_lee", "arc_flash_lee": "arc_flash_lee",
    "armonicos": "harmonics", "harmonics": "harmonics",
    "series_temporales": "time_series", "time_series": "time_series",
}


def _normalize_study(study: str, standard: str | None = None) -> str:
    key = str(study or "").strip().lower().replace("-", "_").replace(" ", "_")
    standard_key = str(standard or "").strip().lower().replace(" ", "")
    if "60909" in standard_key:
        return "iec60909"
    normalized = ALIASES.get(key, key)
    if normalized == "short_circuit_exploratory" and "60909" in key:
        return "iec60909"
    return normalized


def _has_active_model() -> bool:
    try:
        return bool(str(dss.Circuit.Name() or ""))
    except Exception:
        return False


def obtener_capacidades_motores() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "automatic_dispatch": False,
        "crosscheck": False,
        "default_engine": "opendss",
        "studies": deepcopy(CAPABILITY_MATRIX),
        "readiness_states": {
            "data": ["READY_DATA", "MISSING_DATA"],
            "engine": ["READY_ENGINE", "ENGINE_NOT_READY", "MODULE_NOT_READY"],
            "overall": ["READY_TO_EXECUTE", "MISSING_DATA", "ENGINE_NOT_READY", "MODULE_NOT_READY"],
        },
        "note": "La matriz selecciona/recomienda y evalúa preparación; las tools explícitas siguen ejecutando cada backend.",
    }


def evaluar_preparacion_estudio(
    estudio: str,
    norma: str | None = None,
    tipo_falla: str | None = None,
    permitir_experimental: bool = False,
) -> dict[str, Any]:
    """Devuelve completitud de datos, aptitud del backend y estado global sin ejecutar."""
    normalized = _normalize_study(estudio, norma)
    capability = CAPABILITY_MATRIX.get(normalized)
    if capability is None:
        return {
            "schema_version": 1,
            "study_requested": estudio,
            "study": normalized,
            "overall_status": "UNKNOWN_STUDY",
            "data_status": "MISSING_DATA",
            "engine_status": "ENGINE_NOT_READY",
            "selected_engine": None,
            "missing_data": [{"code": "P2READY000", "message": "Estudio no registrado en la matriz E.", "element": None}],
        }
    result = study_readiness.evaluar(
        study=normalized,
        capability=capability,
        fault_type=tipo_falla,
        allow_experimental=permitir_experimental,
    )
    result["study_requested"] = estudio
    result["standard"] = norma
    return result


def seleccionar_motor_estudio(
    estudio: str,
    norma: str | None = None,
    permitir_experimental: bool = False,
    tipo_falla: str | None = None,
) -> dict[str, Any]:
    normalized = _normalize_study(estudio, norma)
    capability = CAPABILITY_MATRIX.get(normalized)
    if capability is None:
        return {
            "study_requested": estudio, "study": normalized, "decision": "UNKNOWN_STUDY",
            "executable": False, "technical_executable": False, "professional_execution_ready": False,
            "professional_emission": False, "selected_engine": None,
            "reason": "El estudio no existe en la matriz determinista de capacidades.",
            "automatic_dispatch": False, "crosscheck": False,
        }

    module_name = capability.get("module")
    module = None
    if module_name:
        try:
            module = validation_status.get_module_status(module_name)
        except KeyError:
            module = None

    active_model = _has_active_model()
    model_requirement_ok = active_model or not capability.get("requires_active_model", False)
    technical_executable = bool(capability["implemented"] and model_requirement_ok)

    readiness = study_readiness.evaluar(
        study=normalized,
        capability=capability,
        fault_type=tipo_falla,
        allow_experimental=permitir_experimental,
    )
    professional_execution_ready = readiness.get("overall_status") == study_readiness.READY_TO_EXECUTE

    qa = None
    if technical_executable and capability["professional_emission_candidate"] and module_name:
        qa = model_qa.auditar_modelo([module_name])

    professional = bool(
        technical_executable
        and professional_execution_ready
        and capability["professional_emission_candidate"]
        and module
        and module.get("status") in {"VALIDATED_WITH_LIMITATIONS", "VALIDATED"}
        and qa
        and qa.get("summary", {}).get("apto_para_emision")
    )

    alternatives: list[dict[str, Any]] = []
    for engine in capability.get("alternatives", []):
        item: dict[str, Any] = {"engine": engine, "eligible": False, "reason": None}
        if engine == "pandapower":
            if not active_model:
                item.update(
                    compatible_model=False,
                    issues=[{"code": "PP001", "message": "No existe un circuito activo."}],
                    maturity="EXPERIMENTAL",
                    reason="No se evalúa el backend alternativo sin modelo activo.",
                )
            else:
                compatibility = pandapower_engine.evaluar_compatibilidad()
                item.update(
                    compatible_model=compatibility["compatible"],
                    issues=compatibility["issues"],
                    maturity=compatibility["maturity"],
                )
                item["eligible"] = bool(compatibility["compatible"] and permitir_experimental)
                if not permitir_experimental:
                    item["reason"] = "Pandapower sigue EXPERIMENTAL; habilítalo explícitamente para considerarlo alternativa."
                elif not compatibility["compatible"]:
                    item["reason"] = "El modelo activo no entra en el alcance pandapower vigente."
        alternatives.append(item)

    if not technical_executable:
        decision = "NO_APTO_PARA_EJECUCION"
    elif readiness["overall_status"] == study_readiness.MISSING_DATA:
        decision = "EJECUTABLE_CON_DATOS_PROFESIONALES_INCOMPLETOS"
    elif readiness["overall_status"] in {study_readiness.ENGINE_NOT_READY, study_readiness.MODULE_NOT_READY}:
        decision = "NO_APTO_PARA_EJECUCION_PROFESIONAL"
    elif professional:
        decision = "APTO_DENTRO_DE_LIMITACIONES"
    else:
        decision = "EJECUTABLE_NO_APTO_PARA_EMISION"

    reason = capability["reason"]
    if capability.get("requires_active_model") and not active_model:
        reason += " No existe un circuito activo."

    return {
        "study_requested": estudio,
        "study": normalized,
        "standard": norma,
        "fault_type": readiness.get("fault_type"),
        "decision": decision,
        "executable": technical_executable,
        "technical_executable": technical_executable,
        "professional_execution_ready": professional_execution_ready,
        "professional_emission": professional,
        "selected_engine": capability["preferred"],
        "reason": reason,
        "requirements": deepcopy(capability["requirements"]),
        "readiness": readiness,
        "module_status": deepcopy(module),
        "model_active": active_model,
        "qa_summary": deepcopy((qa or {}).get("summary")),
        "alternatives": alternatives,
        "automatic_dispatch": False,
        "crosscheck": False,
    }
