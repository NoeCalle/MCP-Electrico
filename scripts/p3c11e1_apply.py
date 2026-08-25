from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "mcp_electrico/data/ampacity_p3b_numeric_datasets.json"
CANDIDATES = ROOT / "mcp_electrico/data/ampacity_primary_review_candidates.json"
ROADMAP = ROOT / "docs/ROADMAP_PROFESIONAL.md"
DOC = ROOT / "docs/P3C11E_TABLE5E_PRIMARY.md"
TEST = ROOT / "tests/test_p3c11e_table5e_primary.py"

SOURCE_SHA = "2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64"
DATASET_ID = "PERU_CNE_UTIL_2006_TABLE_5E_GROUPING_AIR_METHODS_E_F_PRIMARY_V1"
CANDIDATE_ID = "P3C11E_TABLE_5E_GROUPING_AIR_METHODS_E_F_PRIMARY_REVIEW_CANDIDATE_V1"

# Cada variante preserva una disposición física explícita de las páginas 21-22.
VARIANTS = {
    # Rama A — cables multipolares / método E.
    "A_PERFORATED_TRAYS_CONTACT": {
        "method": "E", "branch": "A_MULTICORE_CABLE_GROUPS", "support": "perforated_trays",
        "contact_mode": "contact", "formation": "not_applicable_multicore", "items": "13",
        "group_label": "number_of_multicore_cables", "columns": [1, 2, 3, 4, 6, 9],
        "values": {1: [1.00, 0.88, 0.82, 0.79, 0.76, 0.73], 2: [1.00, 0.87, 0.80, 0.77, 0.73, 0.68], 3: [1.00, 0.86, 0.79, 0.76, 0.71, 0.66]},
    },
    "A_PERFORATED_TRAYS_SPACED": {
        "method": "E", "branch": "A_MULTICORE_CABLE_GROUPS", "support": "perforated_trays",
        "contact_mode": "spaced_as_figure", "formation": "not_applicable_multicore", "items": "13",
        "group_label": "number_of_multicore_cables", "columns": [1, 2, 3, 4, 6, 9],
        "values": {1: [1.00, 1.00, 0.98, 0.95, 0.91, None], 2: [1.00, 0.99, 0.96, 0.92, 0.87, None], 3: [1.00, 0.99, 0.95, 0.91, 0.85, None]},
    },
    "A_VERTICAL_PERFORATED_TRAYS_CONTACT": {
        "method": "E", "branch": "A_MULTICORE_CABLE_GROUPS", "support": "vertical_perforated_trays",
        "contact_mode": "contact", "formation": "not_applicable_multicore", "items": "13",
        "group_label": "number_of_multicore_cables", "columns": [1, 2, 3, 4, 6, 9],
        "values": {1: [1.00, 0.88, 0.82, 0.78, 0.73, 0.72], 2: [1.00, 0.88, 0.81, 0.76, 0.71, 0.70]},
    },
    "A_VERTICAL_PERFORATED_TRAYS_SPACED": {
        "method": "E", "branch": "A_MULTICORE_CABLE_GROUPS", "support": "vertical_perforated_trays",
        "contact_mode": "spaced_as_figure", "formation": "not_applicable_multicore", "items": "13",
        "group_label": "number_of_multicore_cables", "columns": [1, 2, 3, 4, 6, 9],
        "values": {1: [1.00, 0.91, 0.89, 0.88, 0.87, None], 2: [1.00, 0.91, 0.88, 0.87, 0.85, None]},
    },
    "A_LADDER_TRAYS_CONTACT": {
        "method": "E", "branch": "A_MULTICORE_CABLE_GROUPS", "support": "ladder_trays_clamps_supports",
        "contact_mode": "contact", "formation": "not_applicable_multicore", "items": "14_15_16",
        "group_label": "number_of_multicore_cables", "columns": [1, 2, 3, 4, 6, 9],
        "values": {1: [1.00, 0.87, 0.82, 0.80, 0.79, 0.78], 2: [1.00, 0.86, 0.80, 0.78, 0.76, 0.73], 3: [1.00, 0.85, 0.79, 0.76, 0.73, 0.70]},
    },
    "A_LADDER_TRAYS_SPACED": {
        "method": "E", "branch": "A_MULTICORE_CABLE_GROUPS", "support": "ladder_trays_clamps_supports",
        "contact_mode": "spaced_as_figure", "formation": "not_applicable_multicore", "items": "14_15_16",
        "group_label": "number_of_multicore_cables", "columns": [1, 2, 3, 4, 6, 9],
        "values": {1: [1.00, 1.00, 1.00, 1.00, 1.00, None], 2: [1.00, 0.99, 0.98, 0.97, 0.96, None], 3: [1.00, 0.98, 0.97, 0.96, 0.93, None]},
    },
    # Rama B — circuitos trifásicos de cables unipolares / método F.
    "B_PERFORATED_TRAYS_CONTACT_HORIZONTAL": {
        "method": "F", "branch": "B_SINGLE_CORE_3PH_CIRCUIT_GROUPS", "support": "perforated_trays",
        "contact_mode": "contact", "formation": "three_single_core_horizontal", "items": "13",
        "group_label": "number_of_three_phase_circuits", "columns": [1, 2, 3],
        "values": {1: [0.98, 0.91, 0.87], 2: [0.96, 0.87, 0.81], 3: [0.95, 0.85, 0.78]},
    },
    "B_VERTICAL_PERFORATED_TRAYS_CONTACT_VERTICAL": {
        "method": "F", "branch": "B_SINGLE_CORE_3PH_CIRCUIT_GROUPS", "support": "vertical_perforated_trays",
        "contact_mode": "contact", "formation": "three_single_core_vertical", "items": "13",
        "group_label": "number_of_three_phase_circuits", "columns": [1, 2, 3],
        "values": {1: [0.96, 0.86, None], 2: [0.95, 0.84, None]},
    },
    "B_LADDER_TRAYS_CONTACT_HORIZONTAL": {
        "method": "F", "branch": "B_SINGLE_CORE_3PH_CIRCUIT_GROUPS", "support": "ladder_trays_clamps_supports",
        "contact_mode": "contact", "formation": "three_single_core_horizontal", "items": "14_15_16",
        "group_label": "number_of_three_phase_circuits", "columns": [1, 2, 3],
        "values": {1: [1.00, 0.97, 0.96], 2: [0.98, 0.93, 0.89], 3: [0.97, 0.90, 0.86]},
    },
    "B_PERFORATED_TRAYS_SPACED_TREFOIL": {
        "method": "F", "branch": "B_SINGLE_CORE_3PH_CIRCUIT_GROUPS", "support": "perforated_trays",
        "contact_mode": "spaced_as_figure", "formation": "three_single_core_trefoil", "items": "13",
        "group_label": "number_of_three_phase_circuits", "columns": [1, 2, 3],
        "values": {1: [1.00, 0.98, 0.96], 2: [0.97, 0.93, 0.89], 3: [0.96, 0.92, 0.86]},
    },
    "B_VERTICAL_PERFORATED_TRAYS_SPACED_TREFOIL": {
        "method": "F", "branch": "B_SINGLE_CORE_3PH_CIRCUIT_GROUPS", "support": "vertical_perforated_trays",
        "contact_mode": "spaced_as_figure", "formation": "three_single_core_trefoil", "items": "13",
        "group_label": "number_of_three_phase_circuits", "columns": [1, 2, 3],
        "values": {1: [1.00, 0.91, 0.89], 2: [1.00, 0.90, 0.86]},
    },
    "B_LADDER_TRAYS_SPACED_TREFOIL": {
        "method": "F", "branch": "B_SINGLE_CORE_3PH_CIRCUIT_GROUPS", "support": "ladder_trays_clamps_supports",
        "contact_mode": "spaced_as_figure", "formation": "three_single_core_trefoil", "items": "14_15_16",
        "group_label": "number_of_three_phase_circuits", "columns": [1, 2, 3],
        "values": {1: [1.00, 1.00, 1.00], 2: [0.97, 0.95, 0.93], 3: [0.96, 0.94, 0.90]},
    },
}

