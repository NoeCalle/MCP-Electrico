"""Data, provenance, numerical evidence and migration safeguards."""
from copy import deepcopy
import csv
import json
from pathlib import Path
from math import pi, sin, sqrt

import pytest
from mcp_electrico import modelica_motor_adapter as adapter

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def study(monkeypatch):
    monkeypatch.setattr(adapter,'runtime',lambda:{'ready':False,'reason':'Not installed in unit-test environment'})
    return json.loads((ROOT/'examples/msl_motor_dol.json').read_text())

def test_complete_physics_does_not_promote_missing_runtime(study,tmp_path):
    original=deepcopy(study)
    readiness=adapter.validate(study)
    assert readiness['data_ready'] and not readiness['ready_for_execution']
    blocked=adapter.execute(study,tmp_path/'new')
    assert blocked['status']=='BLOCKED_MODELICA_READINESS'
    assert not (tmp_path/'new').exists() and original==study

@pytest.mark.parametrize('value',[None,True,0,-1,float('nan'),float('inf'),'0.1'])
def test_motor_parameters_are_never_completed_or_coerced(study,value):
    study['motors'][0]['electrical']['rotor_resistance_ohm']=value
    assert not adapter.validate(study)['data_ready']

@pytest.mark.parametrize('value',[None,[],{},False])
def test_malformed_root_is_structured_blockage(value,monkeypatch):
    monkeypatch.setattr(adapter,'runtime',lambda:{'ready':False})
    result=adapter.validate(value)
    assert not result['data_ready'] and result['issues']

def test_restraint_and_curve_coverage_cannot_be_assumed(study):
    study['motors'][0]['mechanical']['anti_reverse']='NONE'
    assert not adapter.validate(study)['data_ready']
    study['motors'][0]['mechanical']['load_curve'][0]['torque_nm']=0
    study['motors'][0]['mechanical']['load_curve'].insert(0,{'speed_rad_s':-100,'torque_nm':0})
    assert adapter.validate(study)['data_ready']
    study['motors'][0]['mechanical']['load_curve'][-1]['speed_rad_s']=100
    assert not adapter.validate(study)['data_ready']

def test_undersampling_and_observation_window_rejected(study):
    study['simulation']['output_step_s']=.001
    assert not adapter.validate(study)['data_ready']
    study['simulation']['output_step_s']=.00005
    study['motors'][0]['starting']['time_s']=3.99
    result=adapter.validate(study)
    assert not result['data_ready']
    assert any('post-start' in issue['message'] or 'two complete' in issue['message'] for issue in result['issues'])

def test_scr_missing_control_and_criteria_block_even_with_installed_runtime(study,monkeypatch):
    monkeypatch.setattr(adapter,'runtime',lambda:{'ready':True})
    study['motors'][0]['starting']['method']='SCR'
    result=adapter.validate(study)
    assert not result['ready_for_execution']
    assert not result['data_ready']
    assert 'SCR' in adapter.contract()['starting_methods']

def test_scr_complete_scoped_package_and_unqualified_topologies(monkeypatch):
    monkeypatch.setattr(adapter,'runtime',lambda:{'ready':True})
    package=json.loads((ROOT/'examples/msl_motor_scr.json').read_text(encoding='utf8'))
    assert adapter.validate(package)['ready_for_execution']
    package['motors'].append(deepcopy(package['motors'][0]))
    package['motors'][1]['id']='SECOND'
    assert adapter.validate(package)['qualification_blockers']==['MULTIMOTOR_SCR_NOT_QUALIFIED']
    package['motors'].pop()
    package['motors'][0]['connection']='wye'
    assert adapter.validate(package)['qualification_blockers']==['SCR_WYE_CONNECTION_NOT_QUALIFIED']
    assert not adapter.validate(package)['ready_for_execution']

def test_cycle_measurements_match_sinusoidal_rms_and_failed_acceleration(tmp_path,study):
    # Test only the reading of external traces, with known waveforms and units.
    file=tmp_path/'trace.csv'
    with file.open('w',newline='') as stream:
        names=['time']+['m0'+n for n in ('speed','torque','ia','ib','ic','vab','vbc','vca','busvab','busvbc','busvca','bypass','vRef')]
        writer=csv.DictWriter(stream,fieldnames=names);writer.writeheader()
        for j in range(4001):
            t=j*.00005
            row={'time':t,'m0speed':0,'m0torque':50,'m0bypass':0,'m0vRef':1}
            for k,(i,v) in enumerate(zip(('ia','ib','ic'),('vab','vbc','vca'))):
                row['m0'+i]=sqrt(2)*100*sin(2*pi*60*t-2*pi*k/3)
                row['m0'+v]=sqrt(2)*480*sin(2*pi*60*t-2*pi*k/3)
                row['m0bus'+v]=row['m0'+v]
            writer.writerow(row)
    study['simulation']['duration_s']=.2
    result=adapter._summaries(file,study)[0]
    assert result['maximum_cycle_rms_current_a']==pytest.approx(100,rel=1e-4)
    assert result['minimum_voltage_pu']==pytest.approx(1,rel=1e-4)
    assert result['minimum_bus_voltage_pu']==pytest.approx(1,rel=1e-4)
    assert result['acceleration_time_s'] is None and not result['criterion']['passed']
    study['simulation']['duration_s']=4
    with pytest.raises(ValueError,match='INCOMPLETE_OBSERVATION'):adapter._summaries(file,study)
    study['simulation']['duration_s']=.2
    bad=file.read_text().replace('m0ia','unavailable',1);file.write_text(bad)
    with pytest.raises(KeyError):adapter._summaries(file,study)

