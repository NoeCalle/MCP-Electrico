"""P5E — coordinación temporal puntual y conservadora.

P5E compara tiempos finales de despeje P5D de un dispositivo downstream y uno
upstream en corrientes explícitas. No infiere topología, no barre dominios y no
promueve el resultado a selectividad total/parcial, backup o cascading.
"""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any

from . import protection_clearing_time

SCHEMA = "MCP_ELECTRICO_P5E_TEMPORAL_COORDINATION_V1"
CONTRACT_SCHEMA = "MCP_ELECTRICO_P5E_COORDINATION_CONTRACT_V1"


def _positive(value: Any, code: str, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{code}: {label} debe ser numérico y >0.") from exc
    if not isfinite(number) or number <= 0:
        raise ValueError(f"{code}: {label} debe ser finito y >0.")
    return number


def _nonnegative(value: Any, code: str, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{code}: {label} debe ser numérico y >=0.") from exc
    if not isfinite(number) or number < 0:
        raise ValueError(f"{code}: {label} debe ser finito y >=0.")
    return number


def _reference(value: str | None, code: str, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{code}: {label} es obligatorio para trazabilidad.")
    return text


def obtener_contrato_p5e() -> dict[str, Any]:
    return {
        "schema": CONTRACT_SCHEMA,
        "method": "TEMPORAL_POINT_COORDINATION",
        "time_source": "P5D_CLEARING_TIME_READY",
        "currents": "EXPLICIT_PER_DEVICE",
        "relationship": "EXPLICIT_UPSTREAM_DOWNSTREAM_REFERENCE",
        "band_comparison": {
            "conservative_margin": "upstream_time_min_s - downstream_time_max_s",
            "pass_rule": "conservative_margin_s >= required_margin_s",
            "average_bands": False,
        },
        "domain_scan": False,
        "topology_inference": False,
        "claims": {
            "temporal_point_coordination": True,
            "total_selectivity": False,
            "partial_selectivity": False,
            "energy_selectivity": False,
            "backup": False,
            "cascading": False,
        },
        "professional_emission": False,
    }


def _interval(result: dict[str, Any]) -> dict[str, float] | None:
    clearing = result.get("clearing_time") or {}
    if result.get("status") != "CLEARING_TIME_READY":
        return None
    try:
        low = float(clearing["time_min_s"])
        high = float(clearing["time_max_s"])
    except (KeyError, TypeError, ValueError):
        return None
    return {"time_min_s": low, "time_max_s": high}


def evaluar_coordinacion_temporal(
    dispositivo_downstream: str,
    corriente_downstream_a: float,
    dispositivo_upstream: str,
    corriente_upstream_a: float,
    margen_minimo_s: float,
    fuente_relacion: str,
    fuente_corrientes: str,
) -> dict[str, Any]:
    """Compara conservadoramente dos clearing times P5D en un punto explícito."""
    downstream_id = str(dispositivo_downstream or "").strip()
    upstream_id = str(dispositivo_upstream or "").strip()
    if not downstream_id or not upstream_id:
        raise ValueError("P5E001: deben declararse dispositivo_downstream y dispositivo_upstream.")
    if downstream_id.lower() == upstream_id.lower():
        raise ValueError("P5E002: downstream y upstream deben ser dispositivos distintos.")

    current_down = _positive(corriente_downstream_a, "P5E003", "corriente_downstream_a")
    current_up = _positive(corriente_upstream_a, "P5E004", "corriente_upstream_a")
    required_margin = _nonnegative(margen_minimo_s, "P5E005", "margen_minimo_s")
    relationship_source = _reference(fuente_relacion, "P5E006", "fuente_relacion")
    currents_source = _reference(fuente_corrientes, "P5E007", "fuente_corrientes")

    downstream = protection_clearing_time.evaluar_tiempo_despeje(downstream_id, current_down)
    upstream = protection_clearing_time.evaluar_tiempo_despeje(upstream_id, current_up)
    down_interval = _interval(downstream)
    up_interval = _interval(upstream)

    if down_interval is None or up_interval is None:
        issues: list[dict[str, str]] = []
        if down_interval is None:
            issues.append({
                "code": "P5E101",
                "message": f"Downstream no tiene clearing time P5D listo: {downstream.get('status')}",
            })
        if up_interval is None:
            issues.append({
                "code": "P5E102",
                "message": f"Upstream no tiene clearing time P5D listo: {upstream.get('status')}",
            })
        return {
            "schema": SCHEMA,
            "status": "COORDINATION_NOT_READY",
            "method": "TEMPORAL_POINT_COORDINATION",
            "relationship_source_reference": relationship_source,
            "currents_source_reference": currents_source,
            "downstream": deepcopy(downstream),
            "upstream": deepcopy(upstream),
            "issues": issues,
            "claims": {
                "temporal_point_coordination": False,
                "selectivity": "NOT_EVALUATED",
                "backup": "NOT_EVALUATED",
                "cascading": "NOT_EVALUATED",
            },
            "professional_emission": False,
        }

    conservative_margin = up_interval["time_min_s"] - down_interval["time_max_s"]
    optimistic_margin = up_interval["time_max_s"] - down_interval["time_min_s"]
    passed = conservative_margin + 1e-12 >= required_margin

    return {
        "schema": SCHEMA,
        "status": "PASS" if passed else "FAIL",
        "method": "TEMPORAL_POINT_COORDINATION",
        "scope": "POINTWISE_TIME_COORDINATION_NOT_SELECTIVITY_CLAIM",
        "relationship": {
            "downstream_device": downstream.get("device_id") or downstream_id,
            "upstream_device": upstream.get("device_id") or upstream_id,
            "source_reference": relationship_source,
            "topology_inferred": False,
        },
        "currents": {
            "downstream_a": current_down,
            "upstream_a": current_up,
            "source_reference": currents_source,
            "same_current_assumed": False,
        },
        "downstream_time": down_interval,
        "upstream_time": up_interval,
        "required_margin_s": required_margin,
        "conservative_margin_s": conservative_margin,
        "optimistic_margin_s": optimistic_margin,
        "pass_rule": "upstream_time_min_s - downstream_time_max_s >= required_margin_s",
        "downstream_trace": deepcopy(downstream),
        "upstream_trace": deepcopy(upstream),
        "claims": {
            "temporal_point_coordination": True,
            "selectivity": "NOT_EVALUATED",
            "backup": "NOT_EVALUATED",
            "cascading": "NOT_EVALUATED",
        },
        "domain_scan_performed": False,
        "professional_emission": False,
    }
