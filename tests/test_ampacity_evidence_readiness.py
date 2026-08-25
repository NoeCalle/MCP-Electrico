import pytest

from mcp_electrico import (
    ampacity,
    ampacity_datasets,
    ampacity_evidence_readiness,
    ampacity_factor_binding,
    conductor_library,
    core,
    engine_selection,
    visual_state,
)


ARRANGEMENT = "grouped_air_surface_embedded_enclosed"


def _base_line():
    core.crear_circuito("ampacity_evidence_readiness_test", 22.9)
    visual_state.reset()
    conductor_library.reset()
    ampacity.reset()
    core.agregar_linea("f_ev", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    conductor_library.aplicar_conductor(
        "Line.f_ev",
        "NEXANS-N2XSY-18-30-CU-70-PH16",
        "air_trefoil_30c",
    )


def _route_grouped():
    return ampacity.definir_aplicabilidad_normativa(
        "Line.f_ev",
        "PERU_CNE_UTIL_2006_030_004",
        "C",
        ambiente="air",
        temperatura_ambiente_c=30.0,
        circuitos_agrupados=2,
        disposicion_agrupamiento=ARRANGEMENT,
    )


def _secondary_factor(route):
    result = ampacity_datasets.resolver_grouping_for_route(
        route,
        circuits_grouped=2,
        arrangement_id=ARRANGEMENT,
        allow_secondary=True,
    )
    return ampacity_factor_binding.construir_factor_desde_resultado(result)


def test_sin_perfiles_evidencia_no_configurada():
    _base_line()
    result = ampacity_evidence_readiness.evaluar()
    assert result["status"] == "NOT_CONFIGURED"
    assert result["professional_normative_evidence_ready"] is False
    assert result["professional_emission"] is False


def test_dataset_secundario_es_ready_data_pero_no_evidencia_primaria():
    _base_line()
    route = _route_grouped()
    factor = _secondary_factor(route)
    ampacity.definir_condiciones(
        "Line.f_ev",
        "PERU_CNE_UTILIZACION_2006",
        220,
        factores=[factor],
        permitir_factores_dataset_secundarios=True,
        ib_diseno_a=180,
        referencia_in="QF1 220 A",
        referencia_ib="memoria de cargas",
        referencia_condiciones_instalacion="método C y agrupamiento verificados",
    )

    readiness = engine_selection.evaluar_preparacion_estudio("ampacidad")
    assert readiness["data_status"] == "READY_DATA"
    assert readiness["overall_status"] == "READY_TO_EXECUTE"

    evidence = ampacity_evidence_readiness.evaluar()
    assert evidence["status"] == "SECONDARY_EVIDENCE_ONLY"
    assert evidence["professional_normative_evidence_ready"] is False
    assert evidence["professional_emission"] is False
    assert evidence["profiles"][0]["factor_evidence"]["dataset_secondary"] == 1


def test_factor_manual_se_clasifica_manual_sin_romper_ready_data():
    _base_line()
    _route_grouped()
    ampacity.definir_condiciones(
        "Line.f_ev",
        "PERU_CNE_UTILIZACION_2006",
        220,
        factores=[{
            "id": "k_group_manual",
            "axis": "grouping",
            "value": 0.80,
            "reference": "factor manual verificado por ingeniería",
        }],
        ib_diseno_a=180,
        referencia_in="QF1 220 A",
        referencia_ib="memoria de cargas",
        referencia_condiciones_instalacion="método C y agrupamiento verificados",
    )
    assert engine_selection.evaluar_preparacion_estudio("ampacidad")["data_status"] == "READY_DATA"
    evidence = ampacity_evidence_readiness.evaluar()
    assert evidence["status"] == "MANUAL_EVIDENCE"
    assert evidence["professional_normative_evidence_ready"] is False


def test_condiciones_base_confirmadas_tienen_estado_propio():
    _base_line()
    ampacity.definir_condiciones(
        "Line.f_ev",
        "PERU_CNE_UTILIZACION_2006",
        220,
        confirmar_condiciones_base=True,
        ib_diseno_a=180,
        referencia_in="QF1 220 A",
        referencia_ib="memoria de cargas",
        referencia_condiciones_instalacion="condiciones base de catálogo confirmadas",
    )
    evidence = ampacity_evidence_readiness.evaluar()
    assert evidence["status"] == "BASE_CONDITIONS_CONFIRMED"
    assert evidence["professional_normative_evidence_ready"] is False


def test_base_y_factores_primarios_clasifican_ready_sin_habilitar_emision_global():
    profile = {
        "element": "Line.synthetic",
        "base": {
            "evidence": {
                "origin": "P3B_BASE_DATASET",
                "normative_base": True,
                "primary": True,
                "professional_emission": True,
            },
        },
        "correction": {
            "mode": "EXPLICIT_FACTORS",
            "factors": [{"origin": "P3B_DATASET"}],
            "factor_evidence": {
                "total": 1,
                "manual": 0,
                "dataset_primary": 1,
                "dataset_secondary": 0,
                "contains_secondary": False,
                "professional_factor_evidence": True,
                "automatic_normative_lookup": True,
            },
        },
    }
    result = ampacity_evidence_readiness._profile_status(profile)
    assert result["status"] == "PRIMARY_EVIDENCE_READY"
    assert result["professional_normative_evidence_ready"] is True


def test_factores_primarios_sin_base_normativa_no_completan_evidencia():
    profile = {
        "element": "Line.synthetic_without_base",
        "correction": {
            "mode": "EXPLICIT_FACTORS",
            "factors": [{"origin": "P3B_DATASET"}],
            "factor_evidence": {
                "total": 1,
                "manual": 0,
                "dataset_primary": 1,
                "dataset_secondary": 0,
                "contains_secondary": False,
                "professional_factor_evidence": True,
                "automatic_normative_lookup": True,
            },
        },
    }
    result = ampacity_evidence_readiness._profile_status(profile)
    assert result["status"] == "EVIDENCE_INCOMPLETE"
    assert result["professional_normative_evidence_ready"] is False
    assert "Iz_base" in result["reasons"][0]

