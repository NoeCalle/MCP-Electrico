"""Lookup exacto de evidencia para la Tabla 5A completa (P3C11A4).

Este módulo NO decide automáticamente qué columna/familia corresponde a un
conductor. Solo expone celdas verificadas de la publicación y protege su alcance
literal. El binding profesional general a Iz permanece separado.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import ampacity_datasets

DATASET_ID = "PERU_CNE_UTIL_2006_TABLE_5A_COMPLETE_PRIMARY_V1"
RESOLVED_EXACT = "RESOLVED_EXACT"
VALUE_NOT_TABULATED = "VALUE_NOT_TABULATED"
SCOPE_MISMATCH = "SCOPE_MISMATCH"
DATASET_SCHEMA_NOT_SUPPORTED = "DATASET_SCHEMA_NOT_SUPPORTED"

_NORMAL_BLOCK = "NORMAL"
_HIGH_BLOCK = "HIGH_OPERATING_TEMPERATURE"
_HIGH_COLUMN_FACTOR = {
    17: "AL_ALA_125C",
    18: "A_AA_FEP_FEPB_200C",
    19: "TFE_250C",
}


def _scope_issue(block: str, base_table_column: int, factor_column_id: str) -> str | None:
    if block == _NORMAL_BLOCK:
        if not 2 <= base_table_column <= 16:
            return "Bloque NORMAL de Tabla 5A solo declara columnas 2-16 de Tablas 1/2."
        return None
    if block == _HIGH_BLOCK:
        expected = _HIGH_COLUMN_FACTOR.get(base_table_column)
        if expected is None:
            return "Bloque HIGH_OPERATING_TEMPERATURE solo declara columnas 17, 18 y 19."
        if factor_column_id != expected:
            return (
                f"Columna base {base_table_column} requiere factor_column_id={expected}; "
                f"recibido={factor_column_id}."
            )
        return None
    return f"table_block no publicado/soportado: {block}"


def resolver_celda(
    *,
    table_block: str,
    base_table_column: int,
    factor_column_id: str,
    ambient_temperature_key: str | int | float,
    dataset_id: str = DATASET_ID,
) -> dict[str, Any]:
    """Resuelve solo una celda publicada, sin interpolar ni extrapolar."""
    dataset = ampacity_datasets.obtener_dataset(dataset_id)
    schema = dataset.get("lookup_schema") or {}
    if dataset.get("table") != "Tabla 5A" or schema.get("type") != "table5a_matrix_v1":
        return {
            "status": DATASET_SCHEMA_NOT_SUPPORTED,
            "dataset_id": dataset.get("id"),
            "factor": None,
            "professional_emission": False,
        }

    block = str(table_block or "").strip().upper()
    factor_id = str(factor_column_id or "").strip().upper()
    try:
        base_col = int(base_table_column)
    except (TypeError, ValueError):
        return {
            "status": SCOPE_MISMATCH,
            "dataset_id": dataset["id"],
            "factor": None,
            "scope_issue": "base_table_column debe ser entero.",
            "professional_emission": False,
        }

    issue = _scope_issue(block, base_col, factor_id)
    if issue:
        return {
            "status": SCOPE_MISMATCH,
            "dataset_id": dataset["id"],
            "factor": None,
            "scope_issue": issue,
            "interpolation": False,
            "extrapolation": False,
            "professional_emission": False,
        }

    matrix = dataset.get("matrix") or {}
    block_data = matrix.get(block) or {}
    columns = block_data.get("columns") or {}
    keys = [str(value) for value in block_data.get("ambient_temperature_keys", [])]
    key = str(ambient_temperature_key).strip()
    if factor_id not in columns or key not in keys:
        return {
            "status": VALUE_NOT_TABULATED,
            "dataset_id": dataset["id"],
            "factor": None,
            "query": {
                "table_block": block,
                "base_table_column": base_col,
                "factor_column_id": factor_id,
                "ambient_temperature_key": key,
            },
            "interpolation": False,
            "extrapolation": False,
            "professional_emission": False,
        }

    value = columns[factor_id][keys.index(key)]
    if value is None:
        return {
            "status": VALUE_NOT_TABULATED,
            "dataset_id": dataset["id"],
            "factor": None,
            "source_token": "-",
            "query": {
                "table_block": block,
                "base_table_column": base_col,
                "factor_column_id": factor_id,
                "ambient_temperature_key": key,
            },
            "interpolation": False,
            "extrapolation": False,
            "professional_emission": False,
        }

    provenance = dataset.get("provenance") or {}
    usage = dataset.get("usage_policy") or {}
    primary = (
        provenance.get("verification_status") == ampacity_datasets.PRIMARY_VERIFIED
        and provenance.get("source_type") == "primary_official"
    )
    return {
        "status": RESOLVED_EXACT,
        "dataset_id": dataset["id"],
        "profile_id": dataset.get("profile_id"),
        "norm_reference_id": dataset.get("norm_reference_id"),
        "table": dataset.get("table"),
        "axis": dataset.get("axis"),
        "factor": float(value),
        "query": {
            "table_block": block,
            "base_table_column": base_col,
            "factor_column_id": factor_id,
            "ambient_temperature_key": key,
        },
        "provenance": deepcopy(provenance),
        "verification_status": provenance.get("verification_status"),
        "interpolation": False,
        "extrapolation": False,
        "professional_emission": bool(primary and usage.get("professional_emission")),
        "automatic_binding_to_iz": False,
        "note": "Celda primaria exacta de Tabla 5A; no implica selección automática de factor para una Iz_base concreta.",
    }
