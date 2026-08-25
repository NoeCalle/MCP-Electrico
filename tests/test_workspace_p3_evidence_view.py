from mcp_electrico import workspace_p3_view


def _item(correction_mode="EXPLICIT_FACTORS", evidence=None, automatic=False):
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
        "factor_evidence": evidence or {},
        "automatic_normative_lookup": automatic,
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
    snapshot = {
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
    html = workspace_p3_view._panel(snapshot)
    assert "Origen Iz base" in html
    assert "Evidencia factores" in html
    assert "CATÁLOGO P2" in html
    assert "SECUNDARIA" in html
    assert "236.8 A" in html
    assert "0.8" in html
    assert "UNDER_VALIDATION" in html
    assert html.count("<th>") == 11


def test_javascript_v3_no_contiene_logica_de_clasificacion_evidencia():
    script = workspace_p3_view._script()
    assert "dataset_primary" not in script
    assert "dataset_secondary" not in script
    assert "automatic_normative_lookup" not in script
    assert "SECUNDARIA" not in script
    assert "PRIMARIA" not in script
