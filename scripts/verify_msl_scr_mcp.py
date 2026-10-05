"""Execute closed-network SCR tests via MCP, with explicit verified scope.

The isolated converter oracle uses a known resistive phase-angle integral,
only for verification. It is not a motor/network production backend.
"""
import argparse
import asyncio
from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT=Path(__file__).resolve().parents[1]

async def run(output):
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    calls=[];cases={}
    def save(name,data):
        (output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    params=StdioServerParameters(command=sys.executable,args=['-X','utf8',str(ROOT/'server.py')],cwd=str(output),env=dict(os.environ,PYTHONUTF8='1'))
    with (output/'MCP-stderr.log').open('w',encoding='utf8') as err:
        async with stdio_client(params,errlog=err) as (rd,wr):
            async with ClientSession(rd,wr,read_timeout_seconds=timedelta(seconds=600)) as client:
                await client.initialize()
                async def call(tool,data,name):
                    response=await client.call_tool(tool,arguments=data)
                    assert not response.isError,response
                    value=response.structuredContent or json.loads(next(c.text for c in response.content if c.type=='text'))
                    save(name,value);calls.append({'tool':tool,'file':name});return value
                qualification=await call('obtener_estado_cierre_modulos',{},'Qualification.json')
                assert qualification['responsibilities']['signature_workflow_required_for_calculation'] is False
                contract=await call('obtener_contrato_dinamica_modelica',{},'Contract.json')
                assert contract['runtime']['ready'] and 'SCR' in contract['starting_methods']
                package=json.loads((ROOT/'examples/msl_motor_scr.json').read_text(encoding='utf8'))
                bad=deepcopy(package);del bad['motors'][0]['starting']['controller']['snubber_capacitance_f']
                blocked=await call('ejecutar_dinamica_modelica',{'paquete_estudio':bad,'directorio_salida':str(output/'Incomplete')},'Incomplete.json')
                assert blocked['status']=='BLOCKED_MODELICA_READINESS' and not (output/'Incomplete').exists()
                two=deepcopy(package);two['motors'].append(deepcopy(two['motors'][0]));two['motors'][1]['id']='SECOND'
                blocked=await call('ejecutar_dinamica_modelica',{'paquete_estudio':two,'directorio_salida':str(output/'Two-SCR')},'Two-SCR-blocked.json')
                assert blocked['status']=='BLOCKED_MODELICA_READINESS' and 'MULTIMOTOR_SCR_NOT_QUALIFIED' in blocked['readiness']['qualification_blockers']
                timeout=deepcopy(package);timeout['simulation']['timeout_s']=0.001
                timed=await call('ejecutar_dinamica_modelica',{'paquete_estudio':timeout,'directorio_salida':str(output/'Deliberate-timeout')},'Deliberate-timeout.json')
                assert timed['status']=='MODELICA_EXECUTION_FAILED' and timed['failure_kind']=='TIMEOUT'
                assert timed['failed_stage']=='COMPILATION' and timed['design_assessment']=='NOT_EVALUATED'
                assert timed['results']==[] and timed['calculation_status']=='NO_VERIFIED_RESULT'
                for tag in ('scr','scr_unreachable','scr_50hz'):
                    package=json.loads((ROOT/f'examples/msl_motor_{tag}.json').read_text(encoding='utf8'))
                    ready=await call('validar_dinamica_modelica',{'paquete_estudio':package},tag+'-readiness.json')
                    assert ready['ready_for_execution'],ready
                    result=await call('ejecutar_dinamica_modelica',{'paquete_estudio':package,'directorio_salida':str(output/tag)},tag+'-result.json')
                    assert result['status']=='MODELICA_MOTOR_STUDIES_COMPLETED',{'status':result['status'],'message':result.get('message'),'motors':[{k:v for k,v in m.items() if k!='trajectory'} for m in result['results']]}
                    motor=result['results'][0]
                    assert motor['verification']['passed'] and result['physical_solver_owned_by_mcp'] is False
                    if tag=='scr_unreachable':
                        assert motor['acceleration_time_s'] is None and motor['bypass_time_s'] is None and not motor['criterion']['passed']
                    else:
                        assert motor['acceleration_time_s'] is not None and motor['bypass_time_s'] is not None
                        # Closed reference control automatically ramps, holds and resumes.
                        samples=motor['trajectory'];refs=[s['controller_voltage_reference_pu'] for s in samples]
                        assert refs[-1]>.999 and max(refs)-min(refs)>.4
                        held=[i for i in range(1,len(refs)) if .41<refs[i]<.95 and abs(refs[i]-refs[i-1])<1e-5]
                        assert len(held)>5,'Current-limit ramp hold not exercised'
                        assert motor['minimum_bus_voltage_pu']>motor['minimum_voltage_pu']+.1
                        assert not motor['criterion']['passed'],'Deliberately strict terminal-voltage criterion must fail'
                    cases[tag]={k:v for k,v in motor.items() if k!='trajectory'}
                    print(json.dumps({'case':tag,**cases[tag]}),flush=True)
    save('Calls.json',calls)
    save('Summary.json',{'transport':'MCP_STDIO','calls':len(calls),'physical_cases':len(cases),'cases':cases,'scope':'ONE_DELTA_MACHINE_RL_NETWORK_MSL_REFERENCE_CONTROLLER','verification_status':qualification['modules']['modelica_scr']['verification_status'],'qualification_revision':qualification['revision'],'manufacturer_qualified':False,'professional_emission':False,'deliberate_timeout_correctly_diagnosed':True,'study_approval_responsibility':'ENGINEER'})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    asyncio.run(run(parser.parse_args().output))
