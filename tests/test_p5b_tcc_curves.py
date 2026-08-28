import math

import pytest

from mcp_electrico import (
    core,
    protection_curves,
    protection_data,
    protection_tcc_tools,
    protection_tools,
    validation_status,
)


def _case(name: str = "p5b") -> None:
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
        ics_ka=27.0,
        fuente_referencia="datasheet fabricante rev A",
    )
    protection_data.vincular_curva(
        "qf1",
        curva_id="CURVE-QF1-A",
        tipo_curva="MANUFACTURER_TCC",
        fuente_referencia="curva fabricante rev A",
        revision="A",
    )


def _single_dataset(dataset_id="ds-single", curve_id="CURVE-QF1-A", semantics="TRIP_TIME"):
    return protection_curves.registrar_dataset(
        dataset_id=dataset_id,
        curve_id=curve_id,
        shape="SINGLE",
        time_semantics=semantics,
        segments=[
            {
                "id": "inverse",
                "points": [
                    {"current_a": 100.0, "time_s": 10.0},
                    {"current_a": 1000.0, "time_s": 0.1},
                ],
            }
        ],
        source_type="TEST_DATA",
        source_reference="benchmark power-law t=100000/I^2",
    )


def test_p5b_single_exact_and_independent_power_law_interpolation():
    _case("p5b_single")
    dataset = _single_dataset()

    exact = protection_curves.evaluar_dataset(dataset["dataset_id"], 100.0)
    midpoint = math.sqrt(100.0 * 1000.0)
    interpolated = protection_curves.evaluar_dataset(dataset["dataset_id"], midpoint)

    assert exact["status"] == "RESOLVED_EXACT"
    assert exact["values"]["time_s"] == pytest.approx(10.0)
    assert exact["interpolation_used"] is False
    assert interpolated["status"] == "RESOLVED_INTERPOLATED"
    assert interpolated["values"]["time_s"] == pytest.approx(1.0, rel=1e-12)
    assert interpolated["interpolation_method"] == "LOG_LOG_LINEAR"
    assert interpolated["extrapolated"] is False
    assert interpolated["cross_segment_interpolation"] is False


def test_p5b_band_preserves_both_boundaries_without_averaging():
    _case("p5b_band")
    dataset = protection_curves.registrar_dataset(
        dataset_id="ds-band",
        curve_id="CURVE-QF1-A",
        shape="BAND",
        time_semantics="TOTAL_CLEARING_TIME",
        segments=[
            {
                "id": "band",
                "points": [
                    {"current_a": 100.0, "time_min_s": 10.0, "time_max_s": 20.0},
                    {"current_a": 1000.0, "time_min_s": 0.1, "time_max_s": 0.2},
                ],
            }
        ],
        source_type="TEST_DATA",
        source_reference="benchmark band",
    )
    result = protection_curves.evaluar_dataset(
        dataset["dataset_id"], math.sqrt(100.0 * 1000.0)
    )

    assert result["values"]["time_min_s"] == pytest.approx(1.0, rel=1e-12)
    assert result["values"]["time_max_s"] == pytest.approx(2.0, rel=1e-12)
    assert "time_s" not in result["values"]
    assert result["time_semantics"] == "TOTAL_CLEARING_TIME"


def test_p5b_never_extrapolates_or_crosses_segment_gap():
    _case("p5b_domains")
    dataset = protection_curves.registrar_dataset(
        dataset_id="ds-gaps",
        curve_id="CURVE-QF1-A",
        shape="SINGLE",
        time_semantics="OPERATING_TIME",
        segments=[
            {
                "id": "low",
                "points": [
                    {"current_a": 100.0, "time_s": 10.0},
                    {"current_a": 200.0, "time_s": 4.0},
                ],
            },
            {
                "id": "high",
                "points": [
                    {"current_a": 400.0, "time_s": 1.0},
                    {"current_a": 800.0, "time_s": 0.2},
                ],
            },
        ],
        source_type="TEST_DATA",
        source_reference="segmented benchmark",
    )

    for current in (50.0, 300.0, 1000.0):
        result = protection_curves.evaluar_dataset(dataset["dataset_id"], current)
        assert result["status"] == "OUT_OF_DOMAIN"
        assert result["values"] is None
        assert result["extrapolated"] is False
        assert result["cross_segment_interpolation"] is False


