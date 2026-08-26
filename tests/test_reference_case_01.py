from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples" / "caso_referencia_01.py"
MANIFEST = ROOT / "mcp_electrico" / "data" / "reference_case_01.json"


def test_reference_case_01_manifest_is_frozen_and_independent():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["id"] == "REF01_BT_480V_RADIAL_HEAVY_V1"
    assert manifest["engine_under_test"] == "OpenDSS"
    assert manifest["reference_freeze"]["reference_depends_on_opendss"] is False
    assert manifest["reference_freeze"]["frozen_values"] is True
    assert manifest["professional_emission"] is False

    expected = manifest["expected_reference"]
    assert abs(expected["vpu_receiving"] - 0.9876942652973213) < 1e-15
    assert abs(expected["current_a"] - 108.92325136220022) < 1e-12
    assert abs(expected["loss_kw"] - 1.0677847218581746) < 1e-12
    assert abs(expected["loss_kvar"] - 0.35592824061939166) < 1e-12
    assert abs(expected["drop_pct"] - 1.2305734702678706) < 1e-12


def test_reference_case_01_passes_against_opendss(tmp_path: Path):
    output = tmp_path / "ref01.json"
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert output.exists()

    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["schema"] == "MCP_ELECTRICO_REFERENCE_RESULT_V1"
    assert result["id"] == "REF01_BT_480V_RADIAL_HEAVY_V1"
    assert result["pass"] is True
    assert result["reference"]["depends_on_opendss"] is False
    assert result["reference"]["frozen_consistency"]["pass"] is True
    assert result["tolerances_match_p1"] is True
    assert all(item["pass"] for item in result["comparisons"].values())
    assert result["professional_emission"] is False
