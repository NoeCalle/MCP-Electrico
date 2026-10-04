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

def test_scr_data_can_never_bypass_the_pending_numerical_gate(study,monkeypatch):
    monkeypatch.setattr(adapter,'runtime',lambda:{'ready':True})
    study['motors'][0]['starting']['method']='SCR'
    result=adapter.validate(study)
    assert not result['ready_for_execution']
    assert result['qualification_blockers']==['SCR_CLOSED_LOOP_NUMERICAL_VALIDATION_PENDING']
    assert adapter.contract()['prepared_not_enabled_methods']==['SCR']

def test_cycle_measurements_match_sinusoidal_rms_and_failed_acceleration(tmp_path,study):
    # Test only the reading of external traces, with known waveforms and units.
    file=tmp_path/'trace.csv'
    with file.open('w',newline='') as stream:
        names=['time']+['m0'+n for n in ('speed','torque','ia','ib','ic','vab','vbc','vca','bypass')]
        writer=csv.DictWriter(stream,fieldnames=names);writer.writeheader()
        for j in range(4001):
            t=j*.00005
            row={'time':t,'m0speed':0,'m0torque':50,'m0bypass':0}
            for k,(i,v) in enumerate(zip(('ia','ib','ic'),('vab','vbc','vca'))):
                row['m0'+i]=sqrt(2)*100*sin(2*pi*60*t-2*pi*k/3)
                row['m0'+v]=sqrt(2)*480*sin(2*pi*60*t-2*pi*k/3)
            writer.writerow(row)
    result=adapter._summaries(file,study)[0]
    assert result['maximum_cycle_rms_current_a']==pytest.approx(100,rel=1e-4)
    assert result['minimum_voltage_pu']==pytest.approx(1,rel=1e-4)
    assert result['acceleration_time_s'] is None and not result['criterion']['passed']
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
