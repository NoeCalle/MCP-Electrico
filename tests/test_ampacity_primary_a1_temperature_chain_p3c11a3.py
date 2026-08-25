import pytest

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


BASE_A1 = "PERU_CNE_UTIL_2006_TABLE_2_COL15_A1_XLPE_3C_CU_70MM2_PRIMARY_V1"
FACTOR_5A = "PERU_CNE_UTIL_2006_TABLE_5A_XLPE_AIR_A1_COL15_PRIMARY_V1"


def _preparar_linea(temp_c: float):
    core.crear_circuito("p3c11a3_primary_chain", 22.9)
    visual_state.reset()
    conductor_library.reset()
    ampacity.reset()
    core.agregar_linea("f_a1", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    assignment = conductor_library.aplicar_conductor(
        "Line.f_a1",
        "NEXANS-N2XSY-18-30-CU-70-PH16",
        "air_trefoil_30c",
    )
    route = ampacity.definir_aplicabilidad_normativa(
        "Line.f_a1",
        "PERU_CNE_UTIL_2006_030_004",
        "A1",
        ambiente="air",
        temperatura_ambiente_c=temp_c,
        circuitos_agrupados=1,
    )
    return assignment, route


def _resolver_base():
    result = ampacity_exact_lookup.resolver_catalogo(
        BASE_A1,
        {
            "installation_method": "A1",
            "conductor_material": "Cu",
            "insulation": "XLPE_EPR",
            "temperature_c": 90,
            "loaded_conductors": 3,
            "section_mm2": 70.0,
        },
    )
    assert result["status"] == "RESOLVED_EXACT"
    assert result["value"] == pytest.approx(179.0)
    assert result["row_metadata"]["table_column"] == 15
    assert result["verification_status"] == "PRIMARY_VERIFIED"
    assert result["professional_emission"] is True
    return ampacity_base_binding.construir_base_desde_resultado(result)


def _resolver_factor(temp_c: float):
    result = ampacity_exact_lookup.resolver_catalogo(
        FACTOR_5A,
        {
            "base_table": "Tabla 2",
            "base_table_column": 15,
            "installation_method": "A1",
            "insulation": "XLPE_EPR",
            "environment": "air",
            "ambient_temperature_c": temp_c,
        },
    )
    assert result["status"] == "RESOLVED_EXACT"
    assert result["verification_status"] == "PRIMARY_VERIFIED"
    assert result["professional_emission"] is True
    return ampacity_factor_binding.construir_factor_desde_resultado(result)


@pytest.mark.parametrize(
    ("temp_c", "expected_factor", "expected_iz"),
    [
        (35.0, 0.96, 171.84),
        (40.0, 0.91, 162.89),
    ],
)
def test_cadena_100pct_primaria_a1_llega_hasta_iz(temp_c, expected_factor, expected_iz):
    assignment, route = _preparar_linea(temp_c)
    assert assignment["ampacidad_aplicada_a"] == pytest.approx(296.0)
    assert route["installation_method"] == "A1"

    base = _resolver_base()
    factor = _resolver_factor(temp_c)

    profile = ampacity.definir_condiciones(
        "Line.f_a1",
        "PERU_CNE_UTILIZACION_2006",
        160.0,
        factores=[factor],
        base_normativa=base,
        ib_diseno_a=140.0,
        referencia_in="QF A1 160 A",
        referencia_ib="memoria de cargas P3C11A3",
        referencia_condiciones_instalacion="A1 / aire / Tabla 2 Col.15 / Tabla 5A verificados",
    )
    assert profile["correction"]["compatibility_checks"][0]["status"] == "COMPATIBLE_EXACT_FACTOR"

    result = ampacity.evaluar("Line.f_a1")
    assert result["status"] == "CUMPLE"
    assert result["values"]["iz_base_a"] == pytest.approx(179.0)
    assert result["values"]["factor_total"] == pytest.approx(expected_factor)
    assert result["values"]["iz_a"] == pytest.approx(expected_iz)
    assert result["checks"] == {"ib_le_in": True, "in_le_iz": True}
    assert result["base_evidence"]["primary"] is True
    assert result["base_evidence"]["table_column"] == 15
    assert result["factor_evidence"]["dataset_primary"] == 1
    assert result["factor_compatibility"][0]["compatible"] is True
    assert result["automatic_normative_lookup"] is True
    assert result["professional_emission"] is False

    base_detail = workspace_p3_view._base_evidence_detail(result)
    factor_detail = workspace_p3_view._factor_detail(result)
    assert "Tabla 2 col. 15" in base_detail
    assert BASE_A1 in base_detail
    assert f"k={expected_factor}" in factor_detail
    assert FACTOR_5A in factor_detail


def test_base_a1_no_extrapola_a_otra_seccion():
    result = ampacity_exact_lookup.resolver_catalogo(
        BASE_A1,
        {
            "installation_method": "A1",
            "conductor_material": "Cu",
            "insulation": "XLPE_EPR",
            "temperature_c": 90,
            "loaded_conductors": 3,
            "section_mm2": 50.0,
        },
    )
    assert result["status"] == "VALUE_NOT_TABULATED"
    assert result["value"] is None
    assert result["professional_emission"] is False
