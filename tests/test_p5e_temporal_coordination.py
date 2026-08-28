import pytest

from mcp_electrico import (
    core,
    protection_coordination,
    protection_coordination_tools,
    protection_curves,
    protection_data,
    validation_status,
)


def _base_case(name: str = "p5e", downstream_semantics="TOTAL_CLEARING_TIME", upstream_semantics="TOTAL_CLEARING_TIME"):
    core.crear_circuito(name, 0.48)
    protection_data.reset()
    protection_curves.reset()
    core.agregar_linea("f1", "sourcebus", "bus1", 0.05, fases=3, r1_ohm_km=0.20, x1_ohm_km=0.08)
    core.agregar_linea("f2", "bus1", "bus2", 0.05, fases=3, r1_ohm_km=0.20, x1_ohm_km=0.08)

    for device, element, curve in (
        ("qf_down", "Line.f2", "CURVE-DOWN"),
        ("qf_up", "Line.f1", "CURVE-UP"),
    ):
        protection_data.definir_dispositivo(
            nombre=device,
            tipo="circuit_breaker",
            elemento_protegido=element,
            in_a=250.0,
            ue_kv=0.48,
            norma_referencia="IEC 60947-2 ficha declarada",
            icu_ka=36.0,
            fuente_referencia=f"datasheet {device}",
        )
        protection_data.vincular_curva(
            device,
            curva_id=curve,
            tipo_curva="MANUFACTURER_TCC",
            fuente_referencia=f"curva {device}",
        )

    protection_curves.registrar_dataset(
        dataset_id="ds-down",
        curve_id="CURVE-DOWN",
        shape="SINGLE",
        time_semantics=downstream_semantics,
        segments=[{
            "id": "published",
            "points": [
                {"current_a": 100.0, "time_s": 1.0},
                {"current_a": 1000.0, "time_s": 0.10},
            ],
        }],
        source_type="TEST_DATA",
        source_reference="downstream benchmark",
    )
    protection_curves.registrar_dataset(
        dataset_id="ds-up",
        curve_id="CURVE-UP",
        shape="SINGLE",
        time_semantics=upstream_semantics,
        segments=[{
            "id": "published",
            "points": [
                {"current_a": 100.0, "time_s": 2.0},
                {"current_a": 1000.0, "time_s": 0.50},
            ],
        }],
        source_type="TEST_DATA",
        source_reference="upstream benchmark",
    )
    protection_curves.vincular_dataset_dispositivo("qf_down", "ds-down")
    protection_curves.vincular_dataset_dispositivo("qf_up", "ds-up")


def test_p5e_single_times_pass_pointwise_margin_without_selectivity_claim():
    _base_case("p5e_pass")
    result = protection_coordination.evaluar_coordinacion_temporal(
        dispositivo_downstream="qf_down",
        corriente_downstream_a=1000.0,
        dispositivo_upstream="qf_up",
        corriente_upstream_a=1000.0,
        margen_minimo_s=0.30,
        fuente_relacion="unifilar rev A: qf_up aguas arriba de qf_down",
        fuente_corrientes="P4/fixture corriente explícita por dispositivo",
    )

    assert result["status"] == "PASS"
    assert result["downstream_time"]["time_min_s"] == pytest.approx(0.10)
    assert result["downstream_time"]["time_max_s"] == pytest.approx(0.10)
    assert result["upstream_time"]["time_min_s"] == pytest.approx(0.50)
    assert result["conservative_margin_s"] == pytest.approx(0.40)
    assert result["required_margin_s"] == pytest.approx(0.30)
    assert result["relationship"]["topology_inferred"] is False
    assert result["currents"]["same_current_assumed"] is False
    assert result["claims"]["temporal_point_coordination"] is True
    assert result["claims"]["selectivity"] == "NOT_EVALUATED"
    assert result["claims"]["backup"] == "NOT_EVALUATED"
    assert result["domain_scan_performed"] is False
    assert result["professional_emission"] is False


def test_p5e_fail_is_based_on_required_margin_not_device_order_name():
    _base_case("p5e_fail")
    result = protection_coordination.evaluar_coordinacion_temporal(
        dispositivo_downstream="qf_down",
        corriente_downstream_a=1000.0,
        dispositivo_upstream="qf_up",
        corriente_upstream_a=1000.0,
        margen_minimo_s=0.45,
        fuente_relacion="unifilar rev A",
        fuente_corrientes="fixture",
    )

    assert result["status"] == "FAIL"
    assert result["conservative_margin_s"] == pytest.approx(0.40)
    assert result["claims"]["selectivity"] == "NOT_EVALUATED"


