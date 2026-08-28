"""P5B — datasets numéricos y evaluación TCC fail-closed.

La interpolación permitida en P5B es lineal en coordenadas log(I)-log(t),
únicamente dentro de un segmento explícito. No hay extrapolación ni unión de
segmentos separados. Las bandas min/max permanecen como bandas.
"""

from __future__ import annotations

from copy import deepcopy
from math import exp, isclose, isfinite, log
from typing import Any

from . import protection_data

SCHEMA = "MCP_ELECTRICO_P5B_TCC_DATASET_V1"
INTERPOLATION = "LOG_LOG_LINEAR"
ALLOWED_SHAPES = {"SINGLE", "BAND"}
ALLOWED_SOURCE_TYPES = {
    "MANUFACTURER_DATASET",
    "MANUFACTURER_DIGITIZED",
    "TEST_DATA",
}
ALLOWED_TIME_SEMANTICS = {
    "TRIP_TIME",
    "TOTAL_CLEARING_TIME",
    "MELTING_TIME",
    "OPERATING_TIME",
}

_datasets: dict[str, dict[str, Any]] = {}


def reset() -> None:
    _datasets.clear()


def _positive(value: Any, code: str, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{code}: {label} debe ser numérico y >0.") from exc
    if not isfinite(number) or number <= 0:
        raise ValueError(f"{code}: {label} debe ser finito y >0.")
    return number


def _normalize_points(shape: str, raw_points: list[dict[str, Any]], segment_id: str) -> list[dict[str, float]]:
    if len(raw_points) < 2:
        raise ValueError(f"P5TCC010: {segment_id} requiere al menos dos puntos.")
    points: list[dict[str, float]] = []
    previous_current: float | None = None
    for index, raw in enumerate(raw_points):
        current = _positive(raw.get("current_a"), "P5TCC011", f"{segment_id}.points[{index}].current_a")
        if previous_current is not None and current <= previous_current:
            raise ValueError(f"P5TCC012: {segment_id} requiere corrientes estrictamente crecientes; no se reordena silenciosamente.")
        previous_current = current
        if shape == "SINGLE":
            time_s = _positive(raw.get("time_s"), "P5TCC013", f"{segment_id}.points[{index}].time_s")
            points.append({"current_a": current, "time_s": time_s})
        else:
            time_min = _positive(raw.get("time_min_s"), "P5TCC014", f"{segment_id}.points[{index}].time_min_s")
            time_max = _positive(raw.get("time_max_s"), "P5TCC015", f"{segment_id}.points[{index}].time_max_s")
            if time_min > time_max:
                raise ValueError(f"P5TCC016: {segment_id}.points[{index}] requiere time_min_s <= time_max_s.")
            points.append({"current_a": current, "time_min_s": time_min, "time_max_s": time_max})
    return points


def registrar_dataset(
    dataset_id: str,
    curve_id: str,
    shape: str,
    time_semantics: str,
    segments: list[dict[str, Any]],
    source_type: str,
    source_reference: str,
    source_url: str | None = None,
    revision: str | None = None,
    digitization_method: str | None = None,
) -> dict[str, Any]:
    """Registra puntos TCC explícitos con dominios segmentados y procedencia."""
    did = str(dataset_id or "").strip()
    cid = str(curve_id or "").strip()
    if not did or not cid:
        raise ValueError("P5TCC001: dataset_id y curve_id son obligatorios.")
    if did.lower() in _datasets:
        raise ValueError(f"P5TCC002: dataset ya registrado: {did}")

    curve_shape = str(shape or "").strip().upper()
    if curve_shape not in ALLOWED_SHAPES:
        raise ValueError("P5TCC003: shape debe ser SINGLE o BAND.")
    semantics = str(time_semantics or "").strip().upper()
    if semantics not in ALLOWED_TIME_SEMANTICS:
        raise ValueError("P5TCC004: time_semantics debe declarar qué tiempo representa la curva.")
    src_type = str(source_type or "").strip().upper()
    if src_type not in ALLOWED_SOURCE_TYPES:
        raise ValueError("P5TCC005: source_type no soportado por P5B.")
    reference = str(source_reference or "").strip()
    if not reference:
        raise ValueError("P5TCC006: source_reference es obligatorio.")
    digitization = str(digitization_method or "").strip() or None
    if src_type == "MANUFACTURER_DIGITIZED" and not digitization:
        raise ValueError("P5TCC007: una curva digitalizada requiere digitization_method explícito.")
    if not segments:
        raise ValueError("P5TCC008: se requiere al menos un segmento explícito.")

    normalized_segments: list[dict[str, Any]] = []
    ids: set[str] = set()
    previous_max: float | None = None
    for index, raw_segment in enumerate(segments):
        sid = str(raw_segment.get("id") or f"segment_{index+1}").strip()
        if not sid or sid.lower() in ids:
            raise ValueError("P5TCC009: cada segmento requiere un id único.")
        ids.add(sid.lower())
        points = _normalize_points(curve_shape, list(raw_segment.get("points") or []), sid)
        current_min = points[0]["current_a"]
        current_max = points[-1]["current_a"]
        if previous_max is not None and current_min <= previous_max:
            raise ValueError(
                "P5TCC017: los dominios de segmentos no pueden solaparse ni tocarse; "
                "una discontinuidad debe conservar un hueco explícito."
            )
        previous_max = current_max
        normalized_segments.append({
            "id": sid,
            "label": str(raw_segment.get("label") or "").strip() or None,
            "current_min_a": current_min,
            "current_max_a": current_max,
            "points": points,
        })

    record = {
        "schema": SCHEMA,
        "dataset_id": did,
        "curve_id": cid,
        "shape": curve_shape,
        "time_semantics": semantics,
        "units": {"current": "A", "time": "s"},
        "interpolation": INTERPOLATION,
        "extrapolation": False,
        "cross_segment_interpolation": False,
        "segments": normalized_segments,
        "source": {
            "type": src_type,
            "reference": reference,
            "url": str(source_url or "").strip() or None,
            "revision": str(revision or "").strip() or None,
            "digitization_method": digitization,
        },
        "synthetic_manufacturer_curve": False,
        "professional_emission": False,
    }
    _datasets[did.lower()] = record
    return deepcopy(record)


def obtener_dataset(dataset_id: str) -> dict[str, Any] | None:
    return deepcopy(_datasets.get(str(dataset_id or "").strip().lower()))


def listar_datasets() -> list[dict[str, Any]]:
    return [deepcopy(item) for item in _datasets.values()]


def _log_interp(x: float, x1: float, y1: float, x2: float, y2: float) -> float:
    ratio = (log(x) - log(x1)) / (log(x2) - log(x1))
    return exp(log(y1) + ratio * (log(y2) - log(y1)))


def _resolve_in_segment(dataset: dict[str, Any], segment: dict[str, Any], current_a: float) -> dict[str, Any]:
    points = segment["points"]
    for point in points:
        if isclose(current_a, float(point["current_a"]), rel_tol=1e-12, abs_tol=0.0):
            values = (
                {"time_s": float(point["time_s"])}
                if dataset["shape"] == "SINGLE"
                else {
                    "time_min_s": float(point["time_min_s"]),
                    "time_max_s": float(point["time_max_s"]),
                }
            )
            return {
                "status": "RESOLVED_EXACT",
                "values": values,
                "interpolation_used": False,
                "bracket": None,
            }

    for left, right in zip(points, points[1:]):
        x1 = float(left["current_a"])
        x2 = float(right["current_a"])
        if x1 < current_a < x2:
            if dataset["shape"] == "SINGLE":
                values = {
                    "time_s": _log_interp(current_a, x1, float(left["time_s"]), x2, float(right["time_s"]))
                }
            else:
                values = {
                    "time_min_s": _log_interp(
                        current_a, x1, float(left["time_min_s"]), x2, float(right["time_min_s"])
                    ),
                    "time_max_s": _log_interp(
                        current_a, x1, float(left["time_max_s"]), x2, float(right["time_max_s"])
                    ),
                }
            return {
                "status": "RESOLVED_INTERPOLATED",
                "values": values,
                "interpolation_used": True,
                "bracket": {"current_left_a": x1, "current_right_a": x2},
            }
    raise RuntimeError("P5TCC_INTERNAL: current inside segment domain but no bracket was found.")


def evaluar_dataset(dataset_id: str, current_a: float) -> dict[str, Any]:
    """Evalúa una curva solo dentro del dominio explícito de un segmento."""
    dataset = obtener_dataset(dataset_id)
    if not dataset:
        return {
            "status": "DATASET_NOT_FOUND",
            "dataset_id": str(dataset_id),
            "current_a": current_a,
            "values": None,
            "professional_emission": False,
        }
    current = _positive(current_a, "P5TCC020", "current_a")
    candidates = [
        item for item in dataset["segments"]
        if float(item["current_min_a"]) <= current <= float(item["current_max_a"])
    ]
    if not candidates:
        return {
            "schema": "MCP_ELECTRICO_P5B_TCC_EVALUATION_V1",
            "status": "OUT_OF_DOMAIN",
            "dataset_id": dataset["dataset_id"],
            "curve_id": dataset["curve_id"],
            "current_a": current,
            "values": None,
            "interpolation_used": False,
            "extrapolated": False,
            "cross_segment_interpolation": False,
            "time_semantics": dataset["time_semantics"],
            "professional_emission": False,
        }
    if len(candidates) != 1:
        raise RuntimeError("P5TCC_INTERNAL: segment domains are ambiguous despite registration validation.")

    segment = candidates[0]
    resolved = _resolve_in_segment(dataset, segment, current)
    return {
        "schema": "MCP_ELECTRICO_P5B_TCC_EVALUATION_V1",
        "status": resolved["status"],
        "dataset_id": dataset["dataset_id"],
        "curve_id": dataset["curve_id"],
        "segment_id": segment["id"],
        "current_a": current,
        "values": resolved["values"],
        "interpolation_method": INTERPOLATION if resolved["interpolation_used"] else None,
        "interpolation_used": resolved["interpolation_used"],
        "bracket": resolved["bracket"],
        "extrapolated": False,
        "cross_segment_interpolation": False,
        "time_semantics": dataset["time_semantics"],
        "source": deepcopy(dataset["source"]),
        "professional_emission": False,
    }


def vincular_dataset_dispositivo(dispositivo: str, dataset_id: str) -> dict[str, Any]:
    dataset = obtener_dataset(dataset_id)
    if not dataset:
        raise ValueError(f"P5TCC030: dataset no encontrado: {dataset_id}")
    return protection_data.vincular_dataset_numerico(
        dispositivo,
        {
            "dataset_id": dataset["dataset_id"],
            "dataset_schema": dataset["schema"],
            "curve_id": dataset["curve_id"],
            "shape": dataset["shape"],
            "time_semantics": dataset["time_semantics"],
            "interpolation": dataset["interpolation"],
            "source": deepcopy(dataset["source"]),
        },
    )


def evaluar_dispositivo(dispositivo: str, current_a: float) -> dict[str, Any]:
    device = protection_data.obtener_dispositivo(dispositivo)
    if not device:
        return {"status": "DEVICE_NOT_FOUND", "device_id": str(dispositivo), "professional_emission": False}
    curve = device.get("curve") or {}
    dataset_id = curve.get("dataset_id")
    if not dataset_id or not curve.get("numeric_dataset_loaded"):
        return {
            "status": "TCC_DATA_NOT_BOUND",
            "device_id": device["id"],
            "current_a": current_a,
            "professional_emission": False,
        }
    result = evaluar_dataset(str(dataset_id), current_a)
    result["device_id"] = device["id"]
    result["protected_element"] = device["protected_element"]
    return result
