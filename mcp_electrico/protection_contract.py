"""Contrato fundacional P5A para protecciones y futura coordinación TCC.

P5A define datos y límites de semántica. No calcula curvas, selectividad ni
tiempos de despeje y no convierte parámetros P4 en datos de protección.
"""

from __future__ import annotations

from copy import deepcopy

SCHEMA_VERSION = 1

P5A_SCOPE = {
    "id": "P5A_PROTECTION_DATA_CONTRACT_V1",
    "status": "FOUNDATION",
    "included_device_types": ["circuit_breaker", "fuse"],
    "excluded_device_types": ["relay"],
    "excluded_note": (
        "Relés requieren un modelo dedicado de CT/VT, funciones ANSI, lógica de disparo "
        "y vínculo con el elemento de corte; no se aproximan como interruptores."
    ),
}

RATING_SEMANTICS = {
    "in_a": "corriente nominal declarada del dispositivo; puede vincularse con In P3 pero no se infiere desde P3",
    "ue_kv": "tensión nominal/de empleo declarada del dispositivo",
    "icu_ka": "capacidad última de corte declarada del interruptor cuando aplique",
    "ics_ka": "capacidad de servicio declarada del interruptor cuando aplique",
    "icw_ka": "corriente soportada de corta duración declarada; duración asociada todavía fuera de P5A",
    "breaking_capacity_ka": "poder de corte declarado del fusible cuando aplique",
}

SETTING_SEMANTICS = {
    "basis": "ABSOLUTE_A",
    "ir_a": "pickup/ajuste largo expresado explícitamente en A",
    "isd_a": "pickup corto expresado explícitamente en A",
    "ii_a": "pickup instantáneo expresado explícitamente en A",
    "rule": "P5A no convierte múltiplos de In en amperios ni inventa ajustes ausentes.",
}

CURVE_POLICY = {
    "numeric_curve_dataset_supported": False,
    "metadata_supported": True,
    "synthetic_manufacturer_curves": False,
    "browser_curve_calculation": False,
    "next_gate": "P5B_NUMERIC_TCC_DATASET",
    "note": (
        "P5A registra identidad/procedencia de curva. Los puntos numéricos, bandas, "
        "ecuaciones normalizadas y evaluación de tiempo se implementan y validan en P5B+."
    ),
}

CLEARING_TIME_POLICY = {
    "p4_tk_s_is_actual_clearing_time": False,
    "automatic_binding_from_p4_tk_s": False,
    "required_future_source": "device_curve_or_tested_protection_logic",
    "note": (
        "tk_s de P4 es un parámetro explícito para Ith; nunca se reutiliza automáticamente "
        "como tiempo real de despeje de una protección."
    ),
}

P3_BINDING_POLICY = {
    "automatic_creation_from_p3_in": False,
    "comparison_when_available": True,
    "mismatch_is_blocking_for_conductor_protection": True,
    "note": "La ficha P5A conserva su propio In y solo contrasta P3 cuando existe una ficha del elemento protegido.",
}

VISUAL_POLICY = {
    "workspace": "same_persistent_workspace",
    "target_view": "V5_PROTECTION_TCC",
    "second_visual_app": False,
    "javascript_engineering_calculation": False,
    "note": "V5 debe consumir objetos, readiness y futuras curvas calculadas/preparadas por Python/MCP.",
}


def obtener_contrato_p5a() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "scope": deepcopy(P5A_SCOPE),
        "ratings": deepcopy(RATING_SEMANTICS),
        "settings": deepcopy(SETTING_SEMANTICS),
        "curve_policy": deepcopy(CURVE_POLICY),
        "clearing_time_policy": deepcopy(CLEARING_TIME_POLICY),
        "p3_binding_policy": deepcopy(P3_BINDING_POLICY),
        "visual_policy": deepcopy(VISUAL_POLICY),
        "professional_emission": False,
    }
