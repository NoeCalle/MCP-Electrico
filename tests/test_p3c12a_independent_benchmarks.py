from copy import deepcopy

from mcp_electrico import ampacity_independent_benchmarks, p3_completion


def test_referencia_independiente_cubre_exactamente_seis_familias_y_fuente_pinneada():
    reference = ampacity_independent_benchmarks.obtener_referencia()
    assert reference["reference_evidence"] == "PRIMARY_INDEPENDENT"
    assert reference["reference_origin"] == "PRIMARY_SOURCE_PAGE_TRANSCRIPTION_INDEPENDENT_OF_PRODUCTION_DATASET"
    assert reference["source_sha256"] == "2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64"
    assert reference["review_record"]["manual_comparison_confirmed"] is True
    assert {case["family"] for case in reference["cases"]} == set(
        ampacity_independent_benchmarks.REQUIRED_FAMILIES
    )
    assert len(reference["cases"]) == 29


def test_suite_independiente_compara_29_casos_reales_y_todas_las_familias_pasan():
    report = ampacity_independent_benchmarks.run_suite()
    assert report["reference_evidence"] == "PRIMARY_INDEPENDENT"
    assert report["independent_reference"] is True
    assert report["cases"] == 29
    assert report["passed"] == 29
    assert report["failed"] == 0
    assert report["pass"] is True
    assert report["result"] == "PASS"
    assert set(report["family_results"]) == set(ampacity_independent_benchmarks.REQUIRED_FAMILIES)
    assert all(item["pass"] for item in report["family_results"].values())
    assert all(row["dataset_verification_status"] == "PRIMARY_VERIFIED" for row in report["case_results"])
    assert all(row["professional_emission"] is True for row in report["case_results"])


def test_mutacion_de_referencia_esperada_hace_fallar_suite_y_no_se_autojustifica():
    reference = ampacity_independent_benchmarks.obtener_referencia()
    mutated = deepcopy(reference)
    mutated["cases"][0]["expected_value"] = 230.0
    report = ampacity_independent_benchmarks.run_suite(payload=mutated)
    assert report["pass"] is False
    assert report["failed"] == 1
    assert report["case_results"][0]["expected_value"] == 230.0
    assert report["case_results"][0]["actual_value"] == 229.0
    assert report["case_results"][0]["result"] == "FAIL"


def test_p3c12a_permanece_base_viva_y_registro_p3c12b_la_promueve_sin_cerrar_p3():
    gate = p3_completion.evaluar_cierre_p3()
    criteria = {item["id"]: item for item in gate["criteria"]}
    assert criteria["P3C11"]["status"] == "DONE"
    assert criteria["P3C12"]["status"] == "DONE"
    assert criteria["P3C13"]["status"] == "PENDING"
    assert gate["phase_status"] == "NOT_READY"
    assert gate["ready_for_next_phase"] is False
    assert gate["next_phase"] is None
    assert gate["professional_emission"] is False
