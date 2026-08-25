from mcp_electrico import ampacity_profiles


def test_metodo_d_agrupado_enruta_a_tabla_5d_y_exige_clasificacion_estructurada():
    result = ampacity_profiles.evaluar_aplicabilidad(
        profile_id="PERU_CNE_UTIL_2006_030_004",
        installation_method="D",
        environment="buried_duct",
        ambient_temperature_c=20.0,
        soil_thermal_resistivity_k_m_per_w=2.5,
        circuits_grouped=3,
    )
    assert result["status"] == "MISSING_INPUTS"
    assert "table5d_branch: A | B | C" in result["missing_parameters"]
    assert "grouping_spacing_id" in result["missing_parameters"]
    grouping = next(item for item in result["required_axes"] if item["axis"] == "grouping")
    assert grouping["required"] is True
    assert "Tabla 5D" in grouping["reference"]
    assert result["grouping_context"]["route"] == "Tabla 5D"


def test_metodo_d_con_disposicion_libre_legacy_permanece_manual_en_d2():
    result = ampacity_profiles.evaluar_aplicabilidad(
        profile_id="PERU_CNE_UTIL_2006_030_004",
        installation_method="D",
        environment="buried_duct",
        ambient_temperature_c=20.0,
        soil_thermal_resistivity_k_m_per_w=2.5,
        circuits_grouped=3,
        grouping_arrangement="ducts_contact",
    )
    assert result["status"] == "MANUAL_REVIEW_REQUIRED"
    assert not result["missing_parameters"]
    assert result["unresolved_numeric_factors"] is True
    assert any("P3C11D2" in item for item in result["manual_review"])
    assert result["grouping_context"]["table5d_branch"] is None
    assert result["grouping_context"]["grouping_spacing_id"] is None
