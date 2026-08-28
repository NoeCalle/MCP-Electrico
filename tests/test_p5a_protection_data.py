import pytest

from mcp_electrico import (
    ampacity,
    core,
    protection_contract,
    protection_data,
    protection_tools,
    validation_status,
)


def _line_case(name: str = "p5a") -> None:
    core.crear_circuito(name, 0.48)
    protection_data.reset()
    core.agregar_linea(
        "f1", "sourcebus", "bus1", 0.05,
        fases=3, r1_ohm_km=0.20, x1_ohm_km=0.08,
    )


def _breaker(**overrides):
    data = {
        "nombre": "qf1",
        "tipo": "circuit_breaker",
        "elemento_protegido": "Line.f1",
        "in_a": 250.0,
        "ue_kv": 0.48,
        "fabricante": "Fabricante prueba",
        "serie": "Serie X",
        "modelo": "Modelo 250",
        "polos": 3,
        "norma_referencia": "IEC 60947-2 ficha declarada",
        "icu_ka": 36.0,
        "ics_ka": 27.0,
        "fuente_referencia": "datasheet fabricante rev A",
    }
    data.update(overrides)
    return protection_data.definir_dispositivo(**data)


def test_p5a_contract_forbids_synthetic_curves_and_p4_tk_binding():
    contract = protection_contract.obtener_contrato_p5a()

    assert contract["scope"]["included_device_types"] == ["circuit_breaker", "fuse"]
    assert contract["scope"]["excluded_device_types"] == ["relay"]
    assert contract["curve_policy"]["numeric_curve_dataset_supported"] is False
    assert contract["curve_policy"]["synthetic_manufacturer_curves"] is False
    assert contract["curve_policy"]["browser_curve_calculation"] is False
    assert contract["clearing_time_policy"]["automatic_binding_from_p4_tk_s"] is False
    assert contract["clearing_time_policy"]["p4_tk_s_is_actual_clearing_time"] is False
    assert contract["p3_binding_policy"]["automatic_creation_from_p3_in"] is False
    assert contract["visual_policy"]["second_visual_app"] is False
    assert contract["professional_emission"] is False


def test_p5a_breaker_keeps_ratings_provenance_and_no_hidden_settings():
    _line_case("p5a_breaker")
    device = _breaker()

    assert device["id"] == "Protection.qf1"
    assert device["device_type"] == "circuit_breaker"
    assert device["protected_element"].lower() == "line.f1"
    assert device["ratings"]["in_a"] == 250.0
    assert device["ratings"]["icu_ka"] == 36.0
    assert device["ratings"]["ics_ka"] == 27.0
    assert device["ratings"]["breaking_capacity_ka"] is None
    assert device["settings"] is None
    assert device["curve"] is None
    assert device["provenance"]["reference"] == "datasheet fabricante rev A"
    assert device["professional_emission"] is False

    readiness = protection_data.evaluar_preparacion("qf1")
    assert readiness["device_data_status"] == "FOUNDATION_READY"
    assert readiness["breaking_capacity_ready"] is True
    assert readiness["tcc_status"] == "MODULE_NOT_READY_P5A"
    assert readiness["p4_tk_s_consumed"] is False
    assert readiness["clearing_time_source"] is None


def test_p5a_fuse_uses_its_own_breaking_capacity_semantics():
    _line_case("p5a_fuse")
    fuse = protection_data.definir_dispositivo(
        nombre="fu1",
        tipo="fuse",
        elemento_protegido="Line.f1",
        in_a=125.0,
        ue_kv=0.5,
        norma_referencia="IEC 60269 ficha declarada",
        poder_corte_ka=100.0,
        categoria_utilizacion="gG",
        fuente_referencia="datasheet fusible",
    )
    assert fuse["ratings"]["breaking_capacity_ka"] == 100.0
    assert fuse["ratings"]["icu_ka"] is None
    assert protection_data.evaluar_preparacion("Protection.fu1")["breaking_capacity_ready"] is True

    with pytest.raises(ValueError, match="P5DATA027"):
        protection_data.definir_dispositivo(
            nombre="fu_bad",
            tipo="fuse",
            elemento_protegido="Line.f1",
            in_a=125.0,
            ue_kv=0.5,
            norma_referencia="IEC 60269",
            icu_ka=36.0,
            fuente_referencia="dato inválido",
        )


