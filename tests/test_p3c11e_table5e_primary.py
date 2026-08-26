import json
from pathlib import Path

import pytest

from mcp_electrico import ampacity_datasets, ampacity_exact_lookup, ampacity_factor_binding, p3_completion

DATASET = "PERU_CNE_UTIL_2006_TABLE_5E_GROUPING_AIR_METHODS_E_F_PRIMARY_V1"
CANDIDATE = "P3C11E_TABLE_5E_GROUPING_AIR_METHODS_E_F_PRIMARY_REVIEW_CANDIDATE_V1"
ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "mcp_electrico/data/ampacity_primary_review_candidates.json"


def q(method, branch, support, mode, formation, trays, units):
    return {
        "installation_method": method, "environment": "air", "table5e_branch": branch,
        "support_family": support, "contact_mode": mode, "cable_formation": formation,
        "tray_count": trays, "grouped_units": units,
    }


def test_dataset_5e_completo_primary_verified_preserva_numericos_y_guiones():
    dataset = ampacity_datasets.obtener_dataset(DATASET)
    assert dataset["table"] == "Tabla 5E"
    assert dataset["axis"] == "grouping"
    assert dataset["provenance"]["verification_status"] == "PRIMARY_VERIFIED"
    assert dataset["usage_policy"]["professional_emission"] is True
    assert dataset["usage_policy"]["p3c11_family_coverage"] is True
    assert dataset["usage_policy"]["automatic_binding_to_iz"] is False
    assert dataset["scope"]["complete_table_verified"] is True
    assert len(dataset["rows"]) == 134
    assert len(dataset["not_tabulated_cells"]) == 10
    assert ampacity_exact_lookup.validar_dataset(dataset)["row_count"] == 134


def test_muestras_limite_y_disposiciones_de_ambas_paginas_resuelven_exactas():
    cases = [
        (q("E", "A_MULTICORE_CABLE_GROUPS", "perforated_trays", "contact", "not_applicable_multicore", 1, 9), 0.73),
        (q("E", "A_MULTICORE_CABLE_GROUPS", "perforated_trays", "contact", "not_applicable_multicore", 3, 9), 0.66),
        (q("E", "A_MULTICORE_CABLE_GROUPS", "ladder_trays_clamps_supports", "spaced_as_figure", "not_applicable_multicore", 1, 6), 1.00),
        (q("E", "A_MULTICORE_CABLE_GROUPS", "vertical_perforated_trays", "spaced_as_figure", "not_applicable_multicore", 2, 4), 0.87),
        (q("F", "B_SINGLE_CORE_3PH_CIRCUIT_GROUPS", "perforated_trays", "contact", "three_single_core_horizontal", 3, 3), 0.78),
        (q("F", "B_SINGLE_CORE_3PH_CIRCUIT_GROUPS", "vertical_perforated_trays", "contact", "three_single_core_vertical", 2, 2), 0.84),
        (q("F", "B_SINGLE_CORE_3PH_CIRCUIT_GROUPS", "ladder_trays_clamps_supports", "contact", "three_single_core_horizontal", 1, 1), 1.00),
        (q("F", "B_SINGLE_CORE_3PH_CIRCUIT_GROUPS", "perforated_trays", "spaced_as_figure", "three_single_core_trefoil", 3, 3), 0.86),
        (q("F", "B_SINGLE_CORE_3PH_CIRCUIT_GROUPS", "ladder_trays_clamps_supports", "spaced_as_figure", "three_single_core_trefoil", 3, 3), 0.90),
    ]
    for query, expected in cases:
        result = ampacity_exact_lookup.resolver_catalogo(DATASET, query)
        assert result["status"] == "RESOLVED_EXACT"
        assert result["value"] == pytest.approx(expected)
        assert result["professional_emission"] is True


def test_celdas_guion_y_consultas_fuera_de_tabla_no_se_inventan():
    probes = [
        q("E", "A_MULTICORE_CABLE_GROUPS", "perforated_trays", "spaced_as_figure", "not_applicable_multicore", 1, 9),
        q("E", "A_MULTICORE_CABLE_GROUPS", "ladder_trays_clamps_supports", "spaced_as_figure", "not_applicable_multicore", 3, 9),
        q("F", "B_SINGLE_CORE_3PH_CIRCUIT_GROUPS", "vertical_perforated_trays", "contact", "three_single_core_vertical", 1, 3),
        q("F", "B_SINGLE_CORE_3PH_CIRCUIT_GROUPS", "perforated_trays", "contact", "three_single_core_horizontal", 4, 2),
        q("G", "B_SINGLE_CORE_3PH_CIRCUIT_GROUPS", "perforated_trays", "contact", "three_single_core_horizontal", 1, 1),
    ]
    for query in probes:
        result = ampacity_exact_lookup.resolver_catalogo(DATASET, query)
        assert result["status"] == "VALUE_NOT_TABULATED"
        assert result["value"] is None
        assert result["professional_emission"] is False


def test_evidencia_5e_preserva_paginas_conteos_y_notas():
    payload = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    item = next(x for x in payload["candidates"] if x["id"] == CANDIDATE)
    assert item["source_hash_match"] is True
    assert item["pdf_pages"] == [568, 569]
    assert item["automated_extraction"]["workflow_run_id"] == 32912314189
    assert item["automated_extraction"]["artifact_id"] == 9586942706
    assert item["candidate_structure"]["numeric_row_count"] == 134
    assert item["candidate_structure"]["explicit_not_tabulated_count"] == 10
    assert item["reviewed_notes"]["single_layer_only"] is True
    assert item["human_reviewer"] is None
    assert item["review_mode"] == "AI_VISUAL_REVIEW_USER_AUTHORIZED"


def test_5e_cierra_su_familia_pero_p3c11_sigue_pendiente_por_5a_5c():
    flags = p3_completion._coverage_flags()
    assert flags["table_5a"] is False
    assert flags["table_5b"] is True
    assert flags["table_5c"] is False
    assert flags["table_5d"] is True
    assert flags["table_5e"] is True
    gate = p3_completion.evaluar_cierre_p3()
    c11 = next(x for x in gate["criteria"] if x["id"] == "P3C11")
    assert c11["status"] == "PENDING"
    assert gate["ready_for_next_phase"] is False
    assert gate["next_phase"] is None


def test_5e_permanece_fail_closed_para_binding_hasta_e2():
    result = ampacity_exact_lookup.resolver_catalogo(
        DATASET,
        q("E", "A_MULTICORE_CABLE_GROUPS", "perforated_trays", "contact", "not_applicable_multicore", 1, 2),
    )
    factor = ampacity_factor_binding.construir_factor_desde_resultado(result)
    with pytest.raises(ValueError):
        ampacity_factor_binding.validar_compatibilidad_contexto(factor, None, None)
