"""Independent time integration of normalized AC+DC energy at 50/60 Hz."""
from math import exp, log, sqrt

import pytest
from scipy.integrate import quad

from mcp_electrico import core, professional_data, iec60909, iec60909_two_phase


@pytest.mark.parametrize("hz", [50., 60.])
@pytest.mark.parametrize("duration", [.02, .1, 1.])
@pytest.mark.parametrize("fault", ["3ph", "2ph"])
def test_thermal_current_uses_declared_frequency_and_duration(hz, duration, fault):
    core.crear_circuito("thermal_frequency", 22.9, hz)
    professional_data.definir_red_equivalente(22.9, 500., 10., 250., 5., fuente_referencia="Synthetic thermal-frequency benchmark")
    execute = iec60909.ejecutar_3ph if fault == "3ph" else iec60909_two_phase.ejecutar_2ph
    result = execute("max", "sourcebus", calcular_ip_ith=True, topology="radial", tk_s=duration)
    assert result["ok"], result
    ik = result["results"]["ikss_ka"]
    kappa = result["results"]["ip_ka"]/sqrt(2)/ik
    rate = -2*hz*log(kappa-1)
    # IEC n=1 AC heat plus exponentially decaying DC squared; not the backend m expression.
    energy = quad(lambda t: 1+2*exp(-2*rate*t), 0, duration, epsabs=1e-12)[0]
    assert result["results"]["ith_ka"] == pytest.approx(ik*sqrt(energy/duration), rel=1e-10)
    projection = result["input_projection"]["thermal_backend_projection"]
    assert projection["declared_duration_s"] == duration
    assert projection["backend_tk_s"]*50 == pytest.approx(hz*duration)
    assert result["input_projection"]["duty"]["tk_s"] == duration


def test_backend_upgrade_cannot_reuse_frequency_workaround_silently(monkeypatch):
    monkeypatch.setattr(iec60909.pp, "__version__", "future-version")
    with pytest.raises(ValueError, match="P4SC304"):
        iec60909._thermal_backend_projection({"requested": True, "tk_s": .1}, 60.)


def test_pinned_backend_frequency_and_ac_factor_assumptions_are_still_true():
    import ast
    import inspect
    from pandapower.shortcircuit.currents import _calc_ith
    assignments = {node.targets[0].id: node.value.value
                   for node in ast.walk(ast.parse(inspect.getsource(_calc_ith)))
                   if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                   and isinstance(node.value, ast.Constant)}
    assert assignments["f"] == 50 and assignments["n"] == 1
