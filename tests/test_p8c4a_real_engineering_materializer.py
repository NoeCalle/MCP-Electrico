from __future__ import annotations

from copy import deepcopy

from opendssdirect import dss

from mcp_electrico import (
    ampacity,
    conductor_library,
    protection_data,
    real_engineering_materializer,
    workspace_state,
)


def _manifest() -> dict:
    return {
        "project": {
            "id": "REAL-P3-001",
            "name": "Piloto P3 real",
            "source_reference": "SLD + expediente aprobado REV-A",
        },
        "requested_scope": ["AMPACITY"],
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
        "protection": {"devices": [], "tcc_datasets": []},
    }


def test_p8c4a_materializes_project_conductor_and_p3_without_calculation():
    result = real_engineering_materializer.materializar_datos_ingenieria(_manifest())

    assert result["engineering_materializer_status"] == "P3_MATERIALIZED_P5_PENDING"
    assert result["p3_materialized"] is True
    assert result["p5_materialized"] is False
    assert result["electrical_calculation_performed"] is False
    assert result["ampacity_calculation_performed"] is False
    assert result["protection_calculation_performed"] is False
    assert result["studies_executed"] == []
    assert workspace_state.status()["studies"] == {}
    assert result["automatic_defaults"] is False
    assert result["automatic_dispatch"] is False
    assert result["crosscheck"] is False
    assert result["professional_emission"] is False

    assignment = conductor_library.obtener_asignacion("Line.feeder")
    assert assignment is not None
    assert assignment["codigo"] == "PROJECT-CABLE-01"
    assert assignment["origen"] == "PROJECT_DATA"
    assert assignment["ampacidad_aplicada_a"] == 500.0
    assert assignment["impedancia_actualizada"] is False
    assert assignment["fuente"]["reference"] == "Approved cable ampacity calculation REV-A"

    dss.Lines.Name("feeder")
    assert abs(float(dss.Lines.R1()) - 0.12) < 1e-12
    assert abs(float(dss.Lines.X1()) - 0.08) < 1e-12
    assert abs(float(dss.CktElement.NormalAmps()) - 500.0) < 1e-9

    profile = ampacity.obtener_condiciones("Line.feeder")
    assert profile is not None
    assert profile["norm"]["id"] == "IEC_60364_5_52_2009_A1_2024"
    assert profile["base"]["ampacity_a"] == 500.0
    assert profile["design_current"]["ib_a"] == 350.0
    assert profile["design_current"]["reference"] == "Load list + feeder sizing REV-A"
    assert profile["protection"]["in_a"] == 400.0
    assert profile["protection"]["reference"] == "Protection schedule REV-A"
    assert profile["correction"]["mode"] == "BASE_CONDITIONS_CONFIRMED"
    assert profile["correction"]["factor_total"] == 1.0
    assert protection_data.snapshot()["devices"] == []


def test_p8c4a_manual_factor_is_explicit_and_not_assumed():
    manifest = _manifest()
    item = manifest["ampacity"][0]
    item["base_conditions_confirmed"] = False
    item["factors"] = [{
        "id": "project_derating",
        "value": 0.91,
        "reference": "Approved derating calculation REV-A",
        "condition": "Project-specific grouping/temperature correction",
    }]

    result = real_engineering_materializer.materializar_datos_ingenieria(manifest)

    assert result["engineering_materializer_status"] == "P3_MATERIALIZED_P5_PENDING"
    profile = ampacity.obtener_condiciones("Line.feeder")
    assert profile is not None
    assert profile["correction"]["mode"] == "EXPLICIT_FACTORS"
    assert profile["correction"]["factor_total"] == 0.91
    assert profile["correction"]["factors"][0]["reference"] == "Approved derating calculation REV-A"


def test_p8c4a_missing_base_ampacity_blocks_before_any_p3_assignment():
    manifest = _manifest()
    del manifest["ampacity"][0]["base_ampacity_a"]

    result = real_engineering_materializer.materializar_datos_ingenieria(manifest)

    assert result["model_materialization_status"] == "MODEL_BUILT_NOT_EXECUTED"
    assert result["engineering_materializer_status"] == "BLOCKED_BY_P3_PREFLIGHT"
    assert result["p3_materialized"] is False
    assert any(item["code"] == "P8C4A003" for item in result["issues"])
    assert conductor_library.snapshot_asignaciones()["alimentadores"] == {}
    assert ampacity.obtener_condiciones("Line.feeder") is None


def test_p8c4a_requires_factors_or_explicit_base_condition_confirmation():
    manifest = _manifest()
    manifest["ampacity"][0]["base_conditions_confirmed"] = False
    manifest["ampacity"][0]["factors"] = []

    result = real_engineering_materializer.materializar_datos_ingenieria(manifest)

    assert result["engineering_materializer_status"] == "BLOCKED_BY_P3_PREFLIGHT"
    assert any(item["code"] == "P8C4A010" for item in result["issues"])
    assert conductor_library.snapshot_asignaciones()["alimentadores"] == {}


def test_p8c4a_unknown_norm_blocks_atomically():
    manifest = _manifest()
    manifest["ampacity"][0]["norm_id"] = "UNKNOWN_PROJECT_NORM"

    result = real_engineering_materializer.materializar_datos_ingenieria(manifest)

    assert result["engineering_materializer_status"] == "BLOCKED_BY_P3_PREFLIGHT"
    assert any(item["code"] == "P8C4A008" for item in result["issues"])
    assert conductor_library.snapshot_asignaciones()["alimentadores"] == {}


def test_p8c4a_duplicate_element_blocks_before_mutation():
    manifest = _manifest()
    manifest["ampacity"].append(deepcopy(manifest["ampacity"][0]))

    result = real_engineering_materializer.materializar_datos_ingenieria(manifest)

    assert result["engineering_materializer_status"] == "BLOCKED_BY_P3_PREFLIGHT"
    assert any(item["code"] == "P8C4A004" for item in result["issues"])
    assert conductor_library.snapshot_asignaciones()["alimentadores"] == {}


def test_p8c4a_rebuild_is_deterministic_and_does_not_create_p5_state():
    manifest = _manifest()
    first = real_engineering_materializer.materializar_datos_ingenieria(manifest)
    second = real_engineering_materializer.materializar_datos_ingenieria(deepcopy(manifest))

    assert first["engineering_materializer_status"] == "P3_MATERIALIZED_P5_PENDING"
    assert second["engineering_materializer_status"] == "P3_MATERIALIZED_P5_PENDING"
    assert first["model_fingerprint_sha256"] == second["model_fingerprint_sha256"]
    assert first["p3"]["engineering_fingerprint_sha256"] == second["p3"]["engineering_fingerprint_sha256"]
    assert protection_data.snapshot()["devices"] == []
    assert workspace_state.status()["studies"] == {}
