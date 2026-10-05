"""Unequal inertias and load curves on two SCR machines; native MSL via MCP."""
import argparse,asyncio,json,os,sys
from datetime import timedelta,datetime,timezone
from hashlib import sha256
from pathlib import Path
import numpy as np
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from verify_msl_scr_two_mcp import cases,read_trace,motor_metrics,independent_motor_checks,common_bus_kvl,compare,SOURCES,ROOT


def mechanical_checks(a,p,index):
    m=p['motors'][index];mech=m['mechanical'];prefix=f'm{index}';omega=a[prefix+'speed'];t=a['time']
    points=mech['load_curve'];speeds=[row['speed_rad_s'] for row in points]
    if omega.min()<min(speeds) or omega.max()>max(speeds):raise ValueError('Load curve does not cover trace')
    load=np.interp(omega,speeds,[row['torque_nm'] for row in points])
    electromagnetic=float(np.trapezoid(a[prefix+'torque']*omega,t))
    load_work=float(np.trapezoid(load*omega,t));damping_work=float(np.trapezoid(mech['damping_nm_s_rad']*omega**2,t))
    kinetic=float(.5*(mech['motor_inertia_kg_m2']+mech['load_inertia_kg_m2'])*(omega[-1]**2-omega[0]**2))
    error=abs(electromagnetic-load_work-damping_work-kinetic)/max(abs(kinetic),1e-12)
    # Reuse only the independent bypass policy; do not feed loaded traces to
    # the zero-load energy oracle as if they were unloaded.
    zero=__import__('copy').deepcopy(p);zero['motors'][index]['mechanical']['damping_nm_s_rad']=0
    for point in zero['motors'][index]['mechanical']['load_curve']:point['torque_nm']=0
    bypass=independent_motor_checks(a,zero,index)
    return {'electromagnetic_work_j':electromagnetic,'load_work_j':load_work,'damping_work_j':damping_work,
            'kinetic_energy_delta_j':kinetic,'energy_relative_error':error,'energy_limit':1e-4,
            'expected_bypass_s':bypass['expected_bypass_s'],'observed_bypass_s':bypass['observed_bypass_s'],
            'bypass_error_s':bypass['bypass_error_s'],'bypass_limit_s':bypass['bypass_limit_s'],'latched':bypass['latched'],
            'passed':error<=1e-4 and bypass['latched'] and bypass['bypass_error_s'] is not None and bypass['bypass_error_s']<=bypass['bypass_limit_s']}


def package():
    p=cases(1.25e-5)['RL-overlapping'];p['id']='TWO-SCR-UNEQUAL-LOADED';p['simulation']['duration_s']=2.3
    for i,m in enumerate(p['motors']):
        mech=m['mechanical'];mech['load_inertia_kg_m2']=.29 if i==0 else .145
        mech['damping_nm_s_rad']=.01 if i==0 else .02
        scale=20 if i==0 else 30
        mech['load_curve']=[{'speed_rad_s':-200,'torque_nm':-scale},{'speed_rad_s':0,'torque_nm':0},
                            {'speed_rad_s':100,'torque_nm':scale/4},{'speed_rad_s':200,'torque_nm':scale}]
        mech['source_reference']='Explicit synthetic unequal piecewise load curves, damping and inertia; not customer pump data'
        m['criteria']['maximum_acceleration_time_s']=2.3-m['starting']['time_s']
    return p


async def run(output):
    output=output.resolve();output.mkdir(parents=True,exist_ok=False);p=package();calls=[]
    rt=json.loads((ROOT/'local_data/modelica-runtime.json').read_text(encoding='utf8'))
    names=SOURCES+['scripts/verify_msl_scr_two_loaded_mcp.py'];hashes={name:sha256((ROOT/name).read_bytes()).hexdigest() for name in names}
    def save(name,value):(output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    save('Predeclared-plan.json',{'input':p,'energy_relative_limit':1e-4,'kvl_absolute_limit_pu':.001,'source_sha256':hashes,'runtime':rt})
    params=StdioServerParameters(command=sys.executable,args=['-X','utf8',str(ROOT/'server.py')],cwd=str(output),env=dict(os.environ,PYTHONUTF8='1'))
    with (output/'MCP-stderr.log').open('w',encoding='utf8') as log:
        async with stdio_client(params,errlog=log) as (rd,wr):
            async with ClientSession(rd,wr,read_timeout_seconds=timedelta(seconds=2400)) as client:
                await client.initialize()
                async def call(tool,args):
                    r=await client.call_tool(tool,arguments=args);assert not r.isError,r
                    value=r.structuredContent or json.loads(next(c.text for c in r.content if c.type=='text'))
                    calls.append({'tool':tool,'arguments':args,'result':value});save('Calls.json',calls);return value
                await call('configurar_dinamica_modelica',{'ruta_omc':rt['executable'],'directorio_msl':rt['library']})
                ready=await call('validar_dinamica_modelica',{'paquete_estudio':p});assert ready['ready_for_execution'],ready
                print('Executing genuine MCP: unequal loaded SCR machines',flush=True)
                result=await call('ejecutar_dinamica_modelica',{'paquete_estudio':p,'directorio_salida':str(output/'Study')});save('Result.json',result)
                assert result['status']=='MODELICA_MOTOR_STUDIES_COMPLETED',{'status':result['status'],'message':result.get('message'),
                    'verification':[m.get('verification') for m in result.get('results',[])]}
    checks={};readers=[]
    for filename in ('Nominal.csv','Refined.csv'):
        a=read_trace(output/'Study'/filename,p)
        checks[filename]={'kvl':common_bus_kvl(a,p),'motors':[mechanical_checks(a,p,i) for i in range(2)],
                          'trace_sha256':sha256((output/'Study'/filename).read_bytes()).hexdigest()}
        assert checks[filename]['kvl']['passed'] and all(m['passed'] for m in checks[filename]['motors']),checks[filename]
        if filename=='Refined.csv':readers=[compare(motor_metrics(a,p,i),result['results'][i],50) for i in range(2)]
    assert all(row['passed'] for row in readers),readers
    assert all(m['bypass_time_s'] is not None for m in result['results'])
    assert hashes=={name:sha256((ROOT/name).read_bytes()).hexdigest() for name in names}
    save('Evidence.json',{'ok':True,'transport':'MCP_STDIO','calls':len(calls),'input':p,'checks':checks,'reader_parity':readers,
                         'motors':[{k:v for k,v in m.items() if k!='trajectory'} for m in result['results']],
                         'source_sha256':hashes,'runtime':rt,'checked_at_utc':datetime.now(timezone.utc).isoformat()})
    print(json.dumps({'ok':True,'calls':len(calls),'case':'UNEQUAL-LOADED'}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    asyncio.run(run(parser.parse_args().output))
