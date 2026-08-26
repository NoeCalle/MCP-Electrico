from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUICKSTART = ROOT / "QUICKSTART.md"
FIRST_RUN = ROOT / "examples" / "primer_uso.py"


def test_quickstart_preserves_first_clone_contract():
    text = QUICKSTART.read_text(encoding="utf-8")
    script = FIRST_RUN.read_text(encoding="utf-8")

    assert "python examples/primer_uso.py" in text
    assert "workspace_primer_uso.html" in text
    assert "resultado_primer_uso.json" in text
    assert "READY_WITH_LIMITATIONS" in text
    assert "VALIDATED_WITH_LIMITATIONS" in text
    assert "UNDER_VALIDATION" in text
    assert "automatic_dispatch=false" in text
    assert "crosscheck=false" in text
    assert "no ejecuta IEC 60909" in text

    assert '"automatic_dispatch": False' in script
    assert '"crosscheck": False' in script
    assert '"pandapower_executed": False' in script
    assert '"executed_engine": "OpenDSS"' in script
