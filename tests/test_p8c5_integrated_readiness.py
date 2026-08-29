from __future__ import annotations

from copy import deepcopy

from mcp_electrico import real_integrated_readiness, workspace_state


def _manifest(requested_scope: list[str] | None = None) -> dict:
    return {
        "project": {
            "id": "REAL-SE-INTEGRATED-001",
            "name": "Subestación piloto real integral",
            "source_reference": "SLD + expediente aprobado REV-A",
        },
        "requested_scope": requested_scope or [
            "POWER_FLOW",
            "VOLTAGE_DROP",
            "AMPACITY",
            "IEC60909_3PH_MAX_MIN",
            "IEC60909_1PH_GROUND_MAX_MIN",
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
                "source_reference": "Transformer nameplate REV-A",
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
            "conductor_description": "PROJECT-CABLE-01 · feeder aprobado",
            "base_ampacity_a": 500.0,
            "norm_id": "IEC_60364_5_52_2009_A1_2024",
            "ib_a": 350.0,
            "ib_reference": "Load list + feeder sizing REV-A",
            "in_a": 400.0,
            "in_reference": "Protection schedule REV-A",
            "installation_reference": "Installation detail REV-A",
            "ampacity_reference": "Approved cable ampacity calculation REV-A",
            "base_conditions_confirmed": True,
            "factors": [],
        }],
        "protection": {
            "devices": [{
                "id": "QF01",
                "type": "circuit_breaker",
                "protected_element": "Line.feeder",
                "in_a": 400.0,
                "ue_kv": 0.48,
                "icu_ka": 36.0,
                "ics_ka": 25.0,
                "breaking_capacity_ka": 36.0,
                "standard_reference": "IEC 60947-2 project specification REV-A",
                "source_reference": "Approved protection schedule REV-A",
                "manufacturer": "PROJECT_MANUFACTURER",
                "model": "PROJECT_BREAKER_400A",
                "poles": 3,
                "curve_id": "QF01-MFR-TCC",
                "curve_type": "MANUFACTURER_TCC",
                "curve_source_reference": "Manufacturer TCC REV-A",
                "curve_revision": "REV-A",
            }],
            "tcc_datasets": [{
                "device_id": "QF01",
                "dataset_id": "QF01-TCC-DATA-REV-A",
                "curve_id": "QF01-MFR-TCC",
                "shape": "BAND",
                "time_semantics": "TOTAL_CLEARING_TIME",
                "source_type": "MANUFACTURER_DATASET",
                "source_reference": "Manufacturer TCC numeric data REV-A",
                "revision": "REV-A",
                "segments": [{
                    "id": "long_short",
                    "points": [
                        {"current_a": 400.0, "time_min_s": 10.0, "time_max_s": 12.0},
                        {"current_a": 4000.0, "time_min_s": 0.10, "time_max_s": 0.12},
                    ],
                }],
            }],
        },
        "study_inputs": {
            "voltage_drop_limit_pct": 5.0,
            "short_circuit_buses": ["load_bus"],
        },
    }


def test_p8c5_full_case_is_ready_after_project_origin_fix():
    result = real_integrated_readiness.evaluar_readiness_integral(_manifest())

    assert result["schema"] == "MCP_ELECTRICO_P8C5_INTEGRATED_READINESS_V1"
    assert result["materialization_layer"] == "P8C4B"
    assert result["materialization_ok"] is True
    assert result["readiness_status"] == "READY_FOR_CONTROLLED_EXECUTION"

    for scope in (
        "POWER_FLOW",
        "VOLTAGE_DROP",
        "AMPACITY",
        "IEC60909_3PH_MAX_MIN",
        "IEC60909_1PH_GROUND_MAX_MIN",
        "PROTECTION_TCC",
    ):
        assert result["scope_readiness"][scope]["status"] == "READY"

    ampacity_view = result["scope_readiness"]["AMPACITY"]
    assert ampacity_view["issues"] == []
    assert ampacity_view["checks"][0]["assignment_origin"] == "PROJECT_DATA"
    assert ampacity_view["checks"][0]["profile_base_origin"] == "P2_PROJECT"

    assert result["blocked_scopes"] == []
    assert result["all_requested_ready"] is True
    assert result["next_gate"] == "P8D_CONTROLLED_EXECUTION"
    assert result["workspace_studies_after_readiness"] == []
    assert workspace_state.status()["studies"] == {}
    assert result["electrical_calculation_performed"] is False
    assert result["ampacity_calculation_performed"] is False
    assert result["short_circuit_calculation_performed"] is False
    assert result["protection_calculation_performed"] is False
    assert result["tcc_evaluation_performed"] is False
    assert result["professional_emission"] is False


