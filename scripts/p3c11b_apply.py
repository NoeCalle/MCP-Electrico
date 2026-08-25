import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
data_path = root / 'mcp_electrico/data/ampacity_p3b_numeric_datasets.json'
payload = json.loads(data_path.read_text(encoding='utf-8'))
dataset_id = 'PERU_CNE_UTIL_2006_TABLE_5B_SOIL_THERMAL_RESISTIVITY_METHOD_D_PRIMARY_V1'
payload['datasets'] = [d for d in payload['datasets'] if d.get('id') != dataset_id]
rows = []
for rho, factor in [(1.0, 1.18), (1.5, 1.10), (2.0, 1.05), (2.5, 1.00), (3.0, 0.96)]:
    rows.append({
        'query': {
            'base_table': 'Tabla 2',
            'installation_method': 'D',
            'environment': 'buried_duct',
            'burial_depth_scope': 'up_to_0_8_m',
            'soil_thermal_resistivity_k_m_per_w': rho,
        },
        'factor': factor,
        'metadata': {
            'base_soil_thermal_resistivity_k_m_per_w': 2.5,
            'max_burial_depth_m': 0.8,
            'factor_accuracy_note': '±5% según Nota 1 de Tabla 5B',
            'direct_buried_excluded': True,
        },
    })
dataset = {
    'id': dataset_id,
    'profile_id': 'PERU_CNE_UTIL_2006_030_004',
    'norm_reference_id': 'PERU_CNE_UTILIZACION_2006',
    'table': 'Tabla 5B',
    'axis': 'soil_thermal_resistivity',
    'scope': {
        'base_tables': ['Tabla 2'],
        'installation_methods': ['D'],
        'environment': ['buried_duct'],
        'burial_depth_scope': ['up_to_0_8_m'],
        'max_burial_depth_m': 0.8,
        'soil_thermal_resistivity_k_m_per_w': [1.0, 1.5, 2.0, 2.5, 3.0],
        'exact_lookup_only': True,
        'interpolation': False,
        'extrapolation': False,
        'complete_table_verified': True,
        'direct_buried_excluded': True,
        'accuracy_note': 'Los factores publicados tienen precisión indicada dentro de ±5%.',
        'note': 'Tabla 5B completa dentro de su alcance literal: método D, cables en ductos soterrados, profundidad hasta 0,8 m.',
    },
    'lookup_schema': {
        'type': 'exact_rows_v1',
        'dimensions': [
            'base_table', 'installation_method', 'environment',
            'burial_depth_scope', 'soil_thermal_resistivity_k_m_per_w',
        ],
        'value_field': 'factor',
    },
    'rows': rows,
    'provenance': {
        'source_type': 'primary_official',
        'verification_status': 'PRIMARY_VERIFIED',
        'primary_source_id': 'MINEM_CNE_UTIL_2006_OFFICIAL_PDF',
        'source_sha256': '2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64',
        'authority': 'Ministerio de Energía y Minas del Perú',
        'reference': 'Código Nacional de Electricidad - Utilización, Regla 030-004(9) y Tabla 5B',
        'page_references': [
            'PDF 37; Sección 030 - Pág. 2 de 11; Regla 030-004(9): método D y resistividad distinta de 2,5 K.m/W -> Tabla 5B',
            'PDF 564; Tablas - Pág. 17 de 82; Tabla 5B completa',
        ],
        'verification_record': {
            'candidate_id': 'P3C11B_TABLE_5B_SOIL_THERMAL_RESISTIVITY_PRIMARY_REVIEW_CANDIDATE_V1',
            'reviewer': 'GPT-5.6 Sol',
            'review_mode': 'AI_VISUAL_REVIEW_USER_AUTHORIZED',
            'review_authorized_by_user': True,
            'review_date': '2026-08-25',
            'review_result': 'APPROVED',
            'review_confidence': 'HIGH',
            'manual_comparison_confirmed': True,
            'complete_table_reviewed': True,
            'reviewed_values': {'1': 1.18, '1.5': 1.10, '2': 1.05, '2.5': 1.00, '3': 0.96},
            'reviewed_scope': {
                'installation_method': 'D', 'environment': 'buried_duct',
                'max_burial_depth_m': 0.8, 'direct_buried_excluded': True,
            },
        },
    },
    'usage_policy': {
        'development_lookup': True,
        'professional_emission': True,
        'requires_explicit_secondary_opt_in': False,
        'verified_subset_only': False,
        'p3c11_family_coverage': True,
        'automatic_binding_to_iz': False,
        'note': 'Cobertura primaria completa de Tabla 5B dentro del alcance literal publicado. El binding contextual hacia Iz permanece fail-closed hasta P3C11B2.',
    },
}
secondary_index = next((i for i, d in enumerate(payload['datasets']) if d.get('id', '').endswith('SECONDARY_V1')), len(payload['datasets']))
payload['datasets'].insert(secondary_index, dataset)
data_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

