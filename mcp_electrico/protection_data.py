"""Datos canónicos P5A para dispositivos de protección.

P5A almacena únicamente datos explícitos con procedencia. No genera curvas de
fabricante, no infiere ajustes desde In y no calcula tiempos de despeje.
"""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any

from opendssdirect import dss

from . import ampacity, protection_contract

_circuit_name = ""
_devices: dict[str, dict[str, Any]] = {}


def _active_circuit_name() -> str:
    try:
        return str(dss.Circuit.Name() or "")
    except Exception:
        return ""


def _sync() -> None:
    global _circuit_name
    current = _active_circuit_name()
    if current != _circuit_name:
        _circuit_name = current
        _devices.clear()


def reset() -> None:
    global _circuit_name
    _circuit_name = _active_circuit_name()
    _devices.clear()


def _positive(value: float | int | None, code: str, label: str, required: bool = False) -> float | None:
    if value is None:
        if required:
            raise ValueError(f"{code}: {label} es obligatorio y debe ser >0.")
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{code}: {label} debe ser numérico y >0.") from exc
    if not isfinite(number) or number <= 0:
        raise ValueError(f"{code}: {label} debe ser finito y >0.")
    return number


def _canonical_element(raw: str) -> str:
    value = str(raw or "").strip()
    if not value or "." not in value:
        raise ValueError("P5DATA003: elemento_protegido debe usar un ID canónico como Line.*, Transformer.* o Bus.*.")
    kind, name = value.split(".", 1)
    if not name.strip():
        raise ValueError("P5DATA003: elemento_protegido no puede quedar vacío.")
    if kind.lower() == "bus":
        buses = {str(item).lower(): str(item) for item in dss.Circuit.AllBusNames()}
        if name.lower() not in buses:
            raise ValueError(f"P5DATA004: barra no encontrada: {value}")
        return f"Bus.{buses[name.lower()]}"
    if not dss.Circuit.SetActiveElement(value):
        raise ValueError(f"P5DATA004: elemento no encontrado: {value}")
    canonical = str(dss.CktElement.Name() or value)
    return canonical


def _provenance(reference: str | None, url: str | None) -> dict[str, Any]:
    ref = str(reference or "").strip()
    if not ref:
        raise ValueError("P5DATA005: se requiere fuente_referencia explícita; no se aceptan ratings sin procedencia.")
    return {"reference": ref, "url": str(url or "").strip() or None}


def _device_key(raw: str) -> str:
    value = str(raw or "").strip()
    if not value:
        raise ValueError("P5DATA010: dispositivo no especificado.")
    if "." not in value:
        value = f"Protection.{value}"
    return value.lower()


