"""P5C — verificaciones técnicas de protección sin claim normativo integral.

P5C separa deliberadamente:
1) capacidad de corte declarada del dispositivo frente a una corriente de falla;
2) soportabilidad térmica adiabática I²t <= k²S² con k, S y tiempo explícitos.

No sustituye la selección completa del dispositivo según su norma de producto,
no usa Ics/Icw como sustitutos de Icu y no consume ``tk_s`` de P4.
"""

from __future__ import annotations

from copy import deepcopy
from math import isfinite, sqrt
from typing import Any

from . import protection_data

SCHEMA_BREAKING = "MCP_ELECTRICO_P5C_BREAKING_CAPACITY_CHECK_V1"
SCHEMA_THERMAL = "MCP_ELECTRICO_P5C_CONDUCTOR_THERMAL_CHECK_V1"

REFERENCE_TARGETS = {
    "circuit_breaker": {
        "id": "IEC_60947_2_2024",
        "designation": "IEC 60947-2:2024",
        "edition": "6.0",
        "publication_date": "2024-09-18",
        "scope_role": "reference_target_for_declared_breaker_ratings",
        "full_conformance_claim": False,
    },
    "fuse": {
        "id": "IEC_60269_1_2024",
        "designation": "IEC 60269-1:2024",
        "edition": "5.0",
        "publication_date": "2024-08-09",
        "scope_role": "reference_target_for_declared_fuse_breaking_capacity",
        "full_conformance_claim": False,
    },
    "conductor_overcurrent": {
        "id": "IEC_60364_4_43_2023",
        "designation": "IEC 60364-4-43:2023",
        "edition": "4.0",
        "publication_date": "2023-07-19",
        "scope_role": "reference_target_for_overcurrent_protection",
        "full_conformance_claim": False,
    },
}


