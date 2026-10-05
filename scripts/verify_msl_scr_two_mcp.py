"""Two native MSL starters on a common bus, exercised through real MCP stdio.

Reference: original MSL single-machine example, symmetry with doubled source
impedance, and independent integral KVL/energy/bypass checks. No physics solver.
"""
import argparse,asyncio,json,os,sys
from copy import deepcopy
from datetime import timedelta,datetime,timezone
from hashlib import sha256
from math import pi,sqrt
from pathlib import Path
import numpy as np
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from msl_scr_native_reference import execute_native
from verify_msl_scr_native_mcp import read_reference,compare,LIMITS

ROOT=Path(__file__).resolve().parents[1]
SOURCES=['mcp_electrico/modelica_motor_adapter.py','scripts/verify_msl_scr_two_mcp.py',
         'examples/msl_motor_scr_native_reference.json','scripts/msl_scr_native_reference.py',
         'scripts/verify_msl_scr_native_mcp.py']


def read_trace(path,package):
    a=np.genfromtxt(path,delimiter=',',names=True,deletechars='')
    if not all(np.isfinite(a[k]).all() for k in a.dtype.names) or np.any(np.diff(a['time'])<0):
        raise ValueError('Nonfinite or unordered trace')
    if a['time'][0]!=0 or abs(a['time'][-1]-package['simulation']['duration_s'])>1e-8:
        raise ValueError('Incomplete observation')
    return a


def motor_metrics(a,p,index):
    # Independent cycle quadrature; preserve both sides of every event.
    t=a['time'];m=p['motors'][index];prefix=f'm{index}';start=m['starting']['time_s'];f=p['network']['frequency_hz']
    def col(k):return a[prefix+k]
    keep=np.r_[t[1:]!=t[:-1],True];unique=t[keep];rows=[]
    for right in start+np.arange(1,int((t[-1]-start)*f+1e-8)+1)/f:
        left=right-1/f
        k0=max(np.searchsorted(t,left,side='right')-1,0);k1=min(np.searchsorted(t,right,side='left')+1,len(t)-1)
        t0,t1=t[k0:k1],t[k0+1:k1+1];valid=(t1>t0)&(t0<right)&(t1>left)
        t0,t1=t0[valid],t1[valid];lo=np.maximum(t0,left);hi=np.minimum(t1,right)
        def mean(key,square=False):
            y=col(key);y0=y[k0:k1][valid];y1=y[k0+1:k1+1][valid]
            slope=(y1-y0)/(t1-t0);v0=y0+slope*(lo-t0);v1=y0+slope*(hi-t0)
            return float(np.sum((hi-lo)*((v0*v0+v0*v1+v1*v1)/3 if square else (v0+v1)/2))*f)
        rows.append({'time_s':float(right),'current_a':max(sqrt(max(mean(k,True),0)) for k in ('ia','ib','ic')),
                     'torque_nm':mean('torque'),'speed_rad_s':float(np.interp(right,unique,col('speed')[keep])),
                     'voltage_pu':min(sqrt(max(mean(k,True),0)) for k in ('vab','vbc','vca'))/(p['network']['kv_ll']*1000),
                     'controller_voltage_reference_pu':float(np.interp(right,unique,col('vRef')[keep]))})
    target=m['criteria']['target_speed_fraction']*2*pi*f/m['electrical']['pole_pairs'];speed=col('speed')[keep]
    hits=np.flatnonzero((unique>=start)&(speed>=target));cross=None
    if len(hits):
        k=hits[0];cross=float(unique[k] if k==0 else unique[k-1]+(target-speed[k-1])*(unique[k]-unique[k-1])/(speed[k]-speed[k-1]))-start
    bypass=np.flatnonzero(col('bypass')>.5)
    return {'trajectory':rows,'acceleration_time_s':cross,'bypass_time_s':float(t[bypass[0]]) if len(bypass) else None,
            'maximum_cycle_rms_current_a':max(r['current_a'] for r in rows)}


def independent_motor_checks(a,p,index):
    t=a['time'];m=p['motors'][index];mech=m['mechanical'];c=m['starting']['controller'];prefix=f'm{index}'
    if mech['damping_nm_s_rad'] or any(row['torque_nm'] for row in mech['load_curve']):
        raise ValueError('Mechanical energy oracle requires zero load and damping')
    speed=a[prefix+'speed'];work=float(np.trapezoid(a[prefix+'torque']*speed,t))
    kinetic=.5*(mech['motor_inertia_kg_m2']+mech['load_inertia_kg_m2'])*(speed[-1]**2-speed[0]**2)
    error=abs(work-kinetic)/max(abs(kinetic),1e-12)
    keep=np.r_[t[1:]!=t[:-1],True];times=t[keep]
    threshold=c['bypass_speed_fraction']*2*pi*p['network']['frequency_hz']/m['electrical']['pole_pairs']
    eligible=(a[prefix+'vRef'][keep]>=1-1e-8)&(speed[keep]>=threshold)
    since=None;expected=None
    for at,ready in zip(times,eligible):
        if not ready:since=None
        elif since is None:since=float(at)
        if since is not None and at-since>=c['bypass_hold_s']-1e-12:
            expected=since+c['bypass_hold_s'];break
    flags=a[prefix+'bypass'][keep]>.5;hits=np.flatnonzero(flags);observed=float(times[hits[0]]) if len(hits) else None
    latched=not len(hits) or bool(flags[hits[0]:].all())
    event_error=abs(expected-observed) if expected is not None and observed is not None else (0 if expected is observed else None)
    limit=2*p['simulation']['output_step_s']+1e-8
    return {'energy_relative_error':float(error),'energy_limit':1e-4,'expected_bypass_s':expected,'observed_bypass_s':observed,
            'bypass_error_s':event_error,'bypass_limit_s':limit,'latched':latched,
            'passed':error<=1e-4 and latched and event_error is not None and event_error<=limit}


