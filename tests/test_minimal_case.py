from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from mcp_electrico.minimal_case import (
    INPUT_SCHEMA,
    RESULT_SCHEMA,
    FIXED_SCOPE,
    MinimalCaseError,
    canonical_sha256,
    cargar_caso,
    normalizar_caso,
)


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "examples" / "caso_minimo.json"
SCRIPT = ROOT / "examples" / "ejecutar_caso_minimo.py"


def test_template_normalizes_to_fixed_p1_scope():
    case = cargar_caso(TEMPLATE)
    assert case["schema"] == INPUT_SCHEMA
    assert case["circuit"] == {
        "name": "caso_bt_01",
        "base_kv_ll": 0.48,
        "frequency_hz": 60,
        "source_bus": "sourcebus",
    }
    assert [line["bus1"] for line in case["lines"]] == ["sourcebus", "sourcebus"]
    assert [line["bus2"] for line in case["lines"]] == ["panel_a", "panel_b"]
    assert {load["bus"] for load in case["loads"]} == {"panel_a", "panel_b"}
    assert len(canonical_sha256(case)) == 64


def test_minimal_case_cli_generates_traceable_outputs(tmp_path: Path):
    out = tmp_path / "salida"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(TEMPLATE),
            "--output-dir",
            str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr

    workspace = out / "workspace_caso_minimo.html"
    normalized_path = out / "caso_entrada_normalizado.json"
    result_path = out / "resultado_caso_minimo.json"
    assert workspace.exists()
    assert normalized_path.exists()
    assert result_path.exists()

    normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert result["schema"] == RESULT_SCHEMA
    assert result["input_schema"] == INPUT_SCHEMA
    assert result["fixed_scope"] == FIXED_SCOPE
    assert result["ok"] is True
    assert result["professional_emission"] is False
    assert result["input_sha256"] == canonical_sha256(normalized)
    assert result["counts"] == {"lines": 2, "loads": 2}
    assert result["checks"] == {
        "input_validated": True,
        "opendss_converged": True,
        "voltage_drop_converged": True,
        "workspace_generated": True,
        "engine_policy_preserved": True,
    }
    assert result["engine_policy"] == {
        "executed_engine": "OpenDSS",
        "automatic_dispatch": False,
        "crosscheck": False,
        "pandapower_executed": False,
    }
    assert result["maturity"]["power_flow"]["status"] == "VALIDATED_WITH_LIMITATIONS"
    assert result["maturity"]["voltage_drop"]["status"] == "VALIDATED_WITH_LIMITATIONS"
    assert result["voltage_drop"]["criterio"]["limite_pct"] == 3.0
    assert result["voltage_drop"]["criterio"]["normativo_universal"] is False

    html = workspace.read_text(encoding="utf-8")
    assert "MCP Eléctrico — Caso mínimo BT editable" in html
    assert "F-01" in html
    assert "TABLERO A" in html


def test_minimal_case_fails_closed_on_loop_or_unknown_fields():
    base = json.loads(TEMPLATE.read_text(encoding="utf-8"))

    loop = deepcopy(base)
    loop["lines"][1]["bus2"] = "panel_a"
    with pytest.raises(MinimalCaseError, match="ya existe"):
        normalizar_caso(loop)

    unknown_bus = deepcopy(base)
    unknown_bus["loads"][0]["bus"] = "bus_inventado"
    with pytest.raises(MinimalCaseError, match="no pertenece al árbol radial"):
        normalizar_caso(unknown_bus)

    unknown_field = deepcopy(base)
    unknown_field["circuit"]["transformer_kva"] = 500
    with pytest.raises(MinimalCaseError, match="campos no soportados"):
        normalizar_caso(unknown_field)
