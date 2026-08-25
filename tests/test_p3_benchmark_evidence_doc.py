from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DOC = ROOT / "docs" / "P3_BENCHMARK_EVIDENCE.md"
EXIT_DOC = ROOT / "docs" / "P3_EXIT_GATE.md"


def test_benchmark_doc_separa_pass_de_evidencia_primaria():
    text = BENCHMARK_DOC.read_text(encoding="utf-8")
    assert "result = PASS" in text
    assert "evidence_level = PRIMARY" in text
    assert "independent_reference = true" in text
    assert "dataset_verification_status = PRIMARY_VERIFIED" in text
    assert "source_sha256" in text
    assert "professional_normative_coverage = true" in text
    assert "P3B_TABLE_5C_SECONDARY_INFRA_V1" in text
    assert "no satisface" in text.lower()
    assert "Table_5D_grouping_buried_method_D" in text
    assert "no existe un booleano manual" in text.lower()


def test_exit_gate_declara_p3c12_evidence_driven():
    text = EXIT_DOC.read_text(encoding="utf-8")
    assert "P3C12 — evidencia de benchmark, no constante" in text
    assert "ampacity_benchmark_evidence.evaluar_cobertura()" in text
    assert "benchmark_evidence" in text
    assert "SECONDARY" in text
    assert "no satisface P3C12" in text
    assert "docs/P3_BENCHMARK_EVIDENCE.md" in text
