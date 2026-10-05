"""Independent checks must reject premature bypass and missing mechanical work."""
import csv
import json
from pathlib import Path
import pytest
from scripts.check_msl_scr_trace import check

ROOT=Path(__file__).resolve().parents[1]


def data(tmp_path, fault=None):
    p=json.loads((ROOT/'examples/msl_motor_scr_native_reference.json').read_text())
    p['network']['frequency_hz']=.1
    p['simulation'].update(duration_s=1,output_step_s=.1)
    p['motors'][0]['starting']['controller']['bypass_hold_s']=.2
    rows=[]
    for k in range(11):
        t=k/10;reference=1 if k in (2,3) or k>=5 else 0
        bypass=1 if k>=7 else 0
        if fault=='early':bypass=1 if k>=2 else 0
        if fault=='unlatched' and k==8:bypass=0
        torque=0 if fault=='energy' else 4*.58
        rows.append([t,4*t,torque,reference,bypass])
    file=tmp_path/'trace.csv'
    with file.open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['time','m0speed','m0torque','m0vRef','m0bypass']);writer.writerows(rows)
    return file,p


def test_bypass_hold_is_cancelled_and_restarts_and_energy_balances(tmp_path):
    file,p=data(tmp_path);result=check(file,p)
    assert result['passed'] and result['bypass']['expected_time_s']==pytest.approx(.7)
    assert result['energy']['relative_error']<1e-12


@pytest.mark.parametrize('fault',['early','unlatched','energy'])
def test_invalid_bypass_or_work_cannot_pass(tmp_path,fault):
    file,p=data(tmp_path,fault);assert not check(file,p)['passed']


def test_energy_oracle_does_not_silently_ignore_nonzero_load(tmp_path):
    file,p=data(tmp_path);p['motors'][0]['mechanical']['load_curve'][0]['torque_nm']=1
    with pytest.raises(ValueError,match='zero load'):check(file,p)
