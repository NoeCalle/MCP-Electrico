from __future__ import annotations

from copy import deepcopy

from mcp_electrico import real_model_readiness, workspace_state


def _manifest(requested_scope: list[str] | None = None) -> dict:
    return {
        "project": {
            "id": "REAL-SE-READINESS-001",
            "name": "Subestación readiness real",
            "source_reference": "SLD + expediente aprobado REV-A",
        },
        "requested_scope": requested_scope or [
            "POWER_FLOW",
            "VOLTAGE_DROP",
            "IEC60909_3PH_MAX_MIN",
            "IEC60909_1PH_GROUND_MAX_MIN",
            "AMPACITY",
            "PROTECTION_TCC",
        ],
        "source": {
            "bus": "red_mt",
            "kv_ll": 22.9,
            "frequency_hz": 60.0,
            "pu": 1.0,
            "angle_deg": 0.0,
            "scc_max_mva": 350.0,
            "x_r_max": 10.0,
            "scc_min_mva": 180.0,
            "x_r_min": 6.0,
            "source_reference": "Utility study REV-A",
        },
        "topology": {
            "buses": ["red_mt", "tgbt", "load_bus"],
            "transformers": [{
                "id": "Transformer.tr01",
                "bus_hv": "red_mt",
                "bus_lv": "tgbt",
                "kva": 1000.0,
                "kv_hv": 22.9,
                "kv_lv": 0.48,
                "uk_percent": 6.0,
                "vector_group": "Dyn11",
                "x_r": 10.0,
                "no_load_loss_kw": 1.8,
                "i0_percent": 0.6,
                "tap_side": "hv",
                "tap_neutral": 0,
                "tap_min": -2,
                "tap_max": 2,
                "tap_step_percent": 2.5,
                "tap_pos": 0,
                "source_reference": "TR nameplate REV-A",
            }],
            "lines": [{
                "id": "Line.feeder",
                "bus1": "tgbt",
                "bus2": "load_bus",
                "phases": 3,
                "length_km": 0.05,
                "r1_ohm_km": 0.12,
                "x1_ohm_km": 0.08,
                "c1_nf_km": 0.0,
                "endtemp_min_c": 90.0,
                "source_reference": "Cable schedule REV-A",
            }],
            "loads": [{
                "id": "Load.load1",
                "bus": "load_bus",
                "phases": 3,
                "kv": 0.48,
                "kw": 250.0,
                "kvar": 80.0,
                "connection": "wye",
                "model": 1,
                "source_reference": "Load list REV-A",
            }],
        },
        "zero_sequence": {
            "source": {
                "r0_max_ohm": 0.15,
                "x0_max_ohm": 0.45,
                "r0_min_ohm": 0.25,
                "x0_min_ohm": 0.80,
                "source_reference": "Utility Z0 study REV-A",
            },
            "lines": [{
                "id": "Line.feeder",
                "r0_ohm_km": 0.36,
                "x0_ohm_km": 0.15,
                "c0_nf_km": 100.0,
                "source_reference": "Cable Z0 calculation REV-A",
            }],
            "transformers": [{
                "id": "Transformer.tr01",
                "uk0_percent": 5.5,
                "ur0_percent": 0.6,
                "magnetizing_z0_ratio_percent": 100.0,
                "magnetizing_r_over_x": 0.0,
                "leakage_share_hv": 0.5,
                "neutral_side": "lv",
                "neutral_mode": "solid",
                "source_reference": "Transformer Z0 test REV-A",
            }],
        },
        "ampacity": [{
            "element_id": "Line.feeder",
            "conductor_code": "PROJECT-CABLE-01",
            "ib_a": 350.0,
            "in_a": 400.0,
            "installation_reference": "Installation detail REV-A",
            "ampacity_reference": "Approved ampacity source REV-A",
        }],
        "protection": {
            "devices": [{
                "id": "QF01",
                "type": "circuit_breaker",
                "protected_element": "Line.feeder",
                "in_a": 400.0,
                "ue_kv": 0.48,
                "breaking_capacity_ka": 36.0,
                "source_reference": "Protection schedule REV-A",
            }],
            "tcc_datasets": [{
                "dataset_id": "QF01-TCC",
                "time_semantics": "TOTAL_CLEARING_TIME",
                "source_type": "MANUFACTURER_DATASET",
                "source_reference": "Manufacturer curve REV-A",
            }],
        },
        "study_inputs": {
            "voltage_drop_limit_pct": 5.0,
            "short_circuit_buses": ["tgbt", "load_bus"],
        },
    }


def test_p8c3c_full_scope_is_partial_only_because_p3_p5_not_materialized():
    result = real_model_readiness.evaluar_readiness(_manifest())

    assert result["schema"] == "MCP_ELECTRICO_P8C3C_ENGINE_READINESS_V1"
    assert result["model_built"] is True
    assert result["readiness_status"] == "PARTIALLY_READY"
    assert result["scope_readiness"]["POWER_FLOW"]["status"] == "READY"
    assert result["scope_readiness"]["VOLTAGE_DROP"]["status"] == "READY"
    assert result["scope_readiness"]["IEC60909_3PH_MAX_MIN"]["status"] == "READY"
    assert result["scope_readiness"]["IEC60909_1PH_GROUND_MAX_MIN"]["status"] == "READY"
    assert result["scope_readiness"]["AMPACITY"]["status"] == "BLOCKED"
    assert result["scope_readiness"]["PROTECTION_TCC"]["status"] == "BLOCKED"
    assert result["ready_scopes"] == [
        "POWER_FLOW",
        "VOLTAGE_DROP",
        "IEC60909_3PH_MAX_MIN",
        "IEC60909_1PH_GROUND_MAX_MIN",
    ]
    assert result["blocked_scopes"] == ["AMPACITY", "PROTECTION_TCC"]
    assert result["all_requested_ready"] is False
    assert result["electrical_calculation_performed"] is False
    assert result["studies_executed"] == []
    assert result["workspace_studies_after_readiness"] == []
    assert workspace_state.status()["studies"] == {}
    assert result["professional_emission"] is False