def definir_dispositivo(
    nombre: str,
    tipo: str,
    elemento_protegido: str,
    in_a: float,
    ue_kv: float,
    fabricante: str | None = None,
    serie: str | None = None,
    modelo: str | None = None,
    polos: int | None = None,
    norma_referencia: str | None = None,
    icu_ka: float | None = None,
    ics_ka: float | None = None,
    icw_ka: float | None = None,
    poder_corte_ka: float | None = None,
    categoria_utilizacion: str | None = None,
    fuente_referencia: str | None = None,
    fuente_url: str | None = None,
) -> dict[str, Any]:
    """Registra un interruptor o fusible sin completar ratings ausentes."""
    _sync()
    if not _circuit_name:
        raise ValueError("P5DATA001: no existe un circuito activo.")

    name = str(nombre or "").strip()
    if not name:
        raise ValueError("P5DATA002: nombre es obligatorio.")
    device_id = f"Protection.{name}"
    key = device_id.lower()
    if key in _devices:
        raise ValueError(f"P5DATA006: {device_id} ya existe.")

    device_type = str(tipo or "").strip().lower()
    allowed = set(protection_contract.P5A_SCOPE["included_device_types"])
    if device_type not in allowed:
        if device_type in set(protection_contract.P5A_SCOPE["excluded_device_types"]):
            raise ValueError("P5DATA007: relay está fuera de P5A; requiere modelo dedicado de CT/VT, funciones y elemento de corte.")
        raise ValueError(f"P5DATA007: tipo no soportado en P5A: {device_type}")

    in_value = _positive(in_a, "P5DATA020", "In", required=True)
    ue_value = _positive(ue_kv, "P5DATA021", "Ue", required=True)
    icu = _positive(icu_ka, "P5DATA022", "Icu")
    ics = _positive(ics_ka, "P5DATA023", "Ics")
    icw = _positive(icw_ka, "P5DATA024", "Icw")
    breaking = _positive(poder_corte_ka, "P5DATA025", "poder_corte")
    if icu is not None and ics is not None and ics > icu:
        raise ValueError("P5DATA026: Ics no puede superar Icu en esta ficha explícita.")
    if device_type == "fuse" and any(value is not None for value in (icu, ics, icw)):
        raise ValueError("P5DATA027: un fusible usa poder_corte_ka; no se renombran Icu/Ics/Icw como ratings de fusible.")
    if device_type == "circuit_breaker" and breaking is not None:
        raise ValueError("P5DATA028: un interruptor usa Icu/Ics/Icw; poder_corte_ka queda reservado al fusible en P5A.")

    pole_value = None
    if polos is not None:
        pole_value = int(polos)
        if pole_value < 1 or pole_value > 4:
            raise ValueError("P5DATA029: polos debe estar entre 1 y 4.")

    standard = str(norma_referencia or "").strip()
    if not standard:
        raise ValueError("P5DATA030: norma_referencia debe ser explícita; P5A no selecciona una norma por tipo de equipo.")

    protected = _canonical_element(elemento_protegido)
    record = {
        "schema": "MCP_ELECTRICO_P5A_PROTECTION_DEVICE_V1",
        "id": device_id,
        "name": name,
        "device_type": device_type,
        "protected_element": protected,
        "manufacturer": str(fabricante or "").strip() or None,
        "series": str(serie or "").strip() or None,
        "model": str(modelo or "").strip() or None,
        "poles": pole_value,
        "standard_reference": standard,
        "ratings": {
            "in_a": in_value,
            "ue_kv": ue_value,
            "icu_ka": icu,
            "ics_ka": ics,
            "icw_ka": icw,
            "breaking_capacity_ka": breaking,
        },
        "settings": None,
        "curve": None,
        "provenance": _provenance(fuente_referencia, fuente_url),
        "professional_emission": False,
    }
    _devices[key] = record
    return deepcopy(record)


def definir_ajustes(
    dispositivo: str,
    ir_a: float | None = None,
    isd_a: float | None = None,
    ii_a: float | None = None,
    fuente_referencia: str | None = None,
    fuente_url: str | None = None,
) -> dict[str, Any]:
    """Registra pickups absolutos en amperios; no transforma múltiplos de In."""
    _sync()
    key = _device_key(dispositivo)
    record = _devices.get(key)
    if not record:
        raise ValueError(f"P5DATA011: dispositivo no encontrado: {dispositivo}")
    if record["device_type"] != "circuit_breaker":
        raise ValueError("P5DATA040: ajustes Ir/Isd/Ii P5A solo se modelan para circuit_breaker.")

    values = {
        "ir_a": _positive(ir_a, "P5DATA041", "Ir"),
        "isd_a": _positive(isd_a, "P5DATA042", "Isd"),
        "ii_a": _positive(ii_a, "P5DATA043", "Ii"),
    }
    if all(value is None for value in values.values()):
        raise ValueError("P5DATA044: debe declarar al menos un ajuste Ir/Isd/Ii.")
    present = [value for value in (values["ir_a"], values["isd_a"], values["ii_a"]) if value is not None]
    if present != sorted(present):
        raise ValueError("P5DATA045: los pickups absolutos declarados deben ser no decrecientes Ir <= Isd <= Ii cuando coexisten.")

    record["settings"] = {
        "basis": protection_contract.SETTING_SEMANTICS["basis"],
        **values,
        "provenance": _provenance(fuente_referencia, fuente_url),
        "derived_from_in": False,
    }
    return deepcopy(record)


def vincular_curva(
    dispositivo: str,
    curva_id: str,
    tipo_curva: str,
    fuente_referencia: str,
    fuente_url: str | None = None,
    revision: str | None = None,
) -> dict[str, Any]:
    """Vincula solo metadata de curva; P5A no ingiere ni sintetiza puntos TCC."""
    _sync()
    key = _device_key(dispositivo)
    record = _devices.get(key)
    if not record:
        raise ValueError(f"P5DATA011: dispositivo no encontrado: {dispositivo}")
    curve_id = str(curva_id or "").strip()
    if not curve_id:
        raise ValueError("P5DATA050: curva_id es obligatorio.")
    curve_type = str(tipo_curva or "").strip().upper()
    if curve_type not in {"MANUFACTURER_TCC", "STANDARD_CURVE", "TEST_CURVE"}:
        raise ValueError("P5DATA051: tipo_curva debe ser MANUFACTURER_TCC, STANDARD_CURVE o TEST_CURVE.")
    record["curve"] = {
        "id": curve_id,
        "type": curve_type,
        "revision": str(revision or "").strip() or None,
        "provenance": _provenance(fuente_referencia, fuente_url),
        "numeric_dataset_loaded": False,
        "synthetic": False,
        "tcc_execution_ready": False,
        "next_gate": protection_contract.CURVE_POLICY["next_gate"],
    }
    return deepcopy(record)


