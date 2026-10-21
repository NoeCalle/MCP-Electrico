"""Independent analytical witnesses, sampled crosschecks and fail-closed gates."""
import asyncio
from copy import deepcopy
import json
from math import log10

import numpy as np
import pytest
from scipy.optimize import minimize_scalar

from mcp_electrico import core, protection_curves as curves, protection_data as devices
from mcp_electrico import protection_coordination_range as ranges


@pytest.fixture(autouse=True)
def model():
    core.crear_circuito("range_tests", .48)
    devices.reset()
    curves.reset()
    core.agregar_linea("f1", "sourcebus", "b1", .05, fases=3, r1_ohm_km=.2, x1_ohm_km=.08)
    core.agregar_linea("f2", "b1", "b2", .05, fases=3, r1_ohm_km=.2, x1_ohm_km=.08)
    for name, element in (("down", "Line.f2"), ("up", "Line.f1")):
        devices.definir_dispositivo(name, "circuit_breaker", element, 100, .48,
                                    norma_referencia="TEST_DATA_NOT_PRODUCT_COMPLIANCE",
                                    fuente_referencia="SYNTHETIC_TEST_NOT_MANUFACTURER")
    yield
    devices.reset()
    curves.reset()


def bind(name, points, *, shape="SINGLE", semantics="TOTAL_CLEARING_TIME", segments=None):
    devices.vincular_curva(name, name, "TEST_CURVE", "SYNTHETIC_TEST_NOT_MANUFACTURER")
    curves.registrar_dataset(
        name, name, shape, semantics, segments or [{"id": "s", "points": points}],
        "TEST_DATA", "SYNTHETIC_ANALYTICAL_CURVE_NOT_FIELD_INSTALLATION",
    )
    curves.vincular_dataset_dispositivo(name, name)


def single(currents, times):
    return [{"current_a": i, "time_s": t} for i, t in zip(currents, times)]


def run(**overrides):
    args = dict(dispositivo_downstream="down", dispositivo_upstream="up",
                corriente_minima_downstream_a=100, corriente_maxima_downstream_a=1000,
                factor_corriente_upstream=1, margen_minimo_s=.2,
                fuente_relacion="test explicit series pair", fuente_corrientes="test explicit range and ratio")
    args.update(overrides)
    result = ranges.evaluar_coordinacion_intervalo(**args)
    json.dumps(result, allow_nan=False)
    return result


def test_range_pass_records_full_snapshot_and_no_selectivity_claim():
    bind("down", single([100, 1000], [1, .1]))
    bind("up", single([100, 1000], [4, .4]))
    before = deepcopy((devices.snapshot(), curves.listar_datasets()))
    result = run()
    assert result["status"] == "PASS"
    assert result["worst_case"]["conservative_margin_s"] == pytest.approx(.3)
    assert result["full_requested_range_evaluated"]
    assert result["claims"]["selectivity"] == "NOT_EVALUATED"
    assert len(result["downstream_trace"]["sha256"]) == 64
    assert result["downstream_trace"]["dataset"]["source"]["type"] == "TEST_DATA"
    assert not result["professional_emission"]
    assert before == (devices.snapshot(), curves.listar_datasets())


def test_hidden_knot_failure_despite_passing_extreme_currents():
    bind("down", single([100, 10000], [1, 1]))
    bind("up", single([100, 1000, 10000], [3, .5, 3]))
    result = run(corriente_maxima_downstream_a=10000, margen_minimo_s=1)
    assert 3 - 1 >= 1  # Both extreme-current checks pass.
    assert result["status"] == "FAIL"
    assert result["interval_count"] == 2
    assert result["worst_case"]["downstream_current_a"] == pytest.approx(1000)
    assert result["worst_case"]["conservative_margin_s"] == pytest.approx(-.5)


def test_true_interior_minimum_not_just_knots():
    # x = I / 100.  f(x) = 1/x² - 1/x, f'(2) = 0, f(2) = -1/4.
    bind("down", single([100, 400], [1, .25]))
    bind("up", single([100, 400], [1, .0625]))
    result = run(corriente_maxima_downstream_a=400, margen_minimo_s=0)
    worst = result["worst_case"]
    assert result["status"] == "FAIL"
    assert worst["kind"] == "INTERIOR_STATIONARY_POINT"
    assert worst["downstream_current_a"] == pytest.approx(200)
    assert worst["conservative_margin_s"] == pytest.approx(-.25)


