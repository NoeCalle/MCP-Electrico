"""P3C12A — benchmarks normativos independientes de ampacidad.

Las referencias esperadas viven en un archivo distinto de los datasets de
producción y se transcriben directamente de páginas de la fuente primaria.
Este runner compara esas referencias contra los resolvers reales del producto;
nunca obtiene el valor esperado desde el dataset que está validando.
"""

from __future__ import annotations

from copy import deepcopy
import json
from math import isclose, isfinite
from pathlib import Path
from typing import Any

from . import ampacity_datasets, ampacity_evidence, ampacity_exact_lookup, ampacity_table5a

_DATA_FILE = Path(__file__).with_name("data") / "ampacity_p3c12_independent_reference.json"

PRIMARY_INDEPENDENT = "PRIMARY_INDEPENDENT"
PASS = "PASS"
FAIL = "FAIL"

REQUIRED_FAMILIES = [
    "base_ampacity_strategy_Table_1_2_or_validated_equivalent",
    "Table_5A_temperature",
    "Table_5B_soil_thermal_resistivity_when_applicable",
    "Table_5C_grouping_air",
    "Table_5D_grouping_buried_method_D",
    "Table_5E_arrangement_branches_when_applicable",
]


def _load() -> dict[str, Any]:
    payload = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    return validar_referencia(payload)


def _source_record(source_id: str) -> dict[str, Any] | None:
    key = str(source_id or "").strip().upper()
    for item in ampacity_evidence.listar_fuentes():
        if str(item.get("id") or "").strip().upper() == key:
            return item
    return None


def validar_referencia(payload: dict[str, Any]) -> dict[str, Any]:
    if int(payload.get("schema_version") or 0) != 1:
        raise ValueError("P3C12A001: schema de referencia independiente no soportado")
    if payload.get("reference_evidence") != PRIMARY_INDEPENDENT:
        raise ValueError("P3C12A002: reference_evidence debe ser PRIMARY_INDEPENDENT")
    if payload.get("reference_origin") != "PRIMARY_SOURCE_PAGE_TRANSCRIPTION_INDEPENDENT_OF_PRODUCTION_DATASET":
        raise ValueError("P3C12A003: origen de referencia independiente no declarado")

    source_id = str(payload.get("source_id") or "").strip()
    digest = str(payload.get("source_sha256") or "").strip().lower()
    source = _source_record(source_id)
    if source is None:
        raise ValueError(f"P3C12A004: fuente primaria no registrada: {source_id}")
    if source.get("pin_status") != "PINNED":
        raise ValueError("P3C12A005: fuente primaria no está PINNED")
    if str(source.get("expected_sha256") or "").strip().lower() != digest:
        raise ValueError("P3C12A006: SHA-256 de referencia no coincide con fuente pinneada")
    if str(source.get("norm_reference_id") or "") != str(payload.get("norm_reference_id") or ""):
        raise ValueError("P3C12A007: norm_reference_id no coincide con fuente primaria")

    review = payload.get("review_record") or {}
    if not str(review.get("reviewer") or "").strip():
        raise ValueError("P3C12A008: referencia independiente requiere reviewer")
    if review.get("manual_comparison_confirmed") is not True:
        raise ValueError("P3C12A009: referencia independiente requiere comparación confirmada")

    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("P3C12A010: se requieren casos de benchmark")

    seen: set[str] = set()
    families: set[str] = set()
    for index, case in enumerate(cases):
        cid = str(case.get("id") or "").strip()
        if not cid or cid in seen:
            raise ValueError(f"P3C12A011: id de caso vacío/duplicado en índice {index}")
        seen.add(cid)
        family = str(case.get("family") or "").strip()
        if family not in REQUIRED_FAMILIES:
            raise ValueError(f"P3C12A012: familia no soportada: {family}")
        families.add(family)
        if case.get("resolver") not in {"exact_catalog", "table5a_cell"}:
            raise ValueError(f"P3C12A013: resolver no soportado en {cid}")
        if not str(case.get("dataset_id") or "").strip():
            raise ValueError(f"P3C12A014: {cid} sin dataset_id")
        if not isinstance(case.get("query"), dict) or not case["query"]:
            raise ValueError(f"P3C12A015: {cid} sin query")
        try:
            expected = float(case.get("expected_value"))
            tolerance = float(case.get("tolerance", 0.0))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"P3C12A016: {cid} expected/tolerance no numérico") from exc
        if not isfinite(expected) or not isfinite(tolerance) or tolerance < 0:
            raise ValueError(f"P3C12A017: {cid} expected/tolerance inválido")
        pages = case.get("source_pages") or []
        if not pages:
            raise ValueError(f"P3C12A018: {cid} sin páginas primarias")

    missing = [family for family in REQUIRED_FAMILIES if family not in families]
    if missing:
        raise ValueError(f"P3C12A019: faltan familias en referencia independiente: {missing}")

    return deepcopy(payload)


