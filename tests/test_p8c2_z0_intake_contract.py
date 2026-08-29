from __future__ import annotations

from copy import deepcopy

from mcp_electrico import real_pilot_intake


def _manifest() -> dict:
    return {
        "project": {
            "id": "P8C2-Z0",
            "name": "Piloto contrato Z0",
            "source_reference": "Expediente Z0 REV-A",
        },
        "requested_scope": ["IEC60909_1PH_GROUND_MAX_MIN"],
        "source": {
            "bus": "red_mt",
            "kv_ll": 22.9,
            "scc_max_mva": 350.0,
            "x_r_max": 10.0,
            "scc_min_mva": 180.0,
            "x_r_min": 6.0,
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
            }],
            "lines": [{
                "id": "Line.feeder",
                "bus1": "tgbt",
                "bus2": "load_bus",
                "phases": 3,
                "length_km": 0.05,
                "r1_ohm_km": 0.12,
                "x1_ohm_km": 0.08,
                "endtemp_min_c": 90.0,
            }],
            "loads": [{
                "id": "Load.load1",
                "bus": "load_bus",
                "phases": 3,
                "kv": 0.48,
                "kw": 250.0,
                "kvar": 80.0,
            }],
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
                "magnetizing_z0_ratio_percent": 100.0,
                "magnetizing_r_over_x": 0.0,
                "leakage_share_hv": 0.5,
                "neutral_side": "lv",
                "neutral_mode": "solid",
            }],
        },
    }


def _codes(manifest: dict) -> set[str]:
    return {item["code"] for item in real_pilot_intake.evaluar_admision(manifest)["issues"]}


def test_p8c2_complete_z0_contract_is_ready_to_build():
    result = real_pilot_intake.evaluar_admision(_manifest())
    assert result["ready_to_build_model"] is True
    assert result["issues"] == []
    assert result["electrical_calculation_performed"] is False
    assert result["model_mutation_performed"] is False


def test_p8c2_transformer_requires_all_pandapower_z0_projection_fields():
    manifest = _manifest()
    trafo = manifest["zero_sequence"]["transformers"][0]
    for key in ("magnetizing_z0_ratio_percent", "magnetizing_r_over_x", "leakage_share_hv"):
        del trafo[key]

    result = real_pilot_intake.evaluar_admision(manifest)
    assert result["ready_to_build_model"] is False
    paths = {item["path"] for item in result["issues"] if item["code"] == "P8B_Z021"}
    assert "zero_sequence.transformers[0].magnetizing_z0_ratio_percent" in paths
    assert "zero_sequence.transformers[0].magnetizing_r_over_x" in paths
    assert "zero_sequence.transformers[0].leakage_share_hv" in paths


def test_p8c2_transformer_rejects_contradictory_impedance_and_leakage_share():
    manifest = _manifest()
    trafo = manifest["zero_sequence"]["transformers"][0]
    trafo["uk0_percent"] = 5.0
    trafo["ur0_percent"] = 5.5
    trafo["leakage_share_hv"] = 1.2
    codes = _codes(manifest)
    assert "P8B_Z026" in codes
    assert "P8B_Z028" in codes


def test_p8c2_neutral_side_must_match_wye_winding():
    manifest = _manifest()
    manifest["zero_sequence"]["transformers"][0]["neutral_side"] = "hv"
    codes = _codes(manifest)
    assert "P8B_Z036" in codes


def test_p8c2_impedance_neutral_requires_explicit_nonzero_rx():
    manifest = _manifest()
    trafo = manifest["zero_sequence"]["transformers"][0]
    trafo["neutral_mode"] = "impedance"
    codes = _codes(manifest)
    assert "P8B_Z032" in codes

    trafo["rn_ohm"] = 0.0
    trafo["xn_ohm"] = 0.0
    codes = _codes(manifest)
    assert "P8B_Z034" in codes

    trafo["rn_ohm"] = 0.2
    trafo["xn_ohm"] = 0.1
    result = real_pilot_intake.evaluar_admision(manifest)
    assert result["ready_to_build_model"] is True


def test_p8c2_solid_and_ungrounded_neutral_do_not_accept_hidden_impedance():
    solid = _manifest()
    solid_trafo = solid["zero_sequence"]["transformers"][0]
    solid_trafo["rn_ohm"] = 0.2
    assert "P8B_Z031" in _codes(solid)

    ungrounded = _manifest()
    ungrounded_trafo = ungrounded["zero_sequence"]["transformers"][0]
    ungrounded_trafo["neutral_mode"] = "ungrounded"
    ungrounded_trafo["rn_ohm"] = 0.2
    assert "P8B_Z035" in _codes(ungrounded)


def test_p8c2_ground_scope_blocks_non_three_phase_line_and_zero_z0():
    manifest = _manifest()
    manifest["topology"]["lines"][0]["phases"] = 1
    line_z0 = manifest["zero_sequence"]["lines"][0]
    line_z0["r0_ohm_km"] = 0.0
    line_z0["x0_ohm_km"] = 0.0
    codes = _codes(manifest)
    assert "P8B_Z017" in codes
    assert "P8B_Z016" in codes


def test_p8c2_source_x0_zero_is_blocked_before_p4c07():
    manifest = _manifest()
    manifest["zero_sequence"]["source"]["x0_max_ohm"] = 0.0
    result = real_pilot_intake.evaluar_admision(manifest)
    assert result["ready_to_build_model"] is False
    assert "P8B_Z002V" in {item["code"] for item in result["issues"]}


def test_p8c2_validation_is_read_only():
    manifest = _manifest()
    before = deepcopy(manifest)
    real_pilot_intake.evaluar_admision(manifest)
    assert manifest == before
