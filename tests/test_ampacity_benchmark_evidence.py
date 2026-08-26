from copy import deepcopy

from mcp_electrico import ampacity_benchmark_evidence


FAMILIES = [
    "base_ampacity_strategy_Table_1_2_or_validated_equivalent",
    "Table_5A_temperature",
    "Table_5B_soil_thermal_resistivity_when_applicable",
    "Table_5C_grouping_air",
    "Table_5D_grouping_buried_method_D",
    "Table_5E_arrangement_branches_when_applicable",
]


def _primary_record(family: str, index: int) -> dict:
    return {
        "id": f"PRIMARY_BENCH_{index}",
        "norm_reference_id": "PERU_CNE_UTILIZACION_2006",
        "family": family,
        "table": "fixture",
        "axis": "fixture",
        "benchmark_kind": "INDEPENDENT_MANUAL_REFERENCE",
        "result": "PASS",
        "evidence_level": "PRIMARY",
        "independent_reference": True,
        "dataset_id": f"PRIMARY_DATASET_{index}",
        "dataset_verification_status": "PRIMARY_VERIFIED",
        "source_sha256": "a" * 64,
        "professional_normative_coverage": True,
        "review_record": {
            "reviewer": "Ingeniero revisor",
            "manual_comparison_confirmed": True,
        },
    }


def test_benchmark_secundario_historico_sigue_sin_calificar_aunque_p3c12_tenga_primarios():
    records = ampacity_benchmark_evidence.listar_registros()
    current = next(item for item in records if item["id"] == "P3B_TABLE_5C_SECONDARY_INFRA_V1")
    assert current["result"] == "PASS"
    assert current["evidence_level"] == "SECONDARY"
    assert current["professional_normative_coverage"] is False

    validation = ampacity_benchmark_evidence.validar_record(current)
    assert validation["qualifies_primary"] is False
    assert "evidence_not_primary" in validation["reasons"]

    coverage = ampacity_benchmark_evidence.evaluar_cobertura(FAMILIES)
    assert coverage["ready"] is True
    assert coverage["status"] == "PRIMARY_BENCHMARK_COVERAGE_READY"
    assert coverage["missing_families"] == []
    assert coverage["professional_emission"] is False


def test_pass_primario_sin_referencia_independiente_no_califica():
    record = _primary_record(FAMILIES[0], 1)
    record["independent_reference"] = False
    result = ampacity_benchmark_evidence.validar_record(
        record, check_live_sources=False, check_live_benchmarks=False
    )
    assert result["qualifies_primary"] is False
    assert "reference_not_independent" in result["reasons"]


def test_pass_primario_sin_dataset_primary_verified_no_califica():
    record = _primary_record(FAMILIES[0], 1)
    record["dataset_verification_status"] = "PENDING_PRIMARY_VERIFICATION"
    result = ampacity_benchmark_evidence.validar_record(
        record, check_live_sources=False, check_live_benchmarks=False
    )
    assert result["qualifies_primary"] is False
    assert "dataset_not_primary_verified" in result["reasons"]


def test_primario_estatico_sin_suite_viva_no_califica_en_modo_producto():
    record = _primary_record(FAMILIES[0], 1)
    result = ampacity_benchmark_evidence.validar_record(record, check_live_sources=False)
    assert result["qualifies_primary"] is False
    assert "benchmark_suite_missing" in result["reasons"]
    assert "benchmark_family_mismatch" in result["reasons"]


def test_cobertura_sintetica_primaria_completa_demuestra_logica_aislada():
    records = [_primary_record(family, index) for index, family in enumerate(FAMILIES, start=1)]
    coverage = ampacity_benchmark_evidence.evaluar_cobertura(
        FAMILIES,
        records=deepcopy(records),
        check_live_sources=False,
        check_live_benchmarks=False,
    )
    assert coverage["ready"] is True
    assert coverage["status"] == "PRIMARY_BENCHMARK_COVERAGE_READY"
    assert coverage["missing_families"] == []
    assert all(item["covered"] for item in coverage["coverage"].values())
    assert coverage["professional_emission"] is False


def test_cobertura_parcial_no_se_presenta_como_completa():
    records = [_primary_record(FAMILIES[0], 1), _primary_record(FAMILIES[3], 2)]
    coverage = ampacity_benchmark_evidence.evaluar_cobertura(
        FAMILIES,
        records=records,
        check_live_sources=False,
        check_live_benchmarks=False,
    )
    assert coverage["ready"] is False
    assert FAMILIES[0] not in coverage["missing_families"]
    assert FAMILIES[3] not in coverage["missing_families"]
    assert len(coverage["missing_families"]) == 4
