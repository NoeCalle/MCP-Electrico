from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest
from opendssdirect import dss
from mcp_electrico import reactive_compensation as rc, engine_selection
from scripts.reactive_compensation_reference import reference_package, analytical_reference

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def package():
    return json.loads((ROOT/'examples/reactive_compensation_stage1.json').read_text(encoding='utf8'))

@pytest.mark.parametrize('connection',['wye','delta'])
@pytest.mark.parametrize('pu',[.9,1.,1.1])
@pytest.mark.parametrize('frequency',[50,60])
def test_native_engine_against_closed_form_impedance_circuit(package,tmp_path,connection,pu,frequency):
    p=reference_package(package,connection,pu,frequency)
    assert rc.validate(p)['ready_for_execution']
    result=rc.execute(p,str(tmp_path/'case'))
    assert result['status']=='REACTIVE_COMPENSATION_COMPLETED',result
    for label,compensated in [('before',False),('after',True)]:
        actual=result['results'][0][label];expected=analytical_reference(p,compensated)
        assert actual['source']['p_kw']==pytest.approx(expected['p_kw'],abs=.0002)
        assert actual['source']['q_kvar']==pytest.approx(expected['q_kvar'],abs=.0002)
        assert actual['buses'][1]['minimum_pu']==pytest.approx(expected['voltage_pu'],abs=2e-6)
        assert actual['lines'][0]['maximum_phase_current_a']==pytest.approx(expected['current_a'],abs=.002)
        assert actual['network_losses_kw']==pytest.approx(expected['line_losses_kw'],abs=.0002)
        assert actual['banks'][0]['actual_injected_kvar']==pytest.approx(expected['injected_kvar'],abs=.0002)
        assert actual['power_balance']['passed']
    assert result['results'][0]['after']['banks'][0]['states']==[1,0,1]

@pytest.mark.parametrize('path,value',[
    (('banks',0,'steps_kvar'),20),(('banks',0,'steps_kvar'),[True]),
    (('banks',0,'connection'),'invalid'),(('base_model','source','pu'),float('nan')),
    (('base_model','source','scc_max_mva'),float('inf')),
    (('base_model','source','pu'),10**400),
    (('scenarios',0,'bank_states','bank1'),[True,0,0]),
    (('scenarios',0,'load_multiplier'),-1), (('options','allow_experimental'),'false'),
    (('criteria','source_reference'),''), (('base_model','topology','loads',0,'model'),3),
    (('base_model','topology','lines',0,'normamps_a'),None),
])
def test_reject_incomplete_or_unsupported_inputs_without_calculation(package,tmp_path,path,value):
    target=package
    for key in path[:-1]:target=target[key]
    target[path[-1]]=value
    result=rc.execute(package,str(tmp_path/'blocked'))
    assert result['status']=='BLOCKED_REACTIVE_COMPENSATION_INPUTS'
    assert not result['readiness']['electrical_calculation_performed']
    assert not (tmp_path/'blocked').exists()

def test_light_load_leading_pf_and_paired_baseline(package,tmp_path):
    result=rc.execute(package,str(tmp_path/'cases'))
    rows={r['id']:r for r in result['results']}
    assert result['status']=='REACTIVE_COMPENSATION_COMPLETED'
    assert rows['nominal_100']['criteria']['passed']
    assert rows['light_50']['after']['source']['power_factor']>.999
    assert rows['light_50']['after']['source']['reactive_direction']=='LEADING'
    assert not rows['light_50']['criteria']['passed']
    assert rows['light_50']['before']['source']==rows['light_off']['before']['source']
    assert result['recommendations'][1]['selected_scenario_id']=='nominal_100'
    integrity=json.loads((tmp_path/'cases/Integrity.json').read_text())
    for name,digest in integrity['files_sha256'].items():assert hashlib.sha256((tmp_path/'cases'/name).read_bytes()).hexdigest()==digest
    assert 'Pérdidas de red' in (tmp_path/'cases/Informe.html').read_text(encoding='utf8')
    assert rc.execute(package,str(tmp_path/'cases'))['status']=='BLOCKED_OUTPUT_DIRECTORY'

def test_parent_model_settings_solution_and_meters_preserved(package,tmp_path):
    dss('Clear');dss('New Circuit.parent basekv=12.47');dss('New Load.keep bus1=sourcebus kv=12.47 kw=100 kvar=20');dss('Solve')
    dss.Circuit.SetActiveBus('sourcebus')
    before=(dss.Circuit.Name(),dss.Circuit.AllElementNames(),dss.Circuit.TotalPower(),dss.Bus.VMagAngle(),dss.Solution.Frequency(),dss.Solution.Converged(),deepcopy(rc.network.workspace_state.status()))
    rc.execute(package,str(tmp_path/'isolated'))
    after=(dss.Circuit.Name(),dss.Circuit.AllElementNames(),dss.Circuit.TotalPower(),dss.Bus.VMagAngle(),dss.Solution.Frequency(),dss.Solution.Converged(),deepcopy(rc.network.workspace_state.status()))
    assert after==before

def test_overload_is_distinct_from_nonconvergence(package,tmp_path):
    package['base_model']['topology']['lines'][0]['normamps_a']=10
    result=rc.execute(package,str(tmp_path/'overload'))
    assert result['results'][0]['after']['converged']
    assert result['results'][0]['after']['overload_evaluation']=='OVERLOADED'
    package['options']['max_iterations']=1
    package['base_model']['source']['scc_max_mva']=1
    result=rc.execute(package,str(tmp_path/'nonconvergent'))
    invalid=[r for r in result['results'] if not r['after'].get('converged')]
    assert invalid,result
    for row in invalid:
        assert row['after']['overload_evaluation']=='NOT_EVALUABLE'
        assert not row['criteria']['evaluated']

def test_first_bus_and_route_require_explicit_package(package):
    package['options']['allow_experimental']=False
    assert rc.validate(package)['ready_for_execution']
    p=reference_package(package);engine,_=rc._create_engine(p,p['scenarios'][0]);engine.Solution.Solve()
    assert len(rc.network._bus_voltage_pu(engine,'supply'))==3
    assert rc.network._bus_voltage_pu(engine,'absent')==[]
    result=engine_selection.seleccionar_motor_estudio('compensacion_reactiva',permitir_experimental=True)
    assert result['selected_engine']=='opendss'
    assert result['readiness']['overall_status']=='MISSING_DATA'
    assert not result['readiness']['data_evaluated']
    assert not result['executable']
    assert not result['professional_emission']
