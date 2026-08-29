from __future__ import annotations

from copy import deepcopy

from mcp_electrico import real_pilot_intake


def _complete_manifest() -> dict:
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
        "source": {
            "kv_ll": 22.9,
            "scc_max_mva": 350.0,
            "x_r_max": 10.0,
            "scc_min_mva": 180.0,
            "x_r_min": 6.0,
        },
        "topology": {
            "buses": ["sourcebus", "se_mt", "tgbt", "load_bus"],
            "transformers": [{
                "id": "Transformer.tr01",
                "bus_hv": "se_mt",
                "bus_lv": "tgbt",
                "kva": 1000.0,
                "kv_hv": 22.9,
                "kv_lv": 0.48,
                "uk_percent": 6.0,
                "vector_group": "Dyn11",
                "x_r": 10.0,
            }],
            "lines": [{
                "id": "Line.feeder",
                "bus1": "tgbt",
                "bus2": "load_bus",
                "length_km": 0.05,
                "r1_ohm_km": 0.12,
                "x1_ohm_km": 0.08,
                "endtemp_min_c": 90.0,
            }],
            "loads": [{"id": "Load.load1", "bus": "load_bus", "kw": 250.0, "kvar": 80.0}],
        },
        "zero_sequence": {
            "source": {
                "r0_max_ohm": 0.15,
                "x0_max_ohm": 0.45,
                "r0_min_ohm": 0.25,
                "x0_min_ohm": 0.80,
            },
            "lines": [{
                "id": "Line.feeder",
                "r0_ohm_km": 0.36,
                "x0_ohm_km": 0.15,
                "c0_nf_km": 100.0,
            }],
            "transformers": [{
                "id": "Transformer.tr01",
                "uk0_percent": 5.5,
                "ur0_percent": 0.6,
                "neutral_side": "lv",
                "neutral_mode": "solid",
            }],
        },
        "ampacity": [{
            "element_id": "Line.feeder",
            "conductor_code": "PROJECT-CABLE-01",
            "ib_a": 350.0,
            "in_a": 400.0,
            "installation_reference": "Cable schedule + installation detail REV-A",
            "ampacity_reference": "Manufacturer datasheet / applicable table",
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


def test_p8b_complete_manifest_is_ready_only_for_model_build():
    result = real_pilot_intake.evaluar_admision(_complete_manifest())
    assert result["schema"] == "MCP_ELECTRICO_P8B_REAL_PILOT_INTAKE_V1"
    assert result["intake_status"] == "READY_TO_BUILD_MODEL"
    assert result["ready_to_build_model"] is True
    assert result["issues"] == []
    assert all(item["status"] == "INPUTS_PRESENT" for item in result["study_input_readiness"].values())
    assert all(item["engineering_execution_claim"] is False for item in result["study_input_readiness"].values())
    assert result["electrical_calculation_performed"] is False
    assert result["model_mutation_performed"] is False
    assert result["automatic_defaults"] is False
    assert result["automatic_dispatch"] is False
    assert result["crosscheck"] is False
    assert result["professional_emission"] is False


def test_p8b_ground_fault_blocks_without_explicit_zero_sequence():
    manifest = _complete_manifest()
    manifest.pop("zero_sequence")
    result = real_pilot_intake.evaluar_admision(manifest)
    assert result["intake_status"] == "BLOCKED_MISSING_INPUTS"
    assert result["ready_to_build_model"] is False
    assert result["study_input_readiness"]["IEC60909_1PH_GROUND_MAX_MIN"]["status"] == "MISSING_INPUTS"
    paths = {item["path"] for item in result["issues"]}
    assert "zero_sequence.source.r0_max_ohm" in paths
    assert "zero_sequence.lines" in paths
    assert "zero_sequence.transformers" in paths


def test_p8b_min_short_circuit_never_invents_line_temperature():
    manifest = _complete_manifest()
    del manifest["topology"]["lines"][0]["endtemp_min_c"]
    result = real_pilot_intake.evaluar_admision(manifest)
    assert result["ready_to_build_model"] is False
    issue = next(item for item in result["issues"] if item["code"] == "P8B_SC21")
    assert issue["path"].endswith("endtemp_min_c")
    assert "no se inventa" in issue["message"]


def test_p8b_protection_requires_traceable_device_and_tcc_metadata():
    manifest = _complete_manifest()
    manifest["protection"]["devices"][0]["source_reference"] = None
    manifest["protection"]["tcc_datasets"][0]["source_reference"] = None
    result = real_pilot_intake.evaluar_admision(manifest)
    assert result["ready_to_build_model"] is False
    p5 = result["study_input_readiness"]["PROTECTION_TCC"]
    assert p5["status"] == "MISSING_INPUTS"
    missing = {item["path"] for item in p5["missing"]}
    assert "protection.devices[0].source_reference" in missing
    assert "protection.tcc_datasets[0].source_reference" in missing


def test_p8b_unknown_scope_fails_closed_without_changing_manifest():
    manifest = _complete_manifest()
    before = deepcopy(manifest)
    manifest["requested_scope"].append("ARC_FLASH_IEEE1584")
    result = real_pilot_intake.evaluar_admision(manifest)
    assert result["ready_to_build_model"] is False
    assert any(item["code"] == "P8B_SCOPE01" for item in result["issues"])
    assert "ARC_FLASH_IEEE1584" not in real_pilot_intake.ALLOWED_SCOPE
    assert before["source"] == manifest["source"]
    assert result["professional_emission"] is False


def test_p8b_empty_requested_scope_has_explicit_blocker():
    manifest = _complete_manifest()
    manifest["requested_scope"] = []
    result = real_pilot_intake.evaluar_admision(manifest)
    assert result["ready_to_build_model"] is False
    issue = next(item for item in result["issues"] if item["code"] == "P8B_SCOPE00")
    assert issue["path"] == "requested_scope"
    assert result["study_input_readiness"] == {}


def test_p8b_obviously_invalid_source_values_fail_closed():
    manifest = _complete_manifest()
    manifest["source"]["kv_ll"] = -22.9
    manifest["source"]["scc_max_mva"] = 0
    manifest["source"]["x_r_min"] = -1
    result = real_pilot_intake.evaluar_admision(manifest)
    assert result["ready_to_build_model"] is False
    codes = {item["code"] for item in result["issues"]}
    assert "P8B_BASE_09" in codes
    assert "P8B_SC01V" in codes
    assert "P8B_SC04V" in codes
    assert result["electrical_calculation_performed"] is False
    assert result["model_mutation_performed"] is False


def test_p8b_invalid_passive_line_values_fail_closed():
    manifest = _complete_manifest()
    line = manifest["topology"]["lines"][0]
    line["length_km"] = 0
    line["r1_ohm_km"] = -0.1
    result = real_pilot_intake.evaluar_admision(manifest)
    assert result["ready_to_build_model"] is False
    codes = {item["code"] for item in result["issues"]}
    assert "P8B_SC22" in codes
    assert "P8B_SC23" in codes
