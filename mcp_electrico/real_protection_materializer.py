"""P8C4B — materialización P5/TCC del primer proyecto real.

P8C4A reconstruye el modelo y materializa P3. P8C4B agrega dispositivos P5A,
metadata de curva y datasets numéricos P5B, sin evaluar tiempos, capacidad de
corte, coordinación ni ningún otro estudio.

Reglas:
- preflight P5 completo antes de crear un dispositivo;
- circuit_breaker usa Icu/Ics/Icw; fuse usa breaking_capacity_ka;
- `breaking_capacity_ka` en circuit_breaker solo se tolera como alias legacy de
  P8B si fue declarado explícitamente y coincide exactamente con Icu;
- cada dispositivo tiene una curva y exactamente un dataset numérico ligado;
- SINGLE/BAND y puntos se validan sin extrapolación ni síntesis;
- In P5 debe coincidir con In P3 cuando el mismo Line.* tiene ficha P3;
- no se ejecuta ninguna evaluación P5.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from math import isfinite
from typing import Any

from . import (
    protection_curves,
    protection_data,
    real_engineering_materializer,
    workspace_state,
)

SCHEMA = "MCP_ELECTRICO_P8C4B_REAL_PROTECTION_MATERIALIZER_V1"
STATUS_BLOCKED_PREFLIGHT = "BLOCKED_BY_P5_PREFLIGHT"
STATUS_BLOCKED_ENGINEERING = "BLOCKED_BY_ENGINEERING_MATERIALIZATION"
STATUS_NOT_REQUESTED = "P5_NOT_REQUESTED"
STATUS_MATERIALIZED = "P5_TCC_MATERIALIZED_NOT_EXECUTED"
STATUS_FAILED = "P5_MATERIALIZATION_FAILED"
PROTECTION_SCOPE = "PROTECTION_TCC"
AMPACITY_SCOPE = "AMPACITY"

_ALLOWED_DEVICE_TYPES = {"circuit_breaker", "fuse"}
_ALLOWED_CURVE_TYPES = {"MANUFACTURER_TCC", "STANDARD_CURVE", "TEST_CURVE"}
_ALLOWED_SHAPES = {"SINGLE", "BAND"}
_ALLOWED_TIME_SEMANTICS = {"TRIP_TIME", "TOTAL_CLEARING_TIME", "MELTING_TIME", "OPERATING_TIME"}
_ALLOWED_SOURCE_TYPES = {"MANUFACTURER_DATASET", "MANUFACTURER_DIGITIZED", "TEST_DATA"}


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _positive(value: Any) -> bool:
    number = _number(value)
    return number is not None and number > 0


def _issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _device_name(raw: Any) -> str:
    value = str(raw or "").strip()
    if value.lower().startswith("protection."):
        value = value.split(".", 1)[1]
    return value


def _validate_settings(item: dict[str, Any], path: str, device_type: str) -> list[dict[str, str]]:
    settings = item.get("settings")
    if settings is None:
        return []
    if not isinstance(settings, dict):
        return [_issue("P8C4B030", f"{path}.settings", "settings debe ser un objeto.")]
    issues: list[dict[str, str]] = []
    if device_type != "circuit_breaker":
        issues.append(_issue("P8C4B031", f"{path}.settings", "Ir/Isd/Ii solo se materializan para circuit_breaker."))
        return issues
    values: list[float] = []
    for key in ("ir_a", "isd_a", "ii_a"):
        value = settings.get(key)
        if value is not None:
            if not _positive(value):
                issues.append(_issue("P8C4B032", f"{path}.settings.{key}", f"{key} debe ser >0."))
            else:
                values.append(float(value))
    if not values:
        issues.append(_issue("P8C4B033", f"{path}.settings", "settings requiere al menos Ir, Isd o Ii explícito."))
    if values and values != sorted(values):
        issues.append(_issue("P8C4B034", f"{path}.settings", "Los pickups coexistentes deben cumplir Ir <= Isd <= Ii."))
    if not _present(settings.get("source_reference")):
        issues.append(_issue("P8C4B035", f"{path}.settings.source_reference", "Los ajustes requieren procedencia explícita."))
    return issues


def _validate_points(shape: str, points: Any, path: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not isinstance(points, list) or len(points) < 2:
        return [_issue("P8C4B060", path, "Cada segmento TCC requiere al menos dos puntos explícitos.")]
    previous_current: float | None = None
    for i, point in enumerate(points):
        ppath = f"{path}[{i}]"
        if not isinstance(point, dict):
            issues.append(_issue("P8C4B061", ppath, "Cada punto TCC debe ser un objeto."))
            continue
        current = _number(point.get("current_a"))
        if current is None or current <= 0:
            issues.append(_issue("P8C4B062", f"{ppath}.current_a", "current_a debe ser >0."))
        elif previous_current is not None and current <= previous_current:
            issues.append(_issue("P8C4B063", f"{ppath}.current_a", "Las corrientes deben ser estrictamente crecientes; no se reordenan."))
        if current is not None and current > 0:
            previous_current = current

        if shape == "SINGLE":
            if not _positive(point.get("time_s")):
                issues.append(_issue("P8C4B064", f"{ppath}.time_s", "SINGLE requiere time_s >0."))
        else:
            tmin = _number(point.get("time_min_s"))
            tmax = _number(point.get("time_max_s"))
            if tmin is None or tmin <= 0:
                issues.append(_issue("P8C4B065", f"{ppath}.time_min_s", "BAND requiere time_min_s >0."))
            if tmax is None or tmax <= 0:
                issues.append(_issue("P8C4B066", f"{ppath}.time_max_s", "BAND requiere time_max_s >0."))
            if tmin is not None and tmax is not None and tmin > tmax:
                issues.append(_issue("P8C4B067", ppath, "BAND requiere time_min_s <= time_max_s."))
    return issues


def _validate_dataset(item: dict[str, Any], path: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for key in ("device_id", "dataset_id", "curve_id", "shape", "time_semantics", "source_type", "source_reference", "segments"):
        if not _present(item.get(key)):
            issues.append(_issue("P8C4B050", f"{path}.{key}", f"Dataset TCC materializable requiere {key}."))

    shape = str(item.get("shape") or "").strip().upper()
    if shape and shape not in _ALLOWED_SHAPES:
        issues.append(_issue("P8C4B051", f"{path}.shape", "shape debe ser SINGLE o BAND."))
    semantics = str(item.get("time_semantics") or "").strip().upper()
    if semantics and semantics not in _ALLOWED_TIME_SEMANTICS:
        issues.append(_issue("P8C4B052", f"{path}.time_semantics", "Semántica de tiempo no soportada por P5B."))
    source_type = str(item.get("source_type") or "").strip().upper()
    if source_type and source_type not in _ALLOWED_SOURCE_TYPES:
        issues.append(_issue("P8C4B053", f"{path}.source_type", "source_type no soportado por P5B."))
    if source_type == "MANUFACTURER_DIGITIZED" and not _present(item.get("digitization_method")):
        issues.append(_issue("P8C4B054", f"{path}.digitization_method", "Una curva digitalizada requiere método explícito."))

    segments = item.get("segments")
    if isinstance(segments, list) and segments:
        seen: set[str] = set()
        previous_max: float | None = None
        for i, segment in enumerate(segments):
            spath = f"{path}.segments[{i}]"
            if not isinstance(segment, dict):
                issues.append(_issue("P8C4B055", spath, "Cada segmento debe ser un objeto."))
                continue
            sid = str(segment.get("id") or "").strip()
            if not sid:
                issues.append(_issue("P8C4B056", f"{spath}.id", "Cada segmento requiere id explícito en P8C4B."))
            elif sid.lower() in seen:
                issues.append(_issue("P8C4B057", f"{spath}.id", "IDs de segmento duplicados."))
            else:
                seen.add(sid.lower())
            points = segment.get("points")
            issues.extend(_validate_points(shape, points, f"{spath}.points"))
            if isinstance(points, list) and len(points) >= 2:
                first = _number((points[0] or {}).get("current_a")) if isinstance(points[0], dict) else None
                last = _number((points[-1] or {}).get("current_a")) if isinstance(points[-1], dict) else None
                if first is not None and last is not None and first > 0 and last > 0:
                    if previous_max is not None and first <= previous_max:
                        issues.append(_issue("P8C4B058", spath, "Los dominios de segmentos no pueden solaparse ni tocarse."))
                    previous_max = last
    return issues


def _p5_preflight(manifest: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, Any]], list[dict[str, Any]]]:
    protection = manifest.get("protection") or {}
    devices = protection.get("devices") or []
    datasets = protection.get("tcc_datasets") or []
    issues: list[dict[str, str]] = []
    if not isinstance(devices, list) or not devices:
        issues.append(_issue("P8C4B001", "protection.devices", "PROTECTION_TCC requiere dispositivos P5 materializables."))
        return issues, [], []
    if not isinstance(datasets, list) or not datasets:
        issues.append(_issue("P8C4B002", "protection.tcc_datasets", "PROTECTION_TCC requiere datasets TCC numéricos."))
        return issues, list(devices) if isinstance(devices, list) else [], []

    topology_ids = set()
    topology = manifest.get("topology") or {}
    for group in ("transformers", "lines", "loads"):
        for item in topology.get(group) or []:
            if isinstance(item, dict) and _present(item.get("id")):
                topology_ids.add(str(item["id"]).strip())
    topology_ids.update(f"Bus.{str(bus).strip()}" for bus in topology.get("buses") or [] if str(bus).strip())

    p3_in = {
        str(item.get("element_id") or "").strip(): float(item["in_a"])
        for item in manifest.get("ampacity") or []
        if isinstance(item, dict) and _present(item.get("element_id")) and _positive(item.get("in_a"))
    }

    device_by_id: dict[str, dict[str, Any]] = {}
    curve_by_device: dict[str, str] = {}
    for i, item in enumerate(devices):
        path = f"protection.devices[{i}]"
        if not isinstance(item, dict):
            issues.append(_issue("P8C4B003", path, "El dispositivo debe ser un objeto."))
            continue
        for key in ("id", "type", "protected_element", "in_a", "ue_kv", "standard_reference", "source_reference", "curve_id", "curve_type", "curve_source_reference"):
            if not _present(item.get(key)):
                issues.append(_issue("P8C4B004", f"{path}.{key}", f"Dispositivo P5 materializable requiere {key}."))

        name = _device_name(item.get("id"))
        key = name.lower()
        if name:
            if key in device_by_id:
                issues.append(_issue("P8C4B005", f"{path}.id", "ID de dispositivo duplicado."))
            device_by_id[key] = item
        device_type = str(item.get("type") or "").strip().lower()
        if device_type and device_type not in _ALLOWED_DEVICE_TYPES:
            issues.append(_issue("P8C4B006", f"{path}.type", "P8C4B solo admite circuit_breaker o fuse."))
        for field in ("in_a", "ue_kv"):
            if _present(item.get(field)) and not _positive(item.get(field)):
                issues.append(_issue("P8C4B007", f"{path}.{field}", f"{field} debe ser >0."))

        protected = str(item.get("protected_element") or "").strip()
        if protected and protected not in topology_ids:
            issues.append(_issue("P8C4B008", f"{path}.protected_element", "El elemento protegido no existe en la topología declarada."))
        if protected in p3_in and _positive(item.get("in_a")) and abs(float(item["in_a"]) - p3_in[protected]) > 1e-9:
            issues.append(_issue("P8C4B009", f"{path}.in_a", "In P5 no coincide con In P3 del mismo elemento; no se elige uno silenciosamente."))

        if device_type == "circuit_breaker":
            if not _positive(item.get("icu_ka")):
                issues.append(_issue("P8C4B010", f"{path}.icu_ka", "circuit_breaker requiere Icu explícita >0."))
            for field in ("ics_ka", "icw_ka"):
                if item.get(field) is not None and not _positive(item.get(field)):
                    issues.append(_issue("P8C4B011", f"{path}.{field}", f"{field} debe ser >0 cuando se declara."))
            if _positive(item.get("icu_ka")) and _positive(item.get("ics_ka")) and float(item["ics_ka"]) > float(item["icu_ka"]):
                issues.append(_issue("P8C4B012", path, "Ics no puede superar Icu."))
            legacy = item.get("breaking_capacity_ka")
            if legacy is not None:
                if not _positive(legacy) or not _positive(item.get("icu_ka")) or abs(float(legacy) - float(item["icu_ka"])) > 1e-9:
                    issues.append(_issue("P8C4B013", f"{path}.breaking_capacity_ka", "Alias legacy P8B debe coincidir exactamente con Icu; P5 no lo consume como rating de breaker."))
        elif device_type == "fuse":
            if not _positive(item.get("breaking_capacity_ka")):
                issues.append(_issue("P8C4B014", f"{path}.breaking_capacity_ka", "fuse requiere poder de corte explícito >0."))
            if any(item.get(field) is not None for field in ("icu_ka", "ics_ka", "icw_ka")):
                issues.append(_issue("P8C4B015", path, "fuse no admite Icu/Ics/Icw en P5A."))

        curve_type = str(item.get("curve_type") or "").strip().upper()
        if curve_type and curve_type not in _ALLOWED_CURVE_TYPES:
            issues.append(_issue("P8C4B016", f"{path}.curve_type", "curve_type no soportado por P5A."))
        if name and _present(item.get("curve_id")):
            curve_by_device[key] = str(item["curve_id"]).strip()
        issues.extend(_validate_settings(item, path, device_type))

    dataset_by_device: dict[str, dict[str, Any]] = {}
    dataset_ids: set[str] = set()
    for i, item in enumerate(datasets):
        path = f"protection.tcc_datasets[{i}]"
        if not isinstance(item, dict):
            issues.append(_issue("P8C4B040", path, "El dataset debe ser un objeto."))
            continue
        issues.extend(_validate_dataset(item, path))
        device_key = _device_name(item.get("device_id")).lower()
        if device_key:
            if device_key not in device_by_id:
                issues.append(_issue("P8C4B041", f"{path}.device_id", "Dataset TCC referencia un dispositivo inexistente."))
            if device_key in dataset_by_device:
                issues.append(_issue("P8C4B042", f"{path}.device_id", "P8C4B v1 admite exactamente un dataset TCC por dispositivo."))
            dataset_by_device[device_key] = item
            expected_curve = curve_by_device.get(device_key)
            curve_id = str(item.get("curve_id") or "").strip()
            if expected_curve and curve_id and curve_id != expected_curve:
                issues.append(_issue("P8C4B043", f"{path}.curve_id", "curve_id del dataset no coincide con la curva vinculada al dispositivo."))
        did = str(item.get("dataset_id") or "").strip().lower()
        if did:
            if did in dataset_ids:
                issues.append(_issue("P8C4B044", f"{path}.dataset_id", "dataset_id duplicado."))
            dataset_ids.add(did)

    for device_key in device_by_id:
        if device_key not in dataset_by_device:
            issues.append(_issue("P8C4B045", "protection.tcc_datasets", f"Falta dataset numérico para {device_by_id[device_key].get('id')}."))

    return issues, list(devices), list(datasets)


def _fingerprint(engineering: dict[str, Any], devices: list[dict[str, Any]], datasets: list[dict[str, Any]]) -> str:
    payload = {
        "engineering_fingerprint": ((engineering.get("p3") or {}).get("engineering_fingerprint_sha256") or engineering.get("model_fingerprint_sha256")),
        "devices": devices,
        "datasets": datasets,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(raw.encode("utf-8")).hexdigest()


def materializar_protecciones(manifest: dict[str, Any]) -> dict[str, Any]:
    """Materializa P5A/P5B sin evaluar TCC ni otros checks P5."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest debe ser dict.")
    manifest_copy = deepcopy(manifest)
    requested = [str(x).strip().upper() for x in manifest_copy.get("requested_scope") or [] if str(x).strip()]
    base = {
        "schema": SCHEMA,
        "requested_scope": requested,
        "electrical_calculation_performed": False,
        "ampacity_calculation_performed": False,
        "protection_calculation_performed": False,
        "tcc_evaluation_performed": False,
        "studies_executed": [],
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
    }

    if PROTECTION_SCOPE not in set(requested):
        engineering = real_engineering_materializer.materializar_datos_ingenieria(manifest_copy)
        return {
            **base,
            "protection_materializer_status": STATUS_NOT_REQUESTED,
            "p5_materialized": False,
            "issues": [],
            "engineering": engineering,
        }

    preflight, devices, datasets = _p5_preflight(manifest_copy)
    if preflight:
        return {
            **base,
            "protection_materializer_status": STATUS_BLOCKED_PREFLIGHT,
            "p5_materialized": False,
            "issues": preflight,
            "engineering_materialization_performed": False,
        }

    engineering = real_engineering_materializer.materializar_datos_ingenieria(manifest_copy)
    model_ok = engineering.get("model_materialization_status") == "MODEL_BUILT_NOT_EXECUTED"
    if AMPACITY_SCOPE in set(requested):
        engineering_ok = engineering.get("p3_materialized") is True
    else:
        engineering_ok = model_ok
    if not model_ok or not engineering_ok:
        return {
            **base,
            "protection_materializer_status": STATUS_BLOCKED_ENGINEERING,
            "p5_materialized": False,
            "issues": deepcopy(engineering.get("issues") or []),
            "engineering": engineering,
        }

    protection_data.reset()
    protection_curves.reset()
    materialized_devices: list[dict[str, Any]] = []
    materialized_datasets: list[dict[str, Any]] = []
    legacy_aliases: list[dict[str, Any]] = []
    try:
        for item in devices:
            name = _device_name(item["id"])
            device_type = str(item["type"]).strip().lower()
            if device_type == "circuit_breaker" and item.get("breaking_capacity_ka") is not None:
                legacy_aliases.append({
                    "device_id": item["id"],
                    "field": "breaking_capacity_ka",
                    "role": "P8B_LEGACY_INTAKE_ALIAS_ONLY",
                    "authoritative_p5_field": "icu_ka",
                    "value_ka": float(item["breaking_capacity_ka"]),
                })
            record = protection_data.definir_dispositivo(
                nombre=name,
                tipo=device_type,
                elemento_protegido=str(item["protected_element"]),
                in_a=float(item["in_a"]),
                ue_kv=float(item["ue_kv"]),
                fabricante=str(item.get("manufacturer") or "").strip() or None,
                serie=str(item.get("series") or "").strip() or None,
                modelo=str(item.get("model") or "").strip() or None,
                polos=int(item["poles"]) if item.get("poles") is not None else None,
                norma_referencia=str(item["standard_reference"]),
                icu_ka=float(item["icu_ka"]) if device_type == "circuit_breaker" else None,
                ics_ka=float(item["ics_ka"]) if item.get("ics_ka") is not None and device_type == "circuit_breaker" else None,
                icw_ka=float(item["icw_ka"]) if item.get("icw_ka") is not None and device_type == "circuit_breaker" else None,
                poder_corte_ka=float(item["breaking_capacity_ka"]) if device_type == "fuse" else None,
                categoria_utilizacion=str(item.get("utilization_category") or "").strip() or None,
                fuente_referencia=str(item["source_reference"]),
                fuente_url=str(item.get("source_url") or "").strip() or None,
            )
            settings = item.get("settings")
            if isinstance(settings, dict):
                record = protection_data.definir_ajustes(
                    name,
                    ir_a=settings.get("ir_a"),
                    isd_a=settings.get("isd_a"),
                    ii_a=settings.get("ii_a"),
                    fuente_referencia=str(settings["source_reference"]),
                    fuente_url=str(settings.get("source_url") or "").strip() or None,
                )
            record = protection_data.vincular_curva(
                name,
                curva_id=str(item["curve_id"]),
                tipo_curva=str(item["curve_type"]),
                fuente_referencia=str(item["curve_source_reference"]),
                fuente_url=str(item.get("curve_source_url") or "").strip() or None,
                revision=str(item.get("curve_revision") or "").strip() or None,
            )
            materialized_devices.append(record)

        for item in datasets:
            dataset = protection_curves.registrar_dataset(
                dataset_id=str(item["dataset_id"]),
                curve_id=str(item["curve_id"]),
                shape=str(item["shape"]),
                time_semantics=str(item["time_semantics"]),
                segments=deepcopy(item["segments"]),
                source_type=str(item["source_type"]),
                source_reference=str(item["source_reference"]),
                source_url=str(item.get("source_url") or "").strip() or None,
                revision=str(item.get("revision") or "").strip() or None,
                digitization_method=str(item.get("digitization_method") or "").strip() or None,
            )
            protection_curves.vincular_dataset_dispositivo(_device_name(item["device_id"]), str(item["dataset_id"]))
            materialized_datasets.append(dataset)

        final_devices = [
            protection_data.obtener_dispositivo(_device_name(item["id"]))
            for item in devices
        ]
        readiness = [
            protection_data.evaluar_preparacion(_device_name(item["id"]))
            for item in devices
        ]
        fingerprint = _fingerprint(engineering, final_devices, materialized_datasets)
        return {
            **base,
            "protection_materializer_status": STATUS_MATERIALIZED,
            "p5_materialized": True,
            "issues": [],
            "engineering": engineering,
            "p5": {
                "devices": final_devices,
                "datasets": materialized_datasets,
                "readiness": readiness,
                "legacy_intake_aliases": legacy_aliases,
                "protection_fingerprint_sha256": fingerprint,
            },
            "workspace": workspace_state.status(),
            "note": (
                "P5A/P5B fueron materializados, no evaluados. No se calcularon tiempos TCC, capacidad de corte, "
                "soportabilidad térmica, clearing time ni coordinación."
            ),
        }
    except Exception as exc:
        protection_data.reset()
        protection_curves.reset()
        return {
            **base,
            "protection_materializer_status": STATUS_FAILED,
            "p5_materialized": False,
            "issues": [{"code": "P8C4B900", "path": "protection", "message": f"{type(exc).__name__}: {exc}"}],
            "engineering": engineering,
            "p5_state_reset_after_failure": True,
            "workspace": workspace_state.status(),
        }
