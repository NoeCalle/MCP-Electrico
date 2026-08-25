from mcp_electrico import ampacity_profiles


def test_metodo_d_agrupado_enruta_a_tabla_5d_y_exige_disposicion():
    result = ampacity_profiles.evaluar_aplicabilidad(
        profile_id="PERU_CNE_UTIL_2006_030_004",
        installation_method="D",
        environment="buried_duct",
        ambient_temperature_c=20.0,
        soil_thermal_resistivity_k_m_per_w=2.5,
        circuits_grouped=3,
    )
    assert result["status"] == "MISSING_INPUTS"
    assert "grouping_arrangement" in result["missing_parameters"]
    grouping = next(item for item in result["required_axes"] if item["axis"] == "grouping")
    assert grouping["required"] is True
    assert "Tabla 5D" in grouping["reference"]
    assert result["grouping_context"]["route"] == "Tabla 5D"


def test_metodo_d_con_disposicion_permanece_manual_hasta_dataset_5d():
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
    assert any("Tabla 5D" in item for item in result["manual_review"])
