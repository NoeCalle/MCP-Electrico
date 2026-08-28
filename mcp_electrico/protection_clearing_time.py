"""P5D — promoción fail-closed de tiempos TCC a clearing time.

P5B puede evaluar distintos significados de tiempo. P5D solo promueve
``TOTAL_CLEARING_TIME`` a tiempo final de despeje. Las demás semánticas
permanecen evaluables como curva, pero no se convierten silenciosamente en
clearing time.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import protection_curves

SCHEMA = "MCP_ELECTRICO_P5D_CLEARING_TIME_V1"
CONTRACT_SCHEMA = "MCP_ELECTRICO_P5D_CLEARING_TIME_CONTRACT_V1"

CLEARING_READY_SEMANTICS = {"TOTAL_CLEARING_TIME"}
NON_PROMOTED_SEMANTICS = {"TRIP_TIME", "MELTING_TIME", "OPERATING_TIME"}


def obtener_contrato_p5d() -> dict[str, Any]:
    return {
        "schema": CONTRACT_SCHEMA,
        "clearing_ready_time_semantics": sorted(CLEARING_READY_SEMANTICS),
        "evaluated_but_not_promoted": sorted(NON_PROMOTED_SEMANTICS),
        "band_policy": {
            "preserve_min_max": True,
            "average_band": False,
            "conservative_time_for_thermal_check": "time_max_s",
        },
        "domain_policy": {
            "extrapolation": False,
            "cross_segment_interpolation": False,
            "out_of_domain": "CLEARING_TIME_NOT_READY",
        },
        "p4_tk_s_consumed": False,
        "professional_emission": False,
    }


def _base_from_curve(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "device_id": result.get("device_id"),
        "protected_element": result.get("protected_element"),
        "current_a": result.get("current_a"),
        "dataset_id": result.get("dataset_id"),
        "curve_id": result.get("curve_id"),
        "segment_id": result.get("segment_id"),
        "time_semantics": result.get("time_semantics"),
        "source": deepcopy(result.get("source")),
        "curve_evaluation_status": result.get("status"),
        "interpolation_method": result.get("interpolation_method"),
        "interpolation_used": result.get("interpolation_used", False),
        "bracket": deepcopy(result.get("bracket")),
        "extrapolated": result.get("extrapolated", False),
        "cross_segment_interpolation": result.get("cross_segment_interpolation", False),
        "p4_tk_s_consumed": False,
        "professional_emission": False,
    }


def evaluar_tiempo_despeje(dispositivo: str, current_a: float) -> dict[str, Any]:
    """Evalúa la TCC del dispositivo y promueve solo TOTAL_CLEARING_TIME."""
    curve = protection_curves.evaluar_dispositivo(dispositivo, current_a)

    if curve.get("status") == "DEVICE_NOT_FOUND":
        return {
            "schema": SCHEMA,
            "status": "DEVICE_NOT_FOUND",
            "device_id": curve.get("device_id") or str(dispositivo),
            "clearing_time": None,
            "p4_tk_s_consumed": False,
            "professional_emission": False,
        }

    if curve.get("status") == "TCC_DATA_NOT_BOUND":
        return {
            "schema": SCHEMA,
            "status": "TCC_DATA_NOT_BOUND",
            "device_id": curve.get("device_id") or str(dispositivo),
            "current_a": curve.get("current_a"),
            "clearing_time": None,
            "p4_tk_s_consumed": False,
            "professional_emission": False,
        }

    base = _base_from_curve(curve)
    if curve.get("status") == "OUT_OF_DOMAIN":
        return {
            **base,
            "status": "CLEARING_TIME_NOT_READY",
            "reason": "TCC_OUT_OF_DOMAIN",
            "clearing_time": None,
        }

    semantics = str(curve.get("time_semantics") or "").upper()
    if semantics not in CLEARING_READY_SEMANTICS:
        return {
            **base,
            "status": "TIME_SEMANTICS_NOT_CLEARING_READY",
            "reason": f"{semantics or 'UNDECLARED'} no se promueve automáticamente a clearing time P5D.",
            "curve_values": deepcopy(curve.get("values")),
            "clearing_time": None,
        }

    values = curve.get("values") or {}
    if "time_s" in values:
        time_s = float(values["time_s"])
        clearing = {
            "kind": "SINGLE",
            "time_s": time_s,
            "time_min_s": time_s,
            "time_max_s": time_s,
            "conservative_time_s": time_s,
        }
    elif "time_min_s" in values and "time_max_s" in values:
        time_min = float(values["time_min_s"])
        time_max = float(values["time_max_s"])
        clearing = {
            "kind": "BAND",
            "time_s": None,
            "time_min_s": time_min,
            "time_max_s": time_max,
            "conservative_time_s": time_max,
        }
    else:
        return {
            **base,
            "status": "CLEARING_TIME_NOT_READY",
            "reason": "UNRECOGNIZED_TCC_VALUES",
            "clearing_time": None,
        }

    return {
        **base,
        "status": "CLEARING_TIME_READY",
        "clearing_time": clearing,
        "usable_for_thermal_check": True,
        "thermal_check_recommended_time_field": "conservative_time_s",
        "full_standard_compliance_claim": False,
    }
