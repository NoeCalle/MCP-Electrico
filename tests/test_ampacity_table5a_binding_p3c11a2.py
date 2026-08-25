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


FACTOR_5A = "PERU_CNE_UTIL_2006_TABLE_5A_XLPE_AIR_A1_COL15_PRIMARY_V1"
BASE_C23 = "PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1"


def _linea_a1(temp_c=35.0):
    core.crear_circuito("p3c11a2_binding", 22.9)
    visual_state.reset()
    conductor_library.reset()
    ampacity.reset()
    core.agregar_linea("f_temp", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    conductor_library.aplicar_conductor(
        "Line.f_temp",
        "NEXANS-N2XSY-18-30-CU-70-PH16",
        "air_trefoil_30c",
    )
    return ampacity.definir_aplicabilidad_normativa(
        "Line.f_temp",
        "PERU_CNE_UTIL_2006_030_004",
        "A1",
        ambiente="air",
        temperatura_ambiente_c=temp_c,
        circuitos_agrupados=1,
    )


def _factor_5a(temp_c=35.0):
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
    return ampacity_factor_binding.construir_factor_desde_resultado(result)


def _base_c23_real():
    result = ampacity_exact_lookup.resolver_catalogo(
        BASE_C23,
        {
            "installation_method": "C",
            "conductor_material": "Cu",
            "insulation": "XLPE_EPR",
            "temperature_c": 90,
            "loaded_conductors": 3,
            "section_mm2": 70.0,
        },
    )
    assert result["status"] == "RESOLVED_EXACT"
    return ampacity_base_binding.construir_base_desde_resultado(result)


def _base_a1_sintetica():
    return {
        "origin": "P3B_BASE_DATASET",
        "ampacity_a": 180.0,
        "table": "Tabla 2",
        "axis": "base_ampacity",
        "norm_reference_id": "PERU_CNE_UTILIZACION_2006",
        "profile_id": "PERU_CNE_UTIL_2006_030_004",
        "dataset": {
            "id": "SYNTHETIC_A1_COL15_PRIMARY",
            "query": {
                "installation_method": "A1",
                "conductor_material": "Cu",
                "insulation": "XLPE_EPR",
                "temperature_c": 90,
                "loaded_conductors": 3,
                "section_mm2": 70.0,
            },
            "row_metadata": {"table_column": 15},
            "verification_status": "PRIMARY_VERIFIED",
            "professional_emission": True,
            "automatic_normative_lookup": True,
            "provenance": {"fixture_only": True},
        },
    }


def _definir(factor, base):
    return ampacity.definir_condiciones(
        "Line.f_temp",
        "PERU_CNE_UTILIZACION_2006",
        150,
        factores=[factor],
        base_normativa=base,
        ib_diseno_a=100,
        referencia_in="QF 150 A",
        referencia_ib="memoria de cargas",
        referencia_condiciones_instalacion="routing A1 y temperatura verificados",
    )


def test_lookup_5a_generico_conserva_query_metadata_y_evidencia_primaria():
    factor = _factor_5a(35)
    assert factor["origin"] == "P3B_DATASET"
    assert factor["axis"] == "ambient_temperature"
    assert factor["value"] == pytest.approx(0.96)
    assert factor["table_or_clause"] == "Tabla 5A"
    assert factor["dataset"]["lookup_schema_type"] == "exact_rows_v1"
    assert factor["dataset"]["professional_emission"] is True
    assert factor["dataset"]["row_metadata"]["base_temperature_c"] == 30
    assert factor["dataset"]["query"]["base_table_column"] == 15


def test_factor_5a_sin_iz_base_normativa_se_bloquea():
    _linea_a1(35)
    factor = _factor_5a(35)
    with pytest.raises(ValueError, match="P3C11A2006"):
        _definir(factor, None)


def test_factor_a1_col15_rechaza_la_base_primaria_real_c_col23():
    _linea_a1(35)
    factor = _factor_5a(35)
    base = _base_c23_real()
    assert base["dataset"]["row_metadata"]["table_column"] == 23
    with pytest.raises(ValueError, match="P3C11A2011|P3C11A2015"):
        _definir(factor, base)


def test_binding_compatible_llega_a_iz_y_se_revalida_al_cambiar_routing(monkeypatch):
    _linea_a1(35)
    factor = _factor_5a(35)
    base = _base_a1_sintetica()

    monkeypatch.setattr(
        ampacity_base_binding,
        "validar_base_dataset",
        lambda item, permitir_secundario=False: _base_a1_sintetica(),
    )

    profile = _definir(factor, base)
    check = profile["correction"]["compatibility_checks"][0]
    assert check["status"] == "COMPATIBLE_EXACT_FACTOR"
    assert check["checked"]["base_table_column"] == 15
    assert check["checked"]["ambient_temperature_c"] == pytest.approx(35.0)

    result = ampacity.evaluar("Line.f_temp")
    assert result["status"] == "CUMPLE"
    assert result["values"]["iz_base_a"] == pytest.approx(180.0)
    assert result["values"]["factor_total"] == pytest.approx(0.96)
    assert result["values"]["iz_a"] == pytest.approx(172.8)
    assert result["automatic_normative_lookup"] is True
    assert result["factor_compatibility"][0]["compatible"] is True

    ampacity.definir_aplicabilidad_normativa(
        "Line.f_temp",
        "PERU_CNE_UTIL_2006_030_004",
        "A1",
        ambiente="air",
        temperatura_ambiente_c=40.0,
        circuitos_agrupados=1,
    )
    stale = ampacity.evaluar("Line.f_temp")
    assert stale["status"] == "DATOS_INSUFICIENTES"
    assert stale["missing"] == ["consistencia_factores_normativos"]
    assert "P3C11A2013" in stale["note"]


def test_factor_generico_manipulado_se_revalida_contra_catalogo():
    factor = _factor_5a(35)
    factor["value"] = 0.95
    with pytest.raises(ValueError, match="P3B036"):
        ampacity_factor_binding.validar_factor_dataset(factor)


def test_v3_muestra_columna_base_y_trazabilidad_del_factor_preparada_en_python():
    factor = _factor_5a(35)
    item = {
        "base_evidence": {
            "table": "Tabla 2",
            "table_column": 15,
            "dataset_id": "SYNTHETIC_A1_COL15_PRIMARY",
        },
        "sources": {"factors": [factor]},
    }
    base_detail = workspace_p3_view._base_evidence_detail(item)
    factor_detail = workspace_p3_view._factor_detail(item)
    assert "Tabla 2 col. 15" in base_detail
    assert "ambient_temperature: k=0.96" in factor_detail
    assert "Tabla 5A" in factor_detail
    assert "35 °C" in factor_detail
    assert FACTOR_5A in factor_detail
