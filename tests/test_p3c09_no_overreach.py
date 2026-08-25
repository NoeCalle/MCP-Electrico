from mcp_electrico import ampacity_datasets


DATASET = "PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_PRIMARY_V1"
ARRANGEMENT = "grouped_air_surface_embedded_enclosed"


def test_primary_5c_no_afirma_valores_no_revisados():
    item = ampacity_datasets.obtener_dataset(DATASET)
    assert set(item["values"]) == {"2", "3", "12"}

    result = ampacity_datasets.resolver_factor(
        DATASET,
        installation_method="C",
        circuits_grouped=4,
        arrangement_id=ARRANGEMENT,
    )
    assert result["status"] == "VALUE_NOT_TABULATED"
    assert result["factor"] is None
    assert result["professional_emission"] is False
