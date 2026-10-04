"""Structural benchmark: published topology and independent conservation checks."""
from copy import deepcopy
import json
from math import pi, sin
from pathlib import Path

import numpy as np
import pytest
from opendssdirect import dss

from mcp_electrico import core, motor_soft_starting as soft, motor_starting_tools
from mcp_electrico import soft_starter_reference as ref, workspace_state


def package():
    return json.loads((Path(__file__).resolve().parents[1]/'examples/p13g_reference_comparison.json').read_text())


@pytest.mark.parametrize('angle', [0, 5, 30, 59.9, 60, 60.1, 75, 89.9, 90, 90.1, 120, 135, 149, 150, 165, 180])
def test_independent_waveform_integrals_match_published_three_wire_rms(angle):
    response = ref.response(angle*pi/180)
    assert response['total_rms_pu'] == pytest.approx(response['closed_form_rms_pu'], abs=1e-11)
    # In a resistive floating-star network, neutral power cancels by KCL;
    # input active current coefficient equals output resistive dissipation.
    assert response['fundamental_in_phase_pu'] == pytest.approx(response['total_rms_pu']**2, abs=1e-12)
    assert response['fundamental_pu'] <= response['total_rms_pu']+1e-12


@pytest.mark.parametrize('angle', [0, 30, 60, 75, 90, 120, 149, 150])
def test_three_phase_currents_sum_zero_and_reconstructed_cycle_matches_rms(angle):
    alpha = angle*pi/180
    # 0.01-degree cells resolve the narrow conduction window near cutoff.
    theta = (np.arange(36000)+.5)*2*pi/36000
    va = np.array([ref.waveform(t, alpha) for t in theta])
    vb = np.array([ref.waveform(t-2*pi/3, alpha) for t in theta])
    vc = np.array([ref.waveform(t+2*pi/3, alpha) for t in theta])
    assert np.max(abs(va+vb+vc)) < 1e-12
    assert np.sqrt(2*np.mean(va**2)) == pytest.approx(ref.response(alpha)['total_rms_pu'], abs=2e-5)
    assert 2*np.mean(va*np.sin(theta)) == pytest.approx(ref.response(alpha)['fundamental_in_phase_pu'], abs=2e-5)
    assert 2*np.mean(va*np.cos(theta)) == pytest.approx(ref.response(alpha)['fundamental_quadrature_pu'], abs=2e-5)


def test_reference_is_independent_of_surrogate_and_exact_endpoints(monkeypatch):
    def forbidden(*args): raise AssertionError('Reference must not use surrogate')
    monkeypatch.setattr(soft, 'phase_response', forbidden, raising=False)
    assert ref.response(0)['fundamental_pu'] == pytest.approx(1.)
    assert ref.response(5*pi/6)['total_rms_pu'] == 0.
    assert ref.response(pi)['fundamental_pu'] == 0.
    for angle in (60, 90):
        x = angle*pi/180
        assert ref.rms_closed_form(x-1e-9) == pytest.approx(ref.rms_closed_form(x+1e-9), abs=1e-8)


def test_comparison_against_deleted_physics_is_explicitly_retired():
    result = ref.compare(package())
    assert result['status'] == 'RETIRED_SURROGATE_COMPARISON'
    assert not result['same_angle'] and not result['same_fundamental']


def test_read_only_tool_parent_unchanged_and_registered():
    core.crear_circuito('reference_parent', 13.8, frecuencia=60)
    workspace_state.reset_for_circuit('reference_parent')
    before = (dss.Circuit.Name(), dss.Circuit.AllElementNames(), workspace_state.status())
    p = package(); before_package = deepcopy(p)
    first = ref.compare(p)
    assert first == ref.compare(p) and p == before_package
    assert before == (dss.Circuit.Name(), dss.Circuit.AllElementNames(), workspace_state.status())
    class Registry:
        def __init__(self): self.tools = {}
        def tool(self):
            def register(fn): self.tools[fn.__name__] = fn; return fn
            return register
    registry = Registry(); motor_starting_tools.register(registry)
    assert registry.tools['contrastar_arranque_suave'](p) == first


@pytest.mark.parametrize('value', [None, [], {}, {'bad': 'field'}])
def test_malformed_package_returns_blocked_result(value):
    assert ref.compare(value)['status'] == 'RETIRED_SURROGATE_COMPARISON'
