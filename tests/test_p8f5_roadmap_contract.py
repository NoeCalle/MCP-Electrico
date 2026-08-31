from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_p8_roadmaps_record_p8f5_and_p8_as_closed():
    pilot = (ROOT / "docs" / "P8_REAL_PILOT_ROADMAP.md").read_text(encoding="utf-8")
    hardening = (ROOT / "docs" / "P8F_HARDENING_ROADMAP.md").read_text(encoding="utf-8")

    assert "| P8F4 | DONE |" in pilot
    assert "| P8F5 | DONE |" in pilot
    assert "P8 = CLOSED" in pilot
    assert "FIRST_CONTROLLED_REAL_PROJECT" in pilot
    assert "docs/P8_CONTROLLED_REAL_USE_CHECKLIST.md" in pilot

    assert "| P8F4 | DONE |" in hardening
    assert "| P8F5 | DONE |" in hardening
    assert "P8F = CLOSED" in hardening
    assert "FIRST_CONTROLLED_REAL_PROJECT" in hardening

    assert "| P8F4 | NEXT |" not in pilot
    assert "| P8F5 | PENDING |" not in pilot
    assert "| P8F5 | NEXT |" not in hardening
