"""P3C10A — binding de dataset normativo hacia Iz_base.

Este módulo NO contiene valores CNE/IEC. Recibe únicamente resultados ya
resueltos por ``ampacity_exact_lookup`` y conserva la procedencia necesaria
para usar una futura Tabla 1/2 PRIMARY_VERIFIED como base normativa de P3.

P2 sigue siendo la fuente de datos físicos/producto del conductor. Este binding
separa explícitamente la ampacidad de catálogo P2 de una ampacidad base
normativa usada por el cálculo P3.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import ampacity_exact_lookup

DATASET_ORIGIN = "P3B_BASE_DATASET"
BASE_AXIS = "base_ampacity"
ALLOWED_BASE_TABLES = {"Tabla 1", "Tabla 2"}


def construir_base_desde_resultado(result: dict[str, Any]) -> dict[str, Any]:
    """Construye un registro portable de Iz_base desde un lookup exacto."""
    if str(result.get("status") or "") != ampacity_exact_lookup.RESOLVED_EXACT:
        raise ValueError("P3C10A001: Iz_base requiere lookup exacto resuelto")

    axis = str(result.get("axis") or "").strip()
    table = str(result.get("table") or "").strip()
    dataset_id = str(result.get("dataset_id") or "").strip()
    norm_reference_id = str(result.get("norm_reference_id") or "").strip()
    profile_id = str(result.get("profile_id") or "").strip()
    value = result.get("value")

    if axis != BASE_AXIS:
        raise ValueError("P3C10A002: dataset de Iz_base requiere axis=base_ampacity")
    if table not in ALLOWED_BASE_TABLES:
        raise ValueError("P3C10A003: Iz_base P3-v1 solo acepta Tabla 1 o Tabla 2")
    if not dataset_id:
        raise ValueError("P3C10A004: resultado sin dataset_id")
    if value is None or float(value) <= 0:
        raise ValueError("P3C10A005: ampacidad base debe ser positiva")
    if not norm_reference_id or not profile_id:
        raise ValueError("P3C10A012: Iz_base requiere norm_reference_id y profile_id")

    return {
        "origin": DATASET_ORIGIN,
        "ampacity_a": float(value),
        "table": table,
        "axis": axis,
        "norm_reference_id": norm_reference_id,
        "profile_id": profile_id,
        "dataset": {
            "id": dataset_id,
            "query": deepcopy(result.get("query") or {}),
            "row_metadata": deepcopy(result.get("row_metadata") or {}),
            "verification_status": result.get("verification_status"),
            "professional_emission": bool(result.get("professional_emission")),
            "automatic_normative_lookup": bool(result.get("automatic_normative_lookup")),
            "provenance": deepcopy(result.get("provenance") or {}),
        },
    }


def validar_base_dataset(
    item: dict[str, Any],
    *,
    permitir_secundario: bool = False,
) -> dict[str, Any]:
    """Revalida el dataset activo antes de aceptar su valor como Iz_base."""
    if str(item.get("origin") or "") != DATASET_ORIGIN:
        raise ValueError("P3C10A006: base no identificada como P3B_BASE_DATASET")

    meta = item.get("dataset") or {}
    dataset_id = str(meta.get("id") or "").strip()
    query = deepcopy(meta.get("query") or {})
    if not dataset_id:
        raise ValueError("P3C10A007: base dataset sin dataset_id")

    result = ampacity_exact_lookup.resolver_catalogo(
        dataset_id,
        query,
        allow_secondary=True,
    )
    if result.get("status") != ampacity_exact_lookup.RESOLVED_EXACT:
        raise ValueError(
            f"P3C10A008: el dataset ya no resuelve Iz_base: {result.get('status')}"
        )

    normalized = construir_base_desde_resultado(result)
    if abs(float(normalized["ampacity_a"]) - float(item.get("ampacity_a") or 0)) > 1e-12:
        raise ValueError("P3C10A009: Iz_base declarada no coincide con dataset activo")
    if normalized["table"] != str(item.get("table") or ""):
        raise ValueError("P3C10A010: tabla de Iz_base no coincide con dataset activo")
    if normalized["norm_reference_id"] != str(item.get("norm_reference_id") or ""):
        raise ValueError("P3C10A013: referencia normativa de Iz_base no coincide con dataset activo")
    if normalized["profile_id"] != str(item.get("profile_id") or ""):
        raise ValueError("P3C10A014: perfil normativo de Iz_base no coincide con dataset activo")

    declared_row_metadata = meta.get("row_metadata")
    if declared_row_metadata is not None and declared_row_metadata != normalized["dataset"]["row_metadata"]:
        raise ValueError("P3C10A015: metadata de fila Iz_base no coincide con dataset activo")

    primary = bool(normalized["dataset"]["professional_emission"])
    if not primary and not permitir_secundario:
        raise ValueError("P3C10A011: Iz_base secundaria requiere opt-in explícito")

    return normalized


def resumen_evidencia_base(item: dict[str, Any] | None) -> dict[str, Any]:
    if not item:
        return {
            "origin": "P2_CATALOG",
            "normative_base": False,
            "primary": False,
            "professional_emission": False,
        }
    dataset = item.get("dataset") or {}
    row_metadata = dataset.get("row_metadata") or {}
    primary = bool(dataset.get("professional_emission"))
    return {
        "origin": str(item.get("origin") or ""),
        "normative_base": str(item.get("axis") or "") == BASE_AXIS,
        "primary": primary,
        "professional_emission": primary,
        "dataset_id": dataset.get("id"),
        "table": item.get("table"),
        "table_column": row_metadata.get("table_column"),
        "norm_reference_id": item.get("norm_reference_id"),
        "profile_id": item.get("profile_id"),
        "verification_status": dataset.get("verification_status"),
    }
