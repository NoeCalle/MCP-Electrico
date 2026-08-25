from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"fragment not found in {path}: {old[:120]!r}")
    text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")


# P3A router: burial depth becomes an explicit declared input for Table 5B.
replace_once(
    "mcp_electrico/ampacity_profiles.py",
    "    soil_thermal_resistivity_k_m_per_w: float | None = None,\n    circuits_grouped: int = 1,",
    "    soil_thermal_resistivity_k_m_per_w: float | None = None,\n    burial_depth_m: float | None = None,\n    circuits_grouped: int = 1,",
)
replace_once(
    "mcp_electrico/ampacity_profiles.py",
    "    axes: list[dict[str, Any]] = []\n\n    env_raw = str(environment or \"\").strip().lower()",
    "    axes: list[dict[str, Any]] = []\n    depth: float | None = None\n\n    env_raw = str(environment or \"\").strip().lower()",
)
old_soil = '''    if method == "D":
        if env == "buried_duct":
            if soil_thermal_resistivity_k_m_per_w is None:
                missing.append("soil_thermal_resistivity_k_m_per_w")
            else:
                rho = float(soil_thermal_resistivity_k_m_per_w)
                if rho <= 0:
                    raise ValueError("P3P003: resistividad térmica del suelo debe ser positiva")
                rho_base = float(base["soil_thermal_resistivity_k_m_per_w"])
                changed = abs(rho - rho_base) > 1e-9
                axes.append(_axis(
                    "soil_thermal_resistivity",
                    changed,
                    "Regla 030-004(9) / Tabla 5B",
                    (
                        f"ρsuelo={rho:g} K·m/W difiere de base {rho_base:g} K·m/W."
                        if changed
                        else f"ρsuelo coincide con base {rho_base:g} K·m/W."
                    ),
                    TABLE_DATA_NOT_LOADED if changed else BASE_CONDITION,
                ))
        elif env == "direct_buried":
            manual.append(
                "P3A no extrapola la Tabla 5B a tendido directamente enterrado; "
                "la rama automatizada de 030-004(9) se limita a conductores en ductos enterrados."
            )
'''
new_soil = '''    if method == "D":
        if burial_depth_m is not None:
            depth = float(burial_depth_m)
            if depth <= 0:
                raise ValueError("P3P008: profundidad de enterramiento debe ser positiva")

        if env == "buried_duct":
            if soil_thermal_resistivity_k_m_per_w is None:
                missing.append("soil_thermal_resistivity_k_m_per_w")
            else:
                rho = float(soil_thermal_resistivity_k_m_per_w)
                if rho <= 0:
                    raise ValueError("P3P003: resistividad térmica del suelo debe ser positiva")
                rho_base = float(base["soil_thermal_resistivity_k_m_per_w"])
                changed = abs(rho - rho_base) > 1e-9
                axis_status = BASE_CONDITION
                detail = f"ρsuelo coincide con base {rho_base:g} K·m/W."
                if changed:
                    if depth is None:
                        missing.append("burial_depth_m")
                        axis_status = TABLE_DATA_NOT_LOADED
                    elif depth <= 0.8 + 1e-12:
                        axis_status = TABLE_DATA_NOT_LOADED
                    else:
                        axis_status = MANUAL_REVIEW_REQUIRED
                        manual.append(
                            f"Tabla 5B limita sus factores a ductos hasta 0,8 m; profundidad declarada={depth:g} m. "
                            "No se extrapola automáticamente; use revisión de ingeniería/IEC 60287."
                        )
                    detail = (
                        f"ρsuelo={rho:g} K·m/W difiere de base {rho_base:g} K·m/W; "
                        + (f"profundidad={depth:g} m." if depth is not None else "falta profundidad de enterramiento.")
                    )
                axes.append(_axis(
                    "soil_thermal_resistivity",
                    changed,
                    "Regla 030-004(9) / Tabla 5B",
                    detail,
                    axis_status,
                ))
        elif env == "direct_buried":
            manual.append(
                "P3A no extrapola la Tabla 5B a tendido directamente enterrado; "
                "la rama automatizada de 030-004(9) se limita a conductores en ductos enterrados."
            )
'''
replace_once("mcp_electrico/ampacity_profiles.py", old_soil, new_soil)
replace_once(
    "mcp_electrico/ampacity_profiles.py",
    '        "environment": env,\n        "base_conditions": deepcopy(base),',
    '        "environment": env,\n        "burial_context": {\n            "burial_depth_m": depth,\n            "table_5b_max_automatic_depth_m": 0.8 if method == "D" and env == "buried_duct" else None,\n        },\n        "base_conditions": deepcopy(base),',
)

