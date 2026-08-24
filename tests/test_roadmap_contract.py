from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFESSIONAL = ROOT / "docs" / "ROADMAP_PROFESIONAL.md"
VISUAL = ROOT / "docs" / "ROADMAP_VISUAL.md"


def test_professional_roadmap_keeps_core_phases_and_visual_axis():
    text = PROFESSIONAL.read_text(encoding="utf-8")

    required_headings = [
        "## Fase P0",
        "## Fase P1",
        "## Fase P1.5",
        "## Fase P2",
        "## Fase P3",
        "## Fase P4",
        "## Fase P5",
        "## Fase P6",
        "## Fase P7",
        "## Fase P8",
        "## Eje transversal V",
    ]

    for heading in required_headings:
        assert heading in text, f"Falta del roadmap profesional: {heading}"

    assert "docs/ROADMAP_VISUAL.md" in text
    assert "P4 — Cortocircuito IEC 60909" in text
    assert "P5 — Protección del conductor y coordinación" in text
    assert "P6 — Arc Flash IEEE 1584" in text


def test_visual_roadmap_keeps_cross_phase_deliverables():
    text = VISUAL.read_text(encoding="utf-8")

    required_visual_phases = [
        "## V1",
        "## V2",
        "## V3",
        "## V4",
        "## V5",
        "## V6",
        "## V7",
    ]

    for heading in required_visual_phases:
        assert heading in text, f"Falta del roadmap visual: {heading}"

    assert "panel TCC" in text
    assert "Arc Flash" in text
    assert "cortocircuito IEC 60909" in text
    assert "P1.5 no crea por ahora una segunda interfaz visual" in text
    assert "A futuro se añadirá validación visual automatizada" in text
