"""Protect the independent SCR oracle against event smearing and partial CSVs."""
import csv
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('msl_scr_native_reference',ROOT/'scripts/msl_scr_native_reference.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
sys.modules['msl_scr_native_reference']=native
spec=importlib.util.spec_from_file_location('scr_verification',ROOT/'scripts/verify_msl_scr_native_mcp.py')
verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)


def fixture():
    return json.loads((ROOT/'examples/msl_motor_scr_native_reference.json').read_text(encoding='utf8'))


def test_native_filter_pole_is_checked_numerically():
    assert native.verify_filter_pole('time=0,filter.r[1]=-50',.02)['passed']
    # MSL normalized CriticalDamping order=1 has a slightly different pole.
    with pytest.raises(ValueError,match='pole mismatch'):
        native.verify_filter_pole('time=0,filter.r[1]=-50.11886465038003',.02)


def test_absent_native_filter_pole_is_not_assumed():
    with pytest.raises(ValueError,match='not emitted'):
        native.verify_filter_pole('The simulation finished successfully.',.02)


def trace(path):
    names=['time']+['m0'+k for k in ('speed','torque','ia','ib','ic','vab','vbc','vca','bypass','vRef')]
    # A jump at .4 s: both sides must remain in the integral. Smearing the
    # jump across adjacent samples yields a wrong RMS even at exact endpoints.
    rows=[]
    for t,value in [(0,0),(.4,0),(.4,2),(1,2)]:
        rows.append([t,0,2]+[value]*6+[0,value/2])
    with path.open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(names);writer.writerows(rows)
    return rows,names


def test_independent_oracle_retains_discontinuity_area(tmp_path):
    file=tmp_path/'trace.csv';trace(file)
    p=fixture();p['network'].update(frequency_hz=1,kv_ll=.001)
    p['simulation']['duration_s']=1;p['motors'][0]['starting']['time_s']=0
    result=verify.read_reference(file,p);row=result['trajectory'][0]
    assert row['current_a']==pytest.approx((4*.6)**.5,abs=1e-12)
    assert row['voltage_pu']==pytest.approx((4*.6)**.5,abs=1e-12)
    assert row['torque_nm']==pytest.approx(2,abs=1e-12)
    assert result['duplicate_event_rows']==1
    assert result['acceleration_time_s'] is None and result['bypass_time_s'] is None


@pytest.mark.parametrize('fault',['partial','nonfinite','unordered'])
def test_independent_oracle_rejects_invalid_trace(tmp_path,fault):
    file=tmp_path/'trace.csv';rows,names=trace(file)
    p=fixture();p['simulation']['duration_s']=1
    if fault=='partial':rows[-1][0]=.9
    elif fault=='nonfinite':rows[1][2]=float('nan')
    else:rows[2][0]=.3
    with file.open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(names);writer.writerows(rows)
    with pytest.raises(ValueError):verify.read_reference(file,p)
