import pytest

from mcp_electrico import (
    ampacity, ampacity_base_binding, ampacity_exact_lookup, ampacity_factor_binding,
    conductor_library, core, visual_state, workspace_p3_view,
)

BASE_D = "PERU_CNE_UTIL_2006_TABLE_2_COL25_D_XLPE_3C_CU_70MM2_PRIMARY_V1"
FACTOR_5D = "PERU_CNE_UTIL_2006_TABLE_5D_GROUPING_METHOD_D_PRIMARY_V1"


def base_d():
    r = ampacity_exact_lookup.resolver_catalogo(BASE_D, {
        "installation_method": "D", "conductor_material": "Cu", "insulation": "XLPE_EPR",
        "temperature_c": 90, "loaded_conductors": 3, "section_mm2": 70.0,
    })
    assert r["status"] == "RESOLVED_EXACT"
    return ampacity_base_binding.construir_base_desde_resultado(r)


def factor5d(branch="B_MULTICORE_SINGLE_WAY_DUCTS", env="buried_duct", circuits=3, spacing="0_25_m"):
    r = ampacity_exact_lookup.resolver_catalogo(FACTOR_5D, {
        "installation_method": "D", "environment": env, "table5d_branch": branch,
        "burial_depth_m": 0.7, "soil_thermal_resistivity_k_m_per_w": 2.5,
        "circuits_grouped": circuits, "spacing_id": spacing,
    })
    assert r["status"] == "RESOLVED_EXACT"
    return ampacity_factor_binding.construir_factor_desde_resultado(r)