# P3 public layer stores the declared depth in the routing snapshot.
replace_once(
    "mcp_electrico/ampacity.py",
    "    resistividad_termica_suelo_k_m_w: float | None = None,\n    circuitos_agrupados: int = 1,",
    "    resistividad_termica_suelo_k_m_w: float | None = None,\n    profundidad_enterramiento_m: float | None = None,\n    circuitos_agrupados: int = 1,",
)
replace_once(
    "mcp_electrico/ampacity.py",
    "        soil_thermal_resistivity_k_m_per_w=resistividad_termica_suelo_k_m_w,\n        circuits_grouped=circuitos_agrupados,",
    "        soil_thermal_resistivity_k_m_per_w=resistividad_termica_suelo_k_m_w,\n        burial_depth_m=profundidad_enterramiento_m,\n        circuits_grouped=circuitos_agrupados,",
)
replace_once(
    "mcp_electrico/ampacity.py",
    '''            "soil_thermal_resistivity_k_m_per_w": (
                float(resistividad_termica_suelo_k_m_w)
                if resistividad_termica_suelo_k_m_w is not None
                else None
            ),
            "circuits_grouped": int(circuitos_agrupados),''',
    '''            "soil_thermal_resistivity_k_m_per_w": (
                float(resistividad_termica_suelo_k_m_w)
                if resistividad_termica_suelo_k_m_w is not None
                else None
            ),
            "burial_depth_m": (
                float(profundidad_enterramiento_m)
                if profundidad_enterramiento_m is not None
                else None
            ),
            "circuits_grouped": int(circuitos_agrupados),''',
)

# MCP tool exposes the same explicit input.
replace_once(
    "mcp_electrico/ampacity_tools.py",
    "        resistividad_termica_suelo_k_m_w: float | None = None,\n        circuitos_agrupados: int = 1,",
    "        resistividad_termica_suelo_k_m_w: float | None = None,\n        profundidad_enterramiento_m: float | None = None,\n        circuitos_agrupados: int = 1,",
)
replace_once(
    "mcp_electrico/ampacity_tools.py",
    "            resistividad_termica_suelo_k_m_w=resistividad_termica_suelo_k_m_w,\n            circuitos_agrupados=circuitos_agrupados,",
    "            resistividad_termica_suelo_k_m_w=resistividad_termica_suelo_k_m_w,\n            profundidad_enterramiento_m=profundidad_enterramiento_m,\n            circuitos_agrupados=circuitos_agrupados,",
)

