import json

import pytest

from mcp_electrico import ampacity_datasets, ampacity_exact_lookup, ampacity_factor_binding, p3_completion

DATASET = "PERU_CNE_UTIL_2006_TABLE_5C_GROUPING_COMPLETE_PRIMARY_V1"

EXPECTED = {
    1: (
        "grouped_air_surface_embedded_enclosed",
        "COLS_4_8_METHODS_A_TO_F",
        {"1": 1.00, "2": 0.80, "3": 0.70, "4": 0.65, "5": 0.60, "6": 0.57,
         "7": 0.54, "8": 0.52, "9": 0.50, "12": 0.45, "16": 0.41, "20": 0.38},
    ),
    2: (
        "single_layer_wall_floor_nonperforated_tray",
        "COLS_4_7_METHOD_C",
        {"1": 1.00, "2": 0.85, "3": 0.79, "4": 0.75, "5": 0.73, "6": 0.72,
         "7": 0.72, "8": 0.71, "9_or_more": 0.70},
    ),
    3: (
        "single_layer_direct_under_wood_ceiling",
        "COLS_4_7_METHOD_C",
        {"1": 0.95, "2": 0.81, "3": 0.72, "4": 0.68, "5": 0.66, "6": 0.64,
         "7": 0.63, "8": 0.62, "9_or_more": 0.61},
    ),
    4: (
        "single_layer_perforated_tray_horizontal_vertical",
        "COLS_8_9_METHODS_E_F",
        {"1": 1.00, "2": 0.88, "3": 0.82, "4": 0.77, "5": 0.75, "6": 0.73,
         "7": 0.73, "8": 0.72, "9_or_more": 0.72},
    ),
    5: (
        "single_layer_ladder_tray_support_slats",
        "COLS_8_9_METHODS_E_F",
        {"1": 1.00, "2": 0.87, "3": 0.82, "4": 0.80, "5": 0.80, "6": 0.79,
         "7": 0.79, "8": 0.78, "9_or_more": 0.78},
    ),
}


def _query(item, arrangement, reference_set, group_key):
    return {
        "table5c_item": item,
        "arrangement_id": arrangement,
        "reference_set": reference_set,
        "group_count_key": group_key,
    }


def test_dataset_5c_es_primary_verified_completo_y_shard_visible_en_catalogo():
    dataset = ampacity_datasets.obtener_dataset(DATASET)
    assert dataset["table"] == "Tabla 5C"
    assert dataset["axis"] == "grouping"
    assert dataset["provenance"]["verification_status"] == "PRIMARY_VERIFIED"
    assert dataset["usage_policy"]["professional_emission"] is True
    assert dataset["usage_policy"]["p3c11_family_coverage"] is True
    assert dataset["usage_policy"]["automatic_binding_to_iz"] is False
    assert dataset["scope"]["complete_table_verified"] is True
    assert dataset["scope"]["numeric_row_count"] == 48
    validated = ampacity_exact_lookup.validar_dataset(dataset)
    assert validated["row_count"] == 48
    assert validated["interpolation"] is False
    assert validated["extrapolation"] is False


def test_las_48_filas_publicadas_resuelven_exactamente():
    seen = 0
    for item, (arrangement, reference_set, values) in EXPECTED.items():
        for group_key, expected in values.items():
            result = ampacity_exact_lookup.resolver_catalogo(
                DATASET,
                _query(item, arrangement, reference_set, group_key),
            )
            assert result["status"] == "RESOLVED_EXACT"
            assert result["value"] == pytest.approx(expected)
            assert result["professional_emission"] is True
            assert result["interpolation"] is False
            assert result["extrapolation"] is False
            seen += 1
    assert seen == 48


def test_item1_no_inventa_columnas_intermedias_no_publicadas():
    arrangement, reference_set, _ = EXPECTED[1]
    result = ampacity_exact_lookup.resolver_catalogo(
        DATASET,
        _query(1, arrangement, reference_set, "10"),
    )
    assert result["status"] == "VALUE_NOT_TABULATED"
    assert result["value"] is None
    assert result["interpolation"] is False
    assert result["extrapolation"] is False
    assert result["professional_emission"] is False


def test_banda_9_or_more_es_regla_publicada_y_no_extrapolacion():
    for item in (2, 3, 4, 5):
        arrangement, reference_set, values = EXPECTED[item]
        result = ampacity_exact_lookup.resolver_catalogo(
            DATASET,
            _query(item, arrangement, reference_set, "9_or_more"),
        )
        assert result["value"] == pytest.approx(values["9_or_more"])
        meta = result["row_metadata"]
        assert meta["published_column"] == 9
        assert meta["normative_band_min_grouped_units"] == 9
        assert meta["categorical_rule_not_extrapolation"] is True
        assert "No más factores" in meta["source_rule"]
        assert result["extrapolation"] is False


def test_5c_exact_rows_permanece_fail_closed_para_binding_hasta_c2():
    arrangement, reference_set, _ = EXPECTED[2]
    result = ampacity_exact_lookup.resolver_catalogo(
        DATASET,
        _query(2, arrangement, reference_set, "3"),
    )
    factor = ampacity_factor_binding.construir_factor_desde_resultado(result)
    with pytest.raises(ValueError, match="P3C11A2005|P3C11D2001"):
        ampacity_factor_binding.validar_compatibilidad_contexto(factor, None, None)


def test_shards_rechazan_dataset_id_duplicado(tmp_path, monkeypatch):
    duplicate = ampacity_datasets.obtener_dataset(DATASET)
    shard = tmp_path / "duplicate.json"
    shard.write_text(json.dumps({"schema_version": 1, "datasets": [duplicate]}), encoding="utf-8")
    monkeypatch.setattr(ampacity_datasets, "_DATA_SHARDS", (shard,))
    # El mismo ID existe en el catálogo base solo si se parchea también el base. Para probar la
    # defensa entre shards, se duplica dos veces el shard válido y se excluye el shard real.
    monkeypatch.setattr(ampacity_datasets, "_DATA_SHARDS", (shard, shard))
    with pytest.raises(ValueError, match="P3B023"):
        ampacity_datasets.listar_datasets()


def test_5c_cierra_su_familia_pero_p3c11_aun_espera_5a():
    flags = p3_completion._coverage_flags()
    assert flags["table_5a"] is False
    assert flags["table_5b"] is True
    assert flags["table_5c"] is True
    assert flags["table_5d"] is True
    assert flags["table_5e"] is True
    gate = p3_completion.evaluar_cierre_p3()
    c11 = next(item for item in gate["criteria"] if item["id"] == "P3C11")
    assert c11["status"] == "PENDING"
    assert gate["ready_for_next_phase"] is False
    assert gate["next_phase"] is None
