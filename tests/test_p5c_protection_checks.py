import pytest

from mcp_electrico import (
    conductor_library,
    core,
    protection_check_tools,
    protection_checks,
    protection_data,
    validation_status,
)


def _line_case(name: str = "p5c") -> None:
    core.crear_circuito(name, 0.48)
    protection_data.reset()
    conductor_library.reset()
    core.agregar_linea(
        "f1",
        "sourcebus",
        "bus1",
        0.05,
        fases=3,
        r1_ohm_km=0.20,
        x1_ohm_km=0.08,
    )


def _breaker(icu_ka=36.0, ics_ka=18.0, icw_ka=12.0):
    return protection_data.definir_dispositivo(
        nombre="qf1",
        tipo="circuit_breaker",
        elemento_protegido="Line.f1",
        in_a=250.0,
        ue_kv=0.48,
        norma_referencia="IEC 60947-2 ficha declarada",
        icu_ka=icu_ka,
        ics_ka=ics_ka,
        icw_ka=icw_ka,
        fuente_referencia="datasheet fabricante rev A",
    )


def test_p5c_breaker_uses_icu_only_and_keeps_ics_icw_contextual():
    _line_case("p5c_breaker")
    _breaker(icu_ka=36.0, ics_ka=18.0, icw_ka=12.0)

    result = protection_checks.evaluar_capacidad_corte(
        "qf1",
        corriente_falla_ka=25.0,
        tension_operacion_kv=0.40,
        fuente_corriente="P4 IEC60909 3F MAX bus1 rev X",
        tipo_falla="three_phase",
        escenario="max",
    )

    assert result["status"] == "PASS"
    assert result["rating_used"]["type"] == "Icu"
    assert result["rating_used"]["value_ka"] == 36.0
    assert result["other_declared_ratings_not_used_for_pass"]["ics_ka"] == 18.0
    assert result["other_declared_ratings_not_used_for_pass"]["icw_ka"] == 12.0
    assert result["fault"]["source_reference"].startswith("P4 IEC60909")
    assert result["full_standard_compliance_claim"] is False
    assert result["professional_emission"] is False


def test_p5c_breaker_fails_when_fault_exceeds_icu_even_if_icw_is_higher():
    _line_case("p5c_breaker_fail")
    _breaker(icu_ka=36.0, ics_ka=30.0, icw_ka=50.0)

    result = protection_checks.evaluar_capacidad_corte(
        "qf1",
        corriente_falla_ka=40.0,
        tension_operacion_kv=0.40,
        fuente_corriente="P4 IEC60909 3F MAX",
    )

    assert result["status"] == "FAIL"
    assert result["rating_used"]["type"] == "Icu"
    assert result["margin_ka"] == pytest.approx(-4.0)
    assert result["other_declared_ratings_not_used_for_pass"]["ics_ka"] == 30.0
    assert result["other_declared_ratings_not_used_for_pass"]["icw_ka"] == 50.0


def test_p5c_breaking_capacity_is_fail_closed_above_device_ue():
    _line_case("p5c_voltage")
    _breaker()

    result = protection_checks.evaluar_capacidad_corte(
        "qf1",
        corriente_falla_ka=10.0,
        tension_operacion_kv=0.69,
        fuente_corriente="P4 fixture",
    )

    assert result["status"] == "NOT_APPLICABLE_VOLTAGE"
    assert any(item["code"] == "P5C104" for item in result["issues"])


def test_p5c_fuse_uses_breaking_capacity_not_breaker_ratings():
    _line_case("p5c_fuse")
    protection_data.definir_dispositivo(
        nombre="fu1",
        tipo="fuse",
        elemento_protegido="Line.f1",
        in_a=125.0,
        ue_kv=0.50,
        norma_referencia="IEC 60269-1 ficha declarada",
        poder_corte_ka=100.0,
        categoria_utilizacion="gG",
        fuente_referencia="datasheet fusible",
    )

    result = protection_checks.evaluar_capacidad_corte(
        "fu1",
        corriente_falla_ka=65.0,
        tension_operacion_kv=0.40,
        fuente_corriente="P4 IEC60909 3F MAX",
    )

    assert result["status"] == "PASS"
    assert result["rating_used"]["type"] == "breaking_capacity"
    assert result["rating_used"]["value_ka"] == 100.0


