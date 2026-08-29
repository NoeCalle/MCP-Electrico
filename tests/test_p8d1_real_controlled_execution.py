from __future__ import annotations

from copy import deepcopy

from mcp_electrico import real_controlled_execution, workspace_state


def _manifest(requested_scope: list[str] | None = None) -> dict:
    return {
        "project": {
            "id": "REAL-SE-P8D1-001",
            "name": "Subestación piloto real P8D1",
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


def test_p8d1_executes_p1_p3_p4_and_leaves_p5_explicitly_pending():
    result = real_controlled_execution.ejecutar_controlado(_manifest())

    assert result["schema"] == "MCP_ELECTRICO_P8D1_CONTROLLED_EXECUTION_V1"
    assert result["execution_status"] == "CONTROLLED_EXECUTION_COMPLETED_WITH_P5_PENDING"
    assert result["readiness"]["readiness_status"] == "READY_FOR_CONTROLLED_EXECUTION"
    assert result["pending_scopes"] == ["PROTECTION_TCC"]
    assert result["next_gate"] == "P8D2_EXPLICIT_P5_FAULT_BINDING"

    expected = [
        "POWER_FLOW",
        "VOLTAGE_DROP",
        "AMPACITY",
        "IEC60909_3PH_MAX_MIN",
        "IEC60909_1PH_GROUND_MAX_MIN",
    ]
    assert result["executed_scopes"] == expected
    assert result["results"]["POWER_FLOW"]["powerflow"]["convergio"] is True
    assert result["results"]["AMPACITY"]["status"] == "CUMPLE"
    assert result["results"]["AMPACITY"]["alimentadores"][0]["base_evidence"]["origin"] == "P2_PROJECT"

    three = result["results"]["IEC60909_3PH_MAX_MIN"]
    assert three["target_count"] == 1
    assert three["targets"][0]["bus"] == "load_bus"
    assert three["targets"][0]["result"]["ok"] is True
    assert three["targets"][0]["result"]["scenarios"]["max"]["results"]["ikss_ka"] > 0
    assert three["targets"][0]["result"]["scenarios"]["min"]["results"]["ikss_ka"] > 0

    one = result["results"]["IEC60909_1PH_GROUND_MAX_MIN"]
    assert one["target_count"] == 1
    assert one["targets"][0]["result"]["max"]["ok"] is True
    assert one["targets"][0]["result"]["min"]["ok"] is True

    assert result["results"]["PROTECTION_TCC"]["status"] == "PENDING_P8D2_EXPLICIT_FAULT_BINDING"
    assert result["results"]["PROTECTION_TCC"]["automatic_fault_binding"] is False
    assert result["protection_calculation_performed"] is False
    assert result["automatic_dispatch"] is False
    assert result["automatic_fault_binding"] is False
    assert result["crosscheck"] is False
    assert result["professional_emission"] is False

    studies = workspace_state.status()["studies"]
    for name in ("powerflow", "flow", "voltage_drop", "ampacity", "iec60909_3ph", "iec60909_1ph_ground"):
        assert name in studies
        assert studies[name]["valid"] is True
    assert not any(name.startswith("protection_") for name in studies)


def test_p8d1_without_p5_finishes_and_routes_to_p8e():
    manifest = _manifest([
        "POWER_FLOW",
        "VOLTAGE_DROP",
        "AMPACITY",
        "IEC60909_3PH_MAX_MIN",
        "IEC60909_1PH_GROUND_MAX_MIN",
    ])
    result = real_controlled_execution.ejecutar_controlado(manifest)

    assert result["execution_status"] == "CONTROLLED_EXECUTION_COMPLETED"
    assert result["pending_scopes"] == []
    assert result["next_gate"] == "P8E_WORKSPACE_AND_DOSSIER"
    assert result["electrical_calculation_performed"] is True
    assert result["ampacity_calculation_performed"] is True
    assert result["short_circuit_calculation_performed"] is True


def test_p8d1_readiness_blocker_prevents_all_studies():
    manifest = _manifest()
    manifest["source"]["frequency_hz"] = None

    result = real_controlled_execution.ejecutar_controlado(manifest)

    assert result["execution_status"] == "BLOCKED_BY_READINESS"
    assert result["executed_scopes"] == []
    assert result["electrical_calculation_performed"] is False
    assert result["ampacity_calculation_performed"] is False
    assert result["short_circuit_calculation_performed"] is False
    assert result["protection_calculation_performed"] is False
    assert result["next_gate"] == "P8C5_READINESS_REPAIR"
    assert workspace_state.status()["studies"] == {}


def test_p8d1_multiple_fault_buses_executes_all_without_selecting_one_for_workspace():
    manifest = _manifest(["IEC60909_3PH_MAX_MIN", "IEC60909_1PH_GROUND_MAX_MIN"])
    manifest["study_inputs"]["short_circuit_buses"] = ["tgbt", "load_bus"]

    result = real_controlled_execution.ejecutar_controlado(manifest)

    assert result["execution_status"] == "CONTROLLED_EXECUTION_COMPLETED"
    three = result["results"]["IEC60909_3PH_MAX_MIN"]
    one = result["results"]["IEC60909_1PH_GROUND_MAX_MIN"]
    assert [item["bus"] for item in three["targets"]] == ["tgbt", "load_bus"]
    assert [item["bus"] for item in one["targets"]] == ["tgbt", "load_bus"]
    assert three["automatic_target_selection"] is False
    assert one["automatic_target_selection"] is False

    studies = workspace_state.status()["studies"]
    assert "iec60909_3ph_targets" in studies
    assert "iec60909_1ph_ground_targets" in studies
    assert "iec60909_3ph" not in studies
    assert "iec60909_1ph_ground" not in studies


def test_p8d1_rebuilds_cleanly_on_repeated_execution():
    manifest = _manifest(["POWER_FLOW", "AMPACITY", "IEC60909_3PH_MAX_MIN"])
    first = real_controlled_execution.ejecutar_controlado(manifest)
    first_revision = first["model_revision"]
    second = real_controlled_execution.ejecutar_controlado(deepcopy(manifest))

    assert first["execution_status"] == second["execution_status"] == "CONTROLLED_EXECUTION_COMPLETED"
    assert first["executed_scopes"] == second["executed_scopes"]
    assert first_revision == second["model_revision"]
    assert second["results"]["AMPACITY"]["status"] == "CUMPLE"
    assert second["professional_emission"] is False
