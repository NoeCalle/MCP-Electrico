from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples" / "validar_linea_base.py"


def test_local_baseline_runs_all_four_stages(tmp_path: Path):
    out = tmp_path / "baseline"
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--output-dir", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=240,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr

    manifest_path = out / "manifiesto_linea_base.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["schema"] == "MCP_ELECTRICO_LOCAL_BASELINE_V1"
    assert manifest["ok"] is True
    assert manifest["status"] == "PASS"
    assert manifest["summary"] == {"total_stages": 4, "passed": 4, "failed": 0}
    assert manifest["policy"] == {
        "electrical_logic_added_by_orchestrator": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
    }

    stages = {stage["id"]: stage for stage in manifest["stages"]}
    assert list(stage["id"] for stage in manifest["stages"]) == [
        "diagnostico_local",
        "primer_uso",
        "ref01",
        "caso_minimo",
    ]
    assert all(stage["status"] == "PASS" for stage in stages.values())
    assert all(stage["returncode"] == 0 for stage in stages.values())
    assert stages["diagnostico_local"]["success_key"] == "ok"
    assert stages["primer_uso"]["success_key"] == "ok"
    assert stages["ref01"]["success_key"] == "pass"
    assert stages["caso_minimo"]["success_key"] == "ok"

    expected_schemas = {
        "diagnostico_local": "MCP_ELECTRICO_LOCAL_DIAGNOSTIC_V1",
        "primer_uso": "MCP_ELECTRICO_FIRST_RUN_V1",
        "ref01": "MCP_ELECTRICO_REFERENCE_RESULT_V1",
        "caso_minimo": "MCP_ELECTRICO_MINIMAL_CASE_RESULT_V1",
    }
    for stage_id, schema in expected_schemas.items():
        stage = stages[stage_id]
        assert stage["semantic_success"] is True
        assert stage["result_schema"] == schema
        assert stage["read_error"] is None
        assert stage["execution_error"] is None
        assert all(item["exists"] for item in stage["artifacts"])
        for artifact in stage["artifacts"]:
            assert artifact["size_bytes"] > 0
            assert len(artifact["sha256_raw_file"]) == 64

    assert (out / "01_diagnostico" / "diagnostico_local.json").exists()
    assert (out / "02_primer_uso" / "resultado_primer_uso.json").exists()
    assert (out / "02_primer_uso" / "workspace_primer_uso.html").exists()
    assert (out / "03_ref01" / "resultado_caso_referencia_01.json").exists()
    assert (out / "04_caso_minimo" / "resultado_caso_minimo.json").exists()
    assert (out / "04_caso_minimo" / "caso_entrada_normalizado.json").exists()
    assert (out / "04_caso_minimo" / "workspace_caso_minimo.html").exists()

    assert manifest["runtime"]["git_commit"]
    assert len(manifest["runtime"]["git_commit"]) == 40
    assert "no se usa como criterio de equivalencia entre equipos" in manifest["artifact_hash_note"]
