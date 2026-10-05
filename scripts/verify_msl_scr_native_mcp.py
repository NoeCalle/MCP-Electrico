"""Original MSL SCR parity through fresh MCP stdio and independent quadrature.

No MCP builder or summary reader is used by the reference. Limits and cases
are written before execution. Event jumps retain both sides (zero-width area).
"""
import argparse
import asyncio
from copy import deepcopy
from datetime import timedelta,datetime,timezone
from hashlib import sha256
import json
from math import pi,sqrt
import os
from pathlib import Path
import sys
import numpy as np
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from msl_scr_native_reference import execute_native,SOURCE,ORIGINAL

ROOT=Path(__file__).resolve().parents[1]
LIMITS={'current_relative':.001,'torque_relative':.001,'speed_relative':.001,
        'acceleration_absolute_s':.001,'voltage_absolute_pu':.001,
        'reference_absolute_pu':.001,'bypass_absolute_s':.001}


def read_reference(path,package):
    a=np.genfromtxt(path,delimiter=',',names=True,deletechars='')
    t=a['time'];end=package['simulation']['duration_s']
    if not all(np.isfinite(a[k]).all() for k in a.dtype.names) or np.any(np.diff(t)<0):
        raise ValueError('Nonfinite or unordered reference trace')
    if t[0]!=0 or abs(t[-1]-end)>1e-9:raise ValueError('Incomplete reference observation')
    motor=package['motors'][0];start=motor['starting']['time_s'];f=package['network']['frequency_hz']
    keep=np.r_[t[1:]!=t[:-1],True];unique=t[keep]
    def col(k):return a['m0'+k]
    rows=[]
    for right in start+np.arange(1,int((end-start)*f+1e-8)+1)/f:
        left=right-1/f
        # Clip each positive-width CSV segment to the cycle window. Unlike
        # deduplication, this preserves pre-event values on the left segment.
        select=(t[:-1]<right)&(t[1:]>left)&(t[1:]>t[:-1])
        t0,t1=t[:-1][select],t[1:][select]
        lo=np.maximum(t0,left);hi=np.minimum(t1,right)
        def mean(key,squared=False):
            y=col(key);slope=(y[1:][select]-y[:-1][select])/(t1-t0)
            y0=y[:-1][select]+slope*(lo-t0);y1=y[:-1][select]+slope*(hi-t0)
            area=(hi-lo)*((y0*y0+y0*y1+y1*y1)/3 if squared else (y0+y1)/2)
            return float(np.sum(area)*f)
        rows.append({'time_s':float(right),'current_a':max(sqrt(max(mean(k,True),0)) for k in ('ia','ib','ic')),
                     'speed_rad_s':float(np.interp(right,unique,col('speed')[keep])),
                     'torque_nm':mean('torque'),
                     'voltage_pu':min(sqrt(max(mean(k,True),0)) for k in ('vab','vbc','vca'))/(package['network']['kv_ll']*1000),
                     'controller_voltage_reference_pu':float(np.interp(right,unique,col('vRef')[keep]))})
    speed=col('speed')[keep];target=motor['criteria']['target_speed_fraction']*2*pi*f/motor['electrical']['pole_pairs']
    indices=np.flatnonzero((unique>=start)&(speed>=target));cross=None
    if len(indices):
        k=indices[0]
        cross=float(unique[k-1]+(target-speed[k-1])*(unique[k]-unique[k-1])/(speed[k]-speed[k-1]))-start
    bypass=np.flatnonzero(col('bypass')>.5)
    return {'trajectory':rows,'acceleration_time_s':cross,'bypass_time_s':float(t[bypass[0]]) if len(bypass) else None,
            'maximum_cycle_rms_current_a':max(r['current_a'] for r in rows),'duplicate_event_rows':int(np.sum(np.diff(t)==0))}


def compare(native,actual,frequency):
    a=native['trajectory'];b=actual['trajectory']
    if len(a)!=len(b):raise ValueError('Different observation windows')
    if max(abs(x['time_s']-y['time_s']) for x,y in zip(a,b))>1e-9:raise ValueError('Different cycle boundaries')
    def event_error(key):
        x,y=native[key],actual[key]
        return abs(x-y) if x is not None and y is not None else (0 if x is y else None)
    errors={'current_relative':max(abs(x['current_a']-y['current_a']) for x,y in zip(a,b))/max(native['maximum_cycle_rms_current_a'],1e-12),
            'torque_relative':max(abs(x['torque_nm']-y['torque_nm']) for x,y in zip(a,b))/max(max(abs(x['torque_nm']) for x in a),1e-12),
            'speed_relative':max(abs(x['speed_rad_s']-y['speed_rad_s']) for x,y in zip(a,b))/(frequency*pi),
            'voltage_absolute_pu':max(abs(x['voltage_pu']-y['voltage_pu']) for x,y in zip(a,b)),
            'reference_absolute_pu':max(abs(x['controller_voltage_reference_pu']-y['controller_voltage_reference_pu']) for x,y in zip(a,b)),
            'acceleration_absolute_s':event_error('acceleration_time_s'),'bypass_absolute_s':event_error('bypass_time_s')}
    return {'errors':errors,'predeclared_limits':LIMITS,'passed':all(v is not None and v<=LIMITS[k] for k,v in errors.items())}


