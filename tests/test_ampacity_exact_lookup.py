import pytest

from mcp_electrico import ampacity_exact_lookup


def _factor_dataset():
    return {
        "id": "SYNTHETIC_TEMP",
        "profile_id": "TEST_PROFILE",
        "norm_reference_id": "TEST_NORM",
        "table": "Test Table",
        "axis": "ambient_temperature",
        "lookup_schema": {
            "type": "exact_rows_v1",
            "dimensions": ["insulation_class", "ambient_temperature_c"],
            "value_field": "factor",
        },
        "rows": [
            {"query": {"insulation_class": "X", "ambient_temperature_c": 30}, "factor": 1.0},
            {"query": {"insulation_class": "X", "ambient_temperature_c": 35}, "factor": 0.95},
        ],
    }


def _base_ampacity_dataset():
    return {
        "id": "SYNTHETIC_BASE",
        "profile_id": "TEST_PROFILE",
        "norm_reference_id": "TEST_NORM",
        "table": "Test Base",
        "axis": "base_ampacity",
        "lookup_schema": {
            "type": "exact_rows_v1",
            "dimensions": ["method", "material", "section_mm2"],
            "value_field": "ampacity_a",
        },
        "rows": [
            {
                "query": {"method": "C", "material": "Cu", "section_mm2": 50},
                "ampacity_a": 150.0,
                "metadata": {"fixture_only": True},
            }
        ],
    }


def test_schema_generico_acepta_dimensiones_declaradas_sin_hardcode_normativo():
    result = ampacity_exact_lookup.validar_dataset(_factor_dataset())
    assert result["valid"] is True
    assert result["dimensions"] == ["insulation_class", "ambient_temperature_c"]
    assert result["interpolation"] is False
    assert result["extrapolation"] is False


def test_lookup_factor_es_exacto_y_normaliza_numeros_sin_interpolar():
    dataset = _factor_dataset()
    exact = ampacity_exact_lookup.resolver_dataset(
        dataset,
        {"insulation_class": "X", "ambient_temperature_c": 35.0},
    )
    assert exact["status"] == "RESOLVED_EXACT"
    assert exact["value"] == pytest.approx(0.95)

    missing = ampacity_exact_lookup.resolver_dataset(
        dataset,
        {"insulation_class": "X", "ambient_temperature_c": 32.5},
    )
    assert missing["status"] == "VALUE_NOT_TABULATED"
    assert missing["value"] is None
    assert missing["interpolation"] is False
    assert missing["extrapolation"] is False


def test_mismo_motor_puede_resolver_ampacidad_base_sin_conocer_tabla_real():
    result = ampacity_exact_lookup.resolver_dataset(
        _base_ampacity_dataset(),
        {"method": "C", "material": "Cu", "section_mm2": 50.0},
    )
    assert result["status"] == "RESOLVED_EXACT"
    assert result["value_field"] == "ampacity_a"
    assert result["value"] == pytest.approx(150.0)
    assert result["row_metadata"]["fixture_only"] is True


def test_query_debe_declarar_exactamente_las_dimensiones_del_dataset():
    result = ampacity_exact_lookup.resolver_dataset(
        _factor_dataset(),
        {"ambient_temperature_c": 35},
    )
    assert result["status"] == "QUERY_DIMENSION_MISMATCH"
    assert result["professional_emission"] is False


def test_schema_rechaza_filas_duplicadas_y_dimensiones_incompletas():
    dataset = _factor_dataset()
    dataset["rows"].append(dict(dataset["rows"][0]))
    with pytest.raises(ValueError, match="P3XL008"):
        ampacity_exact_lookup.validar_dataset(dataset)

    dataset = _factor_dataset()
    dataset["rows"][0]["query"].pop("insulation_class")
    with pytest.raises(ValueError, match="P3XL007"):
        ampacity_exact_lookup.validar_dataset(dataset)


def test_dataset_legado_actual_no_se_migra_implicitamente():
    result = ampacity_exact_lookup.resolver_catalogo(
        "PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_SECONDARY_V1",
        {"circuits_grouped": 2},
        allow_secondary=True,
    )
    assert result["status"] == "DATASET_SCHEMA_NOT_GENERIC"
    assert result["professional_emission"] is False
