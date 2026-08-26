"""P3 — evidencia versionada de benchmarks normativos de ampacidad.

Un benchmark verde no implica cobertura normativa primaria. Este módulo separa
el resultado de ejecución de la calidad de evidencia que puede satisfacer el
gate P3C12. Los registros PRIMARY del producto deben enlazar además con la
suite independiente P3C12A y superar su validación en vivo.
"""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from . import ampacity_datasets, ampacity_evidence, ampacity_independent_benchmarks

_DATA_FILE = Path(__file__).with_name("data") / "ampacity_benchmark_evidence.json"

PASS = "PASS"
PRIMARY = "PRIMARY"
SECONDARY = "SECONDARY"
QUALIFIES_PRIMARY = "QUALIFIES_PRIMARY"
DOES_NOT_QUALIFY = "DOES_NOT_QUALIFY"


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(ch in "0123456789abcdef" for ch in text)


def _primary_source_hashes_by_norm() -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    try:
        sources = ampacity_evidence.listar_fuentes()
    except Exception:
        return result
    for source in sources:
        digest = str(source.get("expected_sha256") or "").strip().lower()
        norm_id = str(source.get("norm_reference_id") or "").strip()
        if (
            source.get("source_class") == "OFFICIAL_PRIMARY_CANDIDATE"
            and source.get("pin_status") == "PINNED"
            and norm_id
            and _valid_sha256(digest)
        ):
            result.setdefault(norm_id, set()).add(digest)
    return result


@lru_cache(maxsize=1)
def _live_independent_suite() -> dict[str, Any]:
    """Ejecuta una vez por proceso la suite P3C12A usada por el gate real."""
    return ampacity_independent_benchmarks.run_suite()


def validar_record(
    record: dict[str, Any],
    *,
    check_live_sources: bool = True,
    check_live_benchmarks: bool = True,
) -> dict[str, Any]:
    rid = str(record.get("id") or "").strip()
    family = str(record.get("family") or "").strip()
    norm_id = str(record.get("norm_reference_id") or "").strip()
    if not rid:
        raise ValueError("P3BEN001: benchmark sin id")
    if not family:
        raise ValueError(f"P3BEN002: {rid} sin family")
    if not norm_id:
        raise ValueError(f"P3BEN006: {rid} sin norm_reference_id")
    if str(record.get("result") or "") != PASS:
        return {
            "valid": True,
            "id": rid,
            "family": family,
            "qualifies_primary": False,
            "status": DOES_NOT_QUALIFY,
            "reasons": ["benchmark_not_passed"],
        }

    evidence_level = str(record.get("evidence_level") or "").upper()
    if evidence_level not in {PRIMARY, SECONDARY}:
        raise ValueError(f"P3BEN003: {rid} evidence_level no soportado")

    reasons: list[str] = []
    if evidence_level != PRIMARY:
        reasons.append("evidence_not_primary")
    if record.get("independent_reference") is not True:
        reasons.append("reference_not_independent")
    if str(record.get("dataset_verification_status") or "") != ampacity_datasets.PRIMARY_VERIFIED:
        reasons.append("dataset_not_primary_verified")

    digest = str(record.get("source_sha256") or "").strip().lower()
    if not _valid_sha256(digest):
        reasons.append("source_sha256_missing_or_invalid")
    elif check_live_sources:
        allowed = _primary_source_hashes_by_norm().get(norm_id, set())
        if digest not in allowed:
            reasons.append("source_sha256_not_pinned_for_norm")

    review = record.get("review_record") or {}
    if not str(review.get("reviewer") or "").strip():
        reasons.append("reviewer_missing")
    if review.get("manual_comparison_confirmed") is not True:
        reasons.append("manual_comparison_not_confirmed")
    if record.get("professional_normative_coverage") is not True:
        reasons.append("professional_normative_coverage_false")

    if evidence_level == PRIMARY and check_live_benchmarks:
        suite_id = str(record.get("benchmark_suite_id") or "").strip()
        benchmark_family = str(record.get("benchmark_family") or "").strip()
        if not suite_id:
            reasons.append("benchmark_suite_missing")
        elif suite_id != "P3C12_PRIMARY_INDEPENDENT_REFERENCE_V1":
            reasons.append("benchmark_suite_not_supported")
        if benchmark_family != family:
            reasons.append("benchmark_family_mismatch")

        if suite_id == "P3C12_PRIMARY_INDEPENDENT_REFERENCE_V1" and benchmark_family == family:
            try:
                suite = _live_independent_suite()
            except Exception:
                reasons.append("independent_suite_error")
            else:
                if suite.get("pass") is not True:
                    reasons.append("independent_suite_not_passed")
                family_result = (suite.get("family_results") or {}).get(family) or {}
                if family_result.get("pass") is not True:
                    reasons.append("independent_family_not_passed")
                if str(suite.get("source_sha256") or "").strip().lower() != digest:
                    reasons.append("independent_suite_source_hash_mismatch")

    qualifies = evidence_level == PRIMARY and not reasons
    return {
        "valid": True,
        "id": rid,
        "family": family,
        "norm_reference_id": norm_id,
        "qualifies_primary": qualifies,
        "status": QUALIFIES_PRIMARY if qualifies else DOES_NOT_QUALIFY,
        "reasons": reasons,
    }