# Factor compatibility: keep Table 5A policy and add an explicit Table 5B policy.
binding = ROOT / "mcp_electrico/ampacity_factor_binding.py"
text = binding.read_text(encoding="utf-8")
start = text.index("def validar_compatibilidad_contexto(")
end = text.index("\ndef resumen_evidencia_factores", start)
new_function = r'''def validar_compatibilidad_contexto(
    factor: dict[str, Any],
    route: dict[str, Any] | None,
    normative_base: dict[str, Any] | None,
) -> dict[str, Any]:
    """Valida compatibilidad contextual de factores ``exact_rows_v1``.

    P3C11A2 habilita Tabla 5A (temperatura) y P3C11B2 habilita Tabla 5B
    (resistividad térmica del suelo). Cualquier otro eje genérico permanece
    fail-closed hasta declarar su propia política.
    """
    if str(factor.get("origin") or "") != DATASET_ORIGIN:
        return {"status": "MANUAL_FACTOR", "compatible": True, "policy": "manual_engineering"}

    meta = factor.get("dataset") or {}
    if meta.get("lookup_schema_type") != ampacity_exact_lookup.EXACT_ROWS_V1:
        return {"status": "LEGACY_FACTOR", "compatible": True, "policy": LEGACY_SCHEMA}

    axis = str(factor.get("axis") or "").strip().lower()
    if axis not in {"ambient_temperature", "soil_thermal_resistivity"}:
        raise ValueError(
            f"P3C11A2004: factor exact_rows_v1 axis={axis or 'NONE'} sin política de compatibilidad implementada"
        )
    if route is None:
        raise ValueError("P3C11A2005: factor normativo exacto requiere routing P3A vinculado")
    if normative_base is None:
        raise ValueError("P3C11A2006: factor normativo exacto requiere Iz_base normativa compatible; catálogo P2 no basta")

    query = meta.get("query") or {}
    base_meta = normative_base.get("dataset") or {}
    base_query = base_meta.get("query") or {}
    base_row = base_meta.get("row_metadata") or {}
    declared = route.get("declared_conditions") or {}

    factor_norm = str(factor.get("norm_reference_id") or "")
    factor_profile = str(factor.get("profile_id") or "")
    if factor_norm != str(normative_base.get("norm_reference_id") or ""):
        raise ValueError("P3C11A2007: factor e Iz_base pertenecen a referencias normativas distintas")
    if factor_profile != str(normative_base.get("profile_id") or ""):
        raise ValueError("P3C11A2008: factor e Iz_base pertenecen a perfiles distintos")
    if factor_profile != str(route.get("profile_id") or ""):
        raise ValueError("P3C11A2009: factor no coincide con perfil del routing P3A")

    expected_method = str(route.get("installation_method") or "")
    if str(query.get("installation_method") or "") != expected_method:
        raise ValueError("P3C11A2010: método del factor no coincide con routing P3A")
    if str(base_query.get("installation_method") or "") != expected_method:
        raise ValueError("P3C11A2011: método de Iz_base no coincide con routing P3A")

    if axis == "ambient_temperature":
        if str(query.get("environment") or "") != str(route.get("environment") or ""):
            raise ValueError("P3C11A2012: ambiente del factor 5A no coincide con routing P3A")
        if not _same_number(query.get("ambient_temperature_c"), declared.get("ambient_temperature_c")):
            raise ValueError("P3C11A2013: temperatura del factor 5A no coincide con la declarada en routing P3A")
        if str(query.get("base_table") or "") != str(normative_base.get("table") or ""):
            raise ValueError("P3C11A2014: tabla base declarada por 5A no coincide con Iz_base")
        if not _same_number(query.get("base_table_column"), base_row.get("table_column")):
            raise ValueError("P3C11A2015: columna base declarada por 5A no coincide con Iz_base")
        if str(query.get("insulation") or "") != str(base_query.get("insulation") or ""):
            raise ValueError("P3C11A2016: aislamiento del factor 5A no coincide con Iz_base")
        return {
            "status": "COMPATIBLE_EXACT_FACTOR",
            "compatible": True,
            "policy": "P3C11A2_TABLE_5A_EXACT_CONTEXT_V1",
            "axis": axis,
            "dataset_id": meta.get("id"),
            "base_dataset_id": base_meta.get("id"),
            "checked": {
                "norm_reference_id": factor_norm,
                "profile_id": factor_profile,
                "installation_method": expected_method,
                "environment": route.get("environment"),
                "ambient_temperature_c": declared.get("ambient_temperature_c"),
                "base_table": normative_base.get("table"),
                "base_table_column": base_row.get("table_column"),
                "insulation": base_query.get("insulation"),
            },
        }

    # P3C11B2 — Tabla 5B.
    if str(factor.get("table_or_clause") or "") != "Tabla 5B":
        raise ValueError("P3C11B2001: eje soil_thermal_resistivity requiere Tabla 5B")
    if expected_method != "D":
        raise ValueError("P3C11B2002: Tabla 5B automática solo se habilita para método D")
    if str(route.get("environment") or "") != "buried_duct":
        raise ValueError("P3C11B2003: Tabla 5B automática requiere cables en ductos enterrados")
    if str(query.get("environment") or "") != "buried_duct":
        raise ValueError("P3C11B2004: dataset 5B no corresponde a ambiente buried_duct")
    if str(query.get("base_table") or "") != str(normative_base.get("table") or ""):
        raise ValueError("P3C11B2005: tabla base declarada por 5B no coincide con Iz_base")
    if str(normative_base.get("table") or "") != "Tabla 2":
        raise ValueError("P3C11B2006: política 5B v1 requiere Iz_base de Tabla 2")
    if not _same_number(
        query.get("soil_thermal_resistivity_k_m_per_w"),
        declared.get("soil_thermal_resistivity_k_m_per_w"),
    ):
        raise ValueError("P3C11B2007: resistividad del factor 5B no coincide con routing P3A")
    depth = declared.get("burial_depth_m")
    if depth is None:
        raise ValueError("P3C11B2008: Tabla 5B requiere profundidad de enterramiento explícita")
    try:
        depth_value = float(depth)
    except (TypeError, ValueError) as exc:
        raise ValueError("P3C11B2009: profundidad de enterramiento no numérica") from exc
    if depth_value <= 0:
        raise ValueError("P3C11B2010: profundidad de enterramiento debe ser positiva")
    if depth_value > 0.8 + 1e-12:
        raise ValueError("P3C11B2011: Tabla 5B no se extrapola a profundidades mayores de 0,8 m")
    if str(query.get("burial_depth_scope") or "") != "up_to_0_8_m":
        raise ValueError("P3C11B2012: dataset 5B no declara el alcance de profundidad esperado")

    return {
        "status": "COMPATIBLE_EXACT_FACTOR",
        "compatible": True,
        "policy": "P3C11B2_TABLE_5B_EXACT_CONTEXT_V1",
        "axis": axis,
        "dataset_id": meta.get("id"),
        "base_dataset_id": base_meta.get("id"),
        "checked": {
            "norm_reference_id": factor_norm,
            "profile_id": factor_profile,
            "installation_method": expected_method,
            "environment": route.get("environment"),
            "soil_thermal_resistivity_k_m_per_w": declared.get("soil_thermal_resistivity_k_m_per_w"),
            "burial_depth_m": depth_value,
            "burial_depth_scope": query.get("burial_depth_scope"),
            "base_table": normative_base.get("table"),
        },
    }
'''
text = text[:start] + new_function + text[end:]
text = text.replace(
    "P3C11A2 añade soporte al schema genérico ``exact_rows_v1``. Para factores de\nTabla 5A la compatibilidad se valida contra routing P3A e Iz_base normativa:\nperfil, referencia, método, ambiente, temperatura, aislamiento, tabla y columna\nbase deben coincidir exactamente. Las familias genéricas futuras permanecen\nfail-closed hasta declarar su propia política de compatibilidad.",
    "P3C11A2 añade soporte al schema genérico ``exact_rows_v1`` para Tabla 5A.\nP3C11B2 incorpora Tabla 5B con validación explícita de método D, ducto enterrado,\nresistividad térmica y profundidad <= 0,8 m. Las familias genéricas futuras\npermanecen fail-closed hasta declarar su propia política de compatibilidad.",
)
binding.write_text(text, encoding="utf-8")

