import pytest

from mcp_electrico import (
    ampacity,
    ampacity_datasets,
    ampacity_factor_binding,
    conductor_library,
    core,
    p3_completion,
    validation_status,
    visual_state,
)


ARRANGEMENT = "grouped_air_surface_embedded_enclosed"
SECONDARY_DATASET = "PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_SECONDARY_V1"


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
    resolved = ampacity_datasets.resolver_factor(
        SECONDARY_DATASET,
        installation_method=route["installation_method"],
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


def test_gate_p3_cierra_p3c01_a_p3c13_y_habilita_p4():
    result = p3_completion.evaluar_cierre_p3()
    assert result["schema_version"] == 2
    assert result["phase"] == "P3"
    assert result["phase_status"] == "READY_WITH_LIMITATIONS"
    assert result["ready_for_next_phase"] is True
    assert result["next_phase"] == "P4_IEC_60909"
    assert result["professional_emission"] is False
    assert result["pending_criteria"] == []

    done = {item["id"] for item in result["criteria"] if item["status"] == "DONE"}
    assert {f"P3C{index:02d}" for index in range(1, 14)} <= done


def test_p3c08_deriva_del_registro_pinneado():
    result = p3_completion.evaluar_cierre_p3()
    criterion = next(item for item in result["criteria"] if item["id"] == "P3C08")
    assert criterion["status"] == "DONE"
    assert criterion["blocking_reason"] is None
    assert criterion["evidence"] == "ampacity_primary_sources.json"


def test_p3c09_deriva_de_dataset_primary_verified_real():
    result = p3_completion.evaluar_cierre_p3()
    criterion = next(item for item in result["criteria"] if item["id"] == "P3C09")
    assert criterion["status"] == "DONE"
    assert criterion["blocking_reason"] is None
    assert criterion["evidence"] == "ampacity_p3b_numeric_datasets.json"


def test_gate_reconoce_iz_base_normativa_primary_verified():
    result = p3_completion.evaluar_cierre_p3()
    criterion = next(item for item in result["criteria"] if item["id"] == "P3C10")
    assert criterion["status"] == "DONE"
    assert criterion["blocking_reason"] is None
    assert "Tabla 1/2" in criterion["evidence"]


def test_p3c11_reconoce_cobertura_completa_5a_5b_5c_5d_5e():
    coverage = p3_completion._coverage_flags()
    assert coverage["base_ampacity_strategy"] is True
    assert coverage["table_5a"] is True
    assert coverage["table_5b"] is True
    assert coverage["table_5c"] is True
    assert coverage["table_5d"] is True
    assert coverage["table_5e"] is True

    result = p3_completion.evaluar_cierre_p3()
    criterion = next(item for item in result["criteria"] if item["id"] == "P3C11")
    assert criterion["status"] == "DONE"
    assert criterion["blocking_reason"] is None


def test_p3c12_deriva_de_seis_benchmarks_primarios_independientes_vivos():
    result = p3_completion.evaluar_cierre_p3()
    criterion = next(item for item in result["criteria"] if item["id"] == "P3C12")
    coverage = result["benchmark_evidence"]

    assert criterion["status"] == "DONE"
    assert criterion["blocking_reason"] is None
    assert coverage["ready"] is True
    assert coverage["status"] == "PRIMARY_BENCHMARK_COVERAGE_READY"
    assert coverage["missing_families"] == []
    assert set(coverage["coverage"]) == set(result["scope"]["required_numeric_families"])
    assert all(item["covered"] for item in coverage["coverage"].values())
    assert "PRIMARY_BENCHMARK_COVERAGE_READY" in criterion["evidence"]
    assert coverage["professional_emission"] is False


def test_alcance_candidato_hace_visible_tabla_5d_y_base_normativa():
    scope = p3_completion.evaluar_cierre_p3()["scope"]
    assert scope["norm_reference_id"] == "PERU_CNE_UTILIZACION_2006"
    assert "D" in scope["installation_methods_routed"]
    assert "Table_5D_grouping_buried_method_D" in scope["required_numeric_families"]
    assert "base_ampacity_strategy_Table_1_2_or_validated_equivalent" in scope["required_numeric_families"]


def test_modelo_secundario_no_impide_cierre_de_fase_pero_no_es_apto_profesionalmente():
    _secondary_ready_model()
    result = p3_completion.evaluar_cierre_p3()

    assert result["phase_status"] == "READY_WITH_LIMITATIONS"
    assert result["ready_for_next_phase"] is True
    assert result["next_phase"] == "P4_IEC_60909"
    assert result["model"]["status"] == "MODEL_TECHNICALLY_READY"
    assert result["model"]["technical_readiness"]["overall_status"] == "READY_TO_EXECUTE"
    assert result["model"]["normative_evidence"]["status"] == "SECONDARY_EVIDENCE_ONLY"
    assert result["model"]["professional_normative_evidence_ready"] is False
    assert result["professional_emission"] is False


def test_p3c13_deriva_de_madurez_validated_with_limitations():
    module = validation_status.get_module_status("ampacity")
    assert module["status"] == "VALIDATED_WITH_LIMITATIONS"
    assert any("Tablas 1/2" in item for item in module["limitations"])
    assert any("fail-closed" in item for item in module["limitations"])

    result = p3_completion.evaluar_cierre_p3()
    maturity = next(item for item in result["criteria"] if item["id"] == "P3C13")
    assert maturity["status"] == "DONE"
    assert maturity["blocking_reason"] is None
    assert "VALIDATED_WITH_LIMITATIONS" in maturity["evidence"]
    assert result["pending_criteria"] == []
