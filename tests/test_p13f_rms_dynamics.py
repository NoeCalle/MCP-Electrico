from copy import deepcopy
import json
from math import exp,pi,sqrt
from pathlib import Path

import numpy as np
import pytest
from opendssdirect import dss

from mcp_electrico import core, motor_dynamics as dynamic, motor_dynamics_intake, workspace_state

ROOT=Path(__file__).resolve().parents[1]


def inputs():
    return tuple(json.loads((ROOT/'examples'/f'p13_dynamic_rms_{s}.json').read_text(encoding='utf-8')) for s in ('manifest','package','options'))


@pytest.mark.parametrize('damped',[False,True])
def test_b01_b02_integrator_against_closed_form_mechanics(damped):
    state=[0.,0.]
    rhs=lambda t,y:[(40-2*y[0])/10,y[0]] if damped else [6,y[0]]
    for j in range(2000): state=dynamic.rk4(rhs,state,j*.001,.001)
    expected=[20*(1-exp(-.4)),40-100*(1-exp(-.4))] if damped else [12,12]
    assert state==pytest.approx(expected,abs=1e-6)


@pytest.mark.parametrize('connection',['delta','wye'])
@pytest.mark.parametrize('slip',[1,.5,.05])
def test_b03_equivalent_circuit_against_independent_nodal_system(connection,slip):
    _,package,_=inputs()
    model=deepcopy(package['motors'][0]); e=model['electrical']
    e.update(frequency_hz=100/pi,stator_resistance_ohm=1,rotor_resistance_ohm=2,
             stator_leakage_inductance_h=3/200,rotor_leakage_inductance_h=4/200,magnetizing_inductance_h=5/200)
    motor={'connection':connection}
    vp=230 if connection=='wye' else 230*sqrt(3)
    zs=1+3j; zr=2/slip+4j; zm=5j
    # Unknowns are stator current and internal EMF; this solves KVL/KCL directly.
    istat,emf=np.linalg.solve(np.array([[zs,1],[1,-1/zm-1/zr]],dtype=complex),[vp,0])
    rotor=emf/zr
    expected_current=abs(istat)*(sqrt(3) if connection=='delta' else 1)
    expected_torque=3*abs(rotor)**2*(2/slip)/100
    result=dynamic.electrical(model,motor,(1-slip)*100,230*sqrt(3))
    assert result['current_a']==pytest.approx(expected_current,rel=1e-12)
    assert result['torque_nm']==pytest.approx(expected_torque,rel=1e-12)
    assert result['input_power_w']==pytest.approx((3*vp*istat.conjugate()).real,rel=1e-12)
    assert abs(result['electrical_balance_residual_w'])<1e-8


def test_b04_b05_b07_coupled_energy_refinement_and_exact_replay():
    m,p,o=inputs(); original=deepcopy((m,p,o))
    core.crear_circuito('dynamic_parent',4.16,frecuencia=60,bus_fuente='parent')
    core.agregar_carga('parent_load','parent',20,4,kv=4.16)
    workspace_state.reset_for_circuit('dynamic_parent')
    before=(dss.Circuit.Name(),dss.Circuit.AllElementNames(),workspace_state.status())
    first=dynamic.execute(m,p,o); replay=dynamic.execute(m,p,o)
    assert first==replay
    assert first['execution_status']=='DYNAMIC_STUDIES_COMPLETED'
    r=first['results'][0]
    assert r['state']=='TARGET_REACHED' and r['criterion']['passed']
    assert 1.7<r['acceleration_time_s']<1.9
    assert r['verification']['maximum_energy_relative_error']<1e-6
    assert max(r['verification']['grid_relative_errors'].values())<1e-5
    assert before==(dss.Circuit.Name(),dss.Circuit.AllElementNames(),workspace_state.status())
    assert (m,p,o)==original


def test_b06_resisting_load_stalls_at_rest_without_false_success():
    m,p,o=inputs()
    for point in p['motors'][0]['mechanical']['load_curve']: point['torque_nm']=10000
    p['simulation'].update(duration_s=.1,time_step_s=.01,maximum_steps=10)
    p['studies'][0]['maximum_acceleration_time_s']=.1
    r=dynamic.execute(m,p,o)
    assert r['execution_status']=='DYNAMIC_STUDIES_COMPLETED'
    assert r['results'][0]['state']=='STALLED_AT_REST'
    assert r['results'][0]['criterion']['passed'] is False
    assert r['results'][0]['acceleration_time_s'] is None


def test_b06_native_network_nonconvergence_is_blocked(monkeypatch):
    m,p,o=inputs()
    original=dynamic.static._build_isolated_base
    def builder(*args):
        ctx,evidence=original(*args)
        class FailedSolution:
            def Converged(self): return False
        class Context:
            Solution=FailedSolution()
            def __call__(self,text): return ctx(text)
            def __getattr__(self,key): return getattr(ctx,key)
        return Context(),evidence
    monkeypatch.setattr(dynamic.static,'_build_isolated_base',builder)
    r=dynamic.execute(m,p,o)
    assert r['execution_status']=='DYNAMIC_INTEGRATION_FAILED'
    assert 'NETWORK_NONCONVERGENCE' in r['error']
    assert r['results']==[] and r['parent_context_mutated'] is False


@pytest.mark.parametrize('field,value',[('backend','OpenDSS'),('electrical_model','EMT'),
    ('energy_relative_tolerance',True),('refinement_relative_tolerance',float('nan')),
    ('rated_speed_fraction',1),('starting_current_relative_tolerance',.2),
    ('energy_relative_tolerance',10**1000),('refinement','NONE'),('source_reference','')])
def test_options_do_not_silently_admit_missing_physics_or_loose_gates(field,value):
    m,p,o=inputs();o[field]=value
    assert not dynamic.readiness(m,p,o)['ready_for_execution']


def test_physical_calibration_blocks_the_unfitted_preparation_fixture():
    m=json.loads((ROOT/'examples/p13_motor_starting_multi_stage3.json').read_text())
    p=json.loads((ROOT/'examples/p13_motor_dynamics_reference.json').read_text())
    _,_,o=inputs()
    r=dynamic.readiness(m,p,o)
    assert not r['ready_for_execution']
    assert r['calibration'][0]['rated_output_relative_error']>.5


def test_actual_integration_error_cannot_promote_a_coarse_grid_to_success():
    m,p,o=inputs();p['simulation'].update(time_step_s=2,maximum_steps=2)
    r=dynamic.execute(m,p,o)
    assert r['execution_status'] in ('DYNAMIC_INTEGRATION_FAILED','DYNAMIC_VALIDATION_FAILED')


def test_network_default_debt_blocks_execution_before_solve():
    m,p,o=inputs(); del m['base_model']['source']['angle_deg']
    p['manifest_sha256']=motor_dynamics_intake.manifest_sha256(m)
    r=dynamic.execute(m,p,o)
    assert r['execution_status']=='BLOCKED_DYNAMIC_READINESS'
    assert r['dynamic_integration_performed'] is False
