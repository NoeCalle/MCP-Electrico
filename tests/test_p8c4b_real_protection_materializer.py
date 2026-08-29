from __future__ import annotations

from copy import deepcopy

from mcp_electrico import (
    conductor_library,
    protection_curves,
    protection_data,
    real_protection_materializer,
    workspace_state,
)


def _manifest() -> dict:
    return {
        "project": {
            "id": "REAL-P5-001",
            "name": "Piloto P5 real",
            "source_reference": "SLD + expediente aprobado REV-A",
        },
        "requested_scope": ["AMPACITY", "PROTECTION_TCC"],
        "source": {
            "bus": "red_mt",
            "kv_ll": 22.9,
            "frequency_hz": 60.0,
            "pu": 1.0,
            "angle_deg": 0.0,
            "source_reference": "Utility data REV-A",
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
        "zero_sequence": {"source": {}, "lines": [], "transformers": []},
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
                        {"current_a": 4000.0, "time_min_s": 0.10, "time_max_s": 0.12}
                    ]
                }],
            }],
        },
    }


def test_p8c4b_materializes_breaker_curve_and_numeric_dataset_without_evaluation():
    result = real_protection_materializer.materializar_protecciones(_manifest())

    assert result["protection_materializer_status"] == "P5_TCC_MATERIALIZED_NOT_EXECUTED"
    assert result["p5_materialized"] is True
    assert result["electrical_calculation_performed"] is False
    assert result["ampacity_calculation_performed"] is False
    assert result["protection_calculation_performed"] is False
    assert result["tcc_evaluation_performed"] is False
    assert result["studies_executed"] == []
    assert workspace_state.status()["studies"] == {}
    assert result["professional_emission"] is False

    assert conductor_library.obtener_asignacion("Line.feeder")["origen"] == "PROJECT_DATA"
    device = protection_data.obtener_dispositivo("QF01")
    assert device is not None
    assert device["device_type"] == "circuit_breaker"
    assert device["ratings"]["icu_ka"] == 36.0
    assert device["ratings"]["ics_ka"] == 25.0
    assert device["ratings"]["breaking_capacity_ka"] is None
    assert device["curve"]["id"] == "QF01-MFR-TCC"
    assert device["curve"]["numeric_dataset_loaded"] is True
    assert device["curve"]["dataset_id"] == "QF01-TCC-DATA-REV-A"
    assert device["curve"]["tcc_execution_ready"] is True

    dataset = protection_curves.obtener_dataset("QF01-TCC-DATA-REV-A")
    assert dataset is not None
    assert dataset["shape"] == "BAND"
    assert dataset["time_semantics"] == "TOTAL_CLEARING_TIME"
    assert dataset["segments"][0]["points"][1]["time_max_s"] == 0.12

    readiness = result["p5"]["readiness"][0]
    assert readiness["breaking_capacity_ready"] is True
    assert readiness["p3_binding"]["status"] == "MATCH"
    assert readiness["tcc_data_ready"] is True
    assert result["p5"]["legacy_intake_aliases"][0]["authoritative_p5_field"] == "icu_ka"


def test_p8c4b_breaker_legacy_alias_must_equal_explicit_icu():
    manifest = _manifest()
    manifest["protection"]["devices"][0]["breaking_capacity_ka"] = 35.0

    result = real_protection_materializer.materializar_protecciones(manifest)

    assert result["protection_materializer_status"] == "BLOCKED_BY_P5_PREFLIGHT"
    assert result["engineering_materialization_performed"] is False
    assert any(item["code"] == "P8C4B013" for item in result["issues"])
    assert protection_data.snapshot()["devices"] == []
    assert protection_curves.listar_datasets() == []


def test_p8c4b_numeric_dataset_is_required_not_metadata_only():
    manifest = _manifest()
    del manifest["protection"]["tcc_datasets"][0]["segments"]

    result = real_protection_materializer.materializar_protecciones(manifest)

    assert result["protection_materializer_status"] == "BLOCKED_BY_P5_PREFLIGHT"
    assert any(item["code"] == "P8C4B050" and item["path"].endswith(".segments") for item in result["issues"])
    assert protection_data.snapshot()["devices"] == []


def test_p8c4b_curve_identity_mismatch_blocks_before_materialization():
    manifest = _manifest()
    manifest["protection"]["tcc_datasets"][0]["curve_id"] = "OTHER-CURVE"

    result = real_protection_materializer.materializar_protecciones(manifest)

    assert result["protection_materializer_status"] == "BLOCKED_BY_P5_PREFLIGHT"
    assert any(item["code"] == "P8C4B043" for item in result["issues"])
    assert protection_data.snapshot()["devices"] == []


def test_p8c4b_p5_in_must_match_p3_in_when_same_line_is_bound():
    manifest = _manifest()
    manifest["protection"]["devices"][0]["in_a"] = 380.0

    result = real_protection_materializer.materializar_protecciones(manifest)

    assert result["protection_materializer_status"] == "BLOCKED_BY_P5_PREFLIGHT"
    assert any(item["code"] == "P8C4B009" for item in result["issues"])
    assert protection_data.snapshot()["devices"] == []


def test_p8c4b_materializes_fuse_with_breaking_capacity_not_icu():
    manifest = _manifest()
    device = manifest["protection"]["devices"][0]
    device["id"] = "F01"
    device["type"] = "fuse"
    device["breaking_capacity_ka"] = 50.0
    device.pop("icu_ka")
    device.pop("ics_ka")
    device["standard_reference"] = "IEC 60269 project specification REV-A"
    device["curve_id"] = "F01-MFR-TCC"
    manifest["protection"]["tcc_datasets"][0] = {
        "device_id": "F01",
        "dataset_id": "F01-TCC-DATA-REV-A",
        "curve_id": "F01-MFR-TCC",
        "shape": "SINGLE",
        "time_semantics": "TOTAL_CLEARING_TIME",
        "source_type": "MANUFACTURER_DATASET",
        "source_reference": "Fuse manufacturer numeric TCC REV-A",
        "segments": [{
            "id": "fuse_total",
            "points": [
                {"current_a": 400.0, "time_s": 30.0},
                {"current_a": 4000.0, "time_s": 0.05}
            ]
        }],
    }

    result = real_protection_materializer.materializar_protecciones(manifest)

    assert result["protection_materializer_status"] == "P5_TCC_MATERIALIZED_NOT_EXECUTED"
    fuse = protection_data.obtener_dispositivo("F01")
    assert fuse is not None
    assert fuse["device_type"] == "fuse"
    assert fuse["ratings"]["breaking_capacity_ka"] == 50.0
    assert fuse["ratings"]["icu_ka"] is None
    assert result["p5"]["readiness"][0]["breaking_capacity_ready"] is True
    assert result["tcc_evaluation_performed"] is False


def test_p8c4b_rebuild_is_deterministic_and_keeps_workspace_unsolved():
    manifest = _manifest()
    first = real_protection_materializer.materializar_protecciones(manifest)
    second = real_protection_materializer.materializar_protecciones(deepcopy(manifest))

    assert first["protection_materializer_status"] == "P5_TCC_MATERIALIZED_NOT_EXECUTED"
    assert second["protection_materializer_status"] == "P5_TCC_MATERIALIZED_NOT_EXECUTED"
    assert first["p5"]["protection_fingerprint_sha256"] == second["p5"]["protection_fingerprint_sha256"]
    assert workspace_state.status()["studies"] == {}
