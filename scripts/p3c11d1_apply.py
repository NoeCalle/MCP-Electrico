from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "mcp_electrico/data/ampacity_p3b_numeric_datasets.json"
CANDIDATES = ROOT / "mcp_electrico/data/ampacity_primary_review_candidates.json"
ROADMAP = ROOT / "docs/ROADMAP_PROFESIONAL.md"
DOC = ROOT / "docs/P3C11D_TABLE5D_PRIMARY.md"
TEST = ROOT / "tests/test_p3c11d_table5d_primary.py"

SOURCE_SHA = "2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64"
DATASET_ID = "PERU_CNE_UTIL_2006_TABLE_5D_GROUPING_METHOD_D_PRIMARY_V1"
CANDIDATE_ID = "P3C11D_TABLE_5D_GROUPING_METHOD_D_PRIMARY_REVIEW_CANDIDATE_V1"

BRANCHES = {
    "A_DIRECT_BURIED_CABLES": {
        "environment": "direct_buried",
        "source_page": 566,
        "marker": "Tablas - Pág. 19 de 82",
        "source_heading": "A.- Cables directamente apoyados en la tierra",
        "row_header": "Número de circuitos",
        "spacings": ["contact", "one_cable_diameter", "0_125_m", "0_25_m", "0_5_m"],
        "values": {
            2: [0.75, 0.80, 0.85, 0.90, 0.90],
            3: [0.65, 0.70, 0.75, 0.80, 0.85],
            4: [0.60, 0.60, 0.70, 0.75, 0.80],
            5: [0.55, 0.55, 0.65, 0.70, 0.80],
            6: [0.50, 0.55, 0.60, 0.70, 0.80],
        },
    },
    "B_MULTICORE_SINGLE_WAY_DUCTS": {
        "environment": "buried_duct",
        "source_page": 567,
        "marker": "Tablas - Pág. 20 de 82",
        "source_heading": "B.- Cable multipolar en ductos de una vía - enterrado",
        "row_header": "Número de cables",
        "spacings": ["contact", "0_25_m", "0_5_m", "1_0_m"],
        "values": {
            2: [0.85, 0.90, 0.95, 0.95],
            3: [0.75, 0.85, 0.90, 0.95],
            4: [0.70, 0.80, 0.85, 0.90],
            5: [0.65, 0.80, 0.85, 0.90],
            6: [0.60, 0.80, 0.80, 0.90],
        },
    },
    "C_SINGLE_CORE_SINGLE_WAY_DUCT_CIRCUITS": {
        "environment": "buried_duct",
        "source_page": 567,
        "marker": "Tablas - Pág. 20 de 82",
        "source_heading": "C.- Cables unipolares en ductos de una vía - enterrado",
        "row_header": "Número de circuitos unipolares de dos o tres cables",
        "spacings": ["contact", "0_25_m", "0_5_m", "1_0_m"],
        "values": {
            2: [0.80, 0.90, 0.90, 0.95],
            3: [0.70, 0.80, 0.85, 0.90],
            4: [0.65, 0.75, 0.80, 0.90],
            5: [0.60, 0.70, 0.80, 0.90],
            6: [0.60, 0.70, 0.80, 0.90],
        },
    },
}

rows = []
for branch_id, branch in BRANCHES.items():
    for circuits, factors in branch["values"].items():
        for spacing_id, factor in zip(branch["spacings"], factors):
            source_token = None
            normalization_note = None
            if branch_id == "C_SINGLE_CORE_SINGLE_WAY_DUCT_CIRCUITS" and circuits == 6 and spacing_id == "1_0_m":
                source_token = ",0,90"
                normalization_note = "El PDF imprime ',0,90'; se normaliza numéricamente a 0.90 conservando el token original."
            rows.append({
                "query": {
                    "installation_method": "D",
                    "environment": branch["environment"],
                    "table5d_branch": branch_id,
                    "burial_depth_m": 0.7,
                    "soil_thermal_resistivity_k_m_per_w": 2.5,
                    "circuits_grouped": circuits,
                    "spacing_id": spacing_id,
                },
                "factor": factor,
                "metadata": {
                    "source_page": branch["source_page"],
                    "document_page_marker": branch["marker"],
                    "source_heading": branch["source_heading"],
                    "source_row_header": branch["row_header"],
                    "source_token": source_token,
                    "normalization_note": normalization_note,
                    "average_rounding_error_note": "hasta ±10% según nota de Tabla 5D",
                    "precision_method_reference": "IEC 60287",
                },
            })

