"""A failed native solve must never publish its last iterate as engineering data."""
import pytest
from opendssdirect import dss
from mcp_electrico import core, studies, workspace_state, visual_state


@pytest.fixture
def limited_solver():
    core.crear_circuito("limited_solver", 0.4)
    core.agregar_linea("f1", "sourcebus", "loadbus", 0.1, r1_ohm_km=.3, x1_ohm_km=.2)
    core.agregar_carga("l1", "loadbus", 80, 30, kv=0.4)
    visual_state.configure_feeder("Line.f1", corriente_nominal_a=100)
    dss("Set MaxIterations=1 Tolerance=0.000000000001")
    workspace_state.reset_for_circuit()
    yield
    dss("Set MaxIterations=100 Tolerance=0.0001")
    visual_state.reset()


def test_native_failure_suppresses_voltages_and_losses(limited_solver):
    result = core.ejecutar_flujo_potencia()
    assert dss.Solution.Converged() is False
    assert result["convergio"] is False
    assert result["resultados_validos"] is False
    assert result["voltajes_por_bus"] == {}
    assert result["perdidas_totales_kw"] is None
    assert result["perdidas_totales_kvar"] is None
    assert result["evaluacion_sobrecarga"] == "NO_EVALUABLE"
    assert result["causa_no_convergencia"] == "NO_DETERMINADA"


@pytest.mark.parametrize("study", [studies.analizar_flujo_operacion, studies.analizar_caida_tension])
def test_failed_study_never_reads_native_last_iterate(limited_solver, monkeypatch, study):
    def reject_read(*args, **kwargs):
        pytest.fail("A failed solve must not read native last-iterate measurements")
    monkeypatch.setattr(studies, "_active_line_measurements", reject_read)
    monkeypatch.setattr(studies, "_raw_bus_voltage_map", reject_read)
    result = study()
    assert result["convergio"] is False
    assert result["resultados_validos"] is False
    assert result["buses"] == result["alimentadores"] == []
    workspace_state.record_solution(result)
    workspace_state.record_study("derived", result)
    state = workspace_state.status()
    assert state["results_current"] is False
    assert state["studies"]["powerflow"]["valid"] is False
    assert state["studies"]["derived"]["valid"] is False


def test_converged_study_restores_validity_after_failure(limited_solver):
    failed = core.ejecutar_flujo_potencia()
    workspace_state.record_solution(failed)
    dss("Set MaxIterations=100 Tolerance=0.0000001")
    # A lightly loaded control scenario verifies recovery, not acceptance of the failed case.
    dss("Edit Load.l1 kW=10 kvar=3")
    flow = studies.analizar_flujo_operacion()
    assert flow["convergio"] is True
    assert flow["powerflow"]["resultados_validos"] is True
    assert flow["buses"] and flow["alimentadores"]
    assert flow["resumen"]["perdidas_totales_kw"] > 0
    workspace_state.record_solution(flow["powerflow"])
    state = workspace_state.status()
    assert state["results_current"] is True
    assert state["studies"]["powerflow"]["valid"] is True


def test_public_server_marks_failed_studies_invalid(limited_solver, tmp_path):
    import server
    from mcp_electrico import workspace
    target = tmp_path / "failure.html"
    workspace.configure(str(target), auto_regenerar=True)
    try:
        failed = server.ejecutar_flujo_potencia()
        assert failed["convergio"] is False
        assert failed["perdidas_totales_kw"] is None
        drop = server.analizar_caida_tension()
        assert drop["criterio"]["estado"] == "NO_EVALUABLE"
        state = server.obtener_estado_workspace()["workspace"]
        assert state["state"] == "ERROR"
        assert state["results_current"] is False
        assert not state["studies"]["flow"]["valid"]
        assert not state["studies"]["voltage_drop"]["valid"]
        assert "ERROR ELÉCTRICO" in target.read_text(encoding="utf-8")
    finally:
        workspace._config.update(path=tmp_path / "unused.html", auto_regenerate=False)
