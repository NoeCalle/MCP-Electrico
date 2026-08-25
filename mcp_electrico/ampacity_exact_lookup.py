"""P3B — motor genérico de lookup exacto para futuros datasets normativos.

No contiene valores del CNE/IEC ni infiere dimensiones de tablas aún no
verificadas. Cada dataset declara explícitamente sus dimensiones y filas. El
motor solo hace coincidencia exacta: nunca interpola, extrapola ni elige el
valor "más cercano".
"""

from __future__ import annotations

from copy import deepcopy
import json
from math import isfinite
from typing import Any

from . import ampacity_datasets

EXACT_ROWS_V1 = "exact_rows_v1"
RESOLVED_EXACT = "RESOLVED_EXACT"
VALUE_NOT_TABULATED = "VALUE_NOT_TABULATED"
QUERY_DIMENSION_MISMATCH = "QUERY_DIMENSION_MISMATCH"
DATASET_SCHEMA_NOT_GENERIC = "DATASET_SCHEMA_NOT_GENERIC"
DATASET_NOT_APPROVED = "DATASET_NOT_APPROVED"


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        number = float(value)
        if not isfinite(number):
            raise ValueError("P3XL001: dimensión numérica no finita")
        return number
    if isinstance(value, str):
        return value.strip()
    raise ValueError(f"P3XL002: tipo de dimensión no soportado: {type(value).__name__}")


def _canonical_query(query: dict[str, Any], dimensions: list[str]) -> str:
    normalized = {name: _normalize_scalar(query[name]) for name in dimensions}
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validar_dataset(dataset: dict[str, Any]) -> dict[str, Any]:
    dataset_id = str(dataset.get("id") or "").strip() or "<sin_id>"
    schema = dataset.get("lookup_schema") or {}
    if schema.get("type") != EXACT_ROWS_V1:
        raise ValueError(f"P3XL003: {dataset_id} no declara lookup_schema exact_rows_v1")

    dimensions = [str(item).strip() for item in schema.get("dimensions", []) if str(item).strip()]
    if not dimensions or len(dimensions) != len(set(dimensions)):
        raise ValueError(f"P3XL004: {dataset_id} requiere dimensiones únicas y no vacías")

    value_field = str(schema.get("value_field") or "value").strip()
    rows = dataset.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"P3XL005: {dataset_id} requiere rows no vacías")

    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("query"), dict):
            raise ValueError(f"P3XL006: {dataset_id} row[{index}] sin query")
        query = row["query"]
        if set(query) != set(dimensions):
            raise ValueError(
                f"P3XL007: {dataset_id} row[{index}] dimensiones={sorted(query)}; "
                f"esperadas={sorted(dimensions)}"
            )
        key = _canonical_query(query, dimensions)
        if key in seen:
            raise ValueError(f"P3XL008: {dataset_id} contiene query exacta duplicada")
        seen.add(key)

        if value_field not in row:
            raise ValueError(f"P3XL009: {dataset_id} row[{index}] sin {value_field}")
        try:
            value = float(row[value_field])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"P3XL010: {dataset_id} row[{index}] valor no numérico") from exc
        if not isfinite(value) or value <= 0:
            raise ValueError(f"P3XL011: {dataset_id} row[{index}] valor debe ser positivo y finito")

    return {
        "valid": True,
        "dataset_id": dataset_id,
        "schema_type": EXACT_ROWS_V1,
        "dimensions": dimensions,
        "value_field": value_field,
        "row_count": len(rows),
        "interpolation": False,
        "extrapolation": False,
    }


def resolver_dataset(dataset: dict[str, Any], query: dict[str, Any]) -> dict[str, Any]:
    validated = validar_dataset(dataset)
    dimensions = validated["dimensions"]
    if set(query) != set(dimensions):
        return {
            "status": QUERY_DIMENSION_MISMATCH,
            "dataset_id": dataset.get("id"),
            "value": None,
            "required_dimensions": dimensions,
            "received_dimensions": sorted(str(item) for item in query),
            "interpolation": False,
            "extrapolation": False,
            "professional_emission": False,
        }

    wanted = _canonical_query(query, dimensions)
    value_field = validated["value_field"]
    for row in dataset["rows"]:
        if _canonical_query(row["query"], dimensions) == wanted:
            return {
                "status": RESOLVED_EXACT,
                "dataset_id": dataset.get("id"),
                "profile_id": dataset.get("profile_id"),
                "norm_reference_id": dataset.get("norm_reference_id"),
                "table": dataset.get("table"),
                "axis": dataset.get("axis"),
                "query": deepcopy(query),
                "value": float(row[value_field]),
                "value_field": value_field,
                "row_metadata": deepcopy(row.get("metadata") or {}),
                "interpolation": False,
                "extrapolation": False,
            }

    return {
        "status": VALUE_NOT_TABULATED,
        "dataset_id": dataset.get("id"),
        "value": None,
        "query": deepcopy(query),
        "required_dimensions": dimensions,
        "available_exact_rows": len(dataset["rows"]),
        "interpolation": False,
        "extrapolation": False,
        "professional_emission": False,
        "note": "No existe una fila exacta para la consulta; no se usa aproximación ni vecino más cercano.",
    }


def resolver_catalogo(
    dataset_id: str,
    query: dict[str, Any],
    *,
    allow_secondary: bool = False,
) -> dict[str, Any]:
    """Resuelve un dataset del catálogo si declara el schema genérico.

    Los datasets secundarios siguen bloqueados por defecto. Este método no
    convierte un dataset en profesional ni modifica su procedencia.
    """
    dataset = ampacity_datasets.obtener_dataset(dataset_id)
    if (dataset.get("lookup_schema") or {}).get("type") != EXACT_ROWS_V1:
        return {
            "status": DATASET_SCHEMA_NOT_GENERIC,
            "dataset_id": dataset["id"],
            "value": None,
            "professional_emission": False,
            "note": "Dataset legado/no genérico; use su resolver específico o migre por PR con evidencia.",
        }

    provenance = dataset.get("provenance") or {}
    usage = dataset.get("usage_policy") or {}
    primary = (
        provenance.get("verification_status") == ampacity_datasets.PRIMARY_VERIFIED
        and provenance.get("source_type") == "primary_official"
    )
    if not primary and not allow_secondary:
        return {
            "status": DATASET_NOT_APPROVED,
            "dataset_id": dataset["id"],
            "value": None,
            "verification_status": provenance.get("verification_status"),
            "professional_emission": False,
        }

    result = resolver_dataset(dataset, query)
    result["provenance"] = deepcopy(provenance)
    result["verification_status"] = provenance.get("verification_status")
    result["professional_emission"] = bool(
        result.get("status") == RESOLVED_EXACT
        and primary
        and usage.get("professional_emission")
    )
    result["automatic_normative_lookup"] = result["professional_emission"]
    return result
