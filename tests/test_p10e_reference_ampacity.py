from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from mcp_electrico import (
    real_controlled_execution,
    real_engineering_materializer,
    real_integrated_readiness,
    real_pilot_intake,
    workspace_state,
)


def _manifest() -> dict:
    path = Path(__file__).resolve().parents[1] / "examples" / "p10_reference_substation_stage4.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _ampacity_by_element(result: dict) -> dict[str, dict]:
    rows = result["results"]["AMPACITY"]["alimentadores"]
    return {str(item["element"]).lower(): item for item in rows}


def test_p10e_reference_intake_accepts_explicit_p3_records():
    result = real_pilot_intake.evaluar_admision(_manifest())

    assert result["intake_status"] == "READY_TO_BUILD_MODEL"
    assert result["ready_to_build_model"] is True
    assert result["issues"] == []
    assert "AMPACITY" in result["requested_scope"]
    assert result["study_input_readiness"]["AMPACITY"]["status"] == "INPUTS_PRESENT"
    assert result["electrical_calculation_performed"] is False
    assert result["automatic_defaults"] is False
    assert result["professional_emission"] is False


def test_p10e_reference_materializes_project_conductors_without_evaluation():
    result = real_engineering_materializer.materializar_datos_ingenieria(_manifest())

    assert result["engineering_materializer_status"] == "P3_MATERIALIZED_P5_PENDING"
    assert result["p3_materialized"] is True
    assert result["p5_materialized"] is False
    assert result["issues"] == []
    assert result["electrical_calculation_performed"] is False
    assert result["ampacity_calculation_performed"] is False

    assignments = result["p3"]["assignments"]
    assert len(assignments) == 2
    assert all(item["origen"] == "PROJECT_DATA" for item in assignments)

    profiles = result["p3"]["profiles"]
    assert len(profiles) == 2
    assert all(item["base"]["origin"] == "P2_PROJECT" for item in profiles)
    assert all(item["correction"]["mode"] == "EXPLICIT_FACTORS" for item in profiles)
    assert all(item["correction"]["automatic_normative_lookup"] is False for item in profiles)

    assert result["automatic_defaults"] is False
    assert result["automatic_dispatch"] is False
    assert result["crosscheck"] is False
    assert result["professional_emission"] is False


def test_p10e_reference_integrated_readiness_is_green():
    result = real_integrated_readiness.evaluar_readiness_integral(_manifest())

    assert result["readiness_status"] == "READY_FOR_CONTROLLED_EXECUTION"
    assert result["materialization_layer"] == "P8C4A"
    assert result["materialization_ok"] is True
    assert result["blocked_scopes"] == []
    assert result["all_requested_ready"] is True

    p3 = result["scope_readiness"]["AMPACITY"]
    assert p3["status"] == "READY"
    assert p3["backend"] == "P3"
    assert len(p3["checks"]) == 2
    assert all(check["ready"] is True for check in p3["checks"])
    assert all(check["assignment_origin"] == "PROJECT_DATA" for check in p3["checks"])
    assert all(check["profile_base_origin"] == "P2_PROJECT" for check in p3["checks"])

    assert result["ampacity_calculation_performed"] is False
    assert result["workspace_studies_after_readiness"] == []
    assert result["professional_emission"] is False


def test_p10e_reference_executes_ampacity_with_explicit_factors():
    result = real_controlled_execution.ejecutar_controlado(_manifest())

    assert result["execution_status"] == "CONTROLLED_EXECUTION_COMPLETED"
    assert result["executed_scopes"] == [
        "POWER_FLOW",
        "VOLTAGE_DROP",
        "AMPACITY",
        "IEC60909_3PH_MAX_MIN",
        "IEC60909_1PH_GROUND_MAX_MIN",
    ]
    assert result["pending_scopes"] == []
    assert result["ampacity_calculation_performed"] is True
    assert result["protection_calculation_performed"] is False

    p3 = result["results"]["AMPACITY"]
    assert p3["status"] == "CUMPLE"
    assert p3["summary"] == {
        "total": 2,
        "cumple": 2,
        "no_cumple": 0,
        "datos_insuficientes": 0,
    }
    assert p3["automatic_normative_lookup"] is False
    assert p3["professional_emission"] is False

    rows = _ampacity_by_element(result)

    mv = rows["line.mv_feeder"]
    assert mv["criterion"] == "Ib <= In <= Iz"
    assert mv["values"]["ib_a"] == pytest.approx(320.0)
    assert mv["values"]["in_a"] == pytest.approx(350.0)
    assert mv["values"]["iz_base_a"] == pytest.approx(450.0)
    assert mv["values"]["factor_total"] == pytest.approx(0.95)
    assert mv["values"]["iz_a"] == pytest.approx(427.5)
    assert mv["checks"] == {"ib_le_in": True, "in_le_iz": True}
    assert mv["base_evidence"]["origin"] == "P2_PROJECT"

    lv = rows["line.lv_feeder"]
    assert lv["values"]["ib_a"] == pytest.approx(700.0)
    assert lv["values"]["in_a"] == pytest.approx(800.0)
    assert lv["values"]["iz_base_a"] == pytest.approx(1000.0)
    assert lv["values"]["factor_total"] == pytest.approx(0.90)
    assert lv["values"]["iz_a"] == pytest.approx(900.0)
    assert lv["checks"] == {"ib_le_in": True, "in_le_iz": True}
    assert lv["base_evidence"]["origin"] == "P2_PROJECT"

    assert result["automatic_dispatch"] is False
    assert result["automatic_fault_binding"] is False
    assert result["crosscheck"] is False
    assert result["professional_emission"] is False

    studies = workspace_state.status()["studies"]
    assert "ampacity" in studies
    assert studies["ampacity"]["valid"] is True
    assert not any(name.startswith("protection_") for name in studies)


def test_p10e_reference_ampacity_is_repeatable():
    manifest = _manifest()
    first = real_controlled_execution.ejecutar_controlado(manifest)
    second = real_controlled_execution.ejecutar_controlado(deepcopy(manifest))

    assert first["execution_status"] == second["execution_status"] == "CONTROLLED_EXECUTION_COMPLETED"
    assert first["model_revision"] == second["model_revision"]

    first_rows = _ampacity_by_element(first)
    second_rows = _ampacity_by_element(second)
    assert first_rows.keys() == second_rows.keys()
    for element in first_rows:
        assert first_rows[element]["status"] == second_rows[element]["status"] == "CUMPLE"
        assert first_rows[element]["values"] == second_rows[element]["values"]