def test_config_corruption_and_library_change_disable_runtime(tmp_path,monkeypatch):
    monkeypatch.setattr(adapter,'CONFIG',tmp_path/'runtime.json')
    monkeypatch.setattr(adapter,'_configuration',None)
    adapter.CONFIG.write_text('{broken')
    assert not adapter.runtime()['ready']
    compiler=tmp_path/'omc';compiler.write_text('compiler')
    library=tmp_path/'msl';(library/'Modelica').mkdir(parents=True)
    (library/'Modelica/package.mo').write_text('version="4.0.0"')
    monkeypatch.setattr(adapter,'_configuration',{'executable':str(compiler),'library':str(library),'compiler_sha256':adapter._digest(compiler),'library_tree_sha256':adapter._library_digest(library)})
    assert adapter.runtime()['ready']
    (library/'Modelica/package.mo').write_text('changed')
    assert not adapter.runtime()['ready']

def test_scr_rms_keeps_both_states_of_switching_events(tmp_path,study):
    # Known 50% duty square wave: RMS=A/sqrt(2), regardless of output grid.
    file=tmp_path/'events.csv';period=1/60
    keys=['speed','torque','ia','ib','ic','vab','vbc','vca','busvab','busvbc','busvca','bypass','vRef']
    events=[(0,100),(period/2,100),(period/2,0),(period,0),(period,100),(1.5*period,100),(1.5*period,0),(2*period,0)]
    with file.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['time']+['m0'+key for key in keys]);writer.writeheader()
        for at,voltage in events:
            row={'time':at,**{'m0'+key:0 for key in keys}}
            for key in ('vab','vbc','vca'):row['m0'+key]=voltage
            for key in ('busvab','busvbc','busvca'):row['m0'+key]=480
            writer.writerow(row)
    study['simulation']['duration_s']=2*period
    result=adapter._summaries(file,study)[0]
    assert len(result['trajectory'])==2
    assert result['minimum_voltage_pu']==pytest.approx(100/sqrt(2)/480,abs=1e-12)
    assert result['minimum_bus_voltage_pu']==pytest.approx(1,abs=1e-12)


def test_timeout_preserves_partial_engine_log_and_is_not_success(tmp_path,monkeypatch):
    import subprocess
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 30, output=b'initialization completed; partial trace', stderr=b'pending event')
    monkeypatch.setattr(adapter.subprocess,'run',timeout)
    record=adapter._run(['native-engine'],tmp_path,{},30)
    assert record['returncode'] is None and record['execution_status']=='TIMEOUT'
    assert record['timeout_s']==30 and 'partial trace' in record['stdout']
    assert record['stderr']=='pending event'


@pytest.mark.parametrize('failure',['TIMEOUT','PROCESS_FAILED','INCOMPLETE_TRACE'])
def test_failed_simulation_never_becomes_failed_electrical_design(tmp_path,monkeypatch,study,failure):
    library=tmp_path/'library'
    for name in ['Modelica/Electrical/Machines/BasicMachines/InductionMachines/IM_SquirrelCage.mo',
                 'Modelica/Electrical/PowerConverters/ACAC/Control/SoftStartControl.mo',
                 'Modelica/Electrical/PowerConverters/ACAC/PolyphaseTriac.mo']:
        file=library/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text('test-source')
    monkeypatch.setattr(adapter,'runtime',lambda:{'ready':True,'library':str(library),'executable':str(tmp_path/'omc')})
    output=tmp_path/'Study'
    def run(command,folder,env,timeout):
        if command[0].endswith('omc'):
            (folder/('MotorStudy.exe' if adapter.platform.system()=='Windows' else 'MotorStudy')).write_text('test-binary')
            return {'command':command,'returncode':0,'execution_status':'COMPLETED','stdout':'compiled','stderr':''}
        (folder/'Nominal.csv').write_text('time,m0speed\n0,0\n0.12,1\n')
        return {'command':command,'returncode':None if failure=='TIMEOUT' else (1 if failure=='PROCESS_FAILED' else 0),
                'execution_status':failure,'stdout':'The simulation finished successfully.' if failure=='INCOMPLETE_TRACE' else 'partial execution', 'stderr':''}
    monkeypatch.setattr(adapter,'_run',run)
    result=adapter.execute(study,output)
    assert result['status']=='MODELICA_EXECUTION_FAILED' and result['results']==[]
    assert result['design_assessment']=='NOT_EVALUATED' and result['calculation_status']=='NO_VERIFIED_RESULT'
    assert result['last_emitted_time_s']==pytest.approx(.12)
    assert result['failure_kind']=={'TIMEOUT':'TIMEOUT','PROCESS_FAILED':'SIMULATION_FAILED','INCOMPLETE_TRACE':'TRACE_VALIDATION_FAILED'}[failure]
    records=json.loads((output/'Execution.json').read_text())
    assert len(records)==2 and records[1]['stage']=='NOMINAL_SIMULATION'