def test_p5c_thermal_check_pass_fail_and_does_not_consume_p4_tk():
    _line_case("p5c_thermal_explicit")

    passed = protection_checks.evaluar_soportabilidad_termica_conductor(
        elemento="Line.f1",
        corriente_falla_ka=20.0,
        tiempo_despeje_s=0.10,
        seccion_mm2=50.0,
        k_a_sqrt_s_per_mm2=143.0,
        fuente_k="valor k declarado por diseñador / referencia técnica",
        fuente_tiempo="tiempo explícito de fixture P5C",
        fuente_seccion="plano/cable schedule rev A",
    )
    failed = protection_checks.evaluar_soportabilidad_termica_conductor(
        elemento="Line.f1",
        corriente_falla_ka=20.0,
        tiempo_despeje_s=0.20,
        seccion_mm2=50.0,
        k_a_sqrt_s_per_mm2=143.0,
        fuente_k="valor k declarado por diseñador / referencia técnica",
        fuente_tiempo="tiempo explícito de fixture P5C",
        fuente_seccion="plano/cable schedule rev A",
    )

    assert passed["status"] == "PASS"
    assert failed["status"] == "FAIL"
    assert passed["results"]["actual_i2t_a2s"] == pytest.approx(40_000_000.0)
    assert passed["results"]["limit_k2s2_a2s"] == pytest.approx((143.0 * 50.0) ** 2)
    assert passed["section_binding"]["status"] == "EXPLICIT_WITHOUT_LIBRARY_ASSIGNMENT"
    assert passed["policies"]["p4_tk_s_consumed"] is False
    assert passed["policies"]["k_derived_automatically"] is False
    assert passed["policies"]["section_derived_automatically"] is False


def test_p5c_thermal_check_requires_section_match_when_conductor_is_assigned():
    _line_case("p5c_section_binding")
    assignment = conductor_library.aplicar_conductor(
        "Line.f1",
        "NEXANS-N2XOH-0.6-1-CU-50",
        "air_flat_30c",
        actualizar_impedancia=False,
    )
    assert assignment["producto"]["seccion_mm2"] == 50

    mismatch = protection_checks.evaluar_soportabilidad_termica_conductor(
        elemento="Line.f1",
        corriente_falla_ka=20.0,
        tiempo_despeje_s=0.10,
        seccion_mm2=70.0,
        k_a_sqrt_s_per_mm2=143.0,
        fuente_k="fixture k",
        fuente_tiempo="fixture time",
    )
    match = protection_checks.evaluar_soportabilidad_termica_conductor(
        elemento="Line.f1",
        corriente_falla_ka=20.0,
        tiempo_despeje_s=0.10,
        seccion_mm2=50.0,
        k_a_sqrt_s_per_mm2=143.0,
        fuente_k="fixture k",
        fuente_tiempo="fixture time",
    )

    assert mismatch["status"] == "SECTION_MISMATCH"
    assert mismatch["section_binding"]["assigned_section_mm2"] == 50.0
    assert mismatch["section_binding"]["automatic_section_substitution"] is False
    assert match["status"] == "PASS"
    assert match["section_binding"]["status"] == "MATCH"
    assert match["section_binding"]["conductor_code"] == "NEXANS-N2XOH-0.6-1-CU-50"


def test_p5c_thermal_check_requires_explicit_section_source_without_assignment():
    _line_case("p5c_section_source")

    with pytest.raises(ValueError, match="P5C209"):
        protection_checks.evaluar_soportabilidad_termica_conductor(
            elemento="Line.f1",
            corriente_falla_ka=10.0,
            tiempo_despeje_s=0.10,
            seccion_mm2=50.0,
            k_a_sqrt_s_per_mm2=143.0,
            fuente_k="fixture k",
            fuente_tiempo="fixture time",
        )


def test_p5c_reference_targets_and_validation_state_are_explicit():
    refs = protection_checks.obtener_referencias_p5c()
    status = validation_status.get_module_status("protection_checks")

    assert refs["targets"]["circuit_breaker"]["designation"] == "IEC 60947-2:2024"
    assert refs["targets"]["fuse"]["designation"] == "IEC 60269-1:2024"
    assert refs["targets"]["conductor_overcurrent"]["designation"] == "IEC 60364-4-43:2023"
    assert refs["scope"] == "REFERENCE_TARGETS_NOT_FULL_CONFORMANCE"
    assert status["status"] == "EXPERIMENTAL"
    assert "P5C" in status["basis"]


def test_p5c_public_tools_register_without_coordination_solver():
    class FakeMCP:
        def __init__(self):
            self.names = []

        def tool(self):
            def decorator(func):
                self.names.append(func.__name__)
                return func
            return decorator

    fake = FakeMCP()
    protection_check_tools.register(fake)

    assert "obtener_referencias_proteccion_p5c" in fake.names
    assert "evaluar_capacidad_corte_p5c" in fake.names
    assert "evaluar_soportabilidad_termica_conductor_p5c" in fake.names
    assert not any("coord" in name.lower() or "select" in name.lower() for name in fake.names)
