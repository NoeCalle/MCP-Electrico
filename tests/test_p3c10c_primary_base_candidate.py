import json
from pathlib import Path

from mcp_electrico import ampacity_datasets, p3_completion


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "mcp_electrico" / "data" / "ampacity_primary_review_candidates.json"
SOURCES = ROOT / "mcp_electrico" / "data" / "ampacity_primary_sources.json"
CANDIDATE_ID = "P3C10C_TABLE_2_XLPE_C_3C_70MM2_PRIMARY_REVIEW_CANDIDATE_V1"
PRIMARY_DATASET = "PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1"


def _candidate():
    data = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    return next(item for item in data["candidates"] if item["id"] == CANDIDATE_ID)


def _source():
    data = json.loads(SOURCES.read_text(encoding="utf-8"))
    return next(item for item in data["sources"] if item["id"] == "MINEM_CNE_UTIL_2006_OFFICIAL_PDF")


def test_p3c10c_candidato_usa_fuente_pinneada_y_pagina_exacta():
    candidate = _candidate()
    source = _source()

    assert source["pin_status"] == "PINNED"
    assert candidate["source_sha256"] == source["expected_sha256"]
    assert candidate["source_hash_match"] is True
    assert candidate["table"] == "Tabla 2"
    assert candidate["table_column"] == 23
    assert candidate["pdf_page_number_one_based"] == 552
    assert candidate["document_page_marker"] == "Tablas - Pág. 5 de 82"


def test_p3c10c_routing_y_dimension_candidata_quedan_explicitos():
    candidate = _candidate()

    assert candidate["purpose"] == "base_ampacity"
    assert candidate["profile_id"] == "PERU_CNE_UTIL_2006_030_004"
    assert candidate["routing_evidence"]["table"] == "Tabla 3"
    assert candidate["routing_evidence"]["pdf_page_number_one_based"] == 555
    assert candidate["candidate_query"] == {
        "installation_method": "C",
        "conductor_material": "Cu",
        "insulation": "XLPE_EPR",
        "temperature_c": 90,
        "loaded_conductors": 3,
        "section_mm2": 70.0,
    }
    assert candidate["candidate_value"] == {"ampacity_a": 229.0}


def test_p3c10c_revision_visual_aprobada_queda_promovida_sin_fingir_revision_humana():
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
    assert candidate["professional_emission"] is False

    assert dataset["provenance"]["verification_status"] == "PRIMARY_VERIFIED"
    assert dataset["provenance"]["source_sha256"] == candidate["source_sha256"]
    assert dataset["usage_policy"]["professional_emission"] is True
    assert dataset["rows"][0]["query"] == candidate["candidate_query"]
    assert dataset["rows"][0]["ampacity_a"] == candidate["candidate_value"]["ampacity_a"]
    assert record["candidate_id"] == CANDIDATE_ID
    assert record["reviewer"] == candidate["reviewer"]
    assert record["review_mode"] == candidate["review_mode"]
    assert record["review_authorized_by_user"] is True
    assert record["manual_comparison_confirmed"] is True

    gate = p3_completion.evaluar_cierre_p3()
    criterion = next(item for item in gate["criteria"] if item["id"] == "P3C10")
    assert criterion["status"] == "DONE"
    assert criterion["blocking_reason"] is None
    assert gate["ready_for_next_phase"] is True
    assert gate["professional_emission"] is False
