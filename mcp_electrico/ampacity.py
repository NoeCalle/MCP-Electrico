"""P3 — fundamento de ampacidad y coordinación Ib/In/Iz.

No contiene todavía tablas automáticas IEC/CNE. Iz se calcula desde una
ampacidad base P2 trazable y factores explícitos referenciados, o desde una
confirmación explícita de coincidencia con las condiciones base publicadas.
In se declara expresamente; no se infiere de metadatos visuales históricos.
"""

from __future__ import annotations

from copy import deepcopy
from math import prod
from typing import Any

from opendssdirect import dss

from . import ampacity_norms, conductor_library, studies

_circuit_name = ""
_profiles: dict[str, dict[str, Any]] = {}


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
        _profiles.clear()


def reset() -> None:
    global _circuit_name
    _circuit_name = _active_circuit_name()
    _profiles.clear()


def _line_name(name: str) -> str:
    full = str(name or "").strip()
    if "." not in full:
        full = f"Line.{full}"
    if not full.lower().startswith("line."):
        raise ValueError("P3A001: el elemento debe ser Line.*")
    if not dss.Circuit.SetActiveElement(full):
        raise ValueError(f"P3A002: elemento no encontrado: {full}")
    return full


def _factor(item: dict[str, Any], index: int) -> dict[str, Any]:
    factor_id = str(item.get("id") or item.get("name") or f"factor_{index+1}").strip()
    value = float(item.get("value"))
    if value <= 0 or value > 2.0:
        raise ValueError(f"P3A010: {factor_id} debe ser >0 y <=2.0")
    reference = str(item.get("reference") or "").strip()
    if not reference:
        raise ValueError(f"P3A011: {factor_id} requiere referencia explícita")
    return {
        "id": factor_id,
        "value": value,
        "reference": reference,
        "table_or_clause": str(item.get("table_or_clause") or "").strip() or None,
        "condition": str(item.get("condition") or "").strip() or None,
    }


def definir_condiciones(
    nombre_elemento: str,
    norma_id: str,
    in_proteccion_a: float,
    factores: list[dict[str, Any]] | None = None,
    confirmar_condiciones_base: bool = False,
    ib_diseno_a: float | None = None,
    usar_corriente_flujo_como_ib: bool = False,
    referencia_in: str | None = None,
    referencia_ib: str | None = None,
) -> dict[str, Any]:
    """Configura datos P3 sin asumir factor 1, In ni Ib silenciosamente."""
    _sync()
    if not _circuit_name:
        raise ValueError("P3A003: no existe circuito activo")
    full = _line_name(nombre_elemento)
    norm = ampacity_norms.obtener_referencia(norma_id)
    assignment = conductor_library.obtener_asignacion(full)
    if not assignment:
        raise ValueError("P3A004: se requiere asignación de conductor P2 trazable")

    in_value = float(in_proteccion_a)
    if in_value <= 0:
        raise ValueError("P3A005: In debe ser positivo")
    if not str(referencia_in or "").strip():
        raise ValueError("P3A006: In requiere referencia explícita")

    raw_factors = factores or []
    if raw_factors and confirmar_condiciones_base:
        raise ValueError("P3A007: use factores o confirme condiciones base, no ambos")
    if not raw_factors and not confirmar_condiciones_base:
        raise ValueError("P3A008: no se asume factor total 1.0")
    validated = [_factor(item, idx) for idx, item in enumerate(raw_factors)]

    if ib_diseno_a is not None and usar_corriente_flujo_como_ib:
        raise ValueError("P3A012: declare Ib o use el flujo, no ambos")
    if ib_diseno_a is None and not usar_corriente_flujo_como_ib:
        raise ValueError("P3A013: debe declarar Ib o aceptar explícitamente la corriente del flujo")
    if ib_diseno_a is not None and float(ib_diseno_a) <= 0:
        raise ValueError("P3A014: Ib debe ser positiva")
    if ib_diseno_a is not None and not str(referencia_ib or "").strip():
        raise ValueError("P3A015: Ib explícita requiere referencia/metodología")

    base = float(assignment.get("ampacidad_aplicada_a") or 0)
    if base <= 0:
        raise ValueError("P3A016: ampacidad base P2 no disponible")
    total = prod(item["value"] for item in validated) if validated else 1.0

    record = {
        "element": full,
        "norm": norm,
        "base": {
            "ampacity_a": base,
            "catalog_installation": assignment.get("instalacion"),
            "catalog_conditions": deepcopy(assignment.get("condiciones_ampacidad")),
            "source": deepcopy(assignment.get("fuente")),
            "conductor_code": assignment.get("codigo"),
        },
        "correction": {
            "mode": "EXPLICIT_FACTORS" if validated else "BASE_CONDITIONS_CONFIRMED",
            "factors": validated,
            "factor_total": total,
            "base_conditions_confirmed": bool(confirmar_condiciones_base),
            "automatic_normative_lookup": False,
        },
        "protection": {"in_a": in_value, "reference": str(referencia_in).strip()},
        "design_current": {
            "mode": "EXPLICIT_DESIGN_CURRENT" if ib_diseno_a is not None else "FLOW_CURRENT_EXPLICITLY_ACCEPTED_AS_IB",
            "ib_a": float(ib_diseno_a) if ib_diseno_a is not None else None,
            "reference": str(referencia_ib or "").strip() or None,
        },
        "maturity": "UNDER_VALIDATION",
    }
    _profiles[full.lower()] = record
    return deepcopy(record)


