import pytest

from mcp_electrico import ampacity_datasets


DATASET = "PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_SECONDARY_V1"
ARRANGEMENT = "grouped_air_surface_embedded_enclosed"


def test_dataset_secundario_es_trazable_y_no_apto_para_emision():
    item = ampacity_datasets.obtener_dataset(DATASET)
    assert item["axis"] == "grouping"
    assert item["table"] == "Tabla 5C"
    assert item["provenance"]["source_type"] == "secondary_reproduction"
    assert item["provenance"]["verification_status"] == "PENDING_PRIMARY_VERIFICATION"
    assert item["usage_policy"]["professional_emission"] is False
    assert item["scope"]["interpolation"] is False
    assert item["scope"]["extrapolation"] is False


def test_lookup_secundario_bloqueado_por_defecto():
    result = ampacity_datasets.resolver_factor(
        DATASET,
        installation_method="C",
        circuits_grouped=3,
        arrangement_id=ARRANGEMENT,
    )
    assert result["status"] == "DATASET_NOT_APPROVED"
    assert result["factor"] is None
    assert result["professional_emission"] is False


@pytest.mark.parametrize(
    ("circuits", "expected"),
    [(2, 0.80), (3, 0.70), (12, 0.45)],
)
def test_lookup_secundario_explicito_reproduce_casos_fijados(circuits, expected):
    result = ampacity_datasets.resolver_factor(
        DATASET,
        installation_method="C",
        circuits_grouped=circuits,
        arrangement_id=ARRANGEMENT,
        allow_secondary=True,
    )
    assert result["status"] == "RESOLVED_SECONDARY"
    assert result["factor"] == pytest.approx(expected)
    assert result["professional_emission"] is False
    assert result["automatic_normative_lookup"] is False


def test_no_interpola_valor_no_tabualdo():
    result = ampacity_datasets.resolver_factor(
        DATASET,
        installation_method="C",
        circuits_grouped=10,
        arrangement_id=ARRANGEMENT,
        allow_secondary=True,
    )
    assert result["status"] == "VALUE_NOT_TABULATED"
    assert result["factor"] is None
    assert result["interpolation"] is False
    assert result["extrapolation"] is False
    assert 9 in result["available_exact_values"]
    assert 12 in result["available_exact_values"]


def test_rechaza_disposicion_o_metodo_fuera_de_alcance():
    bad_arrangement = ampacity_datasets.resolver_factor(
        DATASET,
        installation_method="C",
        circuits_grouped=3,
        arrangement_id="perforated_tray_single_layer",
        allow_secondary=True,
    )
    assert bad_arrangement["status"] == "SCOPE_MISMATCH"

    bad_method = ampacity_datasets.resolver_factor(
        DATASET,
        installation_method="G",
        circuits_grouped=3,
        arrangement_id=ARRANGEMENT,
        allow_secondary=True,
    )
    assert bad_method["status"] == "SCOPE_MISMATCH"


def test_route_lookup_usa_perfil_y_metodo_sin_promover_secundario():
    route = {
        "profile_id": "PERU_CNE_UTIL_2006_030_004",
        "installation_method": "C",
    }
    result = ampacity_datasets.resolver_grouping_for_route(
        route,
        circuits_grouped=3,
        arrangement_id=ARRANGEMENT,
        allow_secondary=True,
    )
    assert result["status"] == "RESOLVED_SECONDARY"
    assert result["factor"] == pytest.approx(0.70)
    assert result["professional_emission"] is False
