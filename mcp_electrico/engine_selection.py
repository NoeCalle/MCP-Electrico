"""Selección determinista de backend por tipo de estudio.

Esta capa no ejecuta estudios. Su función es decidir qué backend corresponde,
qué alternativas existen, qué requisitos deben cumplirse y si el estudio está
habilitado en la madurez actual del proyecto.

No existe cross-check ni despacho automático en esta versión.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import pandapower_engine, validation_status


CAPABILITY_MATRIX: dict[str, dict[str, Any]] = {
    "power_flow": {
        "preferred": "opendss",
        "alternatives": ["pandapower"],
        "module": "power_flow",
        "implemented": True,
        "professional_emission_candidate": True,
        "reason": "OpenDSS es el backend principal validado con limitaciones para flujo de potencia.",
        "requirements": ["circuito activo"],
    },
    "voltage_drop": {
        "preferred": "opendss+mcp",
        "alternatives": [],
        "module": "voltage_drop",
        "implemented": True,
        "professional_emission_candidate": True,
        "reason": "OpenDSS resuelve tensiones y MCP deriva la caída sin redondeo intermedio.",
        "requirements": ["flujo convergente", "líneas con buses origen/destino"],
    },
    "short_circuit_exploratory": {
        "preferred": "opendss",
        "alternatives": [],
        "module": "short_circuit",
        "implemented": True,
        "professional_emission_candidate": False,
        "reason": "FaultStudy existe, pero todavía no constituye IEC 60909 formal.",
        "requirements": ["circuito activo", "barra de falla válida"],
    },
    "iec60909": {
        "preferred": "pandapower",
        "alternatives": [],
        "module": "short_circuit",
        "implemented": False,
        "professional_emission_candidate": False,
        "reason": "P4 definirá pandapower como candidato principal para IEC 60909; el módulo formal aún no está implementado.",
        "requirements": [
            "P2 completo para datos de fuente/transformadores",
            "secuencia cero cuando el tipo de falla la requiera",
            "backend P4 validado",
        ],
    },
    "ampacity": {
        "preferred": "mcp",
        "alternatives": [],
        "module": None,
        "implemented": False,
        "professional_emission_candidate": False,
        "reason": "La ampacidad normativa es una capa MCP de P3, no un resultado del solver de red.",
        "requirements": ["método de instalación", "condiciones térmicas", "factores de corrección", "norma versionada"],
    },
    "protection_coordination": {
        "preferred": "mcp+pandapower",
        "alternatives": [],
        "module": "protection_coordination",
        "implemented": False,
        "professional_emission_candidate": False,
        "reason": "P5 combinará datos de falla/protección con reglas MCP y capacidades de pandapower cuando apliquen.",
        "requirements": ["P4 IEC 60909", "curvas/ajustes de protección", "biblioteca de dispositivos"],
    },
    "arc_flash_ieee1584": {
        "preferred": "mcp",
        "alternatives": [],
        "module": "arc_flash_ieee1584",
        "implemented": False,
        "professional_emission_candidate": False,
        "reason": "IEEE 1584 pertenece a P6 y depende de corriente de arco y tiempo de despeje trazable.",
        "requirements": ["P4 cortocircuito", "P5 tiempo de despeje", "parámetros IEEE 1584"],
    },
    "arc_flash_lee": {
        "preferred": "mcp",
        "alternatives": [],
        "module": "arc_flash_lee",
        "implemented": True,
        "professional_emission_candidate": False,
        "reason": "Lee permanece solo como método simplificado/educativo.",
        "requirements": ["voltaje", "corriente de falla", "tiempo de despeje", "distancia de trabajo"],
    },
    "harmonics": {
        "preferred": "opendss",
        "alternatives": [],
        "module": None,
        "implemented": False,
        "professional_emission_candidate": False,
        "reason": "OpenDSS tiene capacidad de armónicos, pero MCP Eléctrico todavía no expone ni valida un estudio profesional de armónicos.",
        "requirements": ["modelos/espectros armónicos", "módulo MCP específico", "benchmarks"],
    },
    "time_series": {
        "preferred": "opendss",
        "alternatives": [],
        "module": None,
        "implemented": False,
        "professional_emission_candidate": False,
        "reason": "OpenDSS es el candidato preferente para series temporales/distribución, pero el módulo MCP aún no está implementado.",
        "requirements": ["perfiles temporales", "módulo MCP específico", "benchmarks"],
    },
}


ALIASES = {
    "flujo": "power_flow",
    "flujo_potencia": "power_flow",
    "powerflow": "power_flow",
    "power_flow": "power_flow",
    "caida_tension": "voltage_drop",
    "voltage_drop": "voltage_drop",
    "cortocircuito": "short_circuit_exploratory",
    "short_circuit": "short_circuit_exploratory",
    "faultstudy": "short_circuit_exploratory",
    "iec_60909": "iec60909",
    "iec60909": "iec60909",
    "ampacidad": "ampacity",
    "ampacity": "ampacity",
    "proteccion": "protection_coordination",
    "coordinacion_protecciones": "protection_coordination",
    "protection_coordination": "protection_coordination",
    "arc_flash": "arc_flash_ieee1584",
    "arc_flash_ieee1584": "arc_flash_ieee1584",
    "ieee1584": "arc_flash_ieee1584",
    "lee": "arc_flash_lee",
    "arc_flash_lee": "arc_flash_lee",
    "armonicos": "harmonics",
    "harmonics": "harmonics",
    "series_temporales": "time_series",
    "time_series": "time_series",
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


def obtener_capacidades_motores() -> dict[str, Any]:
    """Devuelve la matriz versionada sin ejecutar ni modificar el modelo."""
    return {
        "schema_version": 1,
        "automatic_dispatch": False,
        "crosscheck": False,
        "default_engine": "opendss",
        "studies": deepcopy(CAPABILITY_MATRIX),
        "note": "La matriz selecciona/recomienda; las tools explícitas siguen ejecutando cada backend.",
    }


def seleccionar_motor_estudio(
    estudio: str,
    norma: str | None = None,
    permitir_experimental: bool = False,
) -> dict[str, Any]:
    """Selecciona determinísticamente backend y determina si el estudio es ejecutable.

    `permitir_experimental` solo afecta la elegibilidad de pandapower como
    alternativa de flujo. Nunca convierte un módulo no implementado en
    ejecutable ni apto para emisión.
    """
    normalized = _normalize_study(estudio, norma)
    capability = CAPABILITY_MATRIX.get(normalized)
    if capability is None:
        return {
            "study_requested": estudio,
            "study": normalized,
            "decision": "UNKNOWN_STUDY",
            "executable": False,
            "professional_emission": False,
            "selected_engine": None,
            "reason": "El estudio no existe en la matriz determinista de capacidades.",
        }

    module_name = capability.get("module")
    module = None
    if module_name:
        try:
            module = validation_status.get_module_status(module_name)
        except KeyError:
            module = None

    executable = bool(capability["implemented"])
    professional = bool(
        executable
        and capability["professional_emission_candidate"]
        and module
        and module.get("status") in {"VALIDATED_WITH_LIMITATIONS", "VALIDATED"}
    )

    alternatives: list[dict[str, Any]] = []
    for engine in capability.get("alternatives", []):
        item: dict[str, Any] = {"engine": engine, "eligible": True, "reason": None}
        if engine == "pandapower":
            compatibility = pandapower_engine.evaluar_compatibilidad()
            item["compatible_model"] = compatibility["compatible"]
            item["issues"] = compatibility["issues"]
            item["maturity"] = compatibility["maturity"]
            item["eligible"] = bool(compatibility["compatible"] and permitir_experimental)
            if not permitir_experimental:
                item["reason"] = "Pandapower sigue EXPERIMENTAL; habilítalo explícitamente para considerarlo alternativa."
            elif not compatibility["compatible"]:
                item["reason"] = "El modelo activo no entra en el alcance pandapower vigente."
        alternatives.append(item)

    if not executable:
        decision = "NO_APTO_PARA_EJECUCION"
    elif professional:
        decision = "APTO_DENTRO_DE_LIMITACIONES"
    else:
        decision = "EJECUTABLE_NO_APTO_PARA_EMISION"

    return {
        "study_requested": estudio,
        "study": normalized,
        "standard": norma,
        "decision": decision,
        "executable": executable,
        "professional_emission": professional,
        "selected_engine": capability["preferred"],
        "reason": capability["reason"],
        "requirements": deepcopy(capability["requirements"]),
        "module_status": deepcopy(module),
        "alternatives": alternatives,
        "automatic_dispatch": False,
        "crosscheck": False,
    }
