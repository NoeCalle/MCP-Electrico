"""Registro explícito de elementos TBC que NO se materializan en el solver.

Un placeholder permite documentar Rev.0 sin inventar parámetros eléctricos.
Mientras exista al menos uno, el modelo no puede presentarse como listo para
estudios que dependan de esos elementos.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

SCHEMA = "MCP_ELECTRICO_MODEL_PLACEHOLDERS_V1"
_ALLOWED_TYPES = {
    "TRANSFORMER",
    "LINE",
    "CABLE",
    "BUS_TIE",
    "SWITCH",
    "LOAD",
    "GENERATOR",
    "OTHER",
}

_items: dict[str, dict[str, Any]] = {}


def reset() -> None:
    _items.clear()


def registrar(
    element_id: str,
    element_type: str,
    known_data: dict[str, Any] | None,
    missing_fields: list[str],
    source_reference: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    identifier = str(element_id or "").strip()
    if not identifier:
        raise ValueError("element_id debe ser explícito y no vacío.")

    kind = str(element_type or "").strip().upper()
    if kind not in _ALLOWED_TYPES:
        raise ValueError(
            "element_type no soportado. Use: " + ", ".join(sorted(_ALLOWED_TYPES))
        )

    missing = [str(item).strip() for item in (missing_fields or []) if str(item).strip()]
    if not missing:
        raise ValueError(
            "MODEL_PLACEHOLDER exige missing_fields no vacío; si no faltan datos, "
            "materialice el elemento real."
        )

    record = {
        "id": identifier,
        "element_type": kind,
        "status": "MODEL_PLACEHOLDER_TBC",
        "solver_materialized": False,
        "electrical_calculation_performed": False,
        "known_data": deepcopy(known_data or {}),
        "missing_fields": sorted(set(missing)),
        "source_reference": str(source_reference or "").strip() or None,
        "note": str(note or "").strip() or None,
        "blocks_study_readiness": True,
        "automatic_defaults": False,
        "professional_emission": False,
    }
    _items[identifier.lower()] = record
    return deepcopy(record)


def snapshot() -> dict[str, Any]:
    items = [deepcopy(_items[key]) for key in sorted(_items)]
    return {
        "schema": SCHEMA,
        "count": len(items),
        "items": items,
        "has_study_blockers": bool(items),
        "solver_materialized_count": 0,
        "automatic_defaults": False,
        "professional_emission": False,
    }
