"""Continuous temporal envelope of declared P5B log-log clearing curves.

This is curve postprocessing, not a fault solver or a selectivity certificate.
Every interval is split at both curves' knots; its extrema are its endpoints
and the possible stationary point of the difference of two power functions.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from math import exp, isfinite, log
from typing import Any

from . import protection_curves, protection_data

SCHEMA = "MCP_ELECTRICO_P5E_TEMPORAL_RANGE_V1"
METHOD = "CONTINUOUS_LOG_LOG_TEMPORAL_ENVELOPE"


def _number(value: Any, label: str, *, zero: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError(f"P5ER001: {label} no admite booleanos.")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"P5ER001: {label} debe ser numérico y finito.") from exc
    if not isfinite(number) or (number < 0 if zero else number <= 0):
        raise ValueError(f"P5ER001: {label} debe ser finito y {'>=0' if zero else '>0'}.")
    return number


def _text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"P5ER002: {label} requiere una referencia explícita.")
    return value.strip()


def contract() -> dict:
    return {
        "schema": SCHEMA, "method": METHOD,
        "time_semantics": "TOTAL_CLEARING_TIME",
        "interpolation": "P5B_LOG_LOG_LINEAR_WITHIN_ONE_EXPLICIT_SEGMENT",
        "current_mapping": "I_upstream = factor_corriente_upstream * I_downstream",
        "ratio_required": True, "topology_inference": False,
        "range_policy": "FULL_REQUESTED_RANGE_OR_NOT_READY_NO_CLIPPING",
        "extrema": "ENDPOINTS_ALL_KNOTS_AND_INTERIOR_STATIONARY_POINTS",
        "margin": "upstream_time_min_s - downstream_time_max_s",
        "claims": {"temporal_range_coordination": True, "selectivity": "NOT_EVALUATED",
                   "backup": "NOT_EVALUATED", "cascading": "NOT_EVALUATED"},
        "scope": "DECLARED_INTERPOLATED_CURVES_NOT_PHYSICAL_SELECTIVITY",
        "professional_emission": False,
    }


def _snapshot(device_id: str, low: float, high: float) -> tuple[dict, dict | None]:
    device = protection_data.obtener_dispositivo(device_id)
    trace = {"requested_device": device_id, "device": device}
    if not device:
        return {**trace, "reason": "DEVICE_NOT_FOUND"}, None
    binding = device.get("curve") or {}
    dataset = protection_curves.obtener_dataset(binding.get("dataset_id", ""))
    trace["dataset"] = dataset
    if not binding.get("numeric_dataset_loaded") or not dataset:
        return {**trace, "reason": "TCC_DATA_NOT_BOUND"}, None
    if dataset["time_semantics"] != "TOTAL_CLEARING_TIME":
        return {**trace, "reason": "TIME_SEMANTICS_NOT_CLEARING_READY"}, None
    if dataset["interpolation"] != protection_curves.INTERPOLATION:
        return {**trace, "reason": "UNSUPPORTED_INTERPOLATION"}, None
    for segment in dataset["segments"]:
        if segment["current_min_a"] <= low and high <= segment["current_max_a"]:
            trace["selected_segment_id"] = segment["id"]
            trace["sha256"] = sha256(json.dumps(
                {"device": device, "dataset": dataset}, sort_keys=True,
                ensure_ascii=False, allow_nan=False, separators=(",", ":"),
            ).encode("utf8")).hexdigest()
            return trace, segment
    return {**trace, "reason": "RANGE_OUT_OF_DOMAIN_OR_CROSSES_SEGMENT_GAP"}, None


def _piece(points: list[dict], current: float, field: str) -> tuple[float, float]:
    """Return log(t(current)) and slope in log(I), without extrapolation."""
    for left, right in zip(points, points[1:]):
        if left["current_a"] <= current <= right["current_a"]:
            x0, x1 = log(left["current_a"]), log(right["current_a"])
            y0, y1 = log(left[field]), log(right[field])
            slope = (y1 - y0) / (x1 - x0)
            return y0 + slope * (log(current) - x0), slope
    raise ArithmeticError("No se encontró un tramo TCC que cubra la corriente.")


def evaluar_coordinacion_intervalo(
    dispositivo_downstream: str,
    dispositivo_upstream: str,
    corriente_minima_downstream_a: float,
    corriente_maxima_downstream_a: float,
    factor_corriente_upstream: float,
    margen_minimo_s: float,
    fuente_relacion: str,
    fuente_corrientes: str,
) -> dict:
    """Find the global worst time margin in a fully covered declared range.

    The ratio is explicit and constant; it is not inferred from transformer
    ratings, topology, fault currents, CT ratios or load contributions.
    """
    down_id = _text(dispositivo_downstream, "dispositivo_downstream")
    up_id = _text(dispositivo_upstream, "dispositivo_upstream")
    canonical = lambda value: value.lower().removeprefix("protection.")
    if canonical(down_id) == canonical(up_id):
        raise ValueError("P5ER003: downstream y upstream deben ser distintos.")
    low = _number(corriente_minima_downstream_a, "corriente_minima_downstream_a")
    high = _number(corriente_maxima_downstream_a, "corriente_maxima_downstream_a")
    if low >= high:
        raise ValueError("P5ER004: el intervalo requiere corriente mínima < máxima.")
    ratio = _number(factor_corriente_upstream, "factor_corriente_upstream")
    margin = _number(margen_minimo_s, "margen_minimo_s", zero=True)
    relation = _text(fuente_relacion, "fuente_relacion")
    source = _text(fuente_corrientes, "fuente_corrientes")
    up_low, up_high = low * ratio, high * ratio
    if not all(isfinite(v) and v > 0 for v in (up_low, up_high)) or up_low >= up_high:
        raise ValueError("P5ER005: el rango upstream no es representable con el factor declarado.")

    down_trace, down_segment = _snapshot(down_id, low, high)
    up_trace, up_segment = _snapshot(up_id, up_low, up_high)
    base = {
        **contract(), "required_margin_s": margin,
        "relationship": {"downstream_device": down_id, "upstream_device": up_id,
                         "source_reference": relation, "topology_inferred": False},
        "currents": {"downstream_min_a": low, "downstream_max_a": high,
                     "upstream_min_a": up_low, "upstream_max_a": up_high,
                     "upstream_to_downstream_ratio": ratio,
                     "source_reference": source, "same_current_assumed": False},
        "downstream_trace": down_trace, "upstream_trace": up_trace,
        "domain_scan_performed": False, "full_requested_range_evaluated": False,
        "resultados_validos": False,
        "worst_case": None, "intervals": [],
    }
    if down_segment is None or up_segment is None:
        return {**base, "status": "COORDINATION_RANGE_NOT_READY",
                "issues": [{"device": t["requested_device"], "reason": t["reason"]}
                           for t in (down_trace, up_trace) if "reason" in t],
                "claims": {**base["claims"], "temporal_range_coordination": False}}

    # Registration has already rejected touching/overlapping segments. A whole
    # continuous range must fit one segment per device; gaps are never bridged.
    dp, up = down_segment["points"], up_segment["points"]
    df = "time_s" if down_trace["dataset"]["shape"] == "SINGLE" else "time_max_s"
    uf = "time_s" if up_trace["dataset"]["shape"] == "SINGLE" else "time_min_s"
    knots = sorted({low, high} | {p["current_a"] for p in dp if low < p["current_a"] < high}
                   | {p["current_a"] / ratio for p in up if up_low < p["current_a"] < up_high})
    candidates, intervals = [], []
    try:
        for left, right in zip(knots, knots[1:]):
            log_left, log_right = log(left), log(right)
            width = log_right - log_left
            if width <= 0:
                raise ArithmeticError("Tramo no resoluble en precisión logarítmica.")
            # Use the interior to select the correct branch at every knot.
            middle = exp((log_left + log_right) / 2)
            if not left < middle < right:
                raise ArithmeticError("Tramo no resoluble en precisión de corriente.")
            log_down_mid, q = _piece(dp, middle, df)
            log_up_mid, p = _piece(up, middle * ratio, uf)
            log_down = log_down_mid + q * (log_left - log(middle))
            log_up = log_up_mid + p * (log_left - log(middle))
            positions = [(0.0, "LEFT_ENDPOINT"), (width, "RIGHT_ENDPOINT")]
            if p != 0 and q != 0 and (p > 0) == (q > 0) and p != q:
                stationary = (log(abs(q)) + log_down - log(abs(p)) - log_up) / (p - q)
                if 0 < stationary < width:
                    positions.append((stationary, "INTERIOR_STATIONARY_POINT"))
            local = []
            for position, kind in positions:
                current = left if position == 0 else right if position == width else exp(log_left + position)
                tdown, tup = exp(log_down + q * position), exp(log_up + p * position)
                actual_margin = tup - tdown
                if not all(isfinite(v) and v > 0 for v in (current, tdown, tup)) or not isfinite(actual_margin):
                    raise ArithmeticError("Extremo numérico no finito o no representable.")
                point = {"downstream_current_a": current, "upstream_current_a": current * ratio,
                         "downstream_time_max_s": tdown, "upstream_time_min_s": tup,
                         "conservative_margin_s": actual_margin, "kind": kind}
                local.append(point)
                candidates.append(point)
            worst = min(local, key=lambda point: point["conservative_margin_s"])
            intervals.append({"downstream_min_a": left, "downstream_max_a": right,
                              "candidates": local, "worst_case": worst})
    except (ArithmeticError, ValueError, OverflowError) as exc:
        return {**base, "status": "COORDINATION_RANGE_NOT_READY",
                "issues": [{"reason": "NUMERIC_RANGE_NOT_RESOLVABLE", "message": str(exc)}],
                "claims": {**base["claims"], "temporal_range_coordination": False}}

    worst = min(candidates, key=lambda point: point["conservative_margin_s"])
    # No engineering margin or favourable epsilon is added to turn a FAIL into
    # PASS. Borderline floating point results remain visible for review.
    passed = worst["conservative_margin_s"] >= margin
    return {**base, "status": "PASS" if passed else "FAIL", "issues": [],
            "resultados_validos": True,
            "domain_scan_performed": True, "full_requested_range_evaluated": True,
            "worst_case": deepcopy(worst), "intervals": intervals,
            "candidate_count": len(candidates), "interval_count": len(intervals),
            "pass_rule": "min_over_declared_range(upstream_min - downstream_max) >= required_margin",
            "limits": ["Las bandas y ajustes son los declarados; no se agregan tolerancias ausentes.",
                       "El factor de corrientes constante debe justificarse para el escenario.",
                       "La separación de tiempos de despeje no acredita no actuación upstream.",
                       "No evalúa selectividad energética, instantánea, tablas de fabricante ni Icw."]}