def obtener_dispositivo(dispositivo: str) -> dict[str, Any] | None:
    _sync()
    return deepcopy(_devices.get(_device_key(dispositivo)))


def _p3_binding(record: dict[str, Any]) -> dict[str, Any]:
    element = str(record["protected_element"])
    if not element.lower().startswith("line."):
        return {"status": "NOT_APPLICABLE_P5A", "p3_in_a": None, "device_in_a": record["ratings"]["in_a"]}
    profile = ampacity.obtener_condiciones(element)
    if not profile:
        return {"status": "P3_NOT_CONFIGURED", "p3_in_a": None, "device_in_a": record["ratings"]["in_a"]}
    p3_in = float((profile.get("protection") or {}).get("in_a") or 0)
    device_in = float(record["ratings"]["in_a"])
    match = p3_in > 0 and abs(p3_in - device_in) <= 1e-9
    return {
        "status": "MATCH" if match else "MISMATCH",
        "p3_in_a": p3_in if p3_in > 0 else None,
        "device_in_a": device_in,
        "p3_reference": (profile.get("protection") or {}).get("reference"),
        "automatic_creation_from_p3": False,
    }


def evaluar_preparacion(dispositivo: str) -> dict[str, Any]:
    """Separa readiness del dispositivo, capacidad de corte y TCC."""
    _sync()
    record = obtener_dispositivo(dispositivo)
    if not record:
        return {
            "status": "MISSING_DEVICE",
            "device_id": str(dispositivo),
            "issues": [{"code": "P5READY001", "message": "Dispositivo P5A no registrado."}],
            "professional_emission": False,
        }

    issues: list[dict[str, str]] = []
    ratings = record["ratings"]
    if record["device_type"] == "circuit_breaker" and ratings.get("icu_ka") is None:
        issues.append({"code": "P5READY101", "message": "Interruptor sin Icu explícita; no puede evaluarse capacidad de corte."})
    if record["device_type"] == "fuse" and ratings.get("breaking_capacity_ka") is None:
        issues.append({"code": "P5READY102", "message": "Fusible sin poder de corte explícito; no puede evaluarse capacidad de corte."})

    p3 = _p3_binding(record)
    if p3["status"] == "MISMATCH":
        issues.append({"code": "P5READY201", "message": "In P5A no coincide con In P3 del elemento protegido; no se elige uno silenciosamente."})

    curve = record.get("curve")
    tcc_issues: list[dict[str, str]] = []
    if not curve:
        tcc_issues.append({"code": "P5READY301", "message": "No existe metadata de curva TCC vinculada."})
    else:
        tcc_issues.append({"code": "P5READY302", "message": "P5A no carga datasets numéricos de curva; TCC permanece bloqueada hasta P5B."})

    return {
        "schema": "MCP_ELECTRICO_P5A_PROTECTION_READINESS_V1",
        "device_id": record["id"],
        "device_type": record["device_type"],
        "protected_element": record["protected_element"],
        "device_data_status": "FOUNDATION_READY" if not issues else "MISSING_OR_INCONSISTENT_DATA",
        "breaking_capacity_ready": not any(item["code"] in {"P5READY101", "P5READY102"} for item in issues),
        "p3_binding": p3,
        "tcc_status": "MODULE_NOT_READY_P5A",
        "issues": issues,
        "tcc_issues": tcc_issues,
        "clearing_time_source": None,
        "p4_tk_s_consumed": False,
        "professional_emission": False,
    }


def snapshot() -> dict[str, Any]:
    _sync()
    return {
        "schema": "MCP_ELECTRICO_P5A_PROTECTION_DATA_V1",
        "circuit": _circuit_name,
        "devices": [deepcopy(item) for item in _devices.values()],
        "contract": protection_contract.obtener_contrato_p5a(),
        "professional_emission": False,
    }
