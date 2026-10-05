"""Additional 60 Hz staggered case using the shared two-SCR evidence readers."""
import argparse,asyncio,json,os,sys
from datetime import timedelta,datetime,timezone
from hashlib import sha256
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from verify_msl_scr_two_mcp import cases,read_trace,motor_metrics,independent_motor_checks,common_bus_kvl,compare,SOURCES,ROOT


async def run(output):
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    p=cases(1.25e-5)['RL-overlapping'];p['id']='TWO-SCR-60HZ-OVERLAPPING'
    # The 3 s trial reached the endpoint but exceeded the 600 s runtime budget
    # during refined execution. Both bypass events precede 2.7 s. Keep six
    # complete post-bypass cycles without reusing the timed-out CSV as a result.
    p['network'].update(frequency_hz=60,angle_deg=15);p['simulation']['duration_s']=2.8
    for m in p['motors']:m['criteria']['maximum_acceleration_time_s']=2.8-m['starting']['time_s']
    rt=json.loads((ROOT/'local_data/modelica-runtime.json').read_text(encoding='utf8'));calls=[]
    source_names=SOURCES+['scripts/verify_msl_scr_two_60_mcp.py']
    hashes={name:sha256((ROOT/name).read_bytes()).hexdigest() for name in source_names}
    def save(name,value):(output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    save('Predeclared-plan.json',{'input':p,'energy_relative_limit':1e-4,'kvl_absolute_limit_pu':.001,
                                 'source_sha256':hashes,'runtime':rt})
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
                print('Executing genuine MCP: 60 Hz overlapping SCR',flush=True)
                result=await call('ejecutar_dinamica_modelica',{'paquete_estudio':p,'directorio_salida':str(output/'Study')})
                save('Result.json',result)
                assert result['status']=='MODELICA_MOTOR_STUDIES_COMPLETED',{'status':result['status'],'message':result.get('message'),
                    'verification':[m.get('verification') for m in result.get('results',[])]}
    checks={};readers=[]
    for name in ('Nominal.csv','Refined.csv'):
        a=read_trace(output/'Study'/name,p)
        checks[name]={'kvl':common_bus_kvl(a,p),'motors':[independent_motor_checks(a,p,i) for i in range(2)],
                      'trace_sha256':sha256((output/'Study'/name).read_bytes()).hexdigest()}
        assert checks[name]['kvl']['passed'] and all(m['passed'] for m in checks[name]['motors']),checks[name]
        if name=='Refined.csv':readers=[compare(motor_metrics(a,p,i),result['results'][i],60) for i in range(2)]
    assert all(row['passed'] for row in readers),readers
    assert all(m['bypass_time_s'] is not None for m in result['results'])
    assert hashes=={name:sha256((ROOT/name).read_bytes()).hexdigest() for name in source_names}
    save('Evidence.json',{'ok':True,'transport':'MCP_STDIO','calls':len(calls),'input':p,'checks':checks,'reader_parity':readers,
                         'motors':[{k:v for k,v in m.items() if k!='trajectory'} for m in result['results']],
                         'source_sha256':hashes,'runtime':rt,'checked_at_utc':datetime.now(timezone.utc).isoformat()})
    print(json.dumps({'ok':True,'calls':len(calls),'case':'60HZ-overlapping'}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    asyncio.run(run(parser.parse_args().output))