def test_p5b_rejects_unsorted_touching_or_overlapping_segments():
    _case("p5b_invalid_domains")
    with pytest.raises(ValueError, match="P5TCC012"):
        protection_curves.registrar_dataset(
            dataset_id="unsorted",
            curve_id="CURVE-QF1-A",
            shape="SINGLE",
            time_semantics="TRIP_TIME",
            segments=[
                {
                    "id": "bad",
                    "points": [
                        {"current_a": 200.0, "time_s": 2.0},
                        {"current_a": 100.0, "time_s": 4.0},
                    ],
                }
            ],
            source_type="TEST_DATA",
            source_reference="bad fixture",
        )

    with pytest.raises(ValueError, match="P5TCC017"):
        protection_curves.registrar_dataset(
            dataset_id="touching",
            curve_id="CURVE-QF1-A",
            shape="SINGLE",
            time_semantics="TRIP_TIME",
            segments=[
                {
                    "id": "a",
                    "points": [
                        {"current_a": 100.0, "time_s": 10.0},
                        {"current_a": 200.0, "time_s": 4.0},
                    ],
                },
                {
                    "id": "b",
                    "points": [
                        {"current_a": 200.0, "time_s": 3.0},
                        {"current_a": 400.0, "time_s": 1.0},
                    ],
                },
            ],
            source_type="TEST_DATA",
            source_reference="bad fixture",
        )


def test_p5b_digitized_manufacturer_data_requires_method():
    _case("p5b_digitized")
    with pytest.raises(ValueError, match="P5TCC007"):
        protection_curves.registrar_dataset(
            dataset_id="digitized",
            curve_id="CURVE-QF1-A",
            shape="SINGLE",
            time_semantics="TRIP_TIME",
            segments=[
                {
                    "id": "curve",
                    "points": [
                        {"current_a": 100.0, "time_s": 10.0},
                        {"current_a": 1000.0, "time_s": 0.1},
                    ],
                }
            ],
            source_type="MANUFACTURER_DIGITIZED",
            source_reference="manufacturer page 12",
        )


def test_p5b_binding_is_exact_and_readiness_preserves_p5a_compatibility():
    _case("p5b_binding")
    before = protection_data.evaluar_preparacion("qf1")
    assert before["tcc_status"] == "MODULE_NOT_READY_P5A"
    assert before["tcc_data_status"] == "TCC_DATA_NOT_BOUND"

    _single_dataset(dataset_id="wrong", curve_id="OTHER-CURVE")
    with pytest.raises(ValueError, match="P5TCC032"):
        protection_curves.vincular_dataset_dispositivo("qf1", "wrong")

    _single_dataset(dataset_id="right")
    bound = protection_curves.vincular_dataset_dispositivo("qf1", "right")
    ready = protection_data.evaluar_preparacion("qf1")

    assert bound["curve"]["numeric_dataset_loaded"] is True
    assert bound["curve"]["dataset_id"] == "right"
    assert bound["curve"]["time_semantics"] == "TRIP_TIME"
    assert bound["curve"]["tcc_execution_ready"] is True
    assert ready["tcc_status"] == "TCC_DATA_READY_P5B"
    assert ready["tcc_data_status"] == "TCC_DATA_READY"
    assert ready["tcc_data_ready"] is True
    assert ready["clearing_time_source"] is None
    assert ready["p4_tk_s_consumed"] is False

    result = protection_curves.evaluar_dispositivo(
        "qf1", math.sqrt(100.0 * 1000.0)
    )
    assert result["device_id"] == "Protection.qf1"
    assert result["protected_element"].lower() == "line.f1"
    assert result["values"]["time_s"] == pytest.approx(1.0, rel=1e-12)
    assert result["time_semantics"] == "TRIP_TIME"


def test_p5b_validation_status_keeps_coordination_separate():
    tcc = validation_status.get_module_status("tcc_curve_evaluation")
    coordination = validation_status.get_module_status("protection_coordination")

    assert tcc["status"] == "EXPERIMENTAL"
    assert "P5B" in tcc["basis"]
    assert coordination["status"] == "NOT_IMPLEMENTED"


def test_p5b_public_tools_are_separate_from_p5a_contract():
    class FakeMCP:
        def __init__(self):
            self.names = []

        def tool(self):
            def decorator(func):
                self.names.append(func.__name__)
                return func

            return decorator

    p5a = FakeMCP()
    protection_tools.register(p5a)
    assert "evaluar_curva_tcc_p5b" not in p5a.names

    p5b = FakeMCP()
    protection_tcc_tools.register(p5b)
    assert "registrar_dataset_curva_tcc_p5b" in p5b.names
    assert "vincular_dataset_curva_tcc_p5b" in p5b.names
    assert "evaluar_curva_tcc_p5b" in p5b.names
    assert not any("coord" in name.lower() for name in p5b.names)
