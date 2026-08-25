from mcp_electrico import workspace_p3_view


def _item(correction_mode="EXPLICIT_FACTORS", evidence=None, automatic=False, base_evidence=None):
    return {
        "element": "Line.f1",
        "status": "CUMPLE",
        "values": {
            "ib_a": 180.0,
            "in_a": 220.0,
            "iz_base_a": 296.0,
            "factor_total": 0.8,
            "iz_a": 236.8,
        },
        "sources": {"norm": {"id": "PERU_CNE_UTILIZACION_2006"}},
        "normative_applicability": {
            "profile_id": "PERU_CNE_UTIL_2006_030_004",
            "installation_method": "C",
            "status": "REQUIREMENTS_IDENTIFIED",
        },
        "installation": {"correction_mode": correction_mode},
        "base_evidence": base_evidence or {
            "origin": "P2_CATALOG",
            "normative_base": False,
            "primary": False,
            "professional_emission": False,
        },
        "factor_evidence": evidence or {},
        "automatic_normative_lookup": automatic,
    }


def _snapshot(item):
    return {
        "status": {
            "studies": {
                "ampacity": {
                    "valid": True,
                    "result": {
                        "alimentadores": [item],
                        "summary": {
                            "total": 1,
                            "cumple": 1,
                            "no_cumple": 0,
                            "datos_insuficientes": 0,
                        },
                    },
                }
            }
        }
    }


def test_etiquetas_evidencia_se_derivan_en_python():
    assert workspace_p3_view._evidence_label(_item(
        evidence={"total": 1, "manual": 0, "dataset_primary": 0, "dataset_secondary": 1}
    ))[0] == "SECUNDARIA"
    assert workspace_p3_view._evidence_label(_item(
        evidence={"total": 1, "manual": 1, "dataset_primary": 0, "dataset_secondary": 0}
    ))[0] == "MANUAL"
    assert workspace_p3_view._evidence_label(_item(
        evidence={"total": 1, "manual": 0, "dataset_primary": 1, "dataset_secondary": 0},
        automatic=True,
    ))[0] == "PRIMARIA"
    assert workspace_p3_view._evidence_label(_item(
        correction_mode="BASE_CONDITIONS_CONFIRMED"
    ))[0] == "BASE"
    assert workspace_p3_view._evidence_label(_item(
        evidence={"total": 2, "manual": 1, "dataset_primary": 0, "dataset_secondary": 1}
    ))[0] == "MIXTA"


def test_panel_muestra_evidencia_secundaria_y_valores_ya_calculados():
    item = _item(
        evidence={
            "total": 1,
            "manual": 0,
            "dataset_primary": 0,
            "dataset_secondary": 1,
            "contains_secondary": True,
            "automatic_normative_lookup": False,
        }
    )
    html = workspace_p3_view._panel(_snapshot(item))
    assert "Origen Iz base" in html
    assert "Tabla / dataset base" in html
    assert "Factores aplicados" in html
    assert "Evidencia factores" in html
    assert "CATÁLOGO P2" in html
    assert "SECUNDARIA" in html
    assert "236.8 A" in html
    assert "0.8" in html
    assert "UNDER_VALIDATION" in html
    assert html.count("<th>") == 13


def test_panel_muestra_tabla_columna_y_dataset_de_base_primaria_sin_lookup_en_browser():
    dataset_id = "PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1"
    item = _item(
        correction_mode="BASE_CONDITIONS_CONFIRMED",
        base_evidence={
            "origin": "P3B_BASE_DATASET",
            "normative_base": True,
            "primary": True,
            "professional_emission": True,
            "dataset_id": dataset_id,
            "table": "Tabla 2",
            "table_column": 23,
            "norm_reference_id": "PERU_CNE_UTILIZACION_2006",
            "verification_status": "PRIMARY_VERIFIED",
        },
    )
    html = workspace_p3_view._panel(_snapshot(item))
    assert "PRIMARIA" in html
    assert "Tabla 2 col. 23" in html
    assert dataset_id in html
    assert workspace_p3_view._base_evidence_detail(item) == f"Tabla 2 col. 23 · {dataset_id}"


def test_javascript_v3_no_contiene_logica_de_clasificacion_evidencia():
    script = workspace_p3_view._script()
    assert "dataset_primary" not in script
    assert "dataset_secondary" not in script
    assert "automatic_normative_lookup" not in script
    assert "SECUNDARIA" not in script
    assert "PRIMARIA" not in script
    assert "Tabla 2" not in script
    assert "ambient_temperature" not in script
