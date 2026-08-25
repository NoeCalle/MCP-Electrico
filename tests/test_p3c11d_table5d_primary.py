import json
from pathlib import Path

import pytest

from mcp_electrico import ampacity_datasets, ampacity_exact_lookup, ampacity_factor_binding, p3_completion

DATASET = "PERU_CNE_UTIL_2006_TABLE_5D_GROUPING_METHOD_D_PRIMARY_V1"
CANDIDATE = "P3C11D_TABLE_5D_GROUPING_METHOD_D_PRIMARY_REVIEW_CANDIDATE_V1"
ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "mcp_electrico/data/ampacity_primary_review_candidates.json"

BRANCHES = {
    "A_DIRECT_BURIED_CABLES": ("direct_buried", ["contact", "one_cable_diameter", "0_125_m", "0_25_m", "0_5_m"], {
        2: [0.75,0.80,0.85,0.90,0.90], 3: [0.65,0.70,0.75,0.80,0.85],
        4: [0.60,0.60,0.70,0.75,0.80], 5: [0.55,0.55,0.65,0.70,0.80],
        6: [0.50,0.55,0.60,0.70,0.80]}),
    "B_MULTICORE_SINGLE_WAY_DUCTS": ("buried_duct", ["contact", "0_25_m", "0_5_m", "1_0_m"], {
        2: [0.85,0.90,0.95,0.95], 3: [0.75,0.85,0.90,0.95],
        4: [0.70,0.80,0.85,0.90], 5: [0.65,0.80,0.85,0.90],
        6: [0.60,0.80,0.80,0.90]}),
    "C_SINGLE_CORE_SINGLE_WAY_DUCT_CIRCUITS": ("buried_duct", ["contact", "0_25_m", "0_5_m", "1_0_m"], {
        2: [0.80,0.90,0.90,0.95], 3: [0.70,0.80,0.85,0.90],
        4: [0.65,0.75,0.80,0.90], 5: [0.60,0.70,0.80,0.90],
        6: [0.60,0.70,0.80,0.90]}),
}


def q(branch, env, circuits, spacing, depth=0.7, rho=2.5):
    return {
        "installation_method": "D", "environment": env, "table5d_branch": branch,
        "burial_depth_m": depth, "soil_thermal_resistivity_k_m_per_w": rho,
        "circuits_grouped": circuits, "spacing_id": spacing,
    }


def test_dataset_5d_es_tabla_completa_primary_verified_de_65_filas():
    dataset = ampacity_datasets.obtener_dataset(DATASET)
    assert dataset["table"] == "Tabla 5D"
    assert dataset["axis"] == "grouping"
    assert dataset["provenance"]["verification_status"] == "PRIMARY_VERIFIED"
    assert dataset["usage_policy"]["professional_emission"] is True
    assert dataset["usage_policy"]["p3c11_family_coverage"] is True
    assert dataset["usage_policy"]["automatic_binding_to_iz"] is False
    assert dataset["scope"]["complete_table_verified"] is True
    assert len(dataset["rows"]) == 65
    assert ampacity_exact_lookup.validar_dataset(dataset)["row_count"] == 65


def test_todas_las_65_celdas_resuelven_exactamente():
    count = 0
    for branch, (env, spacings, matrix) in BRANCHES.items():
        for circuits, values in matrix.items():
            for spacing, expected in zip(spacings, values):
                result = ampacity_exact_lookup.resolver_catalogo(DATASET, q(branch, env, circuits, spacing))
                assert result["status"] == "RESOLVED_EXACT"
                assert result["value"] == pytest.approx(expected)
                assert result["professional_emission"] is True
                assert result["interpolation"] is False
                assert result["extrapolation"] is False
                count += 1
    assert count == 65


def test_5d_no_interpola_ni_extrapola_condiciones_publicadas():
    probes = [
        q("A_DIRECT_BURIED_CABLES", "direct_buried", 2, "0_25_m", depth=0.8),
        q("A_DIRECT_BURIED_CABLES", "direct_buried", 2, "0_25_m", rho=1.5),
        q("A_DIRECT_BURIED_CABLES", "direct_buried", 7, "0_25_m"),
        q("B_MULTICORE_SINGLE_WAY_DUCTS", "buried_duct", 2, "0_125_m"),
        q("C_SINGLE_CORE_SINGLE_WAY_DUCT_CIRCUITS", "direct_buried", 2, "1_0_m"),
    ]
    for query in probes:
        result = ampacity_exact_lookup.resolver_catalogo(DATASET, query)
        assert result["status"] == "VALUE_NOT_TABULATED"
        assert result["value"] is None
        assert result["professional_emission"] is False


def test_anomalia_editorial_c6_1m_se_preserva_sin_perder_valor_numerico():
    result = ampacity_exact_lookup.resolver_catalogo(
        DATASET,
        q("C_SINGLE_CORE_SINGLE_WAY_DUCT_CIRCUITS", "buried_duct", 6, "1_0_m"),
    )
    assert result["value"] == pytest.approx(0.90)
    assert result["row_metadata"]["source_token"] == ",0,90"
    assert "normaliza" in result["row_metadata"]["normalization_note"]


def test_evidencia_5d_preserva_paginas_artifact_y_condiciones():
    payload = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    item = next(x for x in payload["candidates"] if x["id"] == CANDIDATE)
    assert item["source_hash_match"] is True
    assert item["pdf_pages"] == [566, 567]
    assert item["automated_extraction"]["workflow_run_id"] == 32911061659
    assert item["automated_extraction"]["artifact_id"] == 9586544930
    assert item["candidate_structure"]["row_count"] == 65
    assert item["candidate_structure"]["burial_depth_m"] == pytest.approx(0.7)
    assert item["candidate_structure"]["soil_thermal_resistivity_k_m_per_w"] == pytest.approx(2.5)
    assert item["publication_anomaly"]["source_token"] == ",0,90"
    assert item["human_reviewer"] is None
    assert item["review_mode"] == "AI_VISUAL_REVIEW_USER_AUTHORIZED"


def test_5d_cierra_solo_su_familia_y_p3c11_global_sigue_pendiente():
    flags = p3_completion._coverage_flags()
    assert flags["table_5a"] is False
    assert flags["table_5b"] is True
    assert flags["table_5c"] is False
    assert flags["table_5d"] is True
    assert flags["table_5e"] is False
    gate = p3_completion.evaluar_cierre_p3()
    c11 = next(x for x in gate["criteria"] if x["id"] == "P3C11")
    assert c11["status"] == "PENDING"
    assert gate["ready_for_next_phase"] is False
    assert gate["next_phase"] is None


def test_5d_permanece_fail_closed_para_binding_hasta_d2():
    result = ampacity_exact_lookup.resolver_catalogo(
        DATASET,
        q("B_MULTICORE_SINGLE_WAY_DUCTS", "buried_duct", 3, "0_25_m"),
    )
    factor = ampacity_factor_binding.construir_factor_desde_resultado(result)
    with pytest.raises(ValueError, match="sin política de compatibilidad implementada"):
        ampacity_factor_binding.validar_compatibilidad_contexto(factor, None, None)
