from __future__ import annotations

from copy import deepcopy

from opendssdirect import dss

from mcp_electrico import (
    conductor_library,
    core,
    professional_data,
    protection_data,
    real_model_materializer,
    workspace_state,
    zero_sequence,
)


def _manifest(*, explicit_optional: bool = True) -> dict:
    transformer = {
        "id": "Transformer.tr01",
        "bus_hv": "red_mt",
        "bus_lv": "tgbt",
        "kva": 1000.0,
        "kv_hv": 22.9,
        "kv_lv": 0.48,
        "uk_percent": 6.0,
        "vector_group": "Dyn11",
        "x_r": 10.0,
        "source_reference": "TR nameplate REV-A",
    }
    line = {
        "id": "Line.feeder",
        "bus1": "tgbt",
        "bus2": "load_bus",
        "phases": 3,
        "length_km": 0.05,
        "r1_ohm_km": 0.12,
        "x1_ohm_km": 0.08,
        "endtemp_min_c": 90.0,
        "source_reference": "Cable schedule REV-A",
    }
    load = {
        "id": "Load.load1",
        "bus": "load_bus",
        "phases": 3,
        "kv": 0.48,
        "kw": 250.0,
        "kvar": 80.0,
        "source_reference": "Load list REV-A",
    }
    source = {
        "bus": "red_mt",
        "kv_ll": 22.9,
        "frequency_hz": 60.0,
        "scc_max_mva": 350.0,
        "x_r_max": 10.0,
        "scc_min_mva": 180.0,
        "x_r_min": 6.0,
        "source_reference": "Utility study REV-A",
    }
    if explicit_optional:
        source.update({"pu": 1.0, "angle_deg": 0.0})
        transformer.update({
            "no_load_loss_kw": 1.8,
            "i0_percent": 0.6,
            "tap_side": "hv",
            "tap_neutral": 0,
            "tap_min": -2,
            "tap_max": 2,
            "tap_step_percent": 2.5,
            "tap_pos": 0,
        })
        line["c1_nf_km"] = 0.0
        load.update({"connection": "wye", "model": 1})

    return {
        "project": {
            "id": "REAL-SE-001",
            "name": "Subestación piloto real",
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
        "source": source,
        "topology": {
            "buses": ["red_mt", "tgbt", "load_bus"],
            "transformers": [transformer],
            "lines": [line],
            "loads": [load],
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
    }


def _source_bus() -> str:
    dss("? Vsource.source.bus1")
    return str(dss.Text.Result() or "").split(".")[0].lower()


def test_p8c3b_p8b_blocker_does_not_mutate_existing_model():
    core.crear_circuito("preexisting", 0.4)
    before = dss.Circuit.Name()
    manifest = _manifest()
    manifest["project"]["source_reference"] = None

    result = real_model_materializer.materializar_modelo(manifest)

    assert result["materializer_status"] == "BLOCKED_BY_P8B_INTAKE"
    assert result["model_mutation_performed"] is False
    assert dss.Circuit.Name() == before


def test_p8c3b_frequency_is_explicit_and_blocks_before_clear():
    core.crear_circuito("preexisting_frequency", 0.4)
    before = dss.Circuit.Name()
    manifest = _manifest()
    del manifest["source"]["frequency_hz"]

    result = real_model_materializer.materializar_modelo(manifest)

    assert result["p8b_intake_status"] == "READY_TO_BUILD_MODEL"
    assert result["materializer_status"] == "BLOCKED_BY_MATERIALIZER_PREFLIGHT"
    assert result["model_mutation_performed"] is False
    assert any(item["code"] == "P8C3B001" for item in result["issues"])
    assert dss.Circuit.Name() == before


def test_p8c3b_builds_custom_source_open_dss_p2_and_z0_without_solving():
    manifest = _manifest(explicit_optional=True)
    result = real_model_materializer.materializar_modelo(manifest)

    assert result["materializer_status"] == "MODEL_BUILT_NOT_EXECUTED"
    assert result["model_mutation_performed"] is True
    assert result["ready_for_engine_preflight"] is True
    assert result["electrical_calculation_performed"] is False
    assert result["studies_executed"] == []
    assert result["automatic_defaults"] is False
    assert result["automatic_dispatch"] is False
    assert result["crosscheck"] is False
    assert result["professional_emission"] is False

    assert _source_bus() == "red_mt"
    buses = {str(item).lower() for item in dss.Circuit.AllBusNames()}
    assert "red_mt" in buses
    assert "sourcebus" not in buses
    assert {name.lower() for name in dss.Transformers.AllNames()} == {"tr01"}
    assert {name.lower() for name in dss.Lines.AllNames()} == {"feeder"}
    assert {name.lower() for name in dss.Loads.AllNames()} == {"load1"}

    p2 = professional_data.snapshot()
    assert p2["source"]["bus"] == "red_mt"
    assert p2["source"]["scenarios"]["max"]["scc3_mva"] == 350.0
    assert p2["transformers"][0]["vector_group"]["grupo_vectorial"] == "Dyn11"
    assert p2["transformers"][0]["losses"]["no_load_loss_kw"] == 1.8
    assert p2["transformers"][0]["tap"]["enabled"] is True

    z0 = zero_sequence.snapshot()
    assert z0["source"]["status"] == "EXPLICIT"
    assert z0["lines"][0]["element"] == "Line.feeder"
    assert z0["transformers"][0]["element"] == "Transformer.tr01"
    assert result["engine_defaults_retained_count"] == 0
    assert workspace_state.status()["studies"] == {}


def test_p8c3b_exposes_engine_defaults_instead_of_inventing_optional_data():
    result = real_model_materializer.materializar_modelo(_manifest(explicit_optional=False))

    assert result["materializer_status"] == "MODEL_BUILT_NOT_EXECUTED"
    assert result["automatic_defaults"] is False
    assert result["engine_defaults_retained_count"] > 0
    paths = {item["path"] for item in result["engine_defaults_retained"]}
    assert "source.pu" in paths
    assert "topology.lines[0].c1_nf_km" in paths
    assert "topology.loads[0].model" in paths
    assert any(path.endswith(".tap") for path in paths)
    assert result["p2"]["transformers"][0]["losses"]["no_load_loss_kw"] is None


def test_p8c3b_preflight_rejects_unsupported_vector_group_before_mutation():
    core.crear_circuito("preexisting_vector", 0.4)
    before = dss.Circuit.Name()
    manifest = _manifest()
    manifest["topology"]["transformers"][0]["vector_group"] = "Dz0"

    result = real_model_materializer.materializar_modelo(manifest)

    assert result["materializer_status"] == "BLOCKED_BY_MATERIALIZER_PREFLIGHT"
    assert result["model_mutation_performed"] is False
    assert any(item["code"] == "P8C3B009" for item in result["issues"])
    assert dss.Circuit.Name() == before


def test_p8c3b_rebuild_same_project_clears_stale_p3_p5_and_is_reproducible():
    manifest = _manifest(explicit_optional=True)
    first = real_model_materializer.materializar_modelo(manifest)
    assert first["materializer_status"] == "MODEL_BUILT_NOT_EXECUTED"

    conductor_library.aplicar_conductor(
        "Line.feeder",
        "NEXANS-N2XSY-18-30-CU-70-PH16",
        "air_trefoil_30c",
    )
    protection_data.definir_dispositivo(
        nombre="QF_STALE",
        tipo="circuit_breaker",
        elemento_protegido="Line.feeder",
        in_a=400.0,
        ue_kv=0.48,
        polos=3,
        norma_referencia="TEST ONLY",
        icu_ka=36.0,
        fuente_referencia="TEST ONLY",
    )
    assert conductor_library.obtener_asignacion("Line.feeder") is not None
    assert len(protection_data.snapshot()["devices"]) == 1

    second = real_model_materializer.materializar_modelo(deepcopy(manifest))

    assert second["materializer_status"] == "MODEL_BUILT_NOT_EXECUTED"
    assert second["circuit_name"] == first["circuit_name"]
    assert second["manifest_sha256"] == first["manifest_sha256"]
    assert second["materialized_fingerprint_sha256"] == first["materialized_fingerprint_sha256"]
    assert conductor_library.obtener_asignacion("Line.feeder") is None
    assert protection_data.snapshot()["devices"] == []
    assert "conductor_library" in second["runtime_resets"]
    assert "protection_data" in second["runtime_resets"]