def test_p8c3c_engine_only_scope_can_be_ready_without_executing():
    manifest = _manifest([
        "POWER_FLOW",
        "VOLTAGE_DROP",
        "IEC60909_3PH_MAX_MIN",
        "IEC60909_1PH_GROUND_MAX_MIN",
    ])
    result = real_model_readiness.evaluar_readiness(manifest)

    assert result["readiness_status"] == "READY_FOR_CONTROLLED_EXECUTION"
    assert result["all_requested_ready"] is True
    assert result["blocked_scopes"] == []
    for item in result["scope_readiness"].values():
        assert item["status"] == "READY"
    assert result["electrical_calculation_performed"] is False
    assert workspace_state.status()["studies"] == {}


def test_p8c3c_short_circuit_requires_explicit_target_buses():
    manifest = _manifest(["IEC60909_3PH_MAX_MIN", "IEC60909_1PH_GROUND_MAX_MIN"])
    del manifest["study_inputs"]["short_circuit_buses"]

    result = real_model_readiness.evaluar_readiness(manifest)

    assert result["model_built"] is True
    assert result["readiness_status"] == "BLOCKED"
    assert result["scope_readiness"]["IEC60909_3PH_MAX_MIN"]["status"] == "BLOCKED"
    assert result["scope_readiness"]["IEC60909_1PH_GROUND_MAX_MIN"]["status"] == "BLOCKED"
    for scope in ("IEC60909_3PH_MAX_MIN", "IEC60909_1PH_GROUND_MAX_MIN"):
        assert any(item["code"] == "P8C3C101" for item in result["scope_readiness"][scope]["issues"])
    assert result["electrical_calculation_performed"] is False


def test_p8c3c_unknown_target_bus_is_blocked_before_p4():
    manifest = _manifest(["IEC60909_3PH_MAX_MIN"])
    manifest["study_inputs"]["short_circuit_buses"] = ["ghost_bus"]

    result = real_model_readiness.evaluar_readiness(manifest)

    view = result["scope_readiness"]["IEC60909_3PH_MAX_MIN"]
    assert view["status"] == "BLOCKED"
    assert any(item["code"] == "P8C3C104" for item in view["issues"])
    assert view["checks"] == []


def test_p8c3c_power_flow_blocks_if_project_would_consume_opendss_defaults():
    manifest = _manifest(["POWER_FLOW", "VOLTAGE_DROP"])
    del manifest["source"]["pu"]
    del manifest["source"]["angle_deg"]
    del manifest["topology"]["lines"][0]["c1_nf_km"]
    del manifest["topology"]["loads"][0]["connection"]
    del manifest["topology"]["loads"][0]["model"]

    result = real_model_readiness.evaluar_readiness(manifest)

    assert result["model_built"] is True
    assert result["readiness_status"] == "BLOCKED"
    for scope in ("POWER_FLOW", "VOLTAGE_DROP"):
        view = result["scope_readiness"][scope]
        assert view["status"] == "BLOCKED"
        assert any(item["code"] == "P8C3C201" for item in view["issues"])
    assert result["electrical_calculation_performed"] is False


def test_p8c3c_voltage_drop_requires_explicit_project_limit():
    manifest = _manifest(["POWER_FLOW", "VOLTAGE_DROP"])
    del manifest["study_inputs"]["voltage_drop_limit_pct"]

    result = real_model_readiness.evaluar_readiness(manifest)

    assert result["scope_readiness"]["POWER_FLOW"]["status"] == "READY"
    voltage = result["scope_readiness"]["VOLTAGE_DROP"]
    assert voltage["status"] == "BLOCKED"
    assert any(item["code"] == "P8C3C210" for item in voltage["issues"])
    assert result["readiness_status"] == "PARTIALLY_READY"


def test_p8c3c_unknown_transformer_tap_blocks_p4_without_blocking_build():
    manifest = _manifest(["IEC60909_3PH_MAX_MIN", "IEC60909_1PH_GROUND_MAX_MIN"])
    trafo = manifest["topology"]["transformers"][0]
    for key in ("tap_side", "tap_neutral", "tap_min", "tap_max", "tap_step_percent", "tap_pos"):
        del trafo[key]

    result = real_model_readiness.evaluar_readiness(manifest)

    assert result["model_built"] is True
    for scope in ("IEC60909_3PH_MAX_MIN", "IEC60909_1PH_GROUND_MAX_MIN"):
        view = result["scope_readiness"][scope]
        assert view["status"] == "BLOCKED"
        assert any(item["code"] == "P8C3C220" for item in view["issues"])
    assert result["electrical_calculation_performed"] is False


def test_p8c3c_build_blocker_propagates_without_study_execution():
    manifest = _manifest(["POWER_FLOW"])
    manifest["source"]["frequency_hz"] = None

    result = real_model_readiness.evaluar_readiness(manifest)

    assert result["model_built"] is False
    assert result["readiness_status"] == "BLOCKED"
    assert result["scope_readiness"]["POWER_FLOW"]["status"] == "BLOCKED"
    assert any(item["code"] == "P8C3B001" for item in result["scope_readiness"]["POWER_FLOW"]["issues"])
    assert result["electrical_calculation_performed"] is False
    assert result["studies_executed"] == []
