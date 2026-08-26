from mcp_electrico import ampacity_benchmark_evidence, ampacity_independent_benchmarks, p3_completion


FAMILIES = set(ampacity_independent_benchmarks.REQUIRED_FAMILIES)


def test_registro_p3c12_tiene_un_primary_vivo_por_cada_familia():
    records = ampacity_benchmark_evidence.listar_registros()
    primary = [record for record in records if record.get("evidence_level") == "PRIMARY"]
    assert {record["family"] for record in primary} == FAMILIES
    assert len(primary) == 6
    for record in primary:
        assert record["benchmark_suite_id"] == "P3C12_PRIMARY_INDEPENDENT_REFERENCE_V1"
        assert record["benchmark_family"] == record["family"]
        assert record["independent_reference"] is True
        assert record["dataset_verification_status"] == "PRIMARY_VERIFIED"
        assert record["professional_normative_coverage"] is True
        validation = ampacity_benchmark_evidence.validar_record(record)
        assert validation["qualifies_primary"] is True
        assert validation["reasons"] == []


def test_p3c12_coverage_ready_y_p3c13_es_unico_bloqueante():
    coverage = ampacity_benchmark_evidence.evaluar_cobertura(list(FAMILIES))
    assert coverage["status"] == "PRIMARY_BENCHMARK_COVERAGE_READY"
    assert coverage["ready"] is True
    assert coverage["missing_families"] == []

    gate = p3_completion.evaluar_cierre_p3()
    criteria = {item["id"]: item for item in gate["criteria"]}
    assert criteria["P3C12"]["status"] == "DONE"
    assert criteria["P3C13"]["status"] == "DONE"
    assert {item["id"] for item in gate["pending_criteria"]} == set()
    assert gate["phase_status"] == "READY_WITH_LIMITATIONS"
    assert gate["ready_for_next_phase"] is True
    assert gate["next_phase"] == "P4_IEC_60909"
