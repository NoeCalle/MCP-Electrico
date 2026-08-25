from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "P3C09_PRIMARY_5C_V1.md"


def test_p3c09_doc_preserva_alcance_y_siguiente_bloque():
    text = DOC.read_text(encoding="utf-8")
    assert "**DONE para el criterio P3C09.**" in text
    assert "PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_PRIMARY_V1" in text
    assert "2 circuitos → 0.80" in text
    assert "3 circuitos → 0.70" in text
    assert "12 circuitos → 0.45" in text
    assert "AI_VISUAL_REVIEW_USER_AUTHORIZED" in text
    assert "P3C10 = PENDING" in text
    assert "70 mm² → 229 A" in text