def obtener_referencia() -> dict[str, Any]:
    return _load()


def _resolver_case(case: dict[str, Any]) -> dict[str, Any]:
    resolver = case["resolver"]
    dataset_id = str(case["dataset_id"])
    query = deepcopy(case["query"])
    if resolver == "exact_catalog":
        raw = ampacity_exact_lookup.resolver_catalogo(dataset_id, query)
        actual = raw.get("value")
    elif resolver == "table5a_cell":
        raw = ampacity_table5a.resolver_celda(dataset_id=dataset_id, **query)
        actual = raw.get("factor")
    else:  # defensa adicional aunque validar_referencia ya lo bloquea
        raise ValueError(f"P3C12A020: resolver no soportado: {resolver}")

    expected = float(case["expected_value"])
    tolerance = float(case.get("tolerance", 0.0))
    status_ok = raw.get("status") == "RESOLVED_EXACT"
    primary_ok = (
        raw.get("verification_status") == ampacity_datasets.PRIMARY_VERIFIED
        and bool(raw.get("professional_emission"))
    )
    value_ok = actual is not None and isclose(float(actual), expected, rel_tol=0.0, abs_tol=tolerance)
    passed = bool(status_ok and primary_ok and value_ok)
    return {
        "id": case["id"],
        "family": case["family"],
        "dataset_id": dataset_id,
        "source_pages": deepcopy(case.get("source_pages") or []),
        "expected_value": expected,
        "actual_value": None if actual is None else float(actual),
        "tolerance": tolerance,
        "resolver_status": raw.get("status"),
        "dataset_verification_status": raw.get("verification_status"),
        "professional_emission": bool(raw.get("professional_emission")),
        "pass": passed,
        "result": PASS if passed else FAIL,
    }


def run_suite(*, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    reference = _load() if payload is None else validar_referencia(deepcopy(payload))
    case_results = [_resolver_case(case) for case in reference["cases"]]

    family_results: dict[str, dict[str, Any]] = {}
    for family in REQUIRED_FAMILIES:
        rows = [row for row in case_results if row["family"] == family]
        passed = sum(1 for row in rows if row["pass"])
        failed = len(rows) - passed
        family_results[family] = {
            "cases": len(rows),
            "passed": passed,
            "failed": failed,
            "pass": bool(rows) and failed == 0,
        }

    failed_total = sum(1 for row in case_results if not row["pass"])
    passed_total = len(case_results) - failed_total
    all_families_pass = all(item["pass"] for item in family_results.values())
    overall_pass = failed_total == 0 and all_families_pass
    return {
        "schema_version": 1,
        "suite_id": reference["suite_id"],
        "norm_reference_id": reference["norm_reference_id"],
        "source_id": reference["source_id"],
        "source_sha256": reference["source_sha256"],
        "reference_evidence": reference["reference_evidence"],
        "independent_reference": True,
        "required_families": deepcopy(REQUIRED_FAMILIES),
        "family_results": family_results,
        "cases": len(case_results),
        "passed": passed_total,
        "failed": failed_total,
        "pass": overall_pass,
        "result": PASS if overall_pass else FAIL,
        "case_results": case_results,
        "professional_emission": False,
        "note": "P3C12A prueba referencias primarias independientes; no promueve todavía el gate P3C12.",
    }