def common_bus_kvl(a,p):
    """Integral KVL, including derivative boundary term during transients.

    Vab_source-Vab_bus = R*sum(Ia-Ib) + L*d(sum(Ia-Ib))/dt.
    Weighted integration by parts avoids differentiation of switching currents.
    """
    t=a['time'];net=p['network'];f=net['frequency_hz'];w=2*pi*f;voltage=net['kv_ll']*1000
    current=sum((a[f'm{i}ia']-a[f'm{i}ib'] for i in range(len(p['motors']))))
    bus=a['m0busvab'];same_bus=max(float(np.max(abs(a[f'm{i}busvab']-bus))) for i in range(len(p['motors'])))
    source_phasor=-1j*voltage*net['pu']/sqrt(3)*np.exp(1j*net['angle_deg']*pi/180)*(1-np.exp(-2j*pi/3))
    keep=np.r_[t[1:]!=t[:-1],True];unique=t[keep];errors=[]
    start=min(m['starting']['time_s'] for m in p['motors'])
    for right in start+np.arange(1,int((t[-1]-start)*f+1e-8)+1)/f:
        left=right-1/f;lo=np.searchsorted(t,left,side='right');hi=np.searchsorted(t,right,side='left')
        times=np.r_[left,t[lo:hi],right];phase=np.exp(-1j*w*times)
        def integral(y):
            values=np.r_[np.interp(left,unique,y[keep]),y[lo:hi],np.interp(right,unique,y[keep])]
            return np.trapezoid(values*phase,times)
        ci=integral(current);boundary=np.interp(right,unique,current[keep])*phase[-1]-np.interp(left,unique,current[keep])*phase[0]
        predicted=source_phasor-(net['r_ohm']*ci+net['x_ohm']/w*(boundary+1j*w*ci))*sqrt(2)*f
        measured=integral(bus)*sqrt(2)*f
        errors.append(float(abs(predicted-measured)/voltage))
    error=max(errors)
    return {'line_pair':'AB','maximum_integral_kvl_residual_pu':error,'limit_pu':.001,
            'same_bus_max_difference_v':same_bus,'includes_all_motor_currents':True,
            'includes_inductive_boundary_term':True,'passed':error<=.001 and same_bus<=1e-8}


def cases(step):
    base=json.loads((ROOT/'examples/msl_motor_scr_native_reference.json').read_text(encoding='utf8'))
    base['simulation'].update(output_step_s=step,maximum_internal_step_s=step,timeout_s=600)
    base['source_reference']='Synthetic two-SCR integration qualification, not customer pump data'
    result={}
    for tag,count,delay,duration,r,x in [('ideal-simultaneous',2,.1,2,0,0),('single-double-Z',1,.1,2.3,.002,.003),
                                        ('RL-simultaneous',2,.1,2.3,.001,.0015),('RL-overlapping',2,.5,2.7,.001,.0015),
                                        ('RL-after-bypass',2,2.0,4.2,.001,.0015)]:
        p=deepcopy(base);p['id']='TWO-SCR-'+tag;p['network'].update(r_ohm=r,x_ohm=x)
        p['network']['source_reference']='Explicit shared per-phase impedance for symmetry and integral KVL tests'
        p['simulation']['duration_s']=duration;p['motors']=[deepcopy(base['motors'][0]) for _ in range(count)]
        for i,m in enumerate(p['motors']):
            m['id']=f'SCR-{i+1}';m['starting']['time_s']=.1 if i==0 else delay
            m['criteria'].update(maximum_acceleration_time_s=duration-m['starting']['time_s'],refinement_current_relative_tolerance=.001,
                                 refinement_speed_relative_tolerance=.001,refinement_time_absolute_tolerance_s=.001)
        result[tag]=p
    return result


