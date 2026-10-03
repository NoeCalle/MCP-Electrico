from copy import deepcopy
import json
from math import cos, pi, sin, sqrt
from pathlib import Path
import shutil

import numpy as np
import pytest
from scipy.integrate import solve_ivp, trapezoid
from opendssdirect import dss

from mcp_electrico import core, motor_dynamics as dynamic, motor_soft_starting as soft
from mcp_electrico import motor_soft_starting_dossier as dossier, motor_starting_tools, workspace_state

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    values = [json.loads((ROOT/'examples'/f'p13_dynamic_rms_{s}.json').read_text(encoding='utf-8')) for s in ('manifest', 'package', 'options')]
    values.append(json.loads((ROOT/'examples/p13_soft_starter_controller.json').read_text(encoding='utf-8')))
    return values


@pytest.mark.parametrize('phi,alpha', [(0., .9), (.3, .7), (.8, 1.2), (1.3, 1.7), (.8, 2.8)])
def test_scr_fourier_and_true_rms_against_independent_numerical_rl_ode(phi, alpha):
    # v=sin(theta), |Z|=1. Solve L di/dtheta + R i=v directly.
    # This oracle does not call the analytical extinction or integral functions.
    response = soft.phase_response(alpha, phi)
    if phi == 0:
        beta = pi
        theta = np.linspace(alpha, beta, 20001)
        current = np.sin(theta)
    else:
        def extinction(t, y): return y[0]
        extinction.terminal = True; extinction.direction = -1
        ode = solve_ivp(lambda t, y: [(sin(t)-cos(phi)*y[0])/sin(phi)],
                        (alpha, 2*pi), [0.], events=extinction, dense_output=True,
                        rtol=1e-11, atol=1e-13, max_step=.002)
        beta = ode.t_events[0][-1]
        theta = np.linspace(alpha, beta, 20001)
        current = ode.sol(theta)[0]
    b = 2/pi*trapezoid(current*np.sin(theta), theta)
    a = 2/pi*trapezoid(current*np.cos(theta), theta)
    rms = sqrt(2/pi*trapezoid(current**2, theta))
    vrms = sqrt(2/pi*trapezoid(np.sin(theta)**2, theta))
    assert response['in_phase'] == pytest.approx(b, abs=2e-8)
    assert response['quadrature'] == pytest.approx(a, abs=2e-8)
    assert response['true_current_factor'] == pytest.approx(rms, abs=2e-8)
    assert response['voltage_rms_factor'] == pytest.approx(vrms, abs=2e-8)
    assert response['extinction_angle_rad'] == pytest.approx(beta, abs=1e-9)
    assert response['gain'] <= response['true_current_factor']+1e-10


@pytest.mark.parametrize('phi', [0., .4, 1.3])
def test_continuous_conduction_resistive_closed_form_and_control_inversion(phi):
    for alpha in (0., phi):
        assert soft.phase_response(alpha, phi)['true_current_factor'] == 1
        assert soft.phase_response(alpha, phi)['gain'] == 1
    for gain in (.03, .2, .6, .95):
        alpha = soft.alpha_for_gain(gain, phi)
        assert soft.phase_response(alpha, phi)['gain'] == pytest.approx(gain, abs=1e-8)
    assert soft.phase_response(pi, phi)['gain'] == 0
    if phi == 0:
        alpha = .9
        assert soft.phase_response(alpha, phi)['true_current_factor']**2 == pytest.approx(1-alpha/pi+sin(2*alpha)/(2*pi), abs=1e-12)


def test_full_voltage_soft_start_recovers_dol_trajectory_and_energy():
    m, p, o, s = inputs()
    s.update(initial_voltage_fraction=1., current_limit_a=1e6)
    dol = dynamic._trajectory(m, p, o, p['studies'][0], 1)
    scr = dynamic._trajectory(m, p, o, p['studies'][0], 1, starter=s)
    assert scr['bypass_time_s'] is not None
    for a, b in zip(dol['trajectory'], scr['trajectory']):
        for field in ('speed_rad_s', 'voltage_pu', 'torque_nm', 'current_a', 'electrical_input_energy_j'):
            assert a[field] == pytest.approx(b[field], rel=1e-9, abs=1e-7)
    assert scr['maximum_energy_relative_error'] < 1e-6


def test_ramp_current_limit_bypass_replay_and_parent_isolation():
    m, p, o, s = inputs(); before_inputs = deepcopy((m, p, o, s))
    core.crear_circuito('scr_parent', 4.16, frecuencia=60, bus_fuente='parent')
    core.agregar_carga('parent_load', 'parent', 20, 4, kv=4.16)
    workspace_state.reset_for_circuit('scr_parent')
    before = (dss.Circuit.Name(), dss.Circuit.AllElementNames(), workspace_state.status())
    first = soft.execute(m, p, o, s)
    assert first['execution_status'] == 'SOFT_STARTER_STUDIES_COMPLETED', first.get('error', first['results'])
    assert first == soft.execute(m, p, o, s)
    r = first['results'][0]; rows = r['trajectory']
    assert r['state'] == 'TARGET_REACHED'
    assert r['bypass_time_s'] is not None and r['bypass_time_s'] >= s['ramp_time_s']+s['bypass_hold_s']
    assert any(row['current_limit_active'] for row in rows)
    assert r['current_limit_verified']
    assert rows[0]['voltage_pu'] < rows[0]['supply_voltage_pu']
    assert r['criterion']['passed'] is False  # initial ramp below the supplied DOL voltage threshold
    assert r['criterion']['normative_compliance_demonstrated'] is False
    assert first['design_acceptance_status'] == 'NOT_DEMONSTRATED'
    assert before == (dss.Circuit.Name(), dss.Circuit.AllElementNames(), workspace_state.status())
    assert (m, p, o, s) == before_inputs