rows = []
not_tabulated = []
for arrangement_id, v in VARIANTS.items():
    for tray_count, values in v["values"].items():
        for grouped_units, factor in zip(v["columns"], values):
            query = {
                "installation_method": v["method"],
                "environment": "air",
                "table5e_branch": v["branch"],
                "support_family": v["support"],
                "contact_mode": v["contact_mode"],
                "cable_formation": v["formation"],
                "tray_count": tray_count,
                "grouped_units": grouped_units,
            }
            metadata = {
                "arrangement_id": arrangement_id,
                "installation_reference_items": v["items"],
                "group_unit_label": v["group_label"],
                "source_pages": [568] if v["method"] == "E" else [569],
                "document_page_marker": "Tablas - Pág. 21 de 82" if v["method"] == "E" else "Tablas - Pág. 22 de 82",
            }
            if factor is None:
                not_tabulated.append({"query": query, "source_token": "-", "metadata": metadata})
            else:
                rows.append({"query": query, "factor": factor, "metadata": metadata})

assert len(rows) == 134, len(rows)
assert len(not_tabulated) == 10, len(not_tabulated)

payload = json.loads(DATA.read_text(encoding="utf-8"))
payload["datasets"] = [d for d in payload["datasets"] if d.get("id") != DATASET_ID]
dataset = {
    "id": DATASET_ID,
    "profile_id": "PERU_CNE_UTIL_2006_030_004",
    "norm_reference_id": "PERU_CNE_UTILIZACION_2006",
    "table": "Tabla 5E",
    "axis": "grouping",
    "scope": {
        "installation_methods": ["E", "F"],
        "environment": ["air"],
        "table5e_branches": ["A_MULTICORE_CABLE_GROUPS", "B_SINGLE_CORE_3PH_CIRCUIT_GROUPS"],
        "support_families": ["perforated_trays", "vertical_perforated_trays", "ladder_trays_clamps_supports"],
        "contact_modes": ["contact", "spaced_as_figure"],
        "tray_counts": [1, 2, 3],
        "exact_lookup_only": True,
        "interpolation": False,
        "extrapolation": False,
        "complete_table_verified": True,
        "numeric_row_count": 134,
        "explicit_not_tabulated_count": 10,
        "accuracy_note": "Los valores son promedios; la extensión de valores es generalmente menor de ±5% según Nota 1.",
        "single_layer_only": True,
        "closer_spacing_policy": "Los factores deben reducirse para espaciamientos más cerrados que los publicados; MCP no infiere esa reducción.",
        "note": "Cobertura completa de Tabla 5E páginas 21-22: rama A método E y rama B método F, preservando disposiciones físicas y celdas '-'.",
    },
    "lookup_schema": {
        "type": "exact_rows_v1",
        "dimensions": [
            "installation_method", "environment", "table5e_branch", "support_family",
            "contact_mode", "cable_formation", "tray_count", "grouped_units"
        ],
        "value_field": "factor"
    },
    "rows": rows,
    "not_tabulated_cells": not_tabulated,
    "provenance": {
        "source_type": "primary_official",
        "verification_status": "PRIMARY_VERIFIED",
        "primary_source_id": "MINEM_CNE_UTIL_2006_OFFICIAL_PDF",
        "source_sha256": SOURCE_SHA,
        "authority": "Ministerio de Energía y Minas del Perú",
        "reference": "Código Nacional de Electricidad - Utilización, Tabla 5E",
        "page_references": [
            "PDF 548-549; Tabla 1: métodos E/F y remisión a Tabla 5E para grupos al aire libre",
            "PDF 568; Tablas - Pág. 21 de 82; Tabla 5E rama A",
            "PDF 569; Tablas - Pág. 22 de 82; Tabla 5E rama B",
        ],
        "verification_record": {
            "candidate_id": CANDIDATE_ID,
            "reviewer": "GPT-5.6 Sol",
            "review_mode": "AI_VISUAL_REVIEW_USER_AUTHORIZED",
            "review_authorized_by_user": True,
            "review_date": "2026-08-25",
            "review_result": "APPROVED",
            "review_confidence": "HIGH",
            "manual_comparison_confirmed": True,
            "complete_table_reviewed": True,
            "reviewed_numeric_row_count": 134,
            "reviewed_not_tabulated_count": 10,
            "human_reviewer": None,
        }
    },
    "usage_policy": {
        "development_lookup": True,
        "professional_emission": True,
        "requires_explicit_secondary_opt_in": False,
        "verified_subset_only": False,
        "p3c11_family_coverage": True,
        "automatic_binding_to_iz": False,
        "note": "Tabla 5E completa por lookup exacto. El binding automático se mantiene bloqueado hasta P3C11E2, que clasificará soporte/formación/separación en P3A."
    }
}
secondary_index = next((i for i, d in enumerate(payload["datasets"]) if d.get("id", "").endswith("SECONDARY_V1")), len(payload["datasets"]))
payload["datasets"].insert(secondary_index, dataset)
DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