def obtener_condiciones(nombre_elemento: str) -> dict[str, Any] | None:
    _sync()
    full = str(nombre_elemento or "").strip()
    if "." not in full:
        full = f"Line.{full}"
    return deepcopy(_profiles.get(full.lower()))


def _flow_ib(full: str) -> float:
    result = studies.analizar_flujo_operacion()
    for item in result.get("alimentadores", []):
        if str(item.get("id") or "").lower() == full.lower():
            value = float(item.get("corriente_max_a") or 0)
            if value > 0:
                return value
    raise ValueError(f"P3A020: no se obtuvo corriente de flujo válida para {full}")


def evaluar(nombre_elemento: str) -> dict[str, Any]:
    """Evalúa el criterio Ib <= In <= Iz dentro del alcance P3 foundation."""
    _sync()
    full = _line_name(nombre_elemento)
    profile = _profiles.get(full.lower())
    if not profile:
        return {
            "element": full,
            "status": "DATOS_INSUFICIENTES",
            "missing": ["condiciones_ampacidad_p3"],
            "maturity": "UNDER_VALIDATION",
        }

    design = profile["design_current"]
    if design["mode"] == "EXPLICIT_DESIGN_CURRENT":
        ib = float(design["ib_a"])
        ib_source = design["reference"]
    else:
        ib = _flow_ib(full)
        ib_source = "OpenDSS corriente_max_a; uso como Ib autorizado explícitamente"

    in_a = float(profile["protection"]["in_a"])
    iz_base = float(profile["base"]["ampacity_a"])
    factor_total = float(profile["correction"]["factor_total"])
    iz = iz_base * factor_total
    c1 = ib <= in_a
    c2 = in_a <= iz

    return {
        "element": full,
        "status": "CUMPLE" if c1 and c2 else "NO_CUMPLE",
        "criterion": "Ib <= In <= Iz",
        "values": {"ib_a": ib, "in_a": in_a, "iz_base_a": iz_base, "factor_total": factor_total, "iz_a": iz},
        "checks": {"ib_le_in": c1, "in_le_iz": c2},
        "sources": {
            "ib": ib_source,
            "in": profile["protection"]["reference"],
            "iz_base": deepcopy(profile["base"]["source"]),
            "norm": deepcopy(profile["norm"]),
            "factors": deepcopy(profile["correction"]["factors"]),
        },
        "installation": {
            "catalog_installation": profile["base"]["catalog_installation"],
            "catalog_conditions": deepcopy(profile["base"]["catalog_conditions"]),
            "correction_mode": profile["correction"]["mode"],
        },
        "maturity": "UNDER_VALIDATION",
        "automatic_normative_lookup": False,
        "note": "Iz usa ampacidad base trazable y factores explícitos; tablas automáticas IEC/CNE aún no implementadas.",
    }


def snapshot() -> dict[str, Any]:
    _sync()
    return {
        "schema_version": 1,
        "circuit": _circuit_name,
        "profiles": [deepcopy(value) for _, value in sorted(_profiles.items())],
        "normative_references": ampacity_norms.listar_referencias(),
        "maturity": "UNDER_VALIDATION",
    }
