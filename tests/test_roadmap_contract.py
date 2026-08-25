from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFESSIONAL = ROOT / "docs" / "ROADMAP_PROFESIONAL.md"
VISUAL = ROOT / "docs" / "ROADMAP_VISUAL.md"
ENGINE = ROOT / "docs" / "ENGINE_SELECTION.md"
P2_EXIT = ROOT / "docs" / "P2_EXIT_GATE.md"
P3_AMPACITY = ROOT / "docs" / "P3_AMPACIDAD.md"


def test_professional_roadmap_keeps_core_phases_and_transversal_axes():
    text = PROFESSIONAL.read_text(encoding="utf-8")

    required_headings = [
        "## Mapa maestro",
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
        "## Eje transversal E",
    ]

    for heading in required_headings:
        assert heading in text, f"Falta del roadmap profesional: {heading}"

    assert "P2 — Datos profesionales | **COMPLETA CON LIMITACIONES (P2 v1)**" in text
    assert "P3 — Ampacidad normativa | **EN PROGRESO — FOUNDATION UNDER_VALIDATION**" in text
    assert "automatic_normative_lookup=false" in text
    assert "docs/P3_AMPACIDAD.md" in text
    assert "evaluar_cierre_p2()" in text
    assert "docs/P2_EXIT_GATE.md" in text
    assert "docs/ROADMAP_VISUAL.md" in text
    assert "docs/ENGINE_SELECTION.md" in text
    assert "no despacha automáticamente la ejecución" in text
    assert "cross-check" in text
    assert "P4 — Cortocircuito IEC 60909" in text
    assert "P5 — Protección del conductor y coordinación" in text
    assert "P6 — Arc Flash IEEE 1584" in text


def test_visual_roadmap_keeps_cross_phase_deliverables():
    text = VISUAL.read_text(encoding="utf-8")

    required_visual_phases = ["## V1", "## V2", "## V3", "## V4", "## V5", "## V6", "## V7"]
    for heading in required_visual_phases:
        assert heading in text, f"Falta del roadmap visual: {heading}"

    assert "COMPLETA CON LIMITACIONES (V2/P2 v1)" in text
    assert "EN PROGRESO — FOUNDATION V3" in text
    assert "UNDER_VALIDATION" in text
    assert "El JavaScript de V3 no calcula" in text
    assert "no es `Iz` normativo P3" in text
    assert "panel TCC" in text
    assert "Arc Flash" in text
    assert "cortocircuito IEC 60909" in text
    assert "P1.5 no crea por ahora una segunda interfaz visual" in text
    assert "A futuro se añadirá validación visual automatizada" in text


def test_engine_selection_doc_keeps_deterministic_safety_rules():
    text = ENGINE.read_text(encoding="utf-8")

    assert "selección determinista" in text
    assert "OpenDSS" in text
    assert "pandapower" in text
    assert "automatic_dispatch=false" in text
    assert "crosscheck=false" in text
    assert "READY_DATA" in text
    assert "MISSING_DATA" in text
    assert "ENGINE_NOT_READY" in text
    assert "MODULE_NOT_READY" in text
    assert "professional_execution_ready" in text
    assert "Nunca confundir `technical_executable`, `professional_execution_ready` y `apto_para_emision`" in text


def test_p2_exit_gate_preserves_scope_and_next_phase():
    text = P2_EXIT.read_text(encoding="utf-8")

    assert "COMPLETE_WITH_LIMITATIONS" in text
    assert "estado de la fase del producto" in text
    assert "estado del modelo activo" in text
    assert "ampacidad de catálogo todavía no es `Iz` normativo" in text
    assert "IEC 60909 sigue perteneciendo a P4" in text
    assert "P3 — ampacidad normativa" in text


def test_p3_foundation_doc_preserves_under_validation_scope():
    text = P3_AMPACITY.read_text(encoding="utf-8")

    assert "UNDER_VALIDATION" in text
    assert "Ib <= In <= Iz" in text
    assert "automatic_tables=false" in text
    assert "P3 no asume silenciosamente `product(k_i)=1`" in text
    assert "automatic_normative_lookup=false" in text
    assert "no cierra P3" in text.lower()
