from math import pi, sqrt
import csv
import json
from pathlib import Path

import numpy as np
import pytest

from mcp_electrico import motor_external_reference as reference, motor_starting_tools


def test_true_line_rms_includes_dc_and_harmonic_and_torque_is_cycle_mean():
    time=np.linspace(0,.05,20001)
    # Known independent integrals: DC 3 A, fundamental 4 A RMS, harmonic 2 A RMS.
    values=dict(time=time,speed=np.full_like(time,10),torque=20+7*np.cos(2*pi*120*time))
    for n,angle in zip(('ia','ib','ic'),(0,-2*pi/3,2*pi/3)):
        values[n]=3+sqrt(2)*4*np.sin(2*pi*60*time+angle)+sqrt(2)*2*np.sin(2*pi*180*time+3*angle)
    rows=reference.cycle_observables(values,[1/120,3/120,5/120],60)
    for row in rows:
        assert row['line_rms_mean_a']==pytest.approx(sqrt(9+16+4),rel=2e-6)
        assert row['torque_cycle_mean_nm']==pytest.approx(20,abs=1e-7)
        assert row['speed_rad_s']==10


def test_partial_cycle_and_extrapolation_are_rejected():
    values=dict(time=np.linspace(0,.02,1001))
    with pytest.raises(ValueError,match='WINDOW_OUTSIDE_SUPPORT'):
        reference.cycle_observables(values,[0],60)


def csv_trace(path, times):
    with path.open('w',newline='') as stream:
        writer=csv.writer(stream)
        writer.writerow(['time','speed','torque','ia','ib','ic','alpha','supply_pu'])
        for k,t in enumerate(times): writer.writerow([t,k,20,0,0,0,0,1])


def test_event_duplicates_keep_last_and_reversed_time_is_rejected(tmp_path):
    path=tmp_path/'trace.csv'
    csv_trace(path,[0,.00005,.00005,.0001])
    data=reference.trace(path)
    assert list(data['speed'])==[0,2,3]
    csv_trace(path,[0,.0001,.00005])
    with pytest.raises(ValueError,match='REVERSED_TIME'): reference.trace(path)


@pytest.mark.parametrize('times',[[0,float('nan')],[0,float('inf')],[0,.001]])
def test_nonfinite_or_undersampled_trace_is_rejected(tmp_path,times):
    path=tmp_path/'trace.csv';csv_trace(path,times)
    with pytest.raises(ValueError): reference.trace(path)


def test_arrival_interpolation_and_target_not_reached():
    assert reference.arrival([0,1,2],[0,10,20],15)==1.5
    assert reference.arrival([0,1,2],[0,10,20],21) is None


def test_missing_or_forged_evidence_does_not_become_design_validation(tmp_path):
    result=reference.compare(tmp_path)
    assert result['status']=='BLOCKED_EXTERNAL_REFERENCE'
    (tmp_path/'Provenance.json').write_text(json.dumps(dict(schema=reference.SCHEMA,fixture_id=reference.FIXTURE,sha256={})))
    result=reference.compare(tmp_path)
    assert result['reason']=='EXTERNAL_EVIDENCE_SCHEMA_OR_FILE_SET'
    assert result['professional_emission'] is False
    assert result['device_validation_promoted'] is False


def test_mcp_comparison_registered_without_calling_external_executable():
    names=[]
    class Recorder:
        def tool(self):
            def decorate(fn): names.append(fn.__name__);return fn
            return decorate
    motor_starting_tools.register(Recorder())
    assert 'contrastar_dinamica_con_modelica' in names


def test_altered_evidence_is_blocked_before_reading_physical_values(tmp_path):
    names=['Inputs.json','DOL-MCP.json','SCR-MCP.json','DOL-Modelica.csv','SCR-Modelica.csv',
           'DOL-Modelica-refined.csv','SCR-Modelica-refined.csv','DOL.mo','SCR.mo',
           'Library-sources.json','Execution.json']
    # A declared digest is not sufficient: the bytes must actually match.
    (tmp_path/'DOL-MCP.json').write_text('{"execution_status":"forged"}')
    (tmp_path/'Provenance.json').write_text(json.dumps(dict(schema=reference.SCHEMA,fixture_id=reference.FIXTURE,
                                                         sha256={n:'0'*64 for n in names})))
    result=reference.compare(tmp_path)
    assert result['reason']=='EXTERNAL_EVIDENCE_HASH_MISMATCH:DOL-MCP.json'
    assert result['status']=='BLOCKED_EXTERNAL_REFERENCE'
    assert 'cases' not in result
