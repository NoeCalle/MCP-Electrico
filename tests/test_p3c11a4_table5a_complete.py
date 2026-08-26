import pytest

from mcp_electrico import ampacity_datasets, ampacity_table5a, p3_completion


DATASET = "PERU_CNE_UTIL_2006_TABLE_5A_COMPLETE_PRIMARY_V1"
PARTIAL_BINDING_DATASET = "PERU_CNE_UTIL_2006_TABLE_5A_XLPE_AIR_A1_COL15_PRIMARY_V1"


def _matrix_counts(dataset):
    numeric = 0
    not_tabulated = 0
    for block in dataset["matrix"].values():
        key_count = len(block["ambient_temperature_keys"])
        for values in block["columns"].values():
            assert len(values) == key_count
            for value in values:
                if value is None:
                    not_tabulated += 1
                else:
                    numeric += 1
    return numeric, not_tabulated


def test_tabla_5a_completa_es_primary_verified_y_preserva_111_mas_45_celdas():
    dataset = ampacity_datasets.obtener_dataset(DATASET)
    assert dataset["table"] == "Tabla 5A"
    assert dataset["axis"] == "ambient_temperature"
    assert dataset["lookup_schema"]["type"] == "table5a_matrix_v1"
    assert dataset["provenance"]["verification_status"] == "PRIMARY_VERIFIED"
    assert dataset["provenance"]["source_sha256"] == "2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64"
    assert dataset["provenance"]["verification_record"]["review_mode"] == "AI_VISUAL_REVIEW_USER_AUTHORIZED"
    assert dataset["provenance"]["verification_record"]["human_reviewer"] is None
    assert dataset["usage_policy"]["p3c11_family_coverage"] is True
    assert dataset["usage_policy"]["automatic_binding_to_iz"] is False
    assert dataset["scope"]["complete_table_verified"] is True
    assert dataset["scope"]["numeric_row_count"] == 111
    assert dataset["scope"]["explicit_not_tabulated_count"] == 45
    assert _matrix_counts(dataset) == (111, 45)


def test_lookup_evidencia_5a_resuelve_celdas_representativas_de_ambos_bloques():
    cases = [
        ({"table_block":"NORMAL", "base_table_column":15, "factor_column_id":"XLPE_EPR_AIR", "ambient_temperature_key":35}, 0.96),
        ({"table_block":"NORMAL", "base_table_column":2, "factor_column_id":"PVC_AIR", "ambient_temperature_key":10}, 1.22),
        ({"table_block":"NORMAL", "base_table_column":16, "factor_column_id":"MI_BARE_NOT_EXPOSED_105C", "ambient_temperature_key":95}, 0.32),
        ({"table_block":"HIGH_OPERATING_TEMPERATURE", "base_table_column":17, "factor_column_id":"AL_ALA_125C", "ambient_temperature_key":"31_40"}, 0.91),
        ({"table_block":"HIGH_OPERATING_TEMPERATURE", "base_table_column":18, "factor_column_id":"A_AA_FEP_FEPB_200C", "ambient_temperature_key":"56_60"}, 0.91),
        ({"table_block":"HIGH_OPERATING_TEMPERATURE", "base_table_column":19, "factor_column_id":"TFE_250C", "ambient_temperature_key":"201_225"}, 0.30),
    ]
    for query, expected in cases:
        result = ampacity_table5a.resolver_celda(**query)
        assert result["status"] == "RESOLVED_EXACT"
        assert result["factor"] == pytest.approx(expected)
        assert result["professional_emission"] is True
        assert result["automatic_binding_to_iz"] is False
        assert result["interpolation"] is False
        assert result["extrapolation"] is False


def test_transcripcion_preserva_valor_publicado_no_monotono_mi_70c_40_45c():
    r40 = ampacity_table5a.resolver_celda(
        table_block="NORMAL", base_table_column=10,
        factor_column_id="MI_PVC_OR_BARE_NOT_EXPOSED_70C", ambient_temperature_key=40,
    )
    r45 = ampacity_table5a.resolver_celda(
        table_block="NORMAL", base_table_column=10,
        factor_column_id="MI_PVC_OR_BARE_NOT_EXPOSED_70C", ambient_temperature_key=45,
    )
    assert r40["factor"] == pytest.approx(0.85)
    assert r45["factor"] == pytest.approx(0.87)


def test_guion_publicado_no_se_convierte_en_factor_ni_se_interpola():
    result = ampacity_table5a.resolver_celda(
        table_block="NORMAL", base_table_column=2,
        factor_column_id="PVC_AIR", ambient_temperature_key=65,
    )
    assert result["status"] == "VALUE_NOT_TABULATED"
    assert result["factor"] is None
    assert result["source_token"] == "-"
    assert result["professional_emission"] is False
    assert result["interpolation"] is False
    assert result["extrapolation"] is False


def test_columnas_20_a_25_permanecen_fail_closed_fuera_del_alcance_literal_5a():
    result = ampacity_table5a.resolver_celda(
        table_block="NORMAL", base_table_column=23,
        factor_column_id="XLPE_EPR_AIR", ambient_temperature_key=35,
    )
    assert result["status"] == "SCOPE_MISMATCH"
    assert result["factor"] is None
    assert "2-16" in result["scope_issue"]
    assert result["professional_emission"] is False


def test_bloque_alta_temperatura_exige_correspondencia_columna_17_18_19():
    result = ampacity_table5a.resolver_celda(
        table_block="HIGH_OPERATING_TEMPERATURE", base_table_column=18,
        factor_column_id="TFE_250C", ambient_temperature_key="81_90",
    )
    assert result["status"] == "SCOPE_MISMATCH"
    assert "requiere factor_column_id=A_AA_FEP_FEPB_200C" in result["scope_issue"]


def test_dataset_completo_no_reemplaza_binding_5a_parcial_ya_validado():
    complete = ampacity_datasets.obtener_dataset(DATASET)
    partial = ampacity_datasets.obtener_dataset(PARTIAL_BINDING_DATASET)
    assert complete["usage_policy"]["automatic_binding_to_iz"] is False
    assert partial["usage_policy"]["automatic_binding_to_iz"] is True
    assert partial["usage_policy"]["p3c11_family_coverage"] is False


def test_p3c11_y_p3c12_done_pero_p4_sigue_bloqueada_por_p3c13():
    flags = p3_completion._coverage_flags()
    assert flags["base_ampacity_strategy"] is True
    assert flags["table_5a"] is True
    assert flags["table_5b"] is True
    assert flags["table_5c"] is True
    assert flags["table_5d"] is True
    assert flags["table_5e"] is True

    gate = p3_completion.evaluar_cierre_p3()
    c11 = next(item for item in gate["criteria"] if item["id"] == "P3C11")
    c12 = next(item for item in gate["criteria"] if item["id"] == "P3C12")
    c13 = next(item for item in gate["criteria"] if item["id"] == "P3C13")
    assert c11["status"] == "DONE"
    assert c12["status"] == "DONE"
    assert c13["status"] == "DONE"
    assert gate["phase_status"] == "READY_WITH_LIMITATIONS"
    assert gate["ready_for_next_phase"] is True
    assert gate["next_phase"] == "P4_IEC_60909"
    assert gate["professional_emission"] is False