def test_band_and_explicit_ratio_use_different_current_scales():
    bind("down", [{"current_a": i, "time_min_s": .01, "time_max_s": t}
                  for i, t in ((100, 1), (1000, .1))], shape="BAND")
    bind("up", [{"current_a": i, "time_min_s": t, "time_max_s": 100}
                for i, t in ((50, 2), (250, .8), (500, .4))], shape="BAND")
    result = run(factor_corriente_upstream=.5)
    assert result["status"] == "PASS"
    assert result["interval_count"] == 2  # upstream knot maps to downstream I=500 A
    assert result["worst_case"]["upstream_current_a"] == pytest.approx(500)
    assert result["worst_case"]["conservative_margin_s"] == pytest.approx(.3)
    assert result["currents"]["same_current_assumed"] is False


@pytest.mark.parametrize("which", ["down", "up"])
def test_internal_domain_gap_blocks_even_with_both_endpoints_present(which):
    bind("down" if which == "up" else "up", single([100, 1000], [1, .1]))
    bind(which, [], segments=[
        {"id": "a", "points": single([100, 200], [4, 2])},
        {"id": "b", "points": single([800, 1000], [.5, .4])},
    ])
    result = run()
    assert result["status"] == "COORDINATION_RANGE_NOT_READY"
    assert result["worst_case"] is None
    assert not result["full_requested_range_evaluated"]
    assert result["issues"][0]["reason"] == "RANGE_OUT_OF_DOMAIN_OR_CROSSES_SEGMENT_GAP"


@pytest.mark.parametrize("semantics", ["TRIP_TIME", "OPERATING_TIME", "MELTING_TIME"])
def test_other_time_semantics_never_promoted(semantics):
    bind("down", single([100, 1000], [1, .1]))
    bind("up", single([100, 1000], [4, .4]), semantics=semantics)
    result = run()
    assert result["status"] == "COORDINATION_RANGE_NOT_READY"
    assert result["issues"][0]["reason"] == "TIME_SEMANTICS_NOT_CLEARING_READY"


def test_no_clipping_extrapolation_or_implicit_missing_dataset():
    bind("down", single([100, 1000], [1, .1]))
    assert run()["status"] == "COORDINATION_RANGE_NOT_READY"
    bind("up", single([100, 1000], [4, .4]))
    assert run(corriente_minima_downstream_a=99)["status"] == "COORDINATION_RANGE_NOT_READY"
    assert run(corriente_maxima_downstream_a=1001)["status"] == "COORDINATION_RANGE_NOT_READY"
    assert run(dispositivo_upstream="missing")["issues"][0]["reason"] == "DEVICE_NOT_FOUND"


@pytest.mark.parametrize("override", [
    {"corriente_minima_downstream_a": 0}, {"corriente_minima_downstream_a": -1},
    {"corriente_maxima_downstream_a": 100}, {"factor_corriente_upstream": True},
    {"factor_corriente_upstream": float("nan")}, {"factor_corriente_upstream": 0},
    {"factor_corriente_upstream": 1e308}, {"factor_corriente_upstream": 1e-324},
    {"margen_minimo_s": -1}, {"margen_minimo_s": float("inf")},
    {"fuente_corrientes": " "}, {"fuente_relacion": None},
    {"dispositivo_upstream": "Protection.DOWN"},
])
def test_invalid_or_untraceable_input_is_rejected(override):
    with pytest.raises(ValueError, match="P5ER"):
        run(**override)


def test_tiny_requested_margin_is_not_erased_by_favourable_epsilon():
    bind("down", single([100, 1000], [1, 1]))
    bind("up", single([100, 1000], [1, 1]))
    assert run(margen_minimo_s=1e-14)["status"] == "FAIL"
    assert run(margen_minimo_s=0)["status"] == "PASS"


