"""P3 — evidencia versionada de benchmarks normativos de ampacidad.

Un benchmark verde no implica cobertura normativa primaria. Este módulo separa
el resultado de ejecución de la calidad de evidencia que puede satisfacer el
gate P3C12.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from . import ampacity_datasets, ampacity_evidence

_DATA_FILE = Path(__file__).with_name("data") / "ampacity_benchmark_evidence.json"

PASS = "PASS"
PRIMARY = "PRIMARY"
SECONDARY = "SECONDARY"
QUALIFIES_PRIMARY = "QUALIFIES_PRIMARY"
DOES_NOT_QUALIFY = "DOES_NOT_QUALIFY"


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(ch in "0123456789abcdef" for ch in text)


def _primary_source_hashes() -> set[str]:
    result: set[str] = set()
    try:
        sources = ampacity_evidence.listar_fuentes()
    except Exception:
        return result
    for source in sources:
        digest = str(source.get("expected_sha256") or "").strip().lower()
        if (
            source.get("source_class") == "OFFICIAL_PRIMARY_CANDIDATE"
            and source.get("pin_status") == "PINNED"
            and _valid_sha256(digest)
        ):
            result.add(digest)
    return result


def validar_record(record: dict[str, Any], *, check_live_sources: bool = True) -> dict[str, Any]:
    rid = str(record.get("id") or "").strip()
    family = str(record.get("family") or "").strip()
    if not rid:
        raise ValueError("P3BEN001: benchmark sin id")
    if not family:
        raise ValueError(f"P3BEN002: {rid} sin family")
    if str(record.get("result") or "") != PASS:
        return {"valid": True, "id": rid, "qualifies_primary": False, "reason": "benchmark_not_passed"}

    evidence_level = str(record.get("evidence_level") or "").upper()
    if evidence_level not in {PRIMARY, SECONDARY}:
        raise ValueError(f"P3BEN003: {rid} evidence_level no soportado")

    qualifies = evidence_level == PRIMARY
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
    elif check_live_sources and digest not in _primary_source_hashes():
        reasons.append("source_sha256_not_pinned")
    review = record.get("review_record") or {}
    if not str(review.get("reviewer") or "").strip():
        reasons.append("reviewer_missing")
    if review.get("manual_comparison_confirmed") is not True:
        reasons.append("manual_comparison_not_confirmed")
    if record.get("professional_normative_coverage") is not True:
        reasons.append("professional_normative_coverage_false")

    qualifies = qualifies and not reasons
    return {
        "valid": True,
        "id": rid,
        "family": family,
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
) -> dict[str, Any]:
    """Evalúa cobertura primaria independiente por familia normativa.

    ``records`` existe para probar la lógica con fixtures sintéticos. El gate del
    producto llama esta función sin override y consume exclusivamente el registro
    versionado del repositorio.
    """
    source_records = listar_registros() if records is None else deepcopy(records)
    required = list(dict.fromkeys(str(item) for item in required_families))
    by_family: dict[str, list[dict[str, Any]]] = {family: [] for family in required}
    for record in source_records:
        family = str(record.get("family") or "")
        if family in by_family:
            check = validar_record(record, check_live_sources=check_live_sources)
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
