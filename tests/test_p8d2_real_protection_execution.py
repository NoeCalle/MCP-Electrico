from __future__ import annotations

from copy import deepcopy

from mcp_electrico import real_protection_execution, workspace_state


def _manifest() -> dict:
    return {
        "project": {
            "id": "REAL-SE-P8D2-001",
            "name": "Subestación piloto real P8D2",
            "source_reference": "SLD + expediente aprobado REV-A",
        },
        "requested_scope": [
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
                    "id": "full_range",
                    "points": [
                        {"current_a": 400.0, "time_min_s": 10.0, "time_max_s": 12.0},
                        {"current_a": 4000.0, "time_min_s": 0.10, "time_max_s": 0.12},
                        {"current_a": 40000.0, "time_min_s": 0.04, "time_max_s": 0.05},
                        {"current_a": 100000.0, "time_min_s": 0.02, "time_max_s": 0.03},
                    ],
                }],
            }],
            "fault_bindings": [{
                "device_id": "QF01",
                "fault_bus": "load_bus",
                "fault_type": "3ph",
                "case": "max",
                "current_quantity": "ikss_ka",
                "operating_voltage_kv": 0.48,
                "source_reference": "Protection fault-duty binding REV-A",
            }],
        },
        "study_inputs": {
            "voltage_drop_limit_pct": 5.0,
            "short_circuit_buses": ["load_bus"],
        },
    }


def test_p8d2_breaker_uses_explicit_3ph_max_result_and_icu():
    result = real_protection_execution.ejecutar_protecciones(_manifest())

    assert result["schema"] == "MCP_ELECTRICO_P8D2_PROTECTION_EXECUTION_V1"
    assert result["execution_status"] == "PROTECTION_EXECUTION_COMPLETED"
    assert result["p4_results_reused"] is True
    assert result["p4_recalculation_inside_p5"] is False
    assert result["automatic_fault_binding"] is False
    assert result["professional_emission"] is False
    assert result["next_gate"] == "P8E_WORKSPACE_AND_DOSSIER"

    device = result["device_results"][0]
    fault = device["fault_provenance"]
    assert device["device_id"] == "Protection.QF01"
    assert fault["fault_bus"] == "load_bus"
    assert fault["fault_type"] == "3ph"
    assert fault["case"] == "max"
    assert fault["current_quantity"] == "ikss_ka"
    assert fault["fault_current_ka"] > 0
    assert fault["automatic_target_selection"] is False

    breaking = device["breaking_capacity"]
    assert breaking["rating_used"]["type"] == "Icu"
    assert breaking["rating_used"]["value_ka"] == 36.0
    assert breaking["other_declared_ratings_not_used_for_pass"]["ics_ka"] == 25.0
    assert device["clearing_time"]["status"] == "CLEARING_TIME_READY"
    assert device["clearing_time"]["clearing_time"]["conservative_time_s"] > 0
    assert device["thermal_check"]["status"] == "NOT_REQUESTED"

    studies = workspace_state.status()["studies"]
    assert "protection_tcc" in studies
    assert studies["protection_tcc"]["valid"] is True
    assert studies["protection_tcc"]["model_revision"] == result["model_revision"]


def test_p8d2_1ph_ground_min_binding_is_explicit_and_supported():
    manifest = _manifest()
    binding = manifest["protection"]["fault_bindings"][0]
    binding["fault_type"] = "1ph-ground"
    binding["case"] = "min"

    result = real_protection_execution.ejecutar_protecciones(manifest)

    assert result["execution_status"] == "PROTECTION_EXECUTION_COMPLETED"
    fault = result["device_results"][0]["fault_provenance"]
    assert fault["fault_type"] == "1ph-ground"
    assert fault["case"] == "min"
    assert fault["fault_bus"] == "load_bus"
    assert fault["fault_current_ka"] > 0
    assert result["automatic_fault_binding"] is False


def test_p8d2_fuse_uses_fuse_breaking_capacity_not_icu_semantics():
    manifest = _manifest()
    manifest["protection"]["devices"] = [{
        "id": "FU01",
        "type": "fuse",
        "protected_element": "Line.feeder",
        "in_a": 400.0,
        "ue_kv": 0.48,
        "breaking_capacity_ka": 50.0,
        "standard_reference": "IEC 60269 project specification REV-A",
        "source_reference": "Approved fuse schedule REV-A",
        "manufacturer": "PROJECT_MANUFACTURER",
        "model": "PROJECT_FUSE_400A",
        "poles": 3,
        "curve_id": "FU01-MFR-TCC",
        "curve_type": "MANUFACTURER_TCC",
        "curve_source_reference": "Manufacturer fuse TCC REV-A",
        "curve_revision": "REV-A",
    }]
    manifest["protection"]["tcc_datasets"] = [{
        "device_id": "FU01",
        "dataset_id": "FU01-TCC-DATA-REV-A",
        "curve_id": "FU01-MFR-TCC",
        "shape": "BAND",
        "time_semantics": "TOTAL_CLEARING_TIME",
        "source_type": "MANUFACTURER_DATASET",
        "source_reference": "Manufacturer fuse TCC numeric data REV-A",
        "revision": "REV-A",
        "segments": [{
            "id": "full_range",
            "points": [
                {"current_a": 400.0, "time_min_s": 8.0, "time_max_s": 10.0},
                {"current_a": 4000.0, "time_min_s": 0.08, "time_max_s": 0.10},
                {"current_a": 40000.0, "time_min_s": 0.03, "time_max_s": 0.04},
                {"current_a": 100000.0, "time_min_s": 0.015, "time_max_s": 0.02},
            ],
        }],
    }]
    manifest["protection"]["fault_bindings"] = [{
        "device_id": "FU01",
        "fault_bus": "load_bus",
        "fault_type": "3ph",
        "case": "max",
        "current_quantity": "ikss_ka",
        "operating_voltage_kv": 0.48,
        "source_reference": "Fuse fault-duty binding REV-A",
    }]

    result = real_protection_execution.ejecutar_protecciones(manifest)

    assert result["execution_status"] == "PROTECTION_EXECUTION_COMPLETED"
    breaking = result["device_results"][0]["breaking_capacity"]
    assert breaking["rating_used"]["type"] == "breaking_capacity"
    assert breaking["rating_used"]["value_ka"] == 50.0
    assert breaking["other_declared_ratings_not_used_for_pass"]["ics_ka"] is None
    assert breaking["other_declared_ratings_not_used_for_pass"]["icw_ka"] is None


