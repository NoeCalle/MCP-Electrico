import json
from pathlib import Path

import pytest

from mcp_electrico import ampacity_datasets, ampacity_exact_lookup, p3_completion


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "mcp_electrico" / "data" / "ampacity_primary_review_candidates.json"
DATASET = "PERU_CNE_UTIL_2006_TABLE_5A_XLPE_AIR_A1_COL15_PRIMARY_V1"
CANDIDATE_ID = "P3C11A_TABLE_5A_XLPE_AIR_A1_COL15_PRIMARY_REVIEW_CANDIDATE_V1"


def _candidate():
    data = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    return next(item for item in data["candidates"] if item["id"] == CANDIDATE_ID)


def _query(temp):
    return {
        "base_table": "Tabla 2",
        "base_table_column": 15,
        "installation_method": "A1",
        "insulation": "XLPE_EPR",
        "environment": "air",
        "ambient_temperature_c": temp,
    }


def test_candidato_5a_preserva_fuente_pinneada_celdas_y_conflicto_abierto():
    candidate = _candidate()

    assert candidate["source_hash_match"] is True
    assert candidate["pdf_page_number_one_based"] == 563
    assert candidate["document_page_marker"] == "Tablas - Pág. 16 de 82"
    assert candidate["candidate_values"] == {"35": 0.96, "40": 0.91}
    assert candidate["candidate_query_scope"]["base_table_column"] == 15
    assert candidate["routing_evidence"]["pdf_page_number_one_based"] == 555
    assert candidate["normative_scope_conflict"]["status"] == "OPEN_FAIL_CLOSED"
    assert candidate["manual_comparison_confirmed"] is True
    assert candidate["human_reviewer"] is None
    assert candidate["reviewer"] == "GPT-5.6 Sol"
    assert candidate["review_mode"] == "AI_VISUAL_REVIEW_USER_AUTHORIZED"
    assert candidate["review_authorized_by_user"] is True
    assert candidate["review_result"] == "APPROVED"
    assert candidate["eligible_for_primary_dataset_pr"] is True


def test_dataset_5a_primary_resuelve_solo_celdas_exactas_revisadas():
    dataset = ampacity_datasets.obtener_dataset(DATASET)
    assert dataset["axis"] == "ambient_temperature"
    assert dataset["table"] == "Tabla 5A"
    assert dataset["provenance"]["verification_status"] == "PRIMARY_VERIFIED"
    assert dataset["usage_policy"]["professional_emission"] is True
    assert dataset["usage_policy"]["p3c11_family_coverage"] is False
    assert dataset["usage_policy"]["automatic_binding_to_iz"] is True

    r35 = ampacity_exact_lookup.resolver_catalogo(DATASET, _query(35))
    r40 = ampacity_exact_lookup.resolver_catalogo(DATASET, _query(40.0))
    assert r35["status"] == "RESOLVED_EXACT"
    assert r35["value"] == pytest.approx(0.96)
    assert r35["professional_emission"] is True
    assert r40["status"] == "RESOLVED_EXACT"
    assert r40["value"] == pytest.approx(0.91)

    not_reviewed = ampacity_exact_lookup.resolver_catalogo(DATASET, _query(45))
    assert not_reviewed["status"] == "VALUE_NOT_TABULATED"
    assert not_reviewed["professional_emission"] is False


def test_dataset_5a_no_se_puede_reutilizar_para_metodo_c_columna_23():
    query = {
        "base_table": "Tabla 2",
        "base_table_column": 23,
        "installation_method": "C",
        "insulation": "XLPE_EPR",
        "environment": "air",
        "ambient_temperature_c": 35,
    }
    result = ampacity_exact_lookup.resolver_catalogo(DATASET, query)
    assert result["status"] == "VALUE_NOT_TABULATED"
    assert result["value"] is None
    assert result["professional_emission"] is False
    assert result["interpolation"] is False
    assert result["extrapolation"] is False


def test_subconjuntos_5a_y_5c_no_cierran_cobertura_de_familia_p3c11():
    flags = p3_completion._coverage_flags()
    assert flags["base_ampacity_strategy"] is True
    assert flags["table_5a"] is False
    assert flags["table_5b"] is False
    assert flags["table_5c"] is False
    assert flags["table_5d"] is False
    assert flags["table_5e"] is False

    gate = p3_completion.evaluar_cierre_p3()
    criterion = next(item for item in gate["criteria"] if item["id"] == "P3C11")
    assert criterion["status"] == "PENDING"
    assert gate["ready_for_next_phase"] is False
    assert gate["professional_emission"] is False
