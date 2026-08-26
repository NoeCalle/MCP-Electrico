from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples" / "primer_uso.py"


def test_primer_uso_smoke_generates_workspace_and_json(tmp_path: Path):
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr

    workspace = tmp_path / "workspace_primer_uso.html"
    result_file = tmp_path / "resultado_primer_uso.json"
    assert workspace.exists()
    assert result_file.exists()

    result = json.loads(result_file.read_text(encoding="utf-8"))
    assert result["schema"] == "MCP_ELECTRICO_FIRST_RUN_V1"
    assert result["ok"] is True
    assert result["checks"] == {
        "opendss_converged": True,
        "workspace_generated": True,
        "p3_closed": True,
        "p4_formally_unblocked": True,
        "ampacity_maturity_consistent": True,
        "iec60909_not_falsely_claimed": True,
    }
    assert result["engine_policy"] == {
        "executed_engine": "OpenDSS",
        "automatic_dispatch": False,
        "crosscheck": False,
        "pandapower_executed": False,
    }
    assert result["p3_gate"]["phase_status"] == "READY_WITH_LIMITATIONS"
    assert result["p3_gate"]["ready_for_next_phase"] is True
    assert result["p3_gate"]["next_phase"] == "P4_IEC_60909"
    assert result["p3_gate"]["professional_emission"] is False
    assert result["maturity"]["ampacity"]["status"] == "VALIDATED_WITH_LIMITATIONS"
    assert result["maturity"]["short_circuit"]["status"] == "UNDER_VALIDATION"
    assert result["power_flow"]["convergio"] is True
    assert result["voltage_drop"]["limite_pct"] == 3.0

    html = workspace.read_text(encoding="utf-8")
    assert "MCP Eléctrico — Primer uso" in html
    assert "Flujo" in html
    assert "Ampacidad" in html