def test_p5a_relay_is_explicitly_out_of_foundation_scope():
    _line_case("p5a_relay")
    with pytest.raises(ValueError, match="P5DATA007"):
        protection_data.definir_dispositivo(
            nombre="r1",
            tipo="relay",
            elemento_protegido="Line.f1",
            in_a=5.0,
            ue_kv=0.11,
            norma_referencia="ficha relé",
            fuente_referencia="datasheet relé",
        )


def test_p5a_settings_are_absolute_explicit_and_never_derived_from_in():
    _line_case("p5a_settings")
    _breaker()
    updated = protection_data.definir_ajustes(
        "qf1",
        ir_a=225.0,
        isd_a=1250.0,
        ii_a=2500.0,
        fuente_referencia="hoja de ajustes aprobada",
    )

    assert updated["settings"]["basis"] == "ABSOLUTE_A"
    assert updated["settings"]["ir_a"] == 225.0
    assert updated["settings"]["isd_a"] == 1250.0
    assert updated["settings"]["ii_a"] == 2500.0
    assert updated["settings"]["derived_from_in"] is False

    with pytest.raises(ValueError, match="P5DATA045"):
        protection_data.definir_ajustes(
            "qf1",
            ir_a=225.0,
            isd_a=2000.0,
            ii_a=1500.0,
            fuente_referencia="ajuste inconsistente",
        )


def test_p5a_curve_link_is_metadata_only_and_keeps_tcc_fail_closed():
    _line_case("p5a_curve")
    _breaker()
    updated = protection_data.vincular_curva(
        "qf1",
        curva_id="MFR-QF1-TCC-REV-A",
        tipo_curva="MANUFACTURER_TCC",
        fuente_referencia="curva fabricante página 42",
        revision="A",
    )

    assert updated["curve"]["numeric_dataset_loaded"] is False
    assert updated["curve"]["synthetic"] is False
    assert updated["curve"]["tcc_execution_ready"] is False
    readiness = protection_data.evaluar_preparacion("qf1")
    assert readiness["tcc_status"] == "MODULE_NOT_READY_P5A"
    assert any(item["code"] == "P5READY302" for item in readiness["tcc_issues"])


def test_p5a_detects_p3_in_mismatch_without_overwriting_either_value(monkeypatch):
    _line_case("p5a_p3")
    _breaker(in_a=250.0)
    monkeypatch.setattr(
        ampacity,
        "obtener_condiciones",
        lambda _element: {"protection": {"in_a": 200.0, "reference": "P3 fixture"}},
    )

    readiness = protection_data.evaluar_preparacion("qf1")
    assert readiness["p3_binding"]["status"] == "MISMATCH"
    assert readiness["p3_binding"]["p3_in_a"] == 200.0
    assert readiness["p3_binding"]["device_in_a"] == 250.0
    assert readiness["p3_binding"]["automatic_creation_from_p3"] is False
    assert any(item["code"] == "P5READY201" for item in readiness["issues"])
    assert readiness["device_data_status"] == "MISSING_OR_INCONSISTENT_DATA"


def test_p5a_validation_status_does_not_promote_coordination_engine():
    data = validation_status.get_module_status("protection_data")
    coordination = validation_status.get_module_status("protection_coordination")

    assert data["status"] == "EXPERIMENTAL"
    assert "P5A" in data["basis"]
    assert coordination["status"] == "NOT_IMPLEMENTED"
    assert "TCC" in coordination["basis"]


def test_p5a_public_tools_register_without_exposing_a_tcc_solver():
    class FakeMCP:
        def __init__(self):
            self.names = []

        def tool(self):
            def decorator(func):
                self.names.append(func.__name__)
                return func
            return decorator

    fake = FakeMCP()
    protection_tools.register(fake)

    assert "obtener_contrato_protecciones_p5a" in fake.names
    assert "definir_dispositivo_proteccion_p5a" in fake.names
    assert "definir_ajustes_proteccion_p5a" in fake.names
    assert "vincular_curva_proteccion_p5a" in fake.names
    assert "evaluar_preparacion_proteccion_p5a" in fake.names
    assert "obtener_estado_protecciones_p5a" in fake.names
    assert not any("tcc" in name.lower() and "vincular" not in name.lower() for name in fake.names)
