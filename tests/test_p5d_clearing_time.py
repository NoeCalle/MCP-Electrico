import math

import pytest

from mcp_electrico import (
    core,
    protection_clearing_time,
    protection_clearing_tools,
    protection_curves,
    protection_data,
    validation_status,
)


def _case(name: str = "p5d", semantics: str = "TOTAL_CLEARING_TIME", shape: str = "SINGLE") -> None:
    core.crear_circuito(name, 0.48)
    protection_data.reset()
    protection_curves.reset()
    core.agregar_linea(
        "f1",
        "sourcebus",
        "bus1",
        0.05,
        fases=3,
        r1_ohm_km=0.20,
        x1_ohm_km=0.08,
    )
    protection_data.definir_dispositivo(
        nombre="qf1",
        tipo="circuit_breaker",
        elemento_protegido="Line.f1",
        in_a=250.0,
        ue_kv=0.48,
        norma_referencia="IEC 60947-2 ficha declarada",
        icu_ka=36.0,
        fuente_referencia="datasheet fabricante rev A",
    )
    protection_data.vincular_curva(
        "qf1",
        curva_id="CURVE-QF1-A",
        tipo_curva="MANUFACTURER_TCC",
        fuente_referencia="curva fabricante rev A",
        revision="A",
    )
    if shape == "SINGLE":
        points = [
            {"current_a": 100.0, "time_s": 10.0},
            {"current_a": 1000.0, "time_s": 0.1},
        ]
    else:
        points = [
            {"current_a": 100.0, "time_min_s": 8.0, "time_max_s": 12.0},
            {"current_a": 1000.0, "time_min_s": 0.08, "time_max_s": 0.12},
        ]
    protection_curves.registrar_dataset(
        dataset_id="ds-qf1",
        curve_id="CURVE-QF1-A",
        shape=shape,
        time_semantics=semantics,
        segments=[{"id": "published", "points": points}],
        source_type="TEST_DATA",
        source_reference="P5D benchmark dataset",
    )
    protection_curves.vincular_dataset_dispositivo("qf1", "ds-qf1")


def test_p5d_total_clearing_single_is_promoted_with_full_trace():
    _case("p5d_single")
    current = math.sqrt(100.0 * 1000.0)
    result = protection_clearing_time.evaluar_tiempo_despeje("qf1", current)

    assert result["status"] == "CLEARING_TIME_READY"
    assert result["time_semantics"] == "TOTAL_CLEARING_TIME"
    assert result["clearing_time"]["kind"] == "SINGLE"
    assert result["clearing_time"]["time_s"] == pytest.approx(1.0, rel=1e-12)
    assert result["clearing_time"]["conservative_time_s"] == pytest.approx(1.0, rel=1e-12)
    assert result["dataset_id"] == "ds-qf1"
    assert result["curve_id"] == "CURVE-QF1-A"
    assert result["segment_id"] == "published"
    assert result["source"]["reference"] == "P5D benchmark dataset"
    assert result["interpolation_used"] is True
    assert result["p4_tk_s_consumed"] is False
    assert result["professional_emission"] is False


def test_p5d_band_preserves_min_max_and_uses_max_only_as_conservative_field():
    _case("p5d_band", shape="BAND")
    current = math.sqrt(100.0 * 1000.0)
    result = protection_clearing_time.evaluar_tiempo_despeje("qf1", current)

    assert result["status"] == "CLEARING_TIME_READY"
    assert result["clearing_time"]["kind"] == "BAND"
    assert result["clearing_time"]["time_s"] is None
    assert result["clearing_time"]["time_min_s"] == pytest.approx(0.8, rel=1e-12)
    assert result["clearing_time"]["time_max_s"] == pytest.approx(1.2, rel=1e-12)
    assert result["clearing_time"]["conservative_time_s"] == pytest.approx(1.2, rel=1e-12)
    assert result["thermal_check_recommended_time_field"] == "conservative_time_s"


@pytest.mark.parametrize("semantics", ["TRIP_TIME", "MELTING_TIME", "OPERATING_TIME"])
def test_p5d_other_time_semantics_are_evaluated_but_not_promoted(semantics):
    _case(f"p5d_{semantics.lower()}", semantics=semantics)
    result = protection_clearing_time.evaluar_tiempo_despeje("qf1", 100.0)

    assert result["status"] == "TIME_SEMANTICS_NOT_CLEARING_READY"
    assert result["time_semantics"] == semantics
    assert result["curve_values"] is not None
    assert result["clearing_time"] is None
    assert result["p4_tk_s_consumed"] is False


def test_p5d_never_extrapolates_to_create_clearing_time():
    _case("p5d_domain")
    result = protection_clearing_time.evaluar_tiempo_despeje("qf1", 2000.0)

    assert result["status"] == "CLEARING_TIME_NOT_READY"
    assert result["reason"] == "TCC_OUT_OF_DOMAIN"
    assert result["clearing_time"] is None
    assert result["extrapolated"] is False
    assert result["cross_segment_interpolation"] is False


def test_p5d_contract_and_validation_status_remain_separate_from_p5e():
    contract = protection_clearing_time.obtener_contrato_p5d()
    clearing = validation_status.get_module_status("protection_clearing_time")
    coordination = validation_status.get_module_status("protection_coordination")

    assert contract["clearing_ready_time_semantics"] == ["TOTAL_CLEARING_TIME"]
    assert contract["band_policy"]["average_band"] is False
    assert contract["p4_tk_s_consumed"] is False
    assert clearing["status"] == "EXPERIMENTAL"
    assert "P5D" in clearing["basis"]
    assert "P5E" not in clearing["basis"]
    assert coordination["status"] == "EXPERIMENTAL"
    assert "P5E" in coordination["basis"]


def test_p5d_public_tools_are_narrow_and_do_not_expose_coordination():
    class FakeMCP:
        def __init__(self):
            self.names = []

        def tool(self):
            def decorator(func):
                self.names.append(func.__name__)
                return func
            return decorator

    fake = FakeMCP()
    protection_clearing_tools.register(fake)

    assert fake.names == [
        "obtener_contrato_tiempo_despeje_p5d",
        "evaluar_tiempo_despeje_p5d",
    ]