assert len(rows) == 65, len(rows)

payload = json.loads(DATA.read_text(encoding="utf-8"))
payload["datasets"] = [d for d in payload["datasets"] if d.get("id") != DATASET_ID]
dataset = {
    "id": DATASET_ID,
    "profile_id": "PERU_CNE_UTIL_2006_030_004",
    "norm_reference_id": "PERU_CNE_UTILIZACION_2006",
    "table": "Tabla 5D",
    "axis": "grouping",
    "scope": {
        "installation_methods": ["D"],
        "environments": ["direct_buried", "buried_duct"],
        "table5d_branches": list(BRANCHES),
        "burial_depth_m": [0.7],
        "soil_thermal_resistivity_k_m_per_w": [2.5],
        "circuits_grouped": [2, 3, 4, 5, 6],
        "exact_lookup_only": True,
        "interpolation": False,
        "extrapolation": False,
        "complete_table_verified": True,
        "accuracy_note": "Los valores son promedios; la nota de Tabla 5D indica errores de hasta ±10% por promedio/redondeo.",
        "precision_note": "Cuando se requieran valores más precisos, la propia tabla remite a IEC 60287.",
        "note": "Cobertura completa de las ramas A, B y C de Tabla 5D bajo sus condiciones publicadas de 0.7 m y 2.5 K.m/W."
    },
    "lookup_schema": {
        "type": "exact_rows_v1",
        "dimensions": [
            "installation_method",
            "environment",
            "table5d_branch",
            "burial_depth_m",
            "soil_thermal_resistivity_k_m_per_w",
            "circuits_grouped",
            "spacing_id"
        ],
        "value_field": "factor"
    },
    "rows": rows,
    "provenance": {
        "source_type": "primary_official",
        "verification_status": "PRIMARY_VERIFIED",
        "primary_source_id": "MINEM_CNE_UTIL_2006_OFFICIAL_PDF",
        "source_sha256": SOURCE_SHA,
        "authority": "Ministerio de Energía y Minas del Perú",
        "reference": "Código Nacional de Electricidad - Utilización, Tabla 5D",
        "page_references": [
            "PDF 555; Tablas - Pág. 8 de 82; Tabla 3: método D -> Tabla 5D para agrupamiento",
            "PDF 566; Tablas - Pág. 19 de 82; Tabla 5D rama A",
            "PDF 567; Tablas - Pág. 20 de 82; Tabla 5D ramas B y C"
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
            "reviewed_row_count": 65,
            "human_reviewer": None
        }
    },
    "usage_policy": {
        "development_lookup": True,
        "professional_emission": True,
        "requires_explicit_secondary_opt_in": False,
        "verified_subset_only": False,
        "p3c11_family_coverage": True,
        "automatic_binding_to_iz": False,
        "note": "Tabla 5D completa y verificable por lookup exacto. El binding automático a Iz permanece bloqueado hasta P3C11D2, que clasificará la disposición física y comprobará contexto P3A."
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
    "purpose": "grouping_correction_method_d",
    "source_id": "MINEM_CNE_UTIL_2006_OFFICIAL_PDF",
    "norm_reference_id": "PERU_CNE_UTILIZACION_2006",
    "profile_id": "PERU_CNE_UTIL_2006_030_004",
    "source_sha256": SOURCE_SHA,
    "source_hash_match": True,
    "table": "Tabla 5D",
    "axis": "grouping",
    "pdf_pages": [566, 567],
    "document_page_markers": ["Tablas - Pág. 19 de 82", "Tablas - Pág. 20 de 82"],
    "routing_evidence": {
        "pdf_page_number_one_based": 555,
        "document_page_marker": "Tablas - Pág. 8 de 82",
        "reference": "Tabla 3",
        "text_scope": "Método D -> Tabla 5D como factor de reducción por agrupamiento"
    },
    "candidate_structure": {
        "branches": {
            key: {
                "environment": value["environment"],
                "source_heading": value["source_heading"],
                "row_header": value["row_header"],
                "spacing_ids": value["spacings"],
                "values": {str(k): v for k, v in value["values"].items()}
            }
            for key, value in BRANCHES.items()
        },
        "row_count": 65,
        "burial_depth_m": 0.7,
        "soil_thermal_resistivity_k_m_per_w": 2.5
    },
    "publication_anomaly": {
        "location": "Rama C; 6 circuitos; separación 1,0 m",
        "source_token": ",0,90",
        "normalized_numeric_value": 0.90,
        "policy": "Preservar token original en metadata y normalizar solo su forma decimal."
    },
    "reviewed_notes": {
        "average_rounding_error": "hasta ±10%",
        "precision_method_reference": "IEC 60287",
        "published_depth_m": 0.7,
        "published_soil_thermal_resistivity_k_m_per_w": 2.5
    },
    "automated_extraction": {
        "workflow_run_id": 32911061659,
        "artifact_id": 9586544930,
        "artifact_digest": "sha256:927949b5276c1515e82f04fe605f5d045d832ca8f2ef3bd980c0f3c5fc587442",
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
    "notes": "Ramas A/B/C revisadas visualmente desde páginas renderizadas de la fuente oficial pinneada. Binding a Iz reservado para P3C11D2."
})
CANDIDATES.write_text(json.dumps(cp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

DOC.write_text('''# P3C11D1 — Tabla 5D primaria completa

Se incorpora la **Tabla 5D completa** del CNE Utilización como dataset numérico `PRIMARY_VERIFIED` de agrupamiento para método D.

## Evidencia primaria

- fuente: `MINEM_CNE_UTIL_2006_OFFICIAL_PDF`;
- SHA-256: `2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64`;
- Tabla 3 / routing: PDF 555, `Tablas - Pág. 8 de 82`;
- Tabla 5D rama A: PDF 566, `Tablas - Pág. 19 de 82`;
- Tabla 5D ramas B/C: PDF 567, `Tablas - Pág. 20 de 82`;
- captura reproducible: workflow run `32911061659`, artifact `9586544930`;
- digest artifact: `sha256:927949b5276c1515e82f04fe605f5d045d832ca8f2ef3bd980c0f3c5fc587442`.

## Estructura

La tabla no se reduce a un factor por número de circuitos. Se conservan tres ramas:

- `A_DIRECT_BURIED_CABLES`: cables directamente apoyados en tierra;
- `B_MULTICORE_SINGLE_WAY_DUCTS`: cable multipolar en ductos de una vía enterrados;
- `C_SINGLE_CORE_SINGLE_WAY_DUCT_CIRCUITS`: circuitos de cables unipolares en ductos de una vía enterrados.

Cada fila exige coincidencia exacta de rama, ambiente, número de circuitos/cables y separación.

## Condiciones publicadas

Los valores de Tabla 5D se publican para:

```text
profundidad = 0.7 m
resistividad térmica del suelo = 2.5 K·m/W
```

La nota de la tabla indica que son valores promedio y que el proceso de promedio/redondeo puede producir errores de hasta **±10 %**. Para valores más precisos remite a **IEC 60287**.

## Anomalía editorial preservada

En rama C, 6 circuitos y separación 1,0 m, el PDF imprime `,0,90`. El dataset conserva ese token en metadata y normaliza su valor numérico a `0.90`; no se oculta la anomalía de la publicación.

## Política

- `exact_rows_v1`;
- 65 filas verificadas;
- sin interpolación;
- sin extrapolación;
- `p3c11_family_coverage=true`;
- `automatic_binding_to_iz=false`.

D1 cierra **cobertura numérica de la familia 5D** dentro del alcance literal publicado, pero no habilita todavía su uso automático en `Iz`. P3C11D2 implementará clasificación de disposición y binding contextual.
''', encoding="utf-8")

TEST.write_text('''import json
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
''', encoding="utf-8")

roadmap = ROADMAP.read_text(encoding="utf-8")
old = "5B ya dispone de cobertura primaria completa + binding seguro hacia Iz; 5A/5C parciales y 5D/5E pendientes"
new = "5B y 5D ya disponen de cobertura primaria completa; 5B además tiene binding seguro hacia Iz; 5A/5C parciales y 5E pendiente"
if old not in roadmap:
    raise SystemExit("Roadmap anchor P3C11 not found")
roadmap = roadmap.replace(old, new, 1)
old2 = "- ampliar cobertura primaria de 5A/5B/5C/5D/5E según el alcance formal P3-v1 (`P3C11`);"
new2 = "- completar cobertura primaria pendiente de 5A/5C/5E y habilitar bindings seguros de las familias ya cubiertas según el alcance formal P3-v1 (`P3C11`);"
roadmap = roadmap.replace(old2, new2, 1)
ROADMAP.write_text(roadmap, encoding="utf-8")