async def verify(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    rt=json.loads((ROOT/'local_data/modelica-runtime.json').read_text(encoding='utf8'))
    fixture=json.loads((ROOT/'examples/msl_motor_scr_native_reference.json').read_text(encoding='utf8'))
    plans=[('base',50,0,.29,.4,1,2),('phase-positive',50,15,.29,.4,1,2),
           ('phase-negative',50,-27,.29,.4,1,2),('inertia',50,0,.58,.4,1,3),
           ('frequency-60',60,15,.29,.4,1,3),('initial-voltage',50,0,.29,.3,1,2.1)]
    if args.first_only:plans=plans[:1]
    if args.cases:
        unknown=set(args.cases)-{p[0] for p in plans}
        if unknown:raise ValueError('Unknown case selection: '+str(sorted(unknown)))
        plans=[p for p in plans if p[0] in args.cases]
    sources=['mcp_electrico/modelica_motor_adapter.py','scripts/msl_scr_native_reference.py','scripts/verify_msl_scr_native_mcp.py','examples/msl_motor_scr_native_reference.json']
    hashes={p:sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}
    def save(name,data):
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    save('Predeclared-plan.json',{'original_class':ORIGINAL,'limits':LIMITS,'cases':plans,
        'native_machine':'MSL Magnetic.FundamentalWave.IM_SquirrelCage',
        'adapter_machine':'MSL Electrical.Machines.IM_SquirrelCage',
        'specializations':['TLoad=0','native CriticalDamping Filter order=1, normalized=false: exact FirstOrder pole',
                           'native RC snubber','native IdealClosingSwitch bypass and OnDelay latch'],
        'physical_solver_owned_by_mcp':False,'design_criteria':'Illustrative fixture only','source_sha256':hashes})
    calls=[];cases={}
    params=StdioServerParameters(command=sys.executable,args=['-X','utf8',str(ROOT/'server.py')],cwd=str(out),env=dict(os.environ,PYTHONUTF8='1'))
    with (out/'MCP-stderr.log').open('w',encoding='utf8') as log:
        async with stdio_client(params,errlog=log) as (read,write):
            # timeout_s is per compiler/simulation stage; allow all stages and
            # CSV postprocessing before the MCP client declares a transport timeout.
            async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=2400)) as client:
                await client.initialize()
                async def call(name,data):
                    raw=await client.call_tool(name,arguments=data);assert not raw.isError,str(raw)
                    result=raw.structuredContent if raw.structuredContent is not None else json.loads(next(c.text for c in raw.content if c.type=='text'))
                    calls.append({'tool':name,'arguments':data,'result':result});save('Calls.json',calls);return result
                await call('configurar_dinamica_modelica',{'ruta_omc':rt['executable'],'directorio_msl':rt['library']})
                for tag,f,angle,inertia,initial,ramp,duration in plans:
                    package=deepcopy(fixture);package['id']+='-'+tag
                    package['network'].update(frequency_hz=f,angle_deg=angle)
                    motor=package['motors'][0];motor['mechanical']['load_inertia_kg_m2']=inertia
                    motor['starting']['controller'].update(initial_voltage_pu=initial,ramp_up_s=ramp)
                    package['simulation']['duration_s']=duration
                    if tag in ('inertia','initial-voltage'):
                        # The 12.5/6.25 us trial exceeded the unchanged 0.001 pu
                        # voltage refinement limit (0.00113436 / 0.00118975 pu).
                        # Tighten the
                        # numerical grid rather than weakening acceptance.
                        package['simulation'].update(output_step_s=6.25e-6,maximum_internal_step_s=6.25e-6)
                    motor['criteria']['maximum_acceleration_time_s']=duration-motor['starting']['time_s']
                    save(tag+'-input.json',package)
                    ready=await call('validar_dinamica_modelica',{'paquete_estudio':package});assert ready['ready_for_execution'],ready
                    print('Native MSL and independent MCP stdio:',tag,flush=True)
                    csv,actual=await asyncio.gather(
                        asyncio.to_thread(execute_native,rt,out/(tag+'-native'),package),
                        call('ejecutar_dinamica_modelica',{'paquete_estudio':package,'directorio_salida':str(out/(tag+'-MCP'))}))
                    native=read_reference(csv,package)
                    assert actual.get('results'),{'status':actual['status'],'message':actual.get('message')}
                    parity=compare(native,actual['results'][0],f)
                    save(tag+'-comparison.json',{'native':native,'mcp':actual['results'][0],**parity})
                    assert actual['status']=='MODELICA_MOTOR_STUDIES_COMPLETED',{'status':actual['status'],'verification':actual['results'][0]['verification']}
                    assert actual['results'][0]['verification']['passed'],actual['results'][0]['verification']
                    assert parity['passed'],parity
                    assert native['bypass_time_s'] is not None,'Case must exercise bypass closure'
                    cases[tag]=parity
                    print('Parity:',tag,parity,flush=True)
    assert hashes=={p:sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},'Source changed during verification'
    save('Evidence.json',{'ok':True,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'transport':'MCP_STDIO',
         'calls':len(calls),'cases':cases,'runtime':rt,'source_sha256':hashes,
         'native_source_sha256':{SOURCE:sha256((Path(rt['library'])/SOURCE).read_bytes()).hexdigest()},
         'scope':'ONE_DELTA_IDEAL_SOURCE_ZERO_LOAD_GENERIC_MSL_SCR','engineer_approval_responsibility':True})
    print(json.dumps({'ok':True,'cases':len(cases),'calls':len(calls)}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--first-only',action='store_true');parser.add_argument('--cases',nargs='+')
    asyncio.run(verify(parser.parse_args()))
