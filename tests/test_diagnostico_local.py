from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples" / "diagnostico_local.py"


def _by_id(result: dict, cid: str) -> dict:
    return next(item for item in result["checks"] if item["id"] == cid)


def test_diagnostico_local_end_to_end(tmp_path: Path):
    target = tmp_path / "diagnostico.json"
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(target)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert target.exists()

    result = json.loads(target.read_text(encoding="utf-8"))
    assert result["schema"] == "MCP_ELECTRICO_LOCAL_DIAGNOSTIC_V1"
    assert result["ok"] is True
    assert result["overall_status"] in {"OK", "OK_WITH_WARNINGS"}
    assert result["summary"]["fatal_failures"] == 0
    assert result["professional_emission"] is False

    assert _by_id(result, "python_version")["status"] in {"OK", "WARN"}
    assert _by_id(result, "python_architecture")["status"] == "OK"
    assert _by_id(result, "repo_layout")["status"] == "OK"
    assert _by_id(result, "output_write")["status"] == "OK"
    assert _by_id(result, "package_mcp")["status"] == "OK"
    assert _by_id(result, "package_opendssdirect")["status"] == "OK"
    assert _by_id(result, "package_pandapower")["status"] == "OK"
    assert _by_id(result, "package_networkx")["status"] == "OK"
    assert _by_id(result, "opendss_direct_smoke")["status"] == "OK"
    assert _by_id(result, "server_public_api")["status"] == "OK"
    assert _by_id(result, "engine_policy")["status"] == "OK"
    assert _by_id(result, "p3_gate")["status"] == "OK"
    assert _by_id(result, "maturity_barrier")["status"] == "OK"

    assert result["opendss_smoke"]["converged"] is True
    assert result["server_smoke"]["converged"] is True

    assert result["engine_policy"] == {
        "automatic_dispatch": False,
        "crosscheck": False,
        "default_engine": "opendss",
        "iec60909_preferred": "pandapower",
        "iec60909_implemented": True,
        "iec60909_professional_emission_candidate": False,
    }
    assert result["p3_gate"]["phase_status"] == "READY_WITH_LIMITATIONS"
    assert result["p3_gate"]["ready_for_next_phase"] is True
    assert result["p3_gate"]["next_phase"] == "P4_IEC_60909"
    assert result["p3_gate"]["professional_emission"] is False
    assert result["maturity"]["ampacity"]["status"] == "VALIDATED_WITH_LIMITATIONS"
    assert result["maturity"]["short_circuit"]["status"] == "UNDER_VALIDATION"

    assert "python examples/primer_uso.py" in result["recommended_next_steps"][0]
    assert "python examples/caso_referencia_01.py" in result["recommended_next_steps"][1]
    assert str(target) == result["outputs"]["diagnostic_json"]
