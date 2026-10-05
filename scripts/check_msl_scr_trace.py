"""Independent energy and bypass-policy checks on recorded SCR fixtures.

This checks external results; it does not integrate a motor or controller.
Energy balance admits only zero load, zero damping and fixed copper losses.
"""
import argparse
from hashlib import sha256
import json
from math import pi
from pathlib import Path
import numpy as np


def check(path,package):
    motor=package['motors'][0];mechanical=motor['mechanical']
    if mechanical['damping_nm_s_rad'] or any(p['torque_nm'] for p in mechanical['load_curve']):
        raise ValueError('Energy oracle requires zero load and zero damping')
    a=np.genfromtxt(path,delimiter=',',names=True,deletechars='')
    t=a['time']
    if np.any(np.diff(t)<0) or not all(np.isfinite(a[k]).all() for k in a.dtype.names):
        raise ValueError('Nonfinite or unordered trace')
    if t[0]!=0 or abs(t[-1]-package['simulation']['duration_s'])>1e-8:
        raise ValueError('Incomplete observation')
    inertia=mechanical['motor_inertia_kg_m2']+mechanical['load_inertia_kg_m2']
    work=float(np.trapezoid(a['m0torque']*a['m0speed'],t))
    kinetic=.5*inertia*(float(a['m0speed'][-1])**2-float(a['m0speed'][0])**2)
    energy_error=abs(work-kinetic)/max(abs(kinetic),1e-12)
    keep=np.r_[t[1:]!=t[:-1],True];times=t[keep]
    c=motor['starting']['controller']
    threshold=c['bypass_speed_fraction']*2*pi*package['network']['frequency_hz']/motor['electrical']['pole_pairs']
    eligible=(a['m0vRef'][keep]>=1-1e-8)&(a['m0speed'][keep]>=threshold)
    expected=None;since=None
    for time,ready in zip(times,eligible):
        if not ready:since=None
        elif since is None:since=float(time)
        if since is not None and time-since>=c['bypass_hold_s']-1e-12:
            expected=since+c['bypass_hold_s'];break
    states=a['m0bypass'][keep]>.5;indices=np.flatnonzero(states)
    observed=float(times[indices[0]]) if len(indices) else None
    latched=not len(indices) or bool(states[indices[0]:].all())
    event_error=abs(expected-observed) if expected is not None and observed is not None else (0 if expected is observed else None)
    time_limit=2*package['simulation']['output_step_s']+1e-8
    result={'energy':{'electromagnetic_work_j':work,'kinetic_energy_delta_j':kinetic,'rotating_inertia_kg_m2':inertia,
                     'fixed_stator_included':False,'relative_error':energy_error,'predeclared_limit':.0001,'passed':energy_error<=.0001},
            'bypass':{'expected_time_s':expected,'observed_time_s':observed,'absolute_error_s':event_error,
                      'predeclared_limit_s':time_limit,'latched':latched,
                      'passed':latched and event_error is not None and event_error<=time_limit},
            'trace_sha256':sha256(Path(path).read_bytes()).hexdigest()}
    result['passed']=result['energy']['passed'] and result['bypass']['passed']
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();directory=args.evidence.resolve()
    plan=json.loads((directory/'Predeclared-plan.json').read_text(encoding='utf8'))
    results={}
    for row in plan['cases']:
        tag=row[0];package=json.loads((directory/(tag+'-input.json')).read_text(encoding='utf8'))
        results[tag]={name:check(directory/(tag+'-'+folder)/file,package)
                     for name,folder,file in [('native','native','Native.csv'),('mcp','MCP','Refined.csv')]}
    evidence={'predeclared_energy_relative_limit':.0001,'bypass_limit':'2 * output_step_s + 1e-8',
              'checker_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'cases':results,
              'ok':all(c['passed'] for r in results.values() for c in r.values())}
    (directory/'Energy-bypass-evidence.json').write_text(json.dumps(evidence,indent=2,allow_nan=False),encoding='utf8')
    print(json.dumps({'ok':evidence['ok'],'traces':2*len(results)}))
    if not evidence['ok']:raise SystemExit(1)
