from mcp_electrico import ampacity_datasets


ARRANGEMENT = "grouped_air_surface_embedded_enclosed"


def test_lookup_bloquea_cantidad_distinta_del_routing():
    route = {
        "profile_id": "PERU_CNE_UTIL_2006_030_004",
        "installation_method": "C",
        "grouping_context": {
            "circuits_grouped": 3,
            "arrangement": ARRANGEMENT,
            "route": "Tabla 5C",
        },
    }
    result = ampacity_datasets.resolver_grouping_for_route(
        route,
        circuits_grouped=4,
        arrangement_id=ARRANGEMENT,
        allow_secondary=True,
    )
    assert result["status"] == "ROUTE_MISMATCH"
    assert result["factor"] is None
    assert result["professional_emission"] is False


def test_lookup_bloquea_disposicion_distinta_del_routing():
    route = {
        "profile_id": "PERU_CNE_UTIL_2006_030_004",
        "installation_method": "C",
        "grouping_context": {
            "circuits_grouped": 3,
            "arrangement": ARRANGEMENT,
            "route": "Tabla 5C",
        },
    }
    result = ampacity_datasets.resolver_grouping_for_route(
        route,
        circuits_grouped=3,
        arrangement_id="perforated_tray_single_layer",
        allow_secondary=True,
    )
    assert result["status"] == "ROUTE_MISMATCH"
    assert result["factor"] is None
