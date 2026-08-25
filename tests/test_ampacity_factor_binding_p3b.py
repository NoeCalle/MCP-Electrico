import pytest

from mcp_electrico import (
    ampacity,
    ampacity_datasets,
    ampacity_factor_binding,
    conductor_library,
    core,
    visual_state,
)


ARRANGEMENT = "grouped_air_surface_embedded_enclosed"
SECONDARY_DATASET = "PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_SECONDARY_V1"


def _linea():
    core.crear_circuito("ampacity_binding_test", 22.9)
    visual_state.reset()
    conductor_library.reset()
    ampacity.reset()
    core.agregar_linea("f_bind", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    conductor_library.aplicar_conductor(
        "Line.f_bind",
        "NEXANS-N2XSY-18-30-CU-70-PH16",
        "air_trefoil_30c",
    )
    route = ampacity.definir_aplicabilidad_normativa(
        "Line.f_bind",
        "PERU_CNE_UTIL_2006_030_004",
        "C",
        ambiente="air",
        temperatura_ambiente_c=30.0,
        circuitos_agrupados=2,
        disposicion_agrupamiento=ARRANGEMENT,
    )
    return route


def _factor_secundario(route):
    result = ampacity_datasets.resolver_factor(
        SECONDARY_DATASET,
        installation_method=route["installation_method"],
        circuits_grouped=2,
        arrangement_id=ARRANGEMENT,
        allow_secondary=True,
    )
    assert result["status"] == "RESOLVED_SECONDARY"
    assert result["factor"] == pytest.approx(0.80)
    return ampacity_factor_binding.construir_factor_desde_resultado(result)


def _definir(factor, permitir=False):
    return ampacity.definir_condiciones(
        "Line.f_bind",
        "PERU_CNE_UTILIZACION_2006",
        220,
        factores=[factor],
        permitir_factores_dataset_secundarios=permitir,
        ib_diseno_a=180,
        referencia_in="QF1 220 A",
        referencia_ib="memoria de cargas",
        referencia_condiciones_instalacion="método C y agrupamiento verificados en levantamiento",
    )


def test_factor_secundario_requiere_opt_in_al_entrar_a_ib_in_iz():
    route = _linea()
    factor = _factor_secundario(route)

    with pytest.raises(ValueError, match="P3B038"):
        _definir(factor, permitir=False)

    profile = _definir(factor, permitir=True)
    evidence = profile["correction"]["factor_evidence"]
    assert evidence == {
        "total": 1,
        "manual": 0,
        "dataset_primary": 0,
        "dataset_secondary": 1,
        "contains_secondary": True,
        "professional_factor_evidence": False,
        "automatic_normative_lookup": False,
    }
    assert profile["correction"]["automatic_normative_lookup"] is False

    stored = profile["correction"]["factors"][0]
    assert stored["origin"] == "P3B_DATASET"
    assert stored["dataset"]["id"] == SECONDARY_DATASET
    assert stored["dataset"]["verification_status"] == "PENDING_PRIMARY_VERIFICATION"
    assert stored["dataset"]["professional_emission"] is False

    result = ampacity.evaluar("Line.f_bind")
    assert result["status"] == "CUMPLE"
    assert result["values"]["factor_total"] == pytest.approx(0.80)
    assert result["values"]["iz_base_a"] == pytest.approx(296.0)
    assert result["values"]["iz_a"] == pytest.approx(236.8)
    assert result["automatic_normative_lookup"] is False
    assert result["professional_emission"] is False
    assert result["factor_evidence"]["contains_secondary"] is True


def test_factor_dataset_manipulado_se_bloquea():
    route = _linea()
    factor = _factor_secundario(route)
    factor["value"] = 0.81

    with pytest.raises(ValueError, match="P3B036"):
        _definir(factor, permitir=True)


def test_factor_dataset_con_query_manipulada_se_bloquea_o_deja_de_resolver():
    route = _linea()
    factor = _factor_secundario(route)
    factor["dataset"]["query"]["circuits_grouped"] = 3

    with pytest.raises(ValueError, match="P3B036"):
        _definir(factor, permitir=True)


def test_factor_manual_conserva_comportamiento_y_no_es_lookup_automatico():
    _linea()
    factor = {
        "id": "k_group_manual",
        "axis": "grouping",
        "value": 0.80,
        "reference": "factor manual verificado por ingeniería",
        "table_or_clause": "030-004(10) / Tabla 5C",
    }
    profile = _definir(factor)
    stored = profile["correction"]["factors"][0]
    assert stored["origin"] == "MANUAL"
    assert profile["correction"]["factor_evidence"]["manual"] == 1
    assert profile["correction"]["automatic_normative_lookup"] is False


def test_resumen_primario_solo_habilita_lookup_si_todos_los_factores_son_primarios():
    primary = {
        "origin": "P3B_DATASET",
        "dataset": {"professional_emission": True},
    }
    secondary = {
        "origin": "P3B_DATASET",
        "dataset": {"professional_emission": False},
    }
    manual = {"origin": "MANUAL"}

    assert ampacity_factor_binding.resumen_evidencia_factores([primary])["automatic_normative_lookup"] is True
    assert ampacity_factor_binding.resumen_evidencia_factores([primary, secondary])["automatic_normative_lookup"] is False
    assert ampacity_factor_binding.resumen_evidencia_factores([primary, manual])["automatic_normative_lookup"] is False