cp = json.loads(CANDIDATES.read_text(encoding="utf-8"))
cp["candidates"] = [c for c in cp["candidates"] if c.get("id") != CANDIDATE_ID]
cp["candidates"].append({
    "id": CANDIDATE_ID,
    "status": "PRIMARY_TABLE_EVIDENCE_REVIEWED",
    "purpose": "grouping_correction_air_methods_e_f",
    "source_id": "MINEM_CNE_UTIL_2006_OFFICIAL_PDF",
    "norm_reference_id": "PERU_CNE_UTILIZACION_2006",
    "profile_id": "PERU_CNE_UTIL_2006_030_004",
    "source_sha256": SOURCE_SHA,
    "source_hash_match": True,
    "table": "Tabla 5E",
    "axis": "grouping",
    "pdf_pages": [568, 569],
    "document_page_markers": ["Tablas - Pág. 21 de 82", "Tablas - Pág. 22 de 82"],
    "routing_evidence": {
        "pdf_pages": [548, 549],
        "reference": "Tabla 1",
        "text_scope": "Métodos E/F al aire libre; Nota 5 remite a Tabla 5E para factores de reducción por grupos de circuitos al aire libre."
    },
    "candidate_structure": {
        "branch_a_method": "E",
        "branch_b_method": "F",
        "variant_count": len(VARIANTS),
        "numeric_row_count": len(rows),
        "explicit_not_tabulated_count": len(not_tabulated),
        "variants": {
            key: {
                "method": v["method"], "branch": v["branch"], "support": v["support"],
                "contact_mode": v["contact_mode"], "formation": v["formation"],
                "installation_reference_items": v["items"], "columns": v["columns"],
                "values": {str(k): values for k, values in v["values"].items()},
            }
            for key, v in VARIANTS.items()
        }
    },
    "reviewed_notes": {
        "single_layer_only": True,
        "average_value_spread": "generalmente menor de ±5%",
        "note2_page568": "300 mm de espaciamiento vertical entre bandejas y al menos 20 mm entre bandeja y pared; menor espaciamiento requiere reducción.",
        "note3_page568": "225 mm de espaciamiento horizontal entre bandejas espalda a espalda; menor espaciamiento requiere reducción.",
        "note2_page569": "Cada juego trifásico cuenta como un circuito cuando existen cables en paralelo por fase.",
        "note3_page569": "300 mm de espaciamiento vertical entre bandejas; menor espaciamiento requiere reducción.",
        "note4_page569": "225 mm horizontal entre bandejas espalda a espalda y al menos 20 mm a pared; menor espaciamiento requiere reducción."
    },
    "automated_extraction": {
        "workflow_run_id": 32912314189,
        "artifact_id": 9586942706,
        "artifact_digest": "sha256:ab88f4455ee09ed2332a878ddb06044515224635136fff1c5e34e69ed8cada8e",
        "page_render_generated": True,
        "page_text_extracted": True,
        "source_pin_verified": True
    },
    "manual_comparison_confirmed": True,
    "human_reviewer": None,
    "reviewer": "GPT-5.6 Sol",
    "review_mode": "AI_VISUAL_REVIEW_USER_AUTHORIZED",
    "review_authorized_by_user": True,
    "review_date": "2026-08-25",
    "review_result": "APPROVED",
    "review_confidence": "HIGH",
    "complete_table_reviewed": True,
    "eligible_for_primary_dataset_pr": True,
    "professional_emission": False,
    "notes": "Tabla 5E completa revisada visualmente desde las páginas 568-569 de la fuente oficial pinneada. Binding reservado para E2."
})
CANDIDATES.write_text(json.dumps(cp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

DOC.write_text('''# P3C11E1 — Tabla 5E primaria completa

Se incorpora la **Tabla 5E completa** del CNE Utilización como dataset `PRIMARY_VERIFIED` para agrupamiento de circuitos al aire libre.

## Evidencia

- fuente oficial pinneada: `MINEM_CNE_UTIL_2006_OFFICIAL_PDF`;
- SHA-256: `2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64`;
- rama A: PDF 568, `Tablas - Pág. 21 de 82`;
- rama B: PDF 569, `Tablas - Pág. 22 de 82`;
- routing/base: Tabla 1, PDF 548-549;
- captura reproducible: run `32912314189`, artifact `9586942706`;
- digest: `sha256:ab88f4455ee09ed2332a878ddb06044515224635136fff1c5e34e69ed8cada8e`.

## Dos ramas normativas

### A — cables multipolares, método E

Conserva tipo de soporte, contacto/espaciado, número de bandejas y número de cables. Se distinguen bandejas perforadas, bandejas perforadas verticales y bandejas de escalera/abrazaderas.

### B — circuitos trifásicos de cables unipolares, método F

Además de soporte, contacto/espaciado y número de bandejas, conserva la formación de los tres cables: horizontal, vertical o triángulo.

La Nota 2 de la rama B exige que, cuando exista más de un cable en paralelo por fase, **cada juego trifásico se considere un circuito** para seleccionar el factor.

## Cobertura completa

La publicación contiene:

```text
134 celdas numéricas
10 celdas marcadas "-"
```

Las 134 celdas numéricas se almacenan como filas `exact_rows_v1`. Las 10 posiciones no tabuladas se preservan explícitamente en `not_tabulated_cells`; no se inventa valor ni se interpola.

## Límites

- una sola capa de cables o grupos en triángulo según la rama;
- los valores son promedios y su extensión es generalmente menor de ±5 %;
- espaciamientos menores a los publicados requieren factores menores, que MCP **no infiere**;
- sin interpolación ni extrapolación.

## Política E1

- `p3c11_family_coverage=true`;
- `professional_emission=true` para lookups exactos dentro del dataset;
- `automatic_binding_to_iz=false`.

E1 cierra la cobertura numérica de 5E. E2 deberá clasificar de forma estructurada soporte, orientación, formación y separación antes de permitir 5E→`Iz` y mostrar esa evidencia en V3.
''', encoding="utf-8")

TEST.write_text('''import json
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
''', encoding="utf-8")

roadmap = ROADMAP.read_text(encoding="utf-8")
old = "5B y 5D ya disponen de cobertura primaria completa y binding seguro hacia Iz; 5A/5C parciales y 5E pendiente"
new = "5B, 5D y 5E ya disponen de cobertura primaria completa; 5B/5D además tienen binding seguro hacia Iz; 5A/5C permanecen parciales"
if old not in roadmap:
    raise SystemExit("Roadmap anchor P3C11E1 not found")
roadmap = roadmap.replace(old, new, 1)
ROADMAP.write_text(roadmap, encoding="utf-8")