# V3 compactly exposes rho/depth scope already prepared by Python.
replace_once(
    "mcp_electrico/workspace_p3_view.py",
    '''        if query.get("circuits_grouped") is not None:
            context.append(f"{query.get('circuits_grouped')} circuitos")
        parts = [f"{axis}: k={value}"]''',
    '''        if query.get("circuits_grouped") is not None:
            context.append(f"{query.get('circuits_grouped')} circuitos")
        if query.get("soil_thermal_resistivity_k_m_per_w") is not None:
            context.append(f"ρ={_fmt(query.get('soil_thermal_resistivity_k_m_per_w'), 2)} K·m/W")
        if query.get("burial_depth_scope") == "up_to_0_8_m":
            context.append("prof. ≤0.8 m")
        parts = [f"{axis}: k={value}"]''',
)

# Add exact PRIMARY Iz_base for method D / Table 2 col.25 / Cu 70 mm² = 178 A.
data_path = ROOT / "mcp_electrico/data/ampacity_p3b_numeric_datasets.json"
payload = json.loads(data_path.read_text(encoding="utf-8"))
base_id = "PERU_CNE_UTIL_2006_TABLE_2_COL25_D_XLPE_3C_CU_70MM2_PRIMARY_V1"
payload["datasets"] = [d for d in payload["datasets"] if d.get("id") != base_id]
base_dataset = {
    "id": base_id,
    "profile_id": "PERU_CNE_UTIL_2006_030_004",
    "norm_reference_id": "PERU_CNE_UTILIZACION_2006",
    "table": "Tabla 2",
    "axis": "base_ampacity",
    "scope": {
        "installation_methods": ["D"],
        "conductor_materials": ["Cu"],
        "insulation": ["XLPE_EPR"],
        "temperature_c": [90],
        "loaded_conductors": [3],
        "section_mm2": [70.0],
        "table_column": 25,
        "exact_lookup_only": True,
        "interpolation": False,
        "extrapolation": False,
        "verified_subset_only": True,
        "note": "Iz_base primaria exacta para demostrar cadena P3C11B2 método D -> Tabla 5B -> Iz.",
    },
    "lookup_schema": {
        "type": "exact_rows_v1",
        "dimensions": ["installation_method", "conductor_material", "insulation", "temperature_c", "loaded_conductors", "section_mm2"],
        "value_field": "ampacity_a",
    },
    "rows": [{
        "query": {
            "installation_method": "D",
            "conductor_material": "Cu",
            "insulation": "XLPE_EPR",
            "temperature_c": 90,
            "loaded_conductors": 3,
            "section_mm2": 70.0,
        },
        "ampacity_a": 178.0,
        "metadata": {
            "table_column": 25,
            "routing_table": "Tabla 3",
            "routing": "Método D, XLPE/EPR, 3 conductores de carga -> Tabla 2 Col. 25",
        },
    }],
    "provenance": {
        "source_type": "primary_official",
        "verification_status": "PRIMARY_VERIFIED",
        "primary_source_id": "MINEM_CNE_UTIL_2006_OFFICIAL_PDF",
        "source_sha256": "2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64",
        "authority": "Ministerio de Energía y Minas del Perú",
        "reference": "Código Nacional de Electricidad - Utilización, Tabla 2 Col. 25; routing por Tabla 3",
        "page_references": [
            "PDF 552; Tablas - Pág. 5 de 82; Tabla 2; Método D; Cu 70 mm2; columna 25 = 178 A",
            "PDF 555; Tablas - Pág. 8 de 82; Tabla 3; D + XLPE/EPR + 3 conductores -> Tabla 2 Col. 25",
        ],
        "verification_record": {
            "candidate_id": "P3C11B2_TABLE_2_XLPE_D_3C_70MM2_PRIMARY_REVIEW_CANDIDATE_V1",
            "reviewer": "GPT-5.6 Sol",
            "review_mode": "AI_VISUAL_REVIEW_USER_AUTHORIZED",
            "review_authorized_by_user": True,
            "review_date": "2026-08-25",
            "review_result": "APPROVED",
            "review_confidence": "HIGH",
            "manual_comparison_confirmed": True,
            "reviewed_query": {
                "installation_method": "D", "conductor_material": "Cu", "insulation": "XLPE_EPR",
                "temperature_c": 90, "loaded_conductors": 3, "section_mm2": 70.0,
            },
            "reviewed_value": {"ampacity_a": 178.0},
        },
    },
    "usage_policy": {
        "development_lookup": True,
        "professional_emission": True,
        "requires_explicit_secondary_opt_in": False,
        "verified_subset_only": True,
        "p3c11_chain_support": True,
        "note": "Apto como Iz_base primaria únicamente para la consulta D/Cu/XLPE-EPR/3 conductores/70 mm2 exacta.",
    },
}
# Place the D base before factor tables.
insert_at = next((i for i, d in enumerate(payload["datasets"]) if d.get("table") == "Tabla 5A"), len(payload["datasets"]))
payload["datasets"].insert(insert_at, base_dataset)
for d in payload["datasets"]:
    if d.get("id") == "PERU_CNE_UTIL_2006_TABLE_5B_SOIL_THERMAL_RESISTIVITY_METHOD_D_PRIMARY_V1":
        d["usage_policy"]["automatic_binding_to_iz"] = True
        d["usage_policy"]["note"] = (
            "Cobertura primaria completa de Tabla 5B dentro del alcance literal publicado. "
            "P3C11B2 habilita binding hacia Iz únicamente para método D, buried_duct, profundidad <=0,8 m y consulta exacta."
        )
