import json
from pathlib import Path
import pytest
from mcp_electrico import ampacity_datasets, ampacity_exact_lookup, ampacity_factor_binding, p3_completion

DATASET = "PERU_CNE_UTIL_2006_TABLE_5B_SOIL_THERMAL_RESISTIVITY_METHOD_D_PRIMARY_V1"
CANDIDATE = "P3C11B_TABLE_5B_SOIL_THERMAL_RESISTIVITY_PRIMARY_REVIEW_CANDIDATE_V1"
ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "mcp_electrico/data/ampacity_primary_review_candidates.json"


def _query(rho, depth_scope="up_to_0_8_m", environment="buried_duct"):
    return {"base_table": "Tabla 2", "installation_method": "D", "environment": environment,
            "burial_depth_scope": depth_scope, "soil_thermal_resistivity_k_m_per_w": rho}


def test_candidato_5b_preserva_tabla_completa_y_limites_publicados():
    payload = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    item = next(x for x in payload["candidates"] if x["id"] == CANDIDATE)
    assert item["source_hash_match"] is True
    assert item["pdf_page_number_one_based"] == 564
    assert item["document_page_marker"] == "Tablas - Pág. 17 de 82"
    assert item["candidate_values"] == {"1": 1.18, "1.5": 1.10, "2": 1.05, "2.5": 1.0, "3": 0.96}
    assert item["reviewed_notes"]["max_burial_depth_m"] == pytest.approx(0.8)
    assert item["complete_table_reviewed"] is True
    assert item["human_reviewer"] is None
    assert item["review_mode"] == "AI_VISUAL_REVIEW_USER_AUTHORIZED"
    assert item["review_result"] == "APPROVED"


@pytest.mark.parametrize(("rho", "expected"), [(1.0, 1.18), (1.5, 1.10), (2.0, 1.05), (2.5, 1.00), (3.0, 0.96)])
def test_tabla_5b_completa_resuelve_solo_filas_exactas(rho, expected):
    result = ampacity_exact_lookup.resolver_catalogo(DATASET, _query(rho))
    assert result["status"] == "RESOLVED_EXACT"
    assert result["value"] == pytest.approx(expected)
    assert result["verification_status"] == "PRIMARY_VERIFIED"
    assert result["professional_emission"] is True
    assert result["interpolation"] is False
    assert result["extrapolation"] is False


def test_5b_no_interpola_ni_sale_del_alcance_de_ducto_hasta_08m():
    results = [
        ampacity_exact_lookup.resolver_catalogo(DATASET, _query(2.7)),
        ampacity_exact_lookup.resolver_catalogo(DATASET, _query(3.0, environment="direct_buried")),
        ampacity_exact_lookup.resolver_catalogo(DATASET, _query(3.0, depth_scope="over_0_8_m")),
    ]
    for result in results:
        assert result["status"] == "VALUE_NOT_TABULATED"
        assert result["value"] is None
        assert result["professional_emission"] is False


def test_5b_cuenta_como_familia_primaria_completa_pero_p3c11_sigue_pendiente():
    dataset = ampacity_datasets.obtener_dataset(DATASET)
    assert dataset["usage_policy"]["p3c11_family_coverage"] is True
    assert dataset["usage_policy"]["automatic_binding_to_iz"] is True
    assert dataset["scope"]["complete_table_verified"] is True
    flags = p3_completion._coverage_flags()
    assert flags["table_5b"] is True
    assert flags["table_5a"] is False
    assert flags["table_5c"] is False
    assert flags["table_5d"] is False
    assert flags["table_5e"] is False
    gate = p3_completion.evaluar_cierre_p3()
    c11 = next(item for item in gate["criteria"] if item["id"] == "P3C11")
    assert c11["status"] == "PENDING"
    assert gate["ready_for_next_phase"] is False
    assert gate["next_phase"] is None


def test_5b_binding_exige_contexto_completo_aunque_dataset_resuelva():
    result = ampacity_exact_lookup.resolver_catalogo(DATASET, _query(3.0))
    factor = ampacity_factor_binding.construir_factor_desde_resultado(result)
    with pytest.raises(ValueError, match="P3C11B2008"):
        ampacity_factor_binding.validar_compatibilidad_contexto(
            factor,
            route={
                "profile_id": "PERU_CNE_UTIL_2006_030_004",
                "installation_method": "D",
                "environment": "buried_duct",
                "declared_conditions": {"soil_thermal_resistivity_k_m_per_w": 3.0},
            },
            normative_base={
                "profile_id": "PERU_CNE_UTIL_2006_030_004",
                "norm_reference_id": "PERU_CNE_UTILIZACION_2006",
                "table": "Tabla 2",
                "dataset": {"query": {"installation_method": "D"}},
            },
        )
