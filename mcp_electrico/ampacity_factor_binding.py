"""Binding P3B -> P3 para factores normativos de ampacidad.

Convierte resultados numéricos P3B en factores P3 sin perder procedencia y
revalida el dataset al momento de configurar Ib/In/Iz. Un factor secundario
requiere opt-in explícito en la configuración P3 y nunca se presenta como
lookup normativo automático profesional.

P3C11A2 añade soporte al schema genérico ``exact_rows_v1`` para Tabla 5A.
P3C11B2 incorpora Tabla 5B con validación explícita de método D, ducto enterrado,
resistividad térmica y profundidad <= 0,8 m. Las familias genéricas futuras
permanecen fail-closed hasta declarar su propia política de compatibilidad.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import ampacity_datasets, ampacity_exact_lookup

DATASET_ORIGIN = "P3B_DATASET"
MANUAL_ORIGIN = "MANUAL"
LEGACY_SCHEMA = "legacy_grouping_v1"


def _generic_result(result: dict[str, Any]) -> bool:
    return str(result.get("status") or "") == ampacity_exact_lookup.RESOLVED_EXACT


def construir_factor_desde_resultado(result: dict[str, Any]) -> dict[str, Any]:
    """Construye un factor portable desde un resultado P3B ya resuelto."""
    status = str(result.get("status") or "")
    generic = _generic_result(result)
    legacy = status in {ampacity_datasets.RESOLVED_PRIMARY, ampacity_datasets.RESOLVED_SECONDARY}
    if not generic and not legacy:
        raise ValueError(
            "P3B030: solo un lookup P3B resuelto puede convertirse en factor P3"
        )

    if generic:
        if str(result.get("value_field") or "") != "factor":
            raise ValueError("P3C11A2001: lookup exacto de factor requiere value_field=factor")
        factor = result.get("value")
        schema_type = ampacity_exact_lookup.EXACT_ROWS_V1
    else:
        factor = result.get("factor")
        schema_type = LEGACY_SCHEMA

    if factor is None:
        raise ValueError("P3B031: resultado P3B resuelto sin factor")
    dataset_id = str(result.get("dataset_id") or "").strip()
    axis = str(result.get("axis") or "").strip().lower()
    if not dataset_id or not axis:
        raise ValueError("P3B032: resultado P3B sin dataset_id/axis")
    if axis == "base_ampacity":
        raise ValueError("P3C11A2002: base_ampacity debe usar ampacity_base_binding")

    query = deepcopy(result.get("query") or {})
    if generic:
        condition = "; ".join(f"{key}={query[key]}" for key in sorted(query))
    else:
        condition = (
            f"method={query.get('installation_method')}; "
            f"circuits_grouped={query.get('circuits_grouped')}; "
            f"arrangement_id={query.get('arrangement_id')}"
        )

    return {
        "id": f"k_{axis}_{dataset_id.lower()}",
        "axis": axis,
        "value": float(factor),
        "reference": f"P3B dataset {dataset_id}",
        "table_or_clause": str(result.get("table") or "").strip() or None,
        "condition": condition,
        "origin": DATASET_ORIGIN,
        "norm_reference_id": str(result.get("norm_reference_id") or "").strip() or None,
        "profile_id": str(result.get("profile_id") or "").strip() or None,
        "dataset": {
            "id": dataset_id,
            "query": query,
            "row_metadata": deepcopy(result.get("row_metadata") or {}),
            "lookup_schema_type": schema_type,
            "verification_status": result.get("verification_status"),
            "professional_emission": bool(result.get("professional_emission")),
            "automatic_normative_lookup": bool(result.get("automatic_normative_lookup")),
            "provenance": deepcopy(result.get("provenance") or {}),
        },
    }


def _resolver_activo(dataset_id: str, query: dict[str, Any]) -> dict[str, Any]:
    dataset = ampacity_datasets.obtener_dataset(dataset_id)
    if (dataset.get("lookup_schema") or {}).get("type") == ampacity_exact_lookup.EXACT_ROWS_V1:
        return ampacity_exact_lookup.resolver_catalogo(
            dataset_id,
            deepcopy(query),
            allow_secondary=True,
        )
    return ampacity_datasets.resolver_factor(
        dataset_id,
        installation_method=str(query.get("installation_method") or ""),
        circuits_grouped=int(query.get("circuits_grouped") or 0),
        arrangement_id=query.get("arrangement_id"),
        allow_secondary=True,
    )


def validar_factor_dataset(
    item: dict[str, Any],
    permitir_secundario: bool = False,
) -> dict[str, Any]:
    """Revalida un factor P3B contra el catálogo activo antes de usarlo en P3."""
    if str(item.get("origin") or "") != DATASET_ORIGIN:
        raise ValueError("P3B033: factor no identificado como P3B_DATASET")
    dataset_meta = item.get("dataset") or {}
    dataset_id = str(dataset_meta.get("id") or "").strip()
    query = deepcopy(dataset_meta.get("query") or {})
    if not dataset_id:
        raise ValueError("P3B034: factor dataset sin dataset_id")

    result = _resolver_activo(dataset_id, query)
    generic = _generic_result(result)
    legacy = result.get("status") in {
        ampacity_datasets.RESOLVED_PRIMARY,
        ampacity_datasets.RESOLVED_SECONDARY,
    }
    if not generic and not legacy:
        raise ValueError(
            f"P3B035: el dataset ya no resuelve el factor declarado: {result.get('status')}"
        )

    expected_value = float(result["value"] if generic else result["factor"])
    declared_value = float(item.get("value"))
    if abs(expected_value - declared_value) > 1e-12:
        raise ValueError("P3B036: valor del factor no coincide con el dataset activo")
    expected_axis = str(result.get("axis") or "").strip().lower()
    if str(item.get("axis") or "").strip().lower() != expected_axis:
        raise ValueError("P3B037: axis del factor no coincide con el dataset")

    declared_row_metadata = dataset_meta.get("row_metadata")
    if generic and declared_row_metadata is not None and declared_row_metadata != (result.get("row_metadata") or {}):
        raise ValueError("P3C11A2003: metadata de fila del factor no coincide con dataset activo")

    primary = bool(result.get("professional_emission"))
    if not primary and not permitir_secundario:
        raise ValueError(
            "P3B038: factor de dataset secundario requiere opt-in explícito en P3"
        )

    normalized = construir_factor_desde_resultado(result)
    normalized["id"] = str(item.get("id") or normalized["id"]).strip()
    return normalized


def _same_number(left: Any, right: Any) -> bool:
    try:
        return abs(float(left) - float(right)) <= 1e-12
    except (TypeError, ValueError):
        return False


def validar_compatibilidad_contexto(
    factor: dict[str, Any],
    route: dict[str, Any] | None,
    normative_base: dict[str, Any] | None,
) -> dict[str, Any]:
    """Valida compatibilidad contextual de factores ``exact_rows_v1``.

    P3C11A2 habilita Tabla 5A (temperatura) y P3C11B2 habilita Tabla 5B
    (resistividad térmica del suelo). Cualquier otro eje genérico permanece
    fail-closed hasta declarar su propia política.
    """
    if str(factor.get("origin") or "") != DATASET_ORIGIN:
        return {"status": "MANUAL_FACTOR", "compatible": True, "policy": "manual_engineering"}

    meta = factor.get("dataset") or {}
    if meta.get("lookup_schema_type") != ampacity_exact_lookup.EXACT_ROWS_V1:
        return {"status": "LEGACY_FACTOR", "compatible": True, "policy": LEGACY_SCHEMA}

    axis = str(factor.get("axis") or "").strip().lower()
    if axis not in {"ambient_temperature", "soil_thermal_resistivity"}:
        raise ValueError(
            f"P3C11A2004: factor exact_rows_v1 axis={axis or 'NONE'} sin política de compatibilidad implementada"
        )
    if route is None:
        raise ValueError("P3C11A2005: factor normativo exacto requiere routing P3A vinculado")
    if normative_base is None:
        raise ValueError("P3C11A2006: factor normativo exacto requiere Iz_base normativa compatible; catálogo P2 no basta")

    query = meta.get("query") or {}
    base_meta = normative_base.get("dataset") or {}
    base_query = base_meta.get("query") or {}
    base_row = base_meta.get("row_metadata") or {}
    declared = route.get("declared_conditions") or {}

    factor_norm = str(factor.get("norm_reference_id") or "")
    factor_profile = str(factor.get("profile_id") or "")
    if factor_norm != str(normative_base.get("norm_reference_id") or ""):
        raise ValueError("P3C11A2007: factor e Iz_base pertenecen a referencias normativas distintas")
    if factor_profile != str(normative_base.get("profile_id") or ""):
        raise ValueError("P3C11A2008: factor e Iz_base pertenecen a perfiles distintos")
    if factor_profile != str(route.get("profile_id") or ""):
        raise ValueError("P3C11A2009: factor no coincide con perfil del routing P3A")

    expected_method = str(route.get("installation_method") or "")
    if str(query.get("installation_method") or "") != expected_method:
        raise ValueError("P3C11A2010: método del factor no coincide con routing P3A")
    if str(base_query.get("installation_method") or "") != expected_method:
        raise ValueError("P3C11A2011: método de Iz_base no coincide con routing P3A")

    if axis == "ambient_temperature":
        if str(query.get("environment") or "") != str(route.get("environment") or ""):
            raise ValueError("P3C11A2012: ambiente del factor 5A no coincide con routing P3A")
        if not _same_number(query.get("ambient_temperature_c"), declared.get("ambient_temperature_c")):
            raise ValueError("P3C11A2013: temperatura del factor 5A no coincide con la declarada en routing P3A")
        if str(query.get("base_table") or "") != str(normative_base.get("table") or ""):
            raise ValueError("P3C11A2014: tabla base declarada por 5A no coincide con Iz_base")
        if not _same_number(query.get("base_table_column"), base_row.get("table_column")):
            raise ValueError("P3C11A2015: columna base declarada por 5A no coincide con Iz_base")
        if str(query.get("insulation") or "") != str(base_query.get("insulation") or ""):
            raise ValueError("P3C11A2016: aislamiento del factor 5A no coincide con Iz_base")
        return {
            "status": "COMPATIBLE_EXACT_FACTOR",
            "compatible": True,
            "policy": "P3C11A2_TABLE_5A_EXACT_CONTEXT_V1",
            "axis": axis,
            "dataset_id": meta.get("id"),
            "base_dataset_id": base_meta.get("id"),
            "checked": {
                "norm_reference_id": factor_norm,
                "profile_id": factor_profile,
                "installation_method": expected_method,
                "environment": route.get("environment"),
                "ambient_temperature_c": declared.get("ambient_temperature_c"),
                "base_table": normative_base.get("table"),
                "base_table_column": base_row.get("table_column"),
                "insulation": base_query.get("insulation"),
            },
        }

    # P3C11B2 — Tabla 5B.
    if str(factor.get("table_or_clause") or "") != "Tabla 5B":
        raise ValueError("P3C11B2001: eje soil_thermal_resistivity requiere Tabla 5B")
    if expected_method != "D":
        raise ValueError("P3C11B2002: Tabla 5B automática solo se habilita para método D")
    if str(route.get("environment") or "") != "buried_duct":
        raise ValueError("P3C11B2003: Tabla 5B automática requiere cables en ductos enterrados")
    if str(query.get("environment") or "") != "buried_duct":
        raise ValueError("P3C11B2004: dataset 5B no corresponde a ambiente buried_duct")
    if str(query.get("base_table") or "") != str(normative_base.get("table") or ""):
        raise ValueError("P3C11B2005: tabla base declarada por 5B no coincide con Iz_base")
    if str(normative_base.get("table") or "") != "Tabla 2":
        raise ValueError("P3C11B2006: política 5B v1 requiere Iz_base de Tabla 2")
    if not _same_number(
        query.get("soil_thermal_resistivity_k_m_per_w"),
        declared.get("soil_thermal_resistivity_k_m_per_w"),
    ):
        raise ValueError("P3C11B2007: resistividad del factor 5B no coincide con routing P3A")
    depth = declared.get("burial_depth_m")
    if depth is None:
        raise ValueError("P3C11B2008: Tabla 5B requiere profundidad de enterramiento explícita")
    try:
        depth_value = float(depth)
    except (TypeError, ValueError) as exc:
        raise ValueError("P3C11B2009: profundidad de enterramiento no numérica") from exc
    if depth_value <= 0:
        raise ValueError("P3C11B2010: profundidad de enterramiento debe ser positiva")
    if depth_value > 0.8 + 1e-12:
        raise ValueError("P3C11B2011: Tabla 5B no se extrapola a profundidades mayores de 0,8 m")
    if str(query.get("burial_depth_scope") or "") != "up_to_0_8_m":
        raise ValueError("P3C11B2012: dataset 5B no declara el alcance de profundidad esperado")

    return {
        "status": "COMPATIBLE_EXACT_FACTOR",
        "compatible": True,
        "policy": "P3C11B2_TABLE_5B_EXACT_CONTEXT_V1",
        "axis": axis,
        "dataset_id": meta.get("id"),
        "base_dataset_id": base_meta.get("id"),
        "checked": {
            "norm_reference_id": factor_norm,
            "profile_id": factor_profile,
            "installation_method": expected_method,
            "environment": route.get("environment"),
            "soil_thermal_resistivity_k_m_per_w": declared.get("soil_thermal_resistivity_k_m_per_w"),
            "burial_depth_m": depth_value,
            "burial_depth_scope": query.get("burial_depth_scope"),
            "base_table": normative_base.get("table"),
        },
    }

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