cand_path = root / 'mcp_electrico/data/ampacity_primary_review_candidates.json'
cp = json.loads(cand_path.read_text(encoding='utf-8'))
cid = 'P3C11B_TABLE_5B_SOIL_THERMAL_RESISTIVITY_PRIMARY_REVIEW_CANDIDATE_V1'
cp['candidates'] = [c for c in cp['candidates'] if c.get('id') != cid]
cp['candidates'].append({
    'id': cid,
    'status': 'PRIMARY_TABLE_EVIDENCE_REVIEWED',
    'purpose': 'soil_thermal_resistivity_correction',
    'source_id': 'MINEM_CNE_UTIL_2006_OFFICIAL_PDF',
    'norm_reference_id': 'PERU_CNE_UTILIZACION_2006',
    'profile_id': 'PERU_CNE_UTIL_2006_030_004',
    'source_sha256': '2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64',
    'source_hash_match': True,
    'table': 'Tabla 5B',
    'axis': 'soil_thermal_resistivity',
    'pdf_page_index_zero_based': 563,
    'pdf_page_number_one_based': 564,
    'document_page_marker': 'Tablas - Pág. 17 de 82',
    'rule_evidence': {
        'pdf_page_number_one_based': 37,
        'document_page_marker': 'Sección 030 - Pág. 2 de 11',
        'reference': 'Regla 030-004(9)',
        'text_scope': 'Método D; cables embutidos en ductos; resistividad distinta de 2,5 K.m/W; Tabla 5B',
    },
    'candidate_values': {'1': 1.18, '1.5': 1.10, '2': 1.05, '2.5': 1.00, '3': 0.96},
    'reviewed_notes': {
        'factor_accuracy': '±5%',
        'direct_buried': 'No se generaliza; Nota 2 distingue cables directamente apoyados en tierra.',
        'max_burial_depth_m': 0.8,
        'more_precise_method': 'IEC 60287 cuando se requieran valores más precisos',
    },
    'automated_extraction': {
        'workflow_run_id': 32907046624,
        'artifact_id': 9585177132,
        'artifact_digest': 'sha256:0acd2b81916e3b2bdbc0dd7e03304ce82fc05591a7672a31553be67e983423d3',
        'page_render_generated': True,
        'page_text_extracted': True,
        'source_pin_verified': True,
    },
    'manual_comparison_confirmed': True,
    'human_reviewer': None,
    'reviewer': 'GPT-5.6 Sol',
    'review_mode': 'AI_VISUAL_REVIEW_USER_AUTHORIZED',
    'review_authorized_by_user': True,
    'review_date': '2026-08-25',
    'review_result': 'APPROVED',
    'review_confidence': 'HIGH',
    'review_checks': [
        'Tabla 5B y marcador Tablas - Pág. 17 de 82 legibles',
        '1 K.m/W = 1.18', '1.5 K.m/W = 1.10', '2 K.m/W = 1.05',
        '2.5 K.m/W = 1.00', '3 K.m/W = 0.96',
        'Nota 2 limita la aplicación automática a ductos soterrados',
        'Nota 3 limita los factores a ductos hasta 0.8 m de profundidad',
        'Regla 030-004(9) confirma Tabla 5B para método D',
    ],
    'complete_table_reviewed': True,
    'eligible_for_primary_dataset_pr': True,
    'professional_emission': False,
    'notes': 'Tabla completa visualmente aprobada bajo autorización explícita del usuario. La cobertura numérica 5B puede declararse completa dentro del alcance literal, pero el binding a Iz queda para P3C11B2.',
})
cand_path.write_text(json.dumps(cp, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

(root / 'tests/test_p3c11b_table5b_primary.py').write_text(r'''import json
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
    assert dataset["usage_policy"]["automatic_binding_to_iz"] is False
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


def test_5b_no_puede_entrar_a_iz_antes_del_binding_contextual_b2():
    result = ampacity_exact_lookup.resolver_catalogo(DATASET, _query(3.0))
    factor = ampacity_factor_binding.construir_factor_desde_resultado(result)
    with pytest.raises(ValueError, match="P3C11A2004"):
        ampacity_factor_binding.validar_compatibilidad_contexto(
            factor,
            route={"profile_id": "PERU_CNE_UTIL_2006_030_004"},
            normative_base={"profile_id": "PERU_CNE_UTIL_2006_030_004"},
        )
''', encoding='utf-8')

(root / 'docs/P3C11B_TABLE5B_PRIMARY.md').write_text('''# P3C11B1 — Tabla 5B primaria completa

Se incorporó la Tabla 5B completa del CNE Utilización a partir de la fuente oficial pinneada.

Fuente: `MINEM_CNE_UTIL_2006_OFFICIAL_PDF`, SHA-256 `2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64`.

Página: PDF 564, `Tablas - Pág. 17 de 82`. La Regla 030-004(9), en PDF 37 / Sección 030 pág. 2 de 11, remite el método D a Tabla 5B cuando la resistividad térmica del suelo difiere de 2,5 K·m/W.

| Resistividad K·m/W | Factor |
| ---: | ---: |
| 1.0 | 1.18 |
| 1.5 | 1.10 |
| 2.0 | 1.05 |
| 2.5 | 1.00 |
| 3.0 | 0.96 |

La revisión visual fue realizada como `AI_VISUAL_REVIEW_USER_AUTHORIZED`, con `human_reviewer=null`.

## Límites preservados

- método D;
- cables en ductos soterrados;
- no se extrapola a cable directamente apoyado en tierra;
- profundidad máxima: **0,8 m**;
- precisión indicada: **±5 %**;
- para mayor precisión la norma remite a IEC 60287.

El lookup exige `environment=buried_duct` y `burial_depth_scope=up_to_0_8_m`; no interpola resistividades.

La tabla tiene `p3c11_family_coverage=true`, pero `automatic_binding_to_iz=false`. P3C11B2 añadirá profundidad al routing P3A y binding contextual hacia `Iz`. P3C11 global continúa `PENDING` y P4 bloqueada.
''', encoding='utf-8')

roadmap = root / 'docs/ROADMAP_PROFESIONAL.md'
text = roadmap.read_text(encoding='utf-8')
needle = '- `P3C11` — cobertura primaria de 5A/5B/5C/5D/5E;'
replacement = '- `P3C11` — cobertura primaria de 5A/5B/5C/5D/5E (**5B ya dispone de cobertura primaria completa; 5A/5C parciales y 5D/5E pendientes**);'
if needle in text:
    text = text.replace(needle, replacement, 1)
roadmap.write_text(text, encoding='utf-8')