async def run(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    packages=cases(args.step);selected=args.cases or list(packages)
    if set(selected)-set(packages):raise ValueError('Unknown case')
    rt=json.loads((ROOT/'local_data/modelica-runtime.json').read_text(encoding='utf8'));calls=[];evidence={}
    hashes={name:sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES}
    def save(name,value):(out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    save('Predeclared-plan.json',{'cases':selected,'inputs':{tag:packages[tag] for tag in selected},'comparison_limits':LIMITS,
                                'energy_relative_limit':.0001,'kvl_absolute_limit_pu':.001,'source_sha256':hashes,'runtime':rt})
    parameters=StdioServerParameters(command=sys.executable,args=['-X','utf8',str(ROOT/'server.py')],cwd=str(out),env=dict(os.environ,PYTHONUTF8='1'))
    with (out/'MCP-stderr.log').open('w',encoding='utf8') as log:
        async with stdio_client(parameters,errlog=log) as (rd,wr):
            async with ClientSession(rd,wr,read_timeout_seconds=timedelta(seconds=2400)) as client:
                await client.initialize()
                async def call(tool,arguments):
                    raw=await client.call_tool(tool,arguments=arguments);assert not raw.isError,raw
                    value=raw.structuredContent or json.loads(next(c.text for c in raw.content if c.type=='text'))
                    calls.append({'tool':tool,'arguments':arguments,'result':value});save('Calls.json',calls);return value
                await call('configurar_dinamica_modelica',{'ruta_omc':rt['executable'],'directorio_msl':rt['library']})
                await call('obtener_contrato_dinamica_modelica',{})
                for tag in selected:
                    p=packages[tag];save(tag+'-input.json',p)
                    ready=await call('validar_dinamica_modelica',{'paquete_estudio':p});assert ready['ready_for_execution'],ready
                    print('Executing genuine MCP:',tag,flush=True)
                    if tag=='ideal-simultaneous':
                        single=deepcopy(p);single['motors']=single['motors'][:1]
                        csv,actual=await asyncio.gather(asyncio.to_thread(execute_native,rt,out/'Original-native',single),
                            call('ejecutar_dinamica_modelica',{'paquete_estudio':p,'directorio_salida':str(out/tag)}))
                        native=read_reference(csv,single);save('Original-native-summary.json',native)
                    else:actual=await call('ejecutar_dinamica_modelica',{'paquete_estudio':p,'directorio_salida':str(out/tag)})
                    save(tag+'-result.json',actual)
                    assert actual['status']=='MODELICA_MOTOR_STUDIES_COMPLETED',{'tag':tag,'status':actual['status'],
                        'verification':[m.get('verification') for m in actual.get('results',[])],'message':actual.get('message')}
                    checks={};metrics=[]
                    for filename in ('Nominal.csv','Refined.csv'):
                        a=read_trace(out/tag/filename,p)
                        checks[filename]={'kvl':common_bus_kvl(a,p),
                            'motors':[independent_motor_checks(a,p,i) for i in range(len(p['motors']))],
                            'trace_sha256':sha256((out/tag/filename).read_bytes()).hexdigest()}
                        assert checks[filename]['kvl']['passed'],checks[filename]['kvl']
                        assert all(row['passed'] for row in checks[filename]['motors']),checks[filename]
                        if filename=='Refined.csv':
                            metrics=[motor_metrics(a,p,i) for i in range(len(p['motors']))]
                    readers=[compare(row,actual['results'][i],p['network']['frequency_hz']) for i,row in enumerate(metrics)]
                    assert all(row['passed'] for row in readers),readers
                    parity=[compare(native,row,50) for row in metrics] if tag=='ideal-simultaneous' else []
                    assert all(row['passed'] for row in parity),parity
                    row={'checks':checks,'independent_reader_parity':readers,'original_native_parity':parity,
                         'motors':[{k:v for k,v in m.items() if k!='trajectory'} for m in actual['results']],
                         'metrics':metrics,'passed':True}
                    evidence[tag]=row;save(tag+'-evidence.json',row)
                    print(json.dumps({'case':tag,'passed':True,'motors':[{'id':m['motor_id'],'acceleration':m['acceleration_time_s'],'bypass':m['bypass_time_s']} for m in actual['results']]}),flush=True)
    symmetry=[]
    if 'single-double-Z' in evidence and 'RL-simultaneous' in evidence:
        solo=evidence['single-double-Z']['metrics'][0]
        symmetry=[compare(solo,row,50) for row in evidence['RL-simultaneous']['metrics']]
        assert all(row['passed'] for row in symmetry),symmetry
    if 'RL-overlapping' in evidence:
        m=evidence['RL-overlapping']['motors'];assert m[0]['acceleration_time_s']+.1>.5
        assert abs(m[0]['bypass_time_s']-m[1]['bypass_time_s'])>.01,'Independent bypass events must be exercised'
    if 'RL-after-bypass' in evidence:
        m=evidence['RL-after-bypass']['motors'];assert m[0]['bypass_time_s']<2
    assert hashes=={name:sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES},'Sources changed during run'
    save('Evidence.json',{'ok':True,'transport':'MCP_STDIO','calls':len(calls),'cases':evidence,'symmetry_parity':symmetry,
                          'source_sha256':hashes,'runtime':rt,'checked_at_utc':datetime.now(timezone.utc).isoformat(),
                          'scope':'ONE_OR_TWO_DELTA_SCR_SHARED_RL_GENERIC_MSL','physical_solver_owned_by_mcp':False})
    print(json.dumps({'ok':True,'cases':len(evidence),'calls':len(calls)}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cases',nargs='+');parser.add_argument('--step',type=float,default=1.25e-5)
    asyncio.run(run(parser.parse_args()))