data_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Record the D base review separately; reuse the same pinned official-page capture.
cand_path = ROOT / "mcp_electrico/data/ampacity_primary_review_candidates.json"
cp = json.loads(cand_path.read_text(encoding="utf-8"))
cid = "P3C11B2_TABLE_2_XLPE_D_3C_70MM2_PRIMARY_REVIEW_CANDIDATE_V1"
cp["candidates"] = [c for c in cp["candidates"] if c.get("id") != cid]
cp["candidates"].append({
    "id": cid,
    "status": "PRIMARY_TABLE_EVIDENCE_REVIEWED",
    "purpose": "base_ampacity_for_table5b_primary_chain",
    "source_id": "MINEM_CNE_UTIL_2006_OFFICIAL_PDF",
    "norm_reference_id": "PERU_CNE_UTILIZACION_2006",
    "profile_id": "PERU_CNE_UTIL_2006_030_004",
    "source_sha256": "2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64",
    "source_hash_match": True,
    "table": "Tabla 2",
    "table_column": 25,
    "pdf_page_index_zero_based": 551,
    "pdf_page_number_one_based": 552,
    "document_page_marker": "Tablas - Pág. 5 de 82",
    "routing_evidence": {
        "table": "Tabla 3", "pdf_page_index_zero_based": 554, "pdf_page_number_one_based": 555,
        "document_page_marker": "Tablas - Pág. 8 de 82",
        "mapping": "Método D, XLPE/EPR, 3 conductores de carga -> Tabla 2 Col. 25",
    },
    "candidate_query": {
        "installation_method": "D", "conductor_material": "Cu", "insulation": "XLPE_EPR",
        "temperature_c": 90, "loaded_conductors": 3, "section_mm2": 70.0,
    },
    "candidate_value": {"ampacity_a": 178.0},
    "automated_extraction": {
        "workflow_run_id": 32880258067,
        "artifact_id": 9575497393,
        "artifact_digest": "sha256:601f536b1a621d0567fb31a556ba3e6f7758fbb99cd22f866ec4682832d9905b",
        "table_page_render_generated": True,
        "routing_page_render_generated": True,
        "source_pin_verified": True,
        "evidence_reused_from_same_verified_pages": True,
    },
    "manual_comparison_confirmed": True,
    "human_reviewer": None,
    "reviewer": "GPT-5.6 Sol",
    "review_mode": "AI_VISUAL_REVIEW_USER_AUTHORIZED",
    "review_authorized_by_user": True,
    "review_date": "2026-08-25",
    "review_result": "APPROVED",
    "review_confidence": "HIGH",
    "review_checks": [
        "Tabla 2 continuación legible en PDF 552",
        "Método D corresponde a columnas 24/25 para XLPE/EPR",
        "3 conductores cargados corresponde a columna 25",
        "Cu 70 mm2 en columna 25 = 178 A",
        "Tabla 3 confirma D + XLPE/EPR + 3 conductores -> Tabla 2 Col. 25",
    ],
    "eligible_for_primary_dataset_pr": True,
    "professional_emission": False,
    "notes": "Revisión visual aprobada bajo autorización del usuario, limitada a D/Col.25/70 mm2=178 A.",
})
cand_path.write_text(json.dumps(cp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Update B1 contract: data family remains complete and binding is now enabled.
b1 = ROOT / "tests/test_p3c11b_table5b_primary.py"
b1_text = b1.read_text(encoding="utf-8")
b1_text = b1_text.replace('assert dataset["usage_policy"]["automatic_binding_to_iz"] is False', 'assert dataset["usage_policy"]["automatic_binding_to_iz"] is True')
old_test = '''def test_5b_no_puede_entrar_a_iz_antes_del_binding_contextual_b2():
    result = ampacity_exact_lookup.resolver_catalogo(DATASET, _query(3.0))
    factor = ampacity_factor_binding.construir_factor_desde_resultado(result)
    with pytest.raises(ValueError, match="P3C11A2004"):
        ampacity_factor_binding.validar_compatibilidad_contexto(
            factor,
            route={"profile_id": "PERU_CNE_UTIL_2006_030_004"},
            normative_base={"profile_id": "PERU_CNE_UTIL_2006_030_004"},
        )
'''
new_test = '''def test_5b_binding_exige_contexto_completo_aunque_dataset_resuelva():
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
'''
if old_test not in b1_text:
    raise RuntimeError("old B1 fail-closed test not found")
b1.write_text(b1_text.replace(old_test, new_test, 1), encoding="utf-8")

# End-to-end real primary chain.
(ROOT / "tests/test_ampacity_table5b_binding_p3c11b2.py").write_text(r'''import pytest

from mcp_electrico import (
    ampacity,
    ampacity_base_binding,
    ampacity_exact_lookup,
    ampacity_factor_binding,
    conductor_library,
    core,
    visual_state,
    workspace_p3_view,
)

BASE_D = "PERU_CNE_UTIL_2006_TABLE_2_COL25_D_XLPE_3C_CU_70MM2_PRIMARY_V1"
FACTOR_5B = "PERU_CNE_UTIL_2006_TABLE_5B_SOIL_THERMAL_RESISTIVITY_METHOD_D_PRIMARY_V1"


def _setup(depth=0.8, rho=3.0):
    core.crear_circuito("p3c11b2_primary_chain", 22.9)
    visual_state.reset()
    conductor_library.reset()
    ampacity.reset()
    core.agregar_linea("f_d", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    assignment = conductor_library.aplicar_conductor(
        "Line.f_d", "NEXANS-N2XSY-18-30-CU-70-PH16", "buried_flat_20c"
    )
    route = ampacity.definir_aplicabilidad_normativa(
        "Line.f_d",
        "PERU_CNE_UTIL_2006_030_004",
        "D",
        ambiente="buried_duct",
        temperatura_ambiente_c=20.0,
        resistividad_termica_suelo_k_m_w=rho,
        profundidad_enterramiento_m=depth,
        circuitos_agrupados=1,
    )
    return assignment, route


def _base():
    r = ampacity_exact_lookup.resolver_catalogo(BASE_D, {
        "installation_method": "D", "conductor_material": "Cu", "insulation": "XLPE_EPR",
        "temperature_c": 90, "loaded_conductors": 3, "section_mm2": 70.0,
    })
    assert r["status"] == "RESOLVED_EXACT"
    assert r["value"] == pytest.approx(178.0)
    assert r["row_metadata"]["table_column"] == 25
    return ampacity_base_binding.construir_base_desde_resultado(r)


def _factor(rho=3.0):
    r = ampacity_exact_lookup.resolver_catalogo(FACTOR_5B, {
        "base_table": "Tabla 2",
        "installation_method": "D",
        "environment": "buried_duct",
        "burial_depth_scope": "up_to_0_8_m",
        "soil_thermal_resistivity_k_m_per_w": rho,
    })
    assert r["status"] == "RESOLVED_EXACT"
    return ampacity_factor_binding.construir_factor_desde_resultado(r)


def test_cadena_100pct_primaria_d_tabla5b_llega_hasta_iz_y_v3():
    assignment, route = _setup(depth=0.8, rho=3.0)
    assert assignment["ampacidad_aplicada_a"] == pytest.approx(246.0)
    assert route["installation_method"] == "D"
    assert route["environment"] == "buried_duct"
    assert route["declared_conditions"]["burial_depth_m"] == pytest.approx(0.8)

    profile = ampacity.definir_condiciones(
        "Line.f_d", "PERU_CNE_UTILIZACION_2006", 160.0,
        factores=[_factor(3.0)], base_normativa=_base(),
        ib_diseno_a=140.0,
        referencia_in="QF-D 160 A",
        referencia_ib="memoria de cargas P3C11B2",
        referencia_condiciones_instalacion="D / buried_duct / profundidad 0,8 m / rho 3 K.m/W",
    )
    check = profile["correction"]["compatibility_checks"][0]
    assert check["status"] == "COMPATIBLE_EXACT_FACTOR"
    assert check["policy"] == "P3C11B2_TABLE_5B_EXACT_CONTEXT_V1"
    assert check["checked"]["burial_depth_m"] == pytest.approx(0.8)

    result = ampacity.evaluar("Line.f_d")
    assert result["status"] == "CUMPLE"
    assert result["values"]["iz_base_a"] == pytest.approx(178.0)
    assert result["values"]["factor_total"] == pytest.approx(0.96)
    assert result["values"]["iz_a"] == pytest.approx(170.88)
    assert result["automatic_normative_lookup"] is True
    assert result["professional_emission"] is False

    factor_detail = workspace_p3_view._factor_detail(result)
    assert "ρ=3 K·m/W" in factor_detail
    assert "prof. ≤0.8 m" in factor_detail
    assert "Tabla 5B" in factor_detail
    assert FACTOR_5B in factor_detail


def test_router_5b_exige_profundidad_si_rho_difiere_de_base():
    core.crear_circuito("p3c11b2_missing_depth", 22.9)
    visual_state.reset(); conductor_library.reset(); ampacity.reset()
    core.agregar_linea("f_d", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    conductor_library.aplicar_conductor("Line.f_d", "NEXANS-N2XSY-18-30-CU-70-PH16", "buried_flat_20c")
    route = ampacity.definir_aplicabilidad_normativa(
        "Line.f_d", "PERU_CNE_UTIL_2006_030_004", "D",
        ambiente="buried_duct", temperatura_ambiente_c=20.0,
        resistividad_termica_suelo_k_m_w=3.0, circuitos_agrupados=1,
    )
    assert "burial_depth_m" in route["missing_parameters"]


def test_profundidad_mayor_08m_permanece_fail_closed():
    _, route = _setup(depth=1.0, rho=3.0)
    assert route["status"] == "MANUAL_REVIEW_REQUIRED"
    factor = _factor(3.0)
    with pytest.raises(ValueError, match="P3C11B2011"):
        ampacity_factor_binding.validar_compatibilidad_contexto(factor, route, _base())


def test_rho_del_factor_debe_coincidir_con_routing():
    _, route = _setup(depth=0.8, rho=3.0)
    with pytest.raises(ValueError, match="P3C11B2007"):
        ampacity_factor_binding.validar_compatibilidad_contexto(_factor(2.0), route, _base())
''', encoding="utf-8")

# Documentation / roadmap sync.
(ROOT / "docs/P3C11B2_TABLE5B_BINDING.md").write_text('''# P3C11B2 — Binding seguro Tabla 5B → Iz

## Resultado

P3C11B1 incorporó la Tabla 5B completa como evidencia primaria. B2 conecta esa familia al cálculo P3 sin relajar sus límites normativos.

La profundidad de enterramiento pasa a ser un dato explícito del routing P3A para método D cuando la resistividad del suelo difiere de 2,5 K·m/W.

## Iz_base primaria D

La fuente oficial pinneada confirma:

```text
Tabla 2
Método D
Cu
XLPE/EPR 90 °C
3 conductores cargados
70 mm²
Columna 25
Iz_base = 178 A
```

Tabla 3 confirma D + XLPE/EPR + 3 conductores → Tabla 2 Col. 25.

## Cadena real

Para ducto enterrado a 0,8 m y rho = 3 K·m/W:

```text
Iz_base = 178 A       Tabla 2 Col.25 PRIMARY_VERIFIED
k_rho   = 0.96        Tabla 5B PRIMARY_VERIFIED
Iz      = 170.88 A
```

El resultado se calcula en Python; no se almacena como valor normativo independiente.

## Fail-closed

Tabla 5B solo entra a Iz cuando coinciden exactamente:

- referencia normativa y perfil;
- método D;
- `environment=buried_duct`;
- `Iz_base` de Tabla 2;
- resistividad declarada y fila exacta de 5B;
- profundidad positiva y <= 0,8 m;
- `burial_depth_scope=up_to_0_8_m`.

Profundidad >0,8 m, ausencia de profundidad, `direct_buried` o resistividad no tabulada no se extrapolan.

## V3

La vista continúa sin calcular ingeniería. Para factores 5B muestra desde Python el `k`, la resistividad y el alcance de profundidad junto con Tabla/dataset.

## Roadmap

La familia 5B queda **cubierta y vinculada**. P3C11 continúa PENDING por 5A/5C parciales y 5D/5E pendientes. P4 sigue bloqueada.
''', encoding="utf-8")

roadmap = ROOT / "docs/ROADMAP_PROFESIONAL.md"
rtext = roadmap.read_text(encoding="utf-8")nrtext = rtext.replace(
    "5B ya dispone de cobertura primaria completa; 5A/5C parciales y 5D/5E pendientes",
    "5B ya dispone de cobertura primaria completa + binding seguro hacia Iz; 5A/5C parciales y 5D/5E pendientes",
)
roadmap.write_text(rtext, encoding="utf-8")
