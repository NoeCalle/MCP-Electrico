from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "docs" / "ROADMAP_PROFESIONAL.md"
VISUAL = ROOT / "docs" / "ROADMAP_VISUAL.md"


def test_roadmap_p3_reflects_current_gate_and_blockers():
    text = ROADMAP.read_text(encoding="utf-8")

    assert "INFRAESTRUCTURA P3B + GATE P3 IMPLEMENTADOS" in text
    assert "Gate formal de salida P3 — implementado" in text
    assert "Infraestructura y fuente `P3C01`–`P3C08`: implementadas" in text
    assert "`P3C09` — al menos una revisión numérica `PRIMARY_VERIFIED`" in text
    assert "`P3C13` — madurez de ampacidad" in text
    assert "**Revisión explícita actual:**" in text
    assert "AI_VISUAL_REVIEW_USER_AUTHORIZED" in text
    assert "habilitados para el siguiente PR de dataset primario" in text
    assert "- gate formal de salida P3;" not in text


def test_visual_roadmap_preserves_p3b_evidence_axis():
    text = VISUAL.read_text(encoding="utf-8")

    assert "FOUNDATION V3 + P3A + EVIDENCIA P3B" in text
    assert "`PRIMARIA`, `SECUNDARIA`, `MANUAL`, `BASE`, `MIXTA` o `INCOMPLETA`" in text
    assert "El JavaScript no decide si una evidencia es primaria o secundaria" in text
    assert "Vínculo con el gate P3" in text
