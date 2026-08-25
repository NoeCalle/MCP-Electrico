import pytest

from mcp_electrico import (
    ampacity,
    ampacity_datasets,
    ampacity_factor_binding,
    conductor_library,
    core,
    p3_completion,
    visual_state,
)


ARRANGEMENT = "grouped_air_surface_embedded_enclosed"


def _secondary_ready_model():
    core.crear_circuito("p3_gate_model", 22.9)
    visual_state.reset()
    conductor_library.reset()
    ampacity.reset()
    core.agregar_linea("f_gate", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    conductor_library.aplicar_conductor(
        "Line.f_gate",
        "NEXANS-N2XSY-18-30-CU-70-PH16",
        "air_trefoil_30c",
    )
    route = ampacity.definir_aplicabilidad_normativa(
        "Line.f_gate",
        "PERU_CNE_UTIL_2006_030_004",
        "C",
        ambiente="air",
        temperatura_ambiente_c=30.0,
        circuitos_agrupados=2,
        disposicion_agrupamiento=ARRANGEMENT,
    )
    resolved = ampacity_datasets.resolver_grouping_for_route(
        route,
        circuits_grouped=2,
        arrangement_id=ARRANGEMENT,
        allow_secondary=True,
    )
    factor = ampacity_factor_binding.construir_factor_desde_resultado(resolved)
    ampacity.definir_condiciones(
        "Line.f_gate",
        "PERU_CNE_UTILIZACION_2006",
        220,
        factores=[factor],
        permitir_factores_dataset_secundarios=True,
        ib_diseno_a=180,
        referencia_in="QF1 220 A",
        referencia_ib="memoria de cargas",
        referencia_condiciones_instalacion="método C y agrupamiento verificados",
    )


def test_gate_p3_declara_pendientes_reales_y_no_avanza_a_p4():
    result = p3_completion.evaluar_cierre_p3()
    assert result["schema_version"] == 2
    assert result["phase"] == "P3"
    assert result["phase_status"] == "NOT_READY"
    assert result["ready_for_next_phase"] is False
    assert result["next_phase"] is None
    assert result["professional_emission"] is False

    pending = {item["id"] for item in result["pending_criteria"]}
    assert {
        "P3C08",
        "P3C09",
        "P3C10",
        "P3C11",
        "P3C12",
        "P3C13",
    } <= pending

    done = {item["id"] for item in result["criteria"] if item["status"] == "DONE"}
    assert {"P3C01", "P3C02", "P3C03", "P3C04", "P3C05", "P3C06", "P3C07"} <= done


def test_gate_expone_que_iz_base_normativa_sigue_pendiente():
    result = p3_completion.evaluar_cierre_p3()
    criterion = next(item for item in result["criteria"] if item["id"] == "P3C10")
    assert criterion["status"] == "PENDING"
    assert "Iz_base" in criterion["blocking_reason"]
    assert "Tabla 1/2" in criterion["blocking_reason"]


def test_p3c12_deriva_del_registro_y_benchmark_secundario_no_lo_satisface():
    result = p3_completion.evaluar_cierre_p3()
    criterion = next(item for item in result["criteria"] if item["id"] == "P3C12")
    coverage = result["benchmark_evidence"]

    assert criterion["status"] == "PENDING"
    assert coverage["ready"] is False
    assert coverage["status"] == "PRIMARY_BENCHMARK_COVERAGE_INCOMPLETE"
    assert set(coverage["missing_families"]) == set(result["scope"]["required_numeric_families"])
    assert "PRIMARY_BENCHMARK_COVERAGE_INCOMPLETE" in criterion["evidence"]
    assert coverage["professional_emission"] is False


def test_alcance_candidato_hace_visible_tabla_5d_y_base_normativa():
    scope = p3_completion.evaluar_cierre_p3()["scope"]
    assert scope["norm_reference_id"] == "PERU_CNE_UTILIZACION_2006"
    assert "D" in scope["installation_methods_routed"]
    assert "Table_5D_grouping_buried_method_D" in scope["required_numeric_families"]
    assert "base_ampacity_strategy_Table_1_2_or_validated_equivalent" in scope["required_numeric_families"]


def test_modelo_secundario_puede_ser_tecnicamente_ready_sin_cerrar_p3():
    _secondary_ready_model()
    result = p3_completion.evaluar_cierre_p3()

    assert result["phase_status"] == "NOT_READY"
    assert result["model"]["status"] == "MODEL_TECHNICALLY_READY"
    assert result["model"]["technical_readiness"]["overall_status"] == "READY_TO_EXECUTE"
    assert result["model"]["normative_evidence"]["status"] == "SECONDARY_EVIDENCE_ONLY"
    assert result["model"]["professional_normative_evidence_ready"] is False
    assert result["ready_for_next_phase"] is False


def test_madurez_actual_under_validation_es_bloqueante():
    result = p3_completion.evaluar_cierre_p3()
    maturity = next(item for item in result["criteria"] if item["id"] == "P3C13")
    assert maturity["status"] == "PENDING"
    assert "UNDER_VALIDATION" in maturity["evidence"]