def _load() -> dict[str, Any]:
    payload = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    if int(payload.get("schema_version") or 0) != 1:
        raise ValueError("P3BEN004: schema de benchmarks no soportado")
    seen: set[str] = set()
    for record in payload.get("records", []):
        rid = str(record.get("id") or "")
        if rid in seen:
            raise ValueError(f"P3BEN005: id de benchmark duplicado: {rid}")
        seen.add(rid)
        validar_record(record)
    return payload


def listar_registros() -> list[dict[str, Any]]:
    return [deepcopy(item) for item in _load().get("records", [])]


def evaluar_cobertura(
    required_families: list[str],
    *,
    records: list[dict[str, Any]] | None = None,
    check_live_sources: bool = True,
    check_live_benchmarks: bool = True,
) -> dict[str, Any]:
    """Evalúa cobertura primaria independiente por familia normativa.

    ``records`` existe para probar la lógica con fixtures sintéticos. El gate del
    producto llama esta función sin override y consume exclusivamente el registro
    versionado del repositorio y la suite independiente viva P3C12A.
    """
    source_records = listar_registros() if records is None else deepcopy(records)
    required = list(dict.fromkeys(str(item) for item in required_families))
    by_family: dict[str, list[dict[str, Any]]] = {family: [] for family in required}
    for record in source_records:
        family = str(record.get("family") or "")
        if family in by_family:
            check = validar_record(
                record,
                check_live_sources=check_live_sources,
                check_live_benchmarks=check_live_benchmarks,
            )
            by_family[family].append({"record": deepcopy(record), "validation": check})

    coverage: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for family in required:
        entries = by_family[family]
        qualifying = [entry for entry in entries if entry["validation"].get("qualifies_primary")]
        done = bool(qualifying)
        if not done:
            missing.append(family)
        coverage[family] = {
            "covered": done,
            "qualifying_record_ids": [entry["record"]["id"] for entry in qualifying],
            "available_record_ids": [entry["record"].get("id") for entry in entries],
            "nonqualifying_reasons": {
                str(entry["record"].get("id")): entry["validation"].get("reasons", [])
                for entry in entries
                if not entry["validation"].get("qualifies_primary")
            },
        }

    return {
        "status": "PRIMARY_BENCHMARK_COVERAGE_READY" if not missing else "PRIMARY_BENCHMARK_COVERAGE_INCOMPLETE",
        "ready": not missing,
        "required_families": required,
        "missing_families": missing,
        "coverage": coverage,
        "professional_emission": False,
        "note": "Cobertura de benchmark no cambia por sí sola madurez ni emisión; es evidencia para P3C12.",
    }