def test_p8c5_p5_and_p3_are_ready_together_without_execution():
    result = real_integrated_readiness.evaluar_readiness_integral(_manifest())

    p3 = result["scope_readiness"]["AMPACITY"]
    assert p3["status"] == "READY"
    assert p3["checks"][0]["profile_base_origin"] == "P2_PROJECT"

    p5 = result["scope_readiness"]["PROTECTION_TCC"]
    assert p5["status"] == "READY"
    check = p5["checks"][0]
    assert check["breaking_capacity_ready"] is True
    assert check["tcc_data_ready"] is True
    assert check["p3_binding"]["status"] == "MATCH"
    assert check["curve_time_semantics"] == "TOTAL_CLEARING_TIME"
    assert p5["tcc_evaluation_performed"] is False


def test_p8c5_engine_only_does_not_materialize_p3_or_p5_and_can_be_ready():
    manifest = _manifest([
        "POWER_FLOW",
        "VOLTAGE_DROP",
        "IEC60909_3PH_MAX_MIN",
        "IEC60909_1PH_GROUND_MAX_MIN",
    ])
    result = real_integrated_readiness.evaluar_readiness_integral(manifest)

    assert result["materialization_layer"] == "P8C3B"
    assert result["materialization_ok"] is True
    assert result["readiness_status"] == "READY_FOR_CONTROLLED_EXECUTION"
    assert result["all_requested_ready"] is True
    assert result["blocked_scopes"] == []
    assert result["next_gate"] == "P8D_CONTROLLED_EXECUTION"
    assert result["workspace_studies_after_readiness"] == []


def test_p8c5_invalid_p5_preflight_blocks_all_scopes_without_inspecting_stale_model():
    manifest = _manifest()
    manifest["protection"]["tcc_datasets"][0]["curve_id"] = "WRONG-CURVE"

    result = real_integrated_readiness.evaluar_readiness_integral(manifest)

    assert result["materialization_layer"] == "P8C4B"
    assert result["materialization_ok"] is False
    assert result["readiness_status"] == "BLOCKED"
    assert result["ready_scopes"] == []
    assert set(result["blocked_scopes"]) == set(manifest["requested_scope"])
    for scope, view in result["scope_readiness"].items():
        assert view["status"] == "BLOCKED"
        assert view["issues"][0]["code"] == "P8C5M001"
    assert result["studies_executed"] == []


def test_p8c5_missing_voltage_drop_limit_blocks_only_voltage_drop():
    manifest = _manifest()
    del manifest["study_inputs"]["voltage_drop_limit_pct"]

    result = real_integrated_readiness.evaluar_readiness_integral(manifest)

    assert result["scope_readiness"]["POWER_FLOW"]["status"] == "READY"
    voltage = result["scope_readiness"]["VOLTAGE_DROP"]
    assert voltage["status"] == "BLOCKED"
    assert any(item["code"] == "P8C3C210" for item in voltage["issues"])
    assert result["scope_readiness"]["AMPACITY"]["status"] == "READY"
    assert result["scope_readiness"]["PROTECTION_TCC"]["status"] == "READY"
    assert result["blocked_scopes"] == ["VOLTAGE_DROP"]


def test_p8c5_is_reproducible_and_readiness_does_not_leave_studies():
    manifest = _manifest()
    first = real_integrated_readiness.evaluar_readiness_integral(manifest)
    second = real_integrated_readiness.evaluar_readiness_integral(deepcopy(manifest))

    assert first["readiness_status"] == second["readiness_status"] == "READY_FOR_CONTROLLED_EXECUTION"
    assert first["ready_scopes"] == second["ready_scopes"]
    assert first["blocked_scopes"] == second["blocked_scopes"] == []
    assert first["materialization"]["p5"]["protection_fingerprint_sha256"] == second["materialization"]["p5"]["protection_fingerprint_sha256"]
    assert workspace_state.status()["studies"] == {}