def test_unresolvable_float_interval_blocks_instead_of_sampling_or_passing():
    bind("down", single([100, 1000], [1, .1]))
    bind("up", single([100, 1000], [4, .4]))
    result = run(corriente_maxima_downstream_a=float(np.nextafter(100., np.inf)))
    assert result["status"] == "COORDINATION_RANGE_NOT_READY"
    assert not result["resultados_validos"]
    assert result["issues"][0]["reason"] == "NUMERIC_RANGE_NOT_RESOLVABLE"


def test_snapshot_digest_changes_with_device_settings():
    bind("down", single([100, 1000], [1, .1]))
    bind("up", single([100, 1000], [4, .4]))
    first = run()
    devices.definir_ajustes("up", ir_a=120, fuente_referencia="synthetic revised settings")
    second = run()
    assert first["upstream_trace"]["sha256"] != second["upstream_trace"]["sha256"]
    assert first["downstream_trace"]["sha256"] == second["downstream_trace"]["sha256"]
    assert first["upstream_trace"]["device"]["settings"] is None


def test_selector_cannot_claim_readiness_without_the_requested_parameters():
    from mcp_electrico import engine_selection
    result = engine_selection.seleccionar_motor_estudio("coordinacion_intervalo")
    assert result["selected_engine"] == "mcp"
    assert not result["executable"]
    assert not result["professional_execution_ready"]
    assert not result["readiness"]["data_evaluated"]


@pytest.mark.parametrize("seed", range(12))
def test_independent_piecewise_minimizer_and_dense_sample_crosscheck(seed):
    rng = np.random.default_rng(seed)
    dc = np.array([100, 210, 500, 1000.])
    uc = np.array([100, 350, 720, 1000.])
    dt, ut = 10 ** rng.uniform(-2, 1, 4), 10 ** rng.uniform(-2, 1, 4)
    bind("down", single(dc, dt))
    bind("up", single(uc, ut))
    result = run()
    # Independent implementation: NumPy interpolation of input points plus
    # SciPy bounded optimization on each merged interval (no production helper).
    def objective(log_current):
        return 10 ** np.interp(log_current, np.log10(uc), np.log10(ut)) - 10 ** np.interp(log_current, np.log10(dc), np.log10(dt))
    knots = np.log10(sorted(set(dc) | set(uc)))
    reference = min([objective(x) for x in knots] + [
        minimize_scalar(objective, bounds=(a, b), method="bounded", options={"xatol": 1e-13}).fun
        for a, b in zip(knots, knots[1:])])
    actual = result["worst_case"]["conservative_margin_s"]
    assert actual == pytest.approx(reference, rel=1e-9, abs=1e-10)
    assert actual <= min(objective(x) for x in np.linspace(log10(100), log10(1000), 4001)) + 1e-10


def test_public_dispatch_calls_one_executor_and_keeps_separate_workspace_result(monkeypatch):
    import server
    from mcp_electrico import study_dispatch, workspace_state
    bind("down", single([100, 1000], [1, .1]))
    bind("up", single([100, 1000], [4, .4]))
    workspace_state.reset_for_circuit()
    calls = []
    original = server.mcp.call_tool
    async def tracked(name, arguments):
        calls.append(name)
        return await original(name, arguments)
    monkeypatch.setattr(server.mcp, "call_tool", tracked)
    params = dict(dispositivo_downstream="down", dispositivo_upstream="up",
                  corriente_minima_downstream_a=100, corriente_maxima_downstream_a=1000,
                  factor_corriente_upstream=1, margen_minimo_s=.2,
                  fuente_relacion="synthetic pair", fuente_corrientes="synthetic range")
    result = asyncio.run(study_dispatch.execute(server.mcp, "coordinacion_intervalo", params))
    assert calls == ["evaluar_coordinacion_intervalo_p5e"]
    assert result["selected_engine"] == "mcp"
    assert not result["fallback"]
    assert result["result"]["status"] == "PASS"
    assert "protection_coordination_range" in workspace_state.status()["studies"]
    params["corriente_maxima_downstream_a"] = 1001
    rejected = asyncio.run(study_dispatch.execute(server.mcp, "coordinacion_intervalo", params))
    assert rejected["result"]["status"] == "COORDINATION_RANGE_NOT_READY"
    assert not workspace_state.status()["studies"]["protection_coordination_range"]["valid"]
