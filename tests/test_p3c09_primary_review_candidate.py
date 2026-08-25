import json
from pathlib import Path

from mcp_electrico import ampacity_datasets, p3_completion


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "mcp_electrico" / "data" / "ampacity_primary_review_candidates.json"
SOURCES = ROOT / "mcp_electrico" / "data" / "ampacity_primary_sources.json"
CANDIDATE_ID = "P3C09_TABLE_5C_ITEM1_PRIMARY_REVIEW_CANDIDATE_V1"
PRIMARY_DATASET = "PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_PRIMARY_V1"


def _candidate():
    data = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    return next(item for item in data["candidates"] if item["id"] == CANDIDATE_ID)


def _source():
    data = json.loads(SOURCES.read_text(encoding="utf-8"))
    return next(item for item in data["sources"] if item["id"] == "MINEM_CNE_UTIL_2006_OFFICIAL_PDF")


def test_candidato_p3c09_proviene_de_fuente_pinneada_exacta():
    candidate = _candidate()
    source = _source()

    assert candidate["source_id"] == source["id"]
    assert source["pin_status"] == "PINNED"
    assert candidate["source_sha256"] == source["expected_sha256"]
    assert candidate["source_hash_match"] is True


def test_candidato_tabla_5c_preserva_subconjunto_y_pagina():
    candidate = _candidate()

    assert candidate["table"] == "Tabla 5C"
    assert candidate["table_item"] == 1
    assert candidate["pdf_page_number_one_based"] == 565
    assert candidate["document_page_marker"] == "Tablas - Pág. 18 de 82"
    assert candidate["candidate_subset"] == {"2": 0.80, "3": 0.70, "12": 0.45}
    assert candidate["automated_extraction"]["workflow_run_id"] == 32877141382
    assert candidate["automated_extraction"]["page_render_generated"] is True


def test_candidato_promovido_sin_fingir_revision_humana():
    candidate = _candidate()
    dataset = ampacity_datasets.obtener_dataset(PRIMARY_DATASET)
    record = dataset["provenance"]["verification_record"]

    assert candidate["manual_comparison_confirmed"] is True
    assert candidate["human_reviewer"] is None
    assert candidate["reviewer"] == "GPT-5.6 Sol"
    assert candidate["review_mode"] == "AI_VISUAL_REVIEW_USER_AUTHORIZED"
    assert candidate["review_authorized_by_user"] is True
    assert candidate["review_result"] == "APPROVED"
    assert candidate["eligible_for_primary_dataset_pr"] is True

    assert dataset["provenance"]["verification_status"] == "PRIMARY_VERIFIED"
    assert dataset["provenance"]["source_sha256"] == candidate["source_sha256"]
    assert dataset["values"] == candidate["candidate_subset"]
    assert record["candidate_id"] == CANDIDATE_ID
    assert record["reviewer"] == candidate["reviewer"]
    assert record["review_mode"] == candidate["review_mode"]
    assert record["review_authorized_by_user"] is True
    assert record["manual_comparison_confirmed"] is True
    assert dataset["usage_policy"]["professional_emission"] is True


def test_p3c09_cierra_pero_p3_global_sigue_bloqueada():
    gate = p3_completion.evaluar_cierre_p3()
    criterion = next(item for item in gate["criteria"] if item["id"] == "P3C09")
    assert criterion["status"] == "DONE"
    assert criterion["blocking_reason"] is None
    assert gate["ready_for_next_phase"] is False
    assert gate["professional_emission"] is False

    pending = {item["id"] for item in gate["pending_criteria"]}
    assert "P3C09" not in pending
    assert "P3C10" not in pending
    assert {"P3C11", "P3C12", "P3C13"} <= pending
