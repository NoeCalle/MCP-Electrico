"""DOL scoped qualification: original MSL example, SI conventions and MCP.

Native reference inherits the original MSL model, independently of the MCP
builder. Independent CSV quadrature checks result reading as well as wiring.
No equations here are a production motor solver.
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
from msl_dol_native_reference import execute_native,SOURCE,ORIGINAL

ROOT=Path(__file__).resolve().parents[1]
LIMITS={'current_relative':.001,'torque_relative':.001,'speed_relative':.001,
        'acceleration_absolute_s':.001,'voltage_absolute_pu':.0002}


def mechanical_energy_check(path,load_inertia):
    a=np.genfromtxt(path,delimiter=',',names=True,deletechars='')
    work=float(np.trapezoid(a['m0torque']*a['m0speed'],a['time']))
    kinetic=.5*(.29+load_inertia)*(float(a['m0speed'][-1])**2-float(a['m0speed'][0])**2)
    relative=abs(work-kinetic)/max(abs(kinetic),1e-12)
    return {'electromagnetic_work_j':work,'rotating_kinetic_energy_delta_j':kinetic,
            'rotor_inertia':.29,'external_load_inertia':load_inertia,'fixed_stator_included':False,
            'relative_error':relative,'predeclared_relative_limit':.0001,'passed':relative<=.0001}


def read_native(path,package):
    a=np.genfromtxt(path,delimiter=',',names=True,deletechars='')
    t=a['time'];keep=np.r_[t[1:]!=t[:-1],True];t=t[keep]
    if t[0]!=0 or abs(t[-1]-1.5)>1e-9:raise ValueError('Native incomplete observation')
    def column(name):return a['m0'+name][keep]
    start=.1;f=50;end=np.arange(1,71)/f+start
    rows=[]
    for right in end:
        left=right-1/f
        tt=np.r_[left,t[(t>left)&(t<right)],right]
        def mean(key,square=False):
            y=np.interp(tt,t,column(key))
            return float(np.trapezoid(y*y if square else y,tt)*f)
        rms=[sqrt(max(mean(key,True),0)) for key in ['ia','ib','ic']]
        voltage=[sqrt(max(mean(key,True),0)) for key in ['vab','vbc','vca']]
        rows.append({'time_s':float(right),'current_a':max(rms),'speed_rad_s':float(np.interp(right,t,column('speed'))),
                     'torque_nm':mean('torque'),'voltage_pu':min(voltage)/(package['network']['kv_ll']*1000)})
    speed=column('speed');target=.9*pi*50
    found=np.flatnonzero((t>=start)&(speed>=target));cross=None
    if len(found):
        k=found[0];cross=float(t[k-1]+(target-speed[k-1])*(t[k]-t[k-1])/(speed[k]-speed[k-1]))-start
    return {'trajectory':rows,'acceleration_time_s':cross,'maximum_cycle_rms_current_a':max(r['current_a'] for r in rows),
            'minimum_voltage_pu':min(r['voltage_pu'] for r in rows)}


def compare(native,result):
    a=native['trajectory'];b=result['trajectory']
    assert len(a)==len(b)==70
    errors={
        'current_relative':max(abs(x['current_a']-y['current_a']) for x,y in zip(a,b))/max(native['maximum_cycle_rms_current_a'],1e-12),
        'torque_relative':max(abs(x['torque_nm']-y['torque_nm']) for x,y in zip(a,b))/max(max(abs(x['torque_nm']) for x in a),1e-12),
        'speed_relative':max(abs(x['speed_rad_s']-y['speed_rad_s']) for x,y in zip(a,b))/(50*pi),
        'voltage_absolute_pu':max(abs(x['voltage_pu']-y['voltage_pu']) for x,y in zip(a,b)),
        'acceleration_absolute_s':abs(native['acceleration_time_s']-result['acceleration_time_s']) if native['acceleration_time_s'] is not None and result['acceleration_time_s'] is not None else (0 if native['acceleration_time_s'] is result['acceleration_time_s'] else float('inf')),
    }
    return {'errors':errors,'predeclared_limits':LIMITS,'passed':all(errors[k]<=LIMITS[k] for k in errors)}


async def verify(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    rt=json.loads((ROOT/'local_data/modelica-runtime.json').read_text(encoding='utf8'))
    calls=[];cases={}
    fixture=json.loads((ROOT/'examples/msl_motor_dol_native_reference.json').read_text(encoding='utf8'))
    sources=['mcp_electrico/modelica_motor_adapter.py','scripts/msl_dol_native_reference.py','scripts/verify_msl_dol_qualification_mcp.py','examples/msl_motor_dol_native_reference.json']
    source_hashes={p:sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}
    plans=[('delta', 'delta',100.,.29,293.15),('wye','wye',100*sqrt(3),.29,293.15),
           ('inertia','delta',100.,.58,293.15),('temperature','delta',100.,.29,353.15)]
    if args.first_only:plans=plans[:1]
    (out/'Predeclared-plan.json').write_text(json.dumps({'original_class':ORIGINAL,'limits':LIMITS,'cases':plans,'no_load_specialization':'TLoad=0, exact zero torque table','source_equation_voltage_basis':'V=sqrt(2/3)*VNominal -> VNominal is line-to-line RMS'},indent=2),encoding='utf8')
    params=StdioServerParameters(command=sys.executable,args=['-X','utf8',str(ROOT/'server.py')],cwd=str(out),env=dict(os.environ,PYTHONUTF8='1'))
    with (out/'MCP-stderr.log').open('w',encoding='utf8') as log:
        async with stdio_client(params,errlog=log) as (read,write):
            async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=900)) as client:
                await client.initialize()
                async def call(name,arguments):
                    raw=await client.call_tool(name,arguments=arguments);assert not raw.isError,str(raw)
                    result=raw.structuredContent if raw.structuredContent is not None else json.loads(next(c.text for c in raw.content if c.type=='text'))
                    calls.append({'tool':name,'arguments':arguments,'result':result});return result
                await call('configurar_dinamica_modelica',{'ruta_omc':rt['executable'],'directorio_msl':rt['library']})
                for tag,connection,voltage,inertia,temperature in plans:
                    package=deepcopy(fixture);package['id']+='-'+tag
                    package['network']['kv_ll']=voltage/1000
                    motor=package['motors'][0];motor['connection']=connection
                    motor['mechanical']['load_inertia_kg_m2']=inertia
                    motor['electrical']['temperature_k']=temperature
                    ready=await call('validar_dinamica_modelica',{'paquete_estudio':package});assert ready['ready_for_execution'],ready
                    print('Running native original MSL:',tag,flush=True)
                    csv=await asyncio.to_thread(execute_native,rt,out/(tag+'-native'),connection,voltage,inertia,temperature)
                    native=read_native(csv,package)
                    print('Running MCP adapter:',tag,flush=True)
                    actual=await call('ejecutar_dinamica_modelica',{'paquete_estudio':package,'directorio_salida':str(out/(tag+'-MCP'))})
                    assert actual['status']=='MODELICA_MOTOR_STUDIES_COMPLETED',actual
                    item=compare(native,actual['results'][0])
                    item['mechanical_energy']={
                        'native':mechanical_energy_check(csv,inertia),
                        'mcp':mechanical_energy_check(out/(tag+'-MCP')/'Refined.csv',inertia),
                    }
                    assert all(e['passed'] for e in item['mechanical_energy'].values()),item
                    (out/(tag+'-comparison.json')).write_text(json.dumps({'native':native,'mcp':actual['results'][0],**item},indent=2),encoding='utf8')
                    assert item['passed'],item
                    cases[tag]={'comparison':item,'native':native,'mcp':actual['results'][0]}
                    print('Parity passed:',tag,item['errors'],flush=True)
                if not args.first_only:
                    base=cases['delta']['mcp'];hot=cases['temperature']['mcp'];star=cases['wye']['mcp'];heavy=cases['inertia']['mcp']
                    assert abs(hot['acceleration_time_s']-base['acceleration_time_s'])<.001
                    assert abs(star['acceleration_time_s']-base['acceleration_time_s'])<.001
                    assert heavy['acceleration_time_s']>base['acceleration_time_s']+.01
                    # At equal winding voltage, Y line current is D line current / sqrt(3).
                    assert abs(star['trajectory'][-1]['current_a']*sqrt(3)/base['trajectory'][-1]['current_a']-1)<.001
                    bad=deepcopy(fixture);bad['network']['basis']='AUTOMATIC_COMPLETE_UNIFILAR_EMT'
                    blocked=await call('ejecutar_dinamica_modelica',{'paquete_estudio':bad,'directorio_salida':str(out/'Invalid-full-network')})
                    assert blocked['status']=='BLOCKED_MODELICA_READINESS' and not (out/'Invalid-full-network').exists()
    assert source_hashes=={p:sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},'Source changed during verification'
    evidence={'ok':True,'transport':'MCP_STDIO','checked_at_utc':datetime.now(timezone.utc).isoformat(),'runtime':rt,
              'calls':calls,'native_cases':cases,'original_class':ORIGINAL,'library_source_sha256':{SOURCE:sha256((Path(rt['library'])/SOURCE).read_bytes()).hexdigest()},
              'source_sha256':source_hashes,
              'professional_emission':False,'physical_solver_owned_by_mcp':False}
    (out/'Evidencia-DOL-MCP.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    print(json.dumps({'ok':True,'native_cases':len(cases),'calls':len(calls)}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--first-only',action='store_true')
    asyncio.run(verify(parser.parse_args()))