def setup_b(depth=0.7, rho=2.5, spacing="0_25_m"):
    core.crear_circuito("p3c11d2", 22.9); visual_state.reset(); conductor_library.reset(); ampacity.reset()
    core.agregar_linea("f_d", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    conductor_library.aplicar_conductor("Line.f_d", "NEXANS-N2XSY-18-30-CU-70-PH16", "buried_flat_20c")
    return ampacity.definir_aplicabilidad_normativa(
        "Line.f_d", "PERU_CNE_UTIL_2006_030_004", "D",
        ambiente="buried_duct", temperatura_ambiente_c=20.0,
        resistividad_termica_suelo_k_m_w=rho, profundidad_enterramiento_m=depth,
        circuitos_agrupados=3, rama_tabla_5d="B", separacion_tabla_5d_id=spacing,
    )


def test_cadena_100pct_primaria_d_tabla5d_b_llega_hasta_iz_y_v3():
    route = setup_b()
    assert route["status"] == "REQUIREMENTS_IDENTIFIED"
    assert route["grouping_context"]["table5d_branch"] == "B_MULTICORE_SINGLE_WAY_DUCTS"
    assert route["grouping_context"]["grouping_spacing_id"] == "0_25_m"
    profile = ampacity.definir_condiciones(
        "Line.f_d", "PERU_CNE_UTILIZACION_2006", 150.0,
        factores=[factor5d()], base_normativa=base_d(), ib_diseno_a=120.0,
        referencia_in="QF-D 150 A", referencia_ib="memoria P3C11D2",
        referencia_condiciones_instalacion="D / 5D-B / 3 circuitos / sep. 0.25 m / 0.7 m / rho 2.5",
    )
    check = profile["correction"]["compatibility_checks"][0]
    assert check["policy"] == "P3C11D2_TABLE_5D_EXACT_CONTEXT_V1"
    assert check["checked"]["spacing_id"] == "0_25_m"
    result = ampacity.evaluar("Line.f_d")
    assert result["status"] == "CUMPLE"
    assert result["values"]["iz_base_a"] == pytest.approx(178.0)
    assert result["values"]["factor_total"] == pytest.approx(0.85)
    assert result["values"]["iz_a"] == pytest.approx(151.3)
    assert result["automatic_normative_lookup"] is True
    detail = workspace_p3_view._factor_detail(result)
    assert "Tabla 5D" in detail
    assert "3 circuitos" in detail
    assert "5D-B multipolar/ducto" in detail
    assert "sep. 0.25 m" in detail
    assert "ρ=2.5 K·m/W" in detail
    assert "prof.=0.7 m" in detail


def test_routing_libre_legacy_permanece_manual_y_no_se_reinterpreta():
    core.crear_circuito("legacy5d", 22.9); visual_state.reset(); conductor_library.reset(); ampacity.reset()
    core.agregar_linea("f", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    route = ampacity.definir_aplicabilidad_normativa(
        "Line.f", "PERU_CNE_UTIL_2006_030_004", "D", ambiente="buried_duct",
        temperatura_ambiente_c=20, resistividad_termica_suelo_k_m_w=2.5,
        profundidad_enterramiento_m=0.7, circuitos_agrupados=3,
        disposicion_agrupamiento="descripcion libre histórica",
    )
    assert route["status"] == "MANUAL_REVIEW_REQUIRED"
    assert route["grouping_context"]["table5d_branch"] is None


def test_routing_5d_sin_clasificacion_estructurada_queda_missing_inputs():
    core.crear_circuito("missing5d", 22.9); visual_state.reset(); conductor_library.reset(); ampacity.reset()
    core.agregar_linea("f", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    route = ampacity.definir_aplicabilidad_normativa(
        "Line.f", "PERU_CNE_UTIL_2006_030_004", "D", ambiente="buried_duct",
        temperatura_ambiente_c=20, resistividad_termica_suelo_k_m_w=2.5,
        profundidad_enterramiento_m=0.7, circuitos_agrupados=3,
    )
    assert route["status"] == "MISSING_INPUTS"
    assert any("table5d_branch" in x for x in route["missing_parameters"])
    assert "grouping_spacing_id" in route["missing_parameters"]


def test_5d_no_se_vincula_fuera_de_07m_ni_rho25():
    route = setup_b(depth=0.8, rho=2.5)
    assert route["status"] == "MANUAL_REVIEW_REQUIRED"
    with pytest.raises(ValueError, match="P3C11D2009"):
        ampacity_factor_binding.validar_compatibilidad_contexto(factor5d(), route, base_d())
    route = setup_b(depth=0.7, rho=3.0)
    assert route["status"] == "MANUAL_REVIEW_REQUIRED"
    with pytest.raises(ValueError, match="P3C11D2010"):
        ampacity_factor_binding.validar_compatibilidad_contexto(factor5d(), route, base_d())


def test_factor_5d_debe_coincidir_con_rama_espaciado_y_numero():
    route = setup_b()
    with pytest.raises(ValueError, match="P3C11D2006"):
        ampacity_factor_binding.validar_compatibilidad_contexto(
            factor5d(spacing="0_5_m"), route, base_d()
        )
    with pytest.raises(ValueError, match="P3C11D2007"):
        ampacity_factor_binding.validar_compatibilidad_contexto(
            factor5d(circuits=2), route, base_d()
        )


def test_rama_a_direct_buried_es_explicita_y_no_se_confunde_con_5b():
    core.crear_circuito("direct5d", 22.9); visual_state.reset(); conductor_library.reset(); ampacity.reset()
    core.agregar_linea("f", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    route = ampacity.definir_aplicabilidad_normativa(
        "Line.f", "PERU_CNE_UTIL_2006_030_004", "D", ambiente="direct_buried",
        temperatura_ambiente_c=20, resistividad_termica_suelo_k_m_w=2.5,
        profundidad_enterramiento_m=0.7, circuitos_agrupados=2,
        rama_tabla_5d="A", separacion_tabla_5d_id="one_cable_diameter",
    )
    assert route["status"] == "REQUIREMENTS_IDENTIFIED"
    assert not any("Tabla 5B" in x for x in route["manual_review"])
    check = ampacity_factor_binding.validar_compatibilidad_contexto(
        factor5d("A_DIRECT_BURIED_CABLES", "direct_buried", 2, "one_cable_diameter"),
        route, base_d(),
    )
    assert check["policy"] == "P3C11D2_TABLE_5D_EXACT_CONTEXT_V1"


def test_rama_y_ambiente_incompatibles_se_rechazan_en_router():
    core.crear_circuito("bad5d", 22.9); visual_state.reset(); conductor_library.reset(); ampacity.reset()
    core.agregar_linea("f", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    with pytest.raises(ValueError, match="P3P011"):
        ampacity.definir_aplicabilidad_normativa(
            "Line.f", "PERU_CNE_UTIL_2006_030_004", "D", ambiente="buried_duct",
            temperatura_ambiente_c=20, resistividad_termica_suelo_k_m_w=2.5,
            profundidad_enterramiento_m=0.7, circuitos_agrupados=2,
            rama_tabla_5d="A", separacion_tabla_5d_id="contact",
        )
