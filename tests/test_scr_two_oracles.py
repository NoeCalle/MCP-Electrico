"""Check that multi-machine evidence cannot silently omit a branch or event."""
from copy import deepcopy
from math import pi,sqrt
from pathlib import Path
import sys
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from verify_msl_scr_two_mcp import cases,common_bus_kvl,motor_metrics,independent_motor_checks
from verify_msl_scr_two_loaded_mcp import mechanical_checks


def test_common_bus_kvl_includes_second_machine_current():
    p=cases(1e-5)['RL-simultaneous'];p['network'].update(r_ohm=1,x_ohm=1)
    p['simulation']['duration_s']=.2
    t=np.linspace(0,.2,20001);w=2*pi*50;v=p['network']['kv_ll']*1000
    keys=['time','m0ia','m0ib','m1ia','m1ib','m0busvab','m1busvab']
    a=np.zeros(len(t),dtype=[(k,float) for k in keys]);a['time']=t
    phi=w*t
    for index,amp in enumerate((10,20)):
        a[f'm{index}ia']=sqrt(2)*amp*np.sin(phi-.3)
        a[f'm{index}ib']=sqrt(2)*amp*np.sin(phi-.3-2*pi/3)
    i=sum(a[f'm{i}ia']-a[f'm{i}ib'] for i in range(2))
    di=sqrt(2)*30*w*(np.cos(phi-.3)-np.cos(phi-.3-2*pi/3))
    source=sqrt(2)*v/sqrt(3)*(np.sin(phi)-np.sin(phi-2*pi/3))
    bus=source-i-di/w;a['m0busvab']=bus;a['m1busvab']=bus
    assert common_bus_kvl(a,p)['passed']
    a['m1ia']=0;a['m1ib']=0
    assert not common_bus_kvl(a,p)['passed']


def test_cycle_quadrature_clips_non_grid_aligned_windows():
    p=cases(1e-5)['RL-simultaneous'];p['motors'][1]['starting']['time_s']=.103
    keys=['time']+['m1'+k for k in ('ia','ib','ic','vab','vbc','vca','speed','torque','vRef','bypass')]
    a=np.zeros(5,dtype=[(k,float) for k in keys]);a['time']=[0,.115,.115,.14,.203]
    for k in ('ia','ib','ic','vab','vbc','vca'):a['m1'+k]=[0,0,2,2,2]
    a['m1torque']=3
    result=motor_metrics(a,p,1)
    assert result['trajectory'][0]['current_a']==pytest.approx(sqrt(4*.008/.02),abs=1e-12)
    assert result['trajectory'][0]['torque_nm']==pytest.approx(3,abs=1e-12)


def test_energy_and_bypass_checks_use_each_motor_own_columns():
    p=cases(.01)['RL-simultaneous'];p['network']['frequency_hz']=.1
    p['simulation']['duration_s']=1
    for m in p['motors']:m['starting']['controller']['bypass_hold_s']=.2
    keys=['time']+[f'm{i}'+k for i in range(2) for k in ('speed','torque','vRef','bypass')]
    a=np.zeros(11,dtype=[(k,float) for k in keys]);a['time']=np.linspace(0,1,11)
    for i in range(2):
        a[f'm{i}speed']=4*a['time'];a[f'm{i}torque']=4*.58
        a[f'm{i}vRef']=[0,0,1,1,0,1,1,1,1,1,1]
        a[f'm{i}bypass']=[0]*7+[1]*4
    assert independent_motor_checks(a,p,0)['passed']
    assert independent_motor_checks(a,p,1)['passed']
    a['m1bypass'][2:]=1
    assert independent_motor_checks(a,p,0)['passed']
    assert not independent_motor_checks(a,p,1)['passed']


def test_loaded_balance_accounts_for_each_curve_inertia_and_damper():
    p=cases(.01)['RL-simultaneous'];p['network']['frequency_hz']=.1;p['simulation']['duration_s']=1
    keys=['time']+[f'm{i}'+k for i in range(2) for k in ('speed','torque','vRef','bypass')]
    a=np.zeros(11,dtype=[(k,float) for k in keys]);a['time']=np.linspace(0,1,11)
    for i,m in enumerate(p['motors']):
        mech=m['mechanical'];mech['load_inertia_kg_m2']=.29/(i+1);mech['damping_nm_s_rad']=.1*(i+1)
        slope=2*(i+1);mech['load_curve']=[{'speed_rad_s':-200,'torque_nm':-200*slope},{'speed_rad_s':200,'torque_nm':200*slope}]
        m['starting']['controller']['bypass_hold_s']=.2
        a[f'm{i}speed']=4*a['time'];a[f'm{i}torque']=4*(.29+mech['load_inertia_kg_m2'])+(slope+mech['damping_nm_s_rad'])*a[f'm{i}speed']
        a[f'm{i}vRef']=[0,0,1,1,0,1,1,1,1,1,1];a[f'm{i}bypass']=[0]*7+[1]*4
    assert mechanical_checks(a,p,0)['passed'] and mechanical_checks(a,p,1)['passed']
    p['motors'][1]['mechanical']['load_curve']=deepcopy(p['motors'][0]['mechanical']['load_curve'])
    assert mechanical_checks(a,p,0)['passed'] and not mechanical_checks(a,p,1)['passed']
