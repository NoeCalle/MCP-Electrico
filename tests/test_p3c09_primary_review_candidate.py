import json
from pathlib import Path

from mcp_electrico import p3_completion


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "mcp_electrico" / "data" / "ampacity_primary_review_candidates.json"
SOURCES = ROOT / "mcp_electrico" / "data" / "ampacity_primary_sources.json"


def _candidate():
    data = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert len(data["candidates"]) == 1
    return data["candidates"][0]


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


def test_candidato_no_sustituye_revision_humana_ni_cierra_p3c09():
    candidate = _candidate()

    assert candidate["manual_comparison_confirmed"] is False
    assert candidate["human_reviewer"] is None
    assert candidate["eligible_for_primary_dataset_pr"] is False
    assert candidate["professional_emission"] is False

    gate = p3_completion.evaluar_cierre_p3()
    criterion = next(item for item in gate["criteria"] if item["id"] == "P3C09")
    assert criterion["status"] == "PENDING"
    assert gate["ready_for_next_phase"] is False
    assert gate["professional_emission"] is False
