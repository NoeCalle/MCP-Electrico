from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

P3_FILES = [
    "tests/test_ampacity_primary_a1_temperature_chain_p3c11a3.py",
    "tests/test_p3c09_primary_dataset_contract.py",
    "tests/test_p3c09_primary_review_candidate.py",
    "tests/test_p3c10_primary_base_dataset.py",
    "tests/test_p3c10c_primary_base_candidate.py",
    "tests/test_p3c11_final_gate.py",
    "tests/test_p3c11a4_table5a_complete.py",
    "tests/test_p3c11a_table5a_primary.py",
    "tests/test_p3c11b_table5b_primary.py",
    "tests/test_p3c11c_table5c_primary.py",
    "tests/test_p3c11d_table5d_primary.py",
    "tests/test_p3c11e_table5e_primary.py",
    "tests/test_p3c12a_independent_benchmarks.py",
    "tests/test_p3c12b_primary_benchmark_gate.py",
]

for rel in P3_FILES:
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    text = text.replace('assert criteria["P3C13"]["status"] == "PENDING"', 'assert criteria["P3C13"]["status"] == "DONE"')
    text = text.replace('assert status["P3C13"] == "PENDING"', 'assert status["P3C13"] == "DONE"')
    text = text.replace('assert c13["status"] == "PENDING"', 'assert c13["status"] == "DONE"')
    text = text.replace('assert gate["ready_for_next_phase"] is False', 'assert gate["ready_for_next_phase"] is True')
    text = text.replace('assert gate["phase_status"] == "NOT_READY"', 'assert gate["phase_status"] == "READY_WITH_LIMITATIONS"')
    text = text.replace('assert gate["next_phase"] is None', 'assert gate["next_phase"] == "P4_IEC_60909"')
    text = text.replace('assert {"P3C13"} <= pending', 'assert "P3C13" not in pending')
    text = text.replace('assert {"P3C12", "P3C13"} <= pending', 'assert "P3C12" not in pending\n    assert "P3C13" not in pending')
    text = text.replace('assert pending == {"P3C13"}', 'assert pending == set()')
    path.write_text(text, encoding="utf-8")

# Madurez y tools
for rel in ["tests/test_ampacity_p3.py", "tests/test_engine_selection.py"]:
    path = ROOT / rel
    text = path.read_text(encoding="utf-8").replace('"UNDER_VALIDATION"', '"VALIDATED_WITH_LIMITATIONS"')
    path.write_text(text, encoding="utf-8")

path = ROOT / "tests/test_ampacity_tools_p3a.py"
text = path.read_text(encoding="utf-8")
text = text.replace('assert gate["phase_status"] == "NOT_READY"', 'assert gate["phase_status"] == "READY_WITH_LIMITATIONS"')
text = text.replace('assert gate["ready_for_next_phase"] is False', 'assert gate["ready_for_next_phase"] is True')
text = text.replace('assert gate["next_phase"] is None', 'assert gate["next_phase"] == "P4_IEC_60909"')
path.write_text(text, encoding="utf-8")

# Documento benchmark: conserva comprobación evidence-driven con encabezado actualizado.
path = ROOT / "tests/test_p3_benchmark_evidence_doc.py"
text = path.read_text(encoding="utf-8")
text = text.replace('"P3C12 — evidencia de benchmark, no constante"', '"P3C12: referencias primarias independientes, 29/29 casos PASS, seis familias"')
path.write_text(text, encoding="utf-8")

# Contrato roadmap maestro/visual actualizado.
path = ROOT / "tests/test_roadmap_contract.py"
text = path.read_text(encoding="utf-8")
text = text.replace(
    'assert "P3 — Ampacidad normativa | **EN PROGRESO — P3C01–P3C10 DONE; COBERTURA Y VALIDACIÓN FINAL PENDIENTES**" in text',
    'assert "P3 — Ampacidad normativa | **COMPLETA CON LIMITACIONES (P3 v1)**" in text',
)
text = text.replace('assert "EN PROGRESO — FOUNDATION V3" in text', 'assert "COMPLETA CON LIMITACIONES (V3/P3-v1)" in text')
text = text.replace('assert "**NOT_READY.**" in text', 'assert "**READY_WITH_LIMITATIONS — P3-v1 CERRADA.**" in text')
path.write_text(text, encoding="utf-8")

path = ROOT / "tests/test_roadmap_p3_contract.py"
text = path.read_text(encoding="utf-8")
text = text.replace('assert "P3C01–P3C10 DONE" in text', 'assert "P3C01–P3C13 DONE" in text')
text = text.replace('assert "`P3C01`–`P3C10`: implementados" in text or "`P3C01`–`P3C10`" in text', 'assert "P3C01–P3C13 = DONE" in text or "P3C01–P3C13 DONE" in text')
text = text.replace('assert "`P3C11` — cobertura primaria" in text', 'assert "`P3C11` — `DONE`" in text')
text = text.replace('assert "`P3C12` — benchmarks normativos independientes" in text', 'assert "`P3C12` — `DONE`" in text')
text = text.replace('assert "`P3C13` — madurez de ampacidad" in text', 'assert "`P3C13` — `DONE`" in text')
text = text.replace('assert "UNDER_VALIDATION" in text', 'assert "VALIDATED_WITH_LIMITATIONS" in text')
text = text.replace('assert "FOUNDATION V3 + P3A + EVIDENCIA P3B + BASE NORMATIVA P3C10" in text', 'assert "COMPLETA CON LIMITACIONES (V3/P3-v1)" in text')
path.write_text(text, encoding="utf-8")