def test_p5e_band_comparison_uses_upstream_min_minus_downstream_max():
    core.crear_circuito("p5e_band", 0.48)
    protection_data.reset()
    protection_curves.reset()
    core.agregar_linea("f1", "sourcebus", "bus1", 0.05, fases=3, r1_ohm_km=0.20, x1_ohm_km=0.08)
    core.agregar_linea("f2", "bus1", "bus2", 0.05, fases=3, r1_ohm_km=0.20, x1_ohm_km=0.08)

    for device, element, curve in (
        ("down", "Line.f2", "BAND-DOWN"),
        ("up", "Line.f1", "BAND-UP"),
    ):
        protection_data.definir_dispositivo(
            nombre=device,
            tipo="circuit_breaker",
            elemento_protegido=element,
            in_a=250.0,
            ue_kv=0.48,
            norma_referencia="IEC 60947-2",
            icu_ka=36.0,
            fuente_referencia=f"datasheet {device}",
        )
        protection_data.vincular_curva(device, curva_id=curve, tipo_curva="MANUFACTURER_TCC", fuente_referencia=f"curve {device}")

    protection_curves.registrar_dataset(
        dataset_id="band-down",
        curve_id="BAND-DOWN",
        shape="BAND",
        time_semantics="TOTAL_CLEARING_TIME",
        segments=[{"id": "s", "points": [
            {"current_a": 100.0, "time_min_s": 0.8, "time_max_s": 1.2},
            {"current_a": 1000.0, "time_min_s": 0.08, "time_max_s": 0.12},
        ]}],
        source_type="TEST_DATA",
        source_reference="band down",
    )
    protection_curves.registrar_dataset(
        dataset_id="band-up",
        curve_id="BAND-UP",
        shape="BAND",
        time_semantics="TOTAL_CLEARING_TIME",
        segments=[{"id": "s", "points": [
            {"current_a": 100.0, "time_min_s": 4.0, "time_max_s": 6.0},
            {"current_a": 1000.0, "time_min_s": 0.40, "time_max_s": 0.60},
        ]}],
        source_type="TEST_DATA",
        source_reference="band up",
    )
    protection_curves.vincular_dataset_dispositivo("down", "band-down")
    protection_curves.vincular_dataset_dispositivo("up", "band-up")

    result = protection_coordination.evaluar_coordinacion_temporal(
        dispositivo_downstream="down",
        corriente_downstream_a=1000.0,
        dispositivo_upstream="up",
        corriente_upstream_a=1000.0,
        margen_minimo_s=0.25,
        fuente_relacion="unifilar fixture",
        fuente_corrientes="fixture",
    )

    assert result["downstream_time"] == {"time_min_s": pytest.approx(0.08), "time_max_s": pytest.approx(0.12)}
    assert result["upstream_time"] == {"time_min_s": pytest.approx(0.40), "time_max_s": pytest.approx(0.60)}
    assert result["conservative_margin_s"] == pytest.approx(0.28)
    assert result["optimistic_margin_s"] == pytest.approx(0.52)
    assert result["status"] == "PASS"


def test_p5e_requires_both_p5d_clearing_times_ready():
    _base_case("p5e_not_ready", upstream_semantics="TRIP_TIME")
    result = protection_coordination.evaluar_coordinacion_temporal(
        dispositivo_downstream="qf_down",
        corriente_downstream_a=1000.0,
        dispositivo_upstream="qf_up",
        corriente_upstream_a=1000.0,
        margen_minimo_s=0.20,
        fuente_relacion="unifilar fixture",
        fuente_corrientes="fixture",
    )

    assert result["status"] == "COORDINATION_NOT_READY"
    assert any(item["code"] == "P5E102" for item in result["issues"])
    assert result["upstream"]["status"] == "TIME_SEMANTICS_NOT_CLEARING_READY"
    assert result["claims"]["temporal_point_coordination"] is False


def test_p5e_requires_explicit_relationship_and_currents_sources():
    _base_case("p5e_trace")
    with pytest.raises(ValueError, match="P5E006"):
        protection_coordination.evaluar_coordinacion_temporal(
            "qf_down", 1000.0, "qf_up", 1000.0, 0.2, "", "fixture"
        )
    with pytest.raises(ValueError, match="P5E007"):
        protection_coordination.evaluar_coordinacion_temporal(
            "qf_down", 1000.0, "qf_up", 1000.0, 0.2, "unifilar", ""
        )


def test_p5e_contract_maturity_and_public_tools_are_narrow():
    contract = protection_coordination.obtener_contrato_p5e()
    maturity = validation_status.get_module_status("protection_coordination")

    assert contract["band_comparison"]["average_bands"] is False
    assert contract["topology_inference"] is False
    assert contract["claims"]["total_selectivity"] is False
    assert contract["claims"]["backup"] is False
    assert maturity["status"] == "EXPERIMENTAL"
    assert "P5E" in maturity["basis"]

    class FakeMCP:
        def __init__(self):
            self.names = []

        def tool(self):
            def decorator(func):
                self.names.append(func.__name__)
                return func
            return decorator

    fake = FakeMCP()
    protection_coordination_tools.register(fake)
    assert fake.names == [
        "obtener_contrato_coordinacion_p5e",
        "evaluar_coordinacion_temporal_p5e",
    ]
