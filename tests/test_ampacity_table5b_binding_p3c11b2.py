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
