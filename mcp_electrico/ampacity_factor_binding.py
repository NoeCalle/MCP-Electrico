"""Binding P3B -> P3 para factores normativos de ampacidad.

Convierte resultados numéricos P3B en factores P3 sin perder procedencia y
revalida el dataset al momento de configurar Ib/In/Iz. Un factor secundario
requiere opt-in explícito en la configuración P3 y nunca se presenta como
lookup normativo automático profesional.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import ampacity_datasets

DATASET_ORIGIN = "P3B_DATASET"
MANUAL_ORIGIN = "MANUAL"


def construir_factor_desde_resultado(result: dict[str, Any]) -> dict[str, Any]:
    """Construye un factor portable desde un resultado P3B ya resuelto."""
    status = str(result.get("status") or "")
    if status not in {ampacity_datasets.RESOLVED_PRIMARY, ampacity_datasets.RESOLVED_SECONDARY}:
        raise ValueError(
            "P3B030: solo un lookup P3B resuelto puede convertirse en factor P3"
        )
    factor = result.get("factor")
    if factor is None:
        raise ValueError("P3B031: resultado P3B resuelto sin factor")
    dataset_id = str(result.get("dataset_id") or "").strip()
    axis = str(result.get("axis") or "").strip().lower()
    if not dataset_id or not axis:
        raise ValueError("P3B032: resultado P3B sin dataset_id/axis")

    query = deepcopy(result.get("query") or {})
    return {
        "id": f"k_{axis}_{dataset_id.lower()}",
        "axis": axis,
        "value": float(factor),
        "reference": f"P3B dataset {dataset_id}",
        "table_or_clause": str(result.get("table") or "").strip() or None,
        "condition": (
            f"method={query.get('installation_method')}; "
            f"circuits_grouped={query.get('circuits_grouped')}; "
            f"arrangement_id={query.get('arrangement_id')}"
        ),
        "origin": DATASET_ORIGIN,
        "dataset": {
            "id": dataset_id,
            "query": query,
            "verification_status": result.get("verification_status"),
            "professional_emission": bool(result.get("professional_emission")),
            "automatic_normative_lookup": bool(result.get("automatic_normative_lookup")),
            "provenance": deepcopy(result.get("provenance")),
        },
    }


def validar_factor_dataset(
    item: dict[str, Any],
    permitir_secundario: bool = False,
) -> dict[str, Any]:
    """Revalida un factor P3B contra el catálogo activo antes de usarlo en P3."""
    if str(item.get("origin") or "") != DATASET_ORIGIN:
        raise ValueError("P3B033: factor no identificado como P3B_DATASET")
    dataset_meta = item.get("dataset") or {}
    dataset_id = str(dataset_meta.get("id") or "").strip()
    query = dataset_meta.get("query") or {}
    if not dataset_id:
        raise ValueError("P3B034: factor dataset sin dataset_id")

    result = ampacity_datasets.resolver_factor(
        dataset_id,
        installation_method=str(query.get("installation_method") or ""),
        circuits_grouped=int(query.get("circuits_grouped") or 0),
        arrangement_id=query.get("arrangement_id"),
        allow_secondary=True,
    )
    if result.get("status") not in {
        ampacity_datasets.RESOLVED_PRIMARY,
        ampacity_datasets.RESOLVED_SECONDARY,
    }:
        raise ValueError(
            f"P3B035: el dataset ya no resuelve el factor declarado: {result.get('status')}"
        )

    expected_value = float(result["factor"])
    declared_value = float(item.get("value"))
    if abs(expected_value - declared_value) > 1e-12:
        raise ValueError("P3B036: valor del factor no coincide con el dataset activo")
    expected_axis = str(result.get("axis") or "").strip().lower()
    if str(item.get("axis") or "").strip().lower() != expected_axis:
        raise ValueError("P3B037: axis del factor no coincide con el dataset")

    primary = result.get("status") == ampacity_datasets.RESOLVED_PRIMARY
    if not primary and not permitir_secundario:
        raise ValueError(
            "P3B038: factor de dataset secundario requiere opt-in explícito en P3"
        )

    normalized = construir_factor_desde_resultado(result)
    normalized["id"] = str(item.get("id") or normalized["id"]).strip()
    return normalized


def resumen_evidencia_factores(factors: list[dict[str, Any]]) -> dict[str, Any]:
    """Resume el origen/evidencia del conjunto de factores configurados."""
    dataset_factors = [item for item in factors if item.get("origin") == DATASET_ORIGIN]
    manual_factors = [item for item in factors if item.get("origin") != DATASET_ORIGIN]
    secondary = [
        item for item in dataset_factors
        if not bool((item.get("dataset") or {}).get("professional_emission"))
    ]
    primary = [
        item for item in dataset_factors
        if bool((item.get("dataset") or {}).get("professional_emission"))
    ]
    automatic = bool(factors) and not manual_factors and len(primary) == len(factors)
    return {
        "total": len(factors),
        "manual": len(manual_factors),
        "dataset_primary": len(primary),
        "dataset_secondary": len(secondary),
        "contains_secondary": bool(secondary),
        "professional_factor_evidence": bool(factors) and not manual_factors and not secondary,
        "automatic_normative_lookup": automatic,
    }