def _positive(value: Any, code: str, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{code}: {label} debe ser numérico y >0.") from exc
    if not isfinite(number) or number <= 0:
        raise ValueError(f"{code}: {label} debe ser finito y >0.")
    return number


def _reference(value: str | None, code: str, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{code}: {label} es obligatorio para trazabilidad.")
    return text


def evaluar_capacidad_corte(
    dispositivo: str,
    corriente_falla_ka: float,
    tension_operacion_kv: float,
    fuente_corriente: str,
    tipo_falla: str | None = None,
    escenario: str | None = None,
) -> dict[str, Any]:
    """Compara una corriente de falla explícita con el rating de corte declarado.

    Interruptor: usa únicamente Icu.
    Fusible: usa únicamente breaking_capacity_ka.

    Ics e Icw se reportan como datos contextuales si existen, pero nunca se
    sustituyen por Icu ni se usan para producir el PASS de capacidad de corte.
    """
    device = protection_data.obtener_dispositivo(dispositivo)
    if not device:
        return {
            "schema": SCHEMA_BREAKING,
            "status": "DEVICE_NOT_FOUND",
            "device_id": str(dispositivo),
            "professional_emission": False,
        }

    fault_ka = _positive(corriente_falla_ka, "P5C101", "corriente_falla_ka")
    operating_kv = _positive(tension_operacion_kv, "P5C102", "tension_operacion_kv")
    source = _reference(fuente_corriente, "P5C103", "fuente_corriente")
    ratings = device.get("ratings") or {}
    ue_kv = float(ratings.get("ue_kv") or 0.0)

    if operating_kv > ue_kv + 1e-12:
        return {
            "schema": SCHEMA_BREAKING,
            "status": "NOT_APPLICABLE_VOLTAGE",
            "check": "DECLARED_BREAKING_CAPACITY_VS_FAULT_CURRENT",
            "device_id": device["id"],
            "device_type": device["device_type"],
            "protected_element": device["protected_element"],
            "fault_current_ka": fault_ka,
            "operating_voltage_kv": operating_kv,
            "device_ue_kv": ue_kv,
            "issues": [
                {
                    "code": "P5C104",
                    "message": "La tensión de operación supera Ue de la ficha; el rating de corte registrado no se aplica automáticamente.",
                }
            ],
            "professional_emission": False,
        }

    if device["device_type"] == "circuit_breaker":
        rating_type = "Icu"
        rating_ka = ratings.get("icu_ka")
        reference_target = REFERENCE_TARGETS["circuit_breaker"]
    elif device["device_type"] == "fuse":
        rating_type = "breaking_capacity"
        rating_ka = ratings.get("breaking_capacity_ka")
        reference_target = REFERENCE_TARGETS["fuse"]
    else:
        return {
            "schema": SCHEMA_BREAKING,
            "status": "DEVICE_TYPE_NOT_SUPPORTED",
            "device_id": device["id"],
            "professional_emission": False,
        }

    if rating_ka is None:
        return {
            "schema": SCHEMA_BREAKING,
            "status": "RATING_NOT_AVAILABLE",
            "check": "DECLARED_BREAKING_CAPACITY_VS_FAULT_CURRENT",
            "device_id": device["id"],
            "rating_type_required": rating_type,
            "fault_current_ka": fault_ka,
            "operating_voltage_kv": operating_kv,
            "issues": [
                {
                    "code": "P5C105",
                    "message": f"Falta {rating_type} explícito; no se sustituye por otro rating.",
                }
            ],
            "professional_emission": False,
        }

    rating = float(rating_ka)
    passed = rating + 1e-12 >= fault_ka
    margin_ka = rating - fault_ka
    return {
        "schema": SCHEMA_BREAKING,
        "status": "PASS" if passed else "FAIL",
        "check": "DECLARED_BREAKING_CAPACITY_VS_FAULT_CURRENT",
        "scope": "TECHNICAL_RATING_COMPARISON_NOT_FULL_STANDARD_COMPLIANCE",
        "device_id": device["id"],
        "device_type": device["device_type"],
        "protected_element": device["protected_element"],
        "standard_reference_declared_by_device": device.get("standard_reference"),
        "reference_target": deepcopy(reference_target),
        "fault": {
            "current_ka": fault_ka,
            "operating_voltage_kv": operating_kv,
            "type": str(tipo_falla or "").strip() or None,
            "case": str(escenario or "").strip().lower() or None,
            "source_reference": source,
        },
        "rating_used": {
            "type": rating_type,
            "value_ka": rating,
            "ue_kv": ue_kv,
        },
        "other_declared_ratings_not_used_for_pass": {
            "ics_ka": ratings.get("ics_ka"),
            "icw_ka": ratings.get("icw_ka"),
        },
        "margin_ka": margin_ka,
        "rating_to_fault_ratio": rating / fault_ka,
        "full_standard_compliance_claim": False,
        "professional_emission": False,
    }


def evaluar_soportabilidad_termica_conductor(
    elemento: str,
    corriente_falla_ka: float,
    tiempo_despeje_s: float,
    seccion_mm2: float,
    k_a_sqrt_s_per_mm2: float,
    fuente_k: str,
    fuente_tiempo: str,
) -> dict[str, Any]:
    """Evalúa I²t <= k²S² con entradas explícitas y trazables.

    El coeficiente ``k`` NO se deriva del material/aislamiento y el tiempo NO
    se toma de P4. P5D podrá entregar posteriormente un tiempo de despeje
    trazable como una de las fuentes aceptadas.
    """
    element = str(elemento or "").strip()
    if not element:
        raise ValueError("P5C201: elemento es obligatorio.")
    fault_ka = _positive(corriente_falla_ka, "P5C202", "corriente_falla_ka")
    clearing_s = _positive(tiempo_despeje_s, "P5C203", "tiempo_despeje_s")
    section = _positive(seccion_mm2, "P5C204", "seccion_mm2")
    k_value = _positive(k_a_sqrt_s_per_mm2, "P5C205", "k_a_sqrt_s_per_mm2")
    k_source = _reference(fuente_k, "P5C206", "fuente_k")
    time_source = _reference(fuente_tiempo, "P5C207", "fuente_tiempo")

    current_a = fault_ka * 1000.0
    actual_i2t = current_a * current_a * clearing_s
    limit_i2t = (k_value * section) ** 2
    passed = actual_i2t <= limit_i2t * (1.0 + 1e-12)
    max_time_s = limit_i2t / (current_a * current_a)
    max_current_a = k_value * section / sqrt(clearing_s)

    return {
        "schema": SCHEMA_THERMAL,
        "status": "PASS" if passed else "FAIL",
        "check": "ADIABATIC_CONDUCTOR_SHORT_CIRCUIT_WITHSTAND",
        "scope": "EXPLICIT_K_S_TIME_ADIABATIC_CHECK",
        "element": element,
        "reference_target": deepcopy(REFERENCE_TARGETS["conductor_overcurrent"]),
        "inputs": {
            "fault_current_ka": fault_ka,
            "clearing_time_s": clearing_s,
            "section_mm2": section,
            "k_a_sqrt_s_per_mm2": k_value,
            "k_source_reference": k_source,
            "clearing_time_source_reference": time_source,
        },
        "results": {
            "actual_i2t_a2s": actual_i2t,
            "limit_k2s2_a2s": limit_i2t,
            "utilization_ratio": actual_i2t / limit_i2t,
            "max_permissible_clearing_time_s_at_input_current": max_time_s,
            "max_permissible_current_ka_at_input_time": max_current_a / 1000.0,
        },
        "policies": {
            "k_derived_automatically": False,
            "section_derived_automatically": False,
            "p4_tk_s_consumed": False,
            "clearing_time_must_be_explicit_or_future_p5d": True,
        },
        "full_standard_compliance_claim": False,
        "professional_emission": False,
    }
