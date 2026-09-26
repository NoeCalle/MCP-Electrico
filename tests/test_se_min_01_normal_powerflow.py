from __future__ import annotations

import json
import math
from pathlib import Path

from mcp_electrico import (
    real_controlled_execution,
    real_integrated_readiness,
    real_pilot_intake,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "examples" / "se_min_01_normal_powerflow.json"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_se_min_01_normal_load_totals_match_design_load_list():
    manifest = _manifest()
    loads = manifest["topology"]["loads"]
    kw = sum(float(item["kw"]) for item in loads)
    kvar = sum(float(item["kvar"]) for item in loads)
    kva = math.hypot(kw, kvar)

    assert round(kw, 3) == 6433.704
    assert round(kvar, 3) == 1679.052
    assert round(kva, 3) == 6649.193

    expected = manifest["model_scope_notes"]["load_totals_expected"]
    assert round(kw, 3) == expected["kw"]
    assert round(kvar, 3) == expected["kvar"]
    assert round(kva, 3) == expected["kva"]


def test_se_min_01_normal_preserves_declared_scope_and_placeholders():
    manifest = _manifest()

    assert manifest["project"]["id"] == "SE-MIN-01"
    assert manifest["project"]["scenario"] == "NORMAL"
    assert manifest["project"]["altitude_m"] == 3800
    assert manifest["requested_scope"] == ["POWER_FLOW"]

    assert manifest["source"]["scc_max_mva"] == 1_000_000.0
    assert "MODEL_PLACEHOLDER_STIFF_SOURCE" in manifest["source"]["source_reference"]

    aux = [
        item
        for item in manifest["topology"]["transformers"]
        if item["id"] in {"Transformer.TR_AUX_A", "Transformer.TR_AUX_B"}
    ]
    assert len(aux) == 2
    assert all(item["kva"] == 1500.0 for item in aux)
    assert all("MODEL_PLACEHOLDER" in item["source_reference"] for item in aux)

    links = manifest["topology"]["lines"]
    assert len(links) == 4
    assert all(item["r1_ohm_km"] == 1e-6 for item in links)
    assert all(item["x1_ohm_km"] == 1e-6 for item in links)
    assert all("MODEL_PLACEHOLDER" in item["source_reference"] for item in links)

    assert (
        manifest["model_scope_notes"]["normal_ties"]["bus_tie_4k16"]
        == "NORMALLY_OPEN_NOT_MATERIALIZED_IN_NORMAL_BASE_CASE"
    )
    assert (
        manifest["model_scope_notes"]["normal_ties"]["bus_tie_480"]
        == "NORMALLY_OPEN_NOT_MATERIALIZED_IN_NORMAL_BASE_CASE"
    )


def test_se_min_01_normal_is_fail_closed_ready_without_engine_defaults():
    manifest = _manifest()

    intake = real_pilot_intake.evaluar_admision(manifest)
    assert intake["intake_status"] == "READY_TO_BUILD_MODEL"
    assert intake["ready_to_build_model"] is True
    assert intake["issues"] == []

    readiness = real_integrated_readiness.evaluar_readiness_integral(manifest)
    assert readiness["readiness_status"] == "READY_FOR_CONTROLLED_EXECUTION", readiness
    assert readiness["all_requested_ready"] is True
    assert readiness["ready_scopes"] == ["POWER_FLOW"]
    assert readiness["blocked_scopes"] == []
    assert readiness["materialization"]["engine_defaults_retained_count"] == 0
    assert readiness["materialization"]["source_p2_materialized"] is True
    assert readiness["automatic_defaults"] is False
    assert readiness["automatic_dispatch"] is False
    assert readiness["professional_emission"] is False


def test_se_min_01_normal_executes_power_flow_only():
    result = real_controlled_execution.ejecutar_controlado(_manifest())

    assert result["execution_status"] == "CONTROLLED_EXECUTION_COMPLETED", result
    assert result["executed_scopes"] == ["POWER_FLOW"]
    assert result["pending_scopes"] == []
    assert "VOLTAGE_DROP" not in result["results"]

    power = result["results"]["POWER_FLOW"]
    assert power["convergio"] is True
    assert power["powerflow"]["convergio"] is True
    assert len(power["buses"]) == 9
    assert len(power["alimentadores"]) == 4
    assert power["resumen"]["perdidas_totales_kw"] >= 0

    vmins = [item["vpu_min"] for item in power["buses"] if item["vpu_min"] is not None]
    assert vmins
    assert 0.80 < min(vmins) <= 1.05

    assert result["electrical_calculation_performed"] is True
    assert result["ampacity_calculation_performed"] is False
    assert result["short_circuit_calculation_performed"] is False
    assert result["protection_calculation_performed"] is False
    assert result["automatic_dispatch"] is False
    assert result["crosscheck"] is False
    assert result["professional_emission"] is False
