from pathlib import Path


DOC = Path(__file__).resolve().parents[1] / "docs" / "P3B_LOOKUP_EXACTO_GENERICO.md"


def test_doc_no_presenta_lookup_generico_como_dato_normativo():
    text = DOC.read_text(encoding="utf-8")
    assert "no agrega datos normativos" in text.lower()
    assert "exact_rows_v1" in text
    assert "no interpola" in text.lower()
    assert "no extrapola" in text.lower()
    assert "DATASET_SCHEMA_NOT_GENERIC" in text
    assert "No se migra implícitamente" in text
    assert "fixtures sintéticos" in text
    assert "no son valores del CNE ni de IEC" in text
