import json
from pathlib import Path


DATA = Path(__file__).parents[1] / "mcp_electrico" / "data" / "ampacity_primary_review_candidates.json"
EXPECTED_IDS = {
    "P3C09_TABLE_5C_ITEM1_PRIMARY_REVIEW_CANDIDATE_V1",
    "P3C10C_TABLE_2_XLPE_C_3C_70MM2_PRIMARY_REVIEW_CANDIDATE_V1",
}


def _candidates():
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    return {item["id"]: item for item in payload["candidates"]}


def test_revisiones_visuales_autorizadas_son_trazables_sin_fingir_revisor_humano():
    candidates = _candidates()
    assert EXPECTED_IDS <= set(candidates)

    for candidate_id in EXPECTED_IDS:
        item = candidates[candidate_id]
        assert item["status"] == "PRIMARY_TABLE_EVIDENCE_REVIEWED"
        assert item["source_hash_match"] is True
        assert item["manual_comparison_confirmed"] is True
        assert item["human_reviewer"] is None
        assert item["reviewer"] == "GPT-5.6 Sol"
        assert item["review_mode"] == "AI_VISUAL_REVIEW_USER_AUTHORIZED"
        assert item["review_authorized_by_user"] is True
        assert item["review_result"] == "APPROVED"
        assert item["review_confidence"] == "HIGH"
        assert item["eligible_for_primary_dataset_pr"] is True
        assert item["professional_emission"] is False
        assert item["review_checks"]


def test_aprobacion_no_equivale_a_primary_verified_ni_emision_profesional():
    for item in _candidates().values():
        if item["id"] not in EXPECTED_IDS:
            continue
        assert item["status"] != "PRIMARY_VERIFIED"
        assert item["professional_emission"] is False
