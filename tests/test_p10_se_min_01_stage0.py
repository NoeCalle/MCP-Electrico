import json
from pathlib import Path

from mcp_electrico.real_pilot_intake import STATUS_BLOCKED, evaluar_admision


def _load_stage0() -> dict:
    path = Path(__file__).resolve().parents[1] / "examples" / "p10_se_min_01_stage0.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_p10_stage0_is_intentionally_fail_closed():
    result = evaluar_admision(_load_stage0())

    assert result["intake_status"] == STATUS_BLOCKED
    assert result["ready_to_build_model"] is False
    assert result["requested_scope"] == ["POWER_FLOW", "VOLTAGE_DROP"]

    assert result["electrical_calculation_performed"] is False
    assert result["model_mutation_performed"] is False
    assert result["automatic_defaults"] is False
    assert result["automatic_dispatch"] is False
    assert result["professional_emission"] is False

    codes = {issue["code"] for issue in result["issues"]}
    assert "P8B_BASE_04" in codes  # source.bus pendiente
    assert "P8B_BASE_06" in codes  # topology.buses pendiente
    assert "P8B_BASE_07" in codes  # transformadores pendientes
    assert "P8B_BASE_08" in codes  # lineas/cables pendientes
    assert "P8B_BASE_09" in codes  # cargas pendientes


def test_p10_stage0_preserves_only_closed_design_basis_values():
    manifest = _load_stage0()

    assert manifest["project"]["id"] == "SE-MIN-01"
    assert manifest["source"]["kv_ll"] == 22.9
    assert manifest["source"]["frequency_hz"] == 60.0

    # No se inventan valores de utility/topologia mientras la ingenieria sigue abierta.
    assert manifest["source"]["bus"] is None
    assert manifest["source"]["scc_max_mva"] is None
    assert manifest["source"]["scc_min_mva"] is None
    assert manifest["topology"]["buses"] == []
    assert manifest["topology"]["transformers"] == []
    assert manifest["topology"]["lines"] == []
    assert manifest["topology"]["loads"] == []
