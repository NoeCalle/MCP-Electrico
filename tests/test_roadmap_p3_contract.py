from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "docs" / "ROADMAP_PROFESIONAL.md"
VISUAL = ROOT / "docs" / "ROADMAP_VISUAL.md"


def test_roadmap_p3_reflects_current_gate_and_blockers():
    text = ROADMAP.read_text(encoding="utf-8")

    assert "P3C01–P3C10 DONE" in text
    assert "Gate formal de salida P3 — implementado" in text
    assert "`P3C01`–`P3C10`: implementados" in text or "`P3C01`–`P3C10`" in text
    assert "`PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_PRIMARY_V1`" in text
    assert "`PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1`" in text
    assert "`P3C11` — cobertura primaria" in text
    assert "`P3C12` — benchmarks normativos independientes" in text
    assert "`P3C13` — madurez de ampacidad" in text
    assert "**Estado actual:**" in text
    assert "AI_VISUAL_REVIEW_USER_AUTHORIZED" in text
    assert "Iz_base = 229 A" in text
    assert "UNDER_VALIDATION" in text
    assert "- `P3C10` — estrategia validada de `Iz_base`" not in text
    assert "- gate formal de salida P3;" not in text


def test_visual_roadmap_preserves_p3b_evidence_axis():
    text = VISUAL.read_text(encoding="utf-8")

    assert "FOUNDATION V3 + P3A + EVIDENCIA P3B + BASE NORMATIVA P3C10" in text
    assert "`PRIMARIA`, `SECUNDARIA`, `MANUAL`, `BASE`, `MIXTA` o `INCOMPLETA`" in text
    assert "Tabla / dataset base" in text
    assert "El JavaScript no decide si una evidencia es primaria o secundaria" in text
    assert "Vínculo con el gate P3" in text