def test_p8d2_missing_binding_blocks_before_electrical_execution_and_clears_stale_workspace():
    seeded = real_protection_execution.ejecutar_protecciones(_manifest())
    assert seeded["execution_status"] == "PROTECTION_EXECUTION_COMPLETED"
    assert workspace_state.status()["studies"]

    manifest = _manifest()
    manifest["protection"].pop("fault_bindings")
    result = real_protection_execution.ejecutar_protecciones(manifest)

    assert result["execution_status"] == "BLOCKED_BY_EXPLICIT_FAULT_BINDING"
    assert result["p8d1_execution"] is None
    assert result["electrical_calculation_performed"] is False
    assert result["protection_calculation_performed"] is False
    assert result["automatic_fault_binding"] is False
    assert result["next_gate"] == "P8D2_REPAIR_EXPLICIT_FAULT_BINDING"
    assert workspace_state.status()["studies"] == {}


def test_p8d2_binding_bus_must_exist_in_p4_executed_targets():
    manifest = _manifest()
    manifest["protection"]["fault_bindings"][0]["fault_bus"] = "tgbt"

    result = real_protection_execution.ejecutar_protecciones(manifest)

    assert result["execution_status"] == "BLOCKED_BY_EXPLICIT_FAULT_BINDING"
    assert result["electrical_calculation_performed"] is True
    assert result["protection_calculation_performed"] is False
    assert any(issue["code"] == "P8D2R002" for issue in result["issues"])
    assert "protection_tcc" not in workspace_state.status()["studies"]


def test_p8d2_binding_does_not_silently_select_between_multiple_p4_targets():
    manifest = _manifest()
    manifest["study_inputs"]["short_circuit_buses"] = ["tgbt", "load_bus"]

    result = real_protection_execution.ejecutar_protecciones(manifest)

    assert result["execution_status"] == "PROTECTION_EXECUTION_COMPLETED"
    p4 = result["p8d1_execution"]["results"]["IEC60909_3PH_MAX_MIN"]
    assert p4["target_count"] == 2
    fault = result["device_results"][0]["fault_provenance"]
    assert fault["fault_bus"] == "load_bus"
    assert fault["automatic_target_selection"] is False


def test_p8d2_rejects_non_ikss_current_quantity_before_p8d1():
    manifest = _manifest()
    manifest["protection"]["fault_bindings"][0]["current_quantity"] = "ip_ka"

    result = real_protection_execution.ejecutar_protecciones(manifest)

    assert result["execution_status"] == "BLOCKED_BY_EXPLICIT_FAULT_BINDING"
    assert result["p8d1_execution"] is None
    assert any(issue["code"] == "P8D2B013" for issue in result["issues"])
    assert result["automatic_fault_binding"] is False


def test_p8d2_tcc_out_of_domain_is_partial_and_not_promoted_to_workspace_p5():
    manifest = _manifest()
    manifest["protection"]["tcc_datasets"][0]["segments"][0]["points"] = [
        {"current_a": 400.0, "time_min_s": 10.0, "time_max_s": 12.0},
        {"current_a": 500.0, "time_min_s": 8.0, "time_max_s": 9.0},
    ]

    result = real_protection_execution.ejecutar_protecciones(manifest)

    assert result["execution_status"] == "PROTECTION_EXECUTION_PARTIAL_TCC_NOT_READY"
    assert result["device_results"][0]["clearing_time"]["status"] == "CLEARING_TIME_NOT_READY"
    assert result["workspace_study_recorded"] is False
    assert result["next_gate"] == "P8D2_TCC_REPAIR"
    assert "protection_tcc" not in workspace_state.status()["studies"]


def test_p8d2_model_revision_is_unchanged_by_protection_execution():
    manifest = _manifest()
    result = real_protection_execution.ejecutar_protecciones(deepcopy(manifest))

    assert result["execution_status"] == "PROTECTION_EXECUTION_COMPLETED"
    assert result["model_revision"] == result["p8d1_execution"]["model_revision"]
    assert workspace_state.status()["model_revision"] == result["model_revision"]
    assert result["professional_emission"] is False