def test_too_low_current_limit_stalls_without_bypass_or_false_numerical_failure():
    m, p, o, s = inputs(); s['current_limit_a'] = 100
    p['simulation'].update(duration_s=.1, time_step_s=.01, maximum_steps=10)
    p['studies'][0]['maximum_acceleration_time_s'] = .1
    r = soft.execute(m, p, o, s)
    assert r['execution_status'] == 'SOFT_STARTER_STUDIES_COMPLETED', r.get('error')
    study = r['results'][0]
    assert study['state'] == 'STALLED_AT_REST'
    assert study['bypass_time_s'] is None and study['acceleration_time_s'] is None
    assert not study['criterion']['passed']
    assert study['maximum_line_current_a'] <= 100*(1+1e-7)


@pytest.mark.parametrize('field,value', [('ramp_time_s', 0), ('initial_voltage_fraction', .0),
    ('current_limit_a', True), ('current_limit_a', float('nan')), ('bypass_hold_s', -1),
    ('connection', 'INSIDE_DELTA'), ('scope_acknowledgement', 'REAL_DEVICE'), ('source_reference', '')])
def test_missing_physics_and_unsupported_scope_are_blocked_before_solving(field, value, monkeypatch):
    m, p, o, s = inputs(); s[field] = value
    def forbidden(*args): raise AssertionError('solver must not be called')
    monkeypatch.setattr(dynamic.static, '_build_isolated_base', forbidden)
    r = soft.execute(m, p, o, s)
    assert r['execution_status'] == 'BLOCKED_SOFT_STARTER_READINESS'
    assert not r['dynamic_integration_performed']


def test_untraceable_or_wrong_voltage_quantity_is_blocked():
    m, p, o, s = inputs()
    ev = s['criterion_evidence']['DYNAMIC-M01']
    ev['voltage_quantity'] = 'TOTAL_RMS'
    assert not soft.readiness(m, p, o, s)['ready_for_execution']
    ev['voltage_quantity'] = 'MOTOR_FUNDAMENTAL_RMS'; ev['clause'] = ''
    assert not soft.readiness(m, p, o, s)['ready_for_execution']
    del s['criterion_evidence']
    assert not soft.readiness(m, p, o, s)['ready_for_execution']


@pytest.mark.parametrize('malformed', ['studies', 'kind', 'controller'])
def test_malformed_payload_is_a_blocked_result_not_an_unhandled_tool_error(malformed):
    m, p, o, s = inputs()
    if malformed == 'studies': p['studies'] = None
    elif malformed == 'kind': s['criterion_evidence']['DYNAMIC-M01']['kind'] = []
    else: s = None
    result = soft.execute(m, p, o, s)
    assert result['execution_status'] == 'BLOCKED_SOFT_STARTER_READINESS'
    assert not result['dynamic_integration_performed']


def test_network_nonconvergence_and_coarse_time_grid_cannot_pass(monkeypatch):
    m, p, o, s = inputs()
    original = dynamic.static._build_isolated_base
    def build(*args):
        engine, evidence = original(*args)
        class Failed:
            def __call__(self, text): return engine(text)
            def __getattr__(self, key): return getattr(engine, key)
            class Solution:
                @staticmethod
                def Converged(): return False
        return Failed(), evidence
    monkeypatch.setattr(dynamic.static, '_build_isolated_base', build)
    r = soft.execute(m, p, o, s)
    assert r['execution_status'] == 'SOFT_STARTER_INTEGRATION_FAILED'
    assert 'NETWORK_NONCONVERGENCE' in r['error']
    monkeypatch.setattr(dynamic.static, '_build_isolated_base', original)
    p['simulation'].update(time_step_s=2, maximum_steps=2)
    r = soft.execute(m, p, o, s)
    assert r['execution_status'] in ('SOFT_STARTER_INTEGRATION_FAILED', 'SOFT_STARTER_VALIDATION_FAILED')


def test_public_tool_registration_contains_all_soft_starter_entrypoints():
    class Registry:
        def __init__(self): self.tools = {}
        def tool(self):
            def register(fn): self.tools[fn.__name__] = fn; return fn
            return register
    registry = Registry(); motor_starting_tools.register(registry)
    expected = {'obtener_contrato_arranque_suave', 'validar_dinamica_arranque_suave',
                'ejecutar_dinamica_arranque_suave', 'generar_dossier_arranque_suave', 'verificar_integridad_dossier_arranque_suave'}
    assert expected <= registry.tools.keys()


def test_scr_dossier_portable_and_detects_altered_controller_or_extra_files(tmp_path):
    m, p, o, s = inputs()
    p['simulation'].update(duration_s=.1, time_step_s=.01, maximum_steps=10)
    p['studies'][0]['maximum_acceleration_time_s'] = .1
    generated = dossier.generate(m, p, o, s, tmp_path/'study')
    assert generated['status'] == 'SOFT_STARTER_DOSSIER_READY', generated
    root = Path(generated['directory'])
    html = (root/'dynamic_workspace.html').read_text(encoding='utf-8')
    assert 'No validada contra un arrancador real' in html
    assert 'RMS total del equivalente RL' in html and 'Arranque directo trifásico' not in html
    assert 'ILLUSTRATIVE' in html and '<polyline' in html
    moved = tmp_path/'portable'; shutil.copytree(root, moved)
    assert dossier.verify(moved/dossier.INDEX)['ok']
    (moved/'soft_starter.json').write_text('{}')
    assert not dossier.verify(moved/dossier.INDEX)['ok']
    assert dossier.verify(generated['index_path'])['ok']
    (root/'extra.txt').write_text('unexpected')
    assert not dossier.verify(generated['index_path'])['ok']
