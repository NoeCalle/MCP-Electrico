"""Real MCP admission/retirement gates and optional installed-MSL executions.

The electrical locked-rotor oracle is an independent linear nodal calculation
used only for testing; it is never a production physics backend.
"""
import argparse
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT=Path(__file__).resolve().parents[1]

def payload(result):
    if result.isError: raise RuntimeError(str(result))
    if result.structuredContent: return result.structuredContent
    return json.loads(next(item.text for item in result.content if item.type=='text'))

async def run(args):
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    calls=[]
    def save(name,value):
        (output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    parameters=StdioServerParameters(command=sys.executable,args=['-X','utf8',str(ROOT/'server.py')],cwd=str(output),env=dict(os.environ,PYTHONUTF8='1'))
    with (output/'MCP-stderr.log').open('w',encoding='utf8') as log:
        async with stdio_client(parameters,errlog=log) as (rd,wr):
            async with ClientSession(rd,wr,read_timeout_seconds=__import__('datetime').timedelta(seconds=600)) as client:
                await client.initialize()
                listing=await client.list_tools();names={t.name for t in listing.tools}
                save('Tools.json',{'count':len(names),'tools':sorted(names)})
                async def call(name,data,file):
                    value=payload(await client.call_tool(name,arguments=data))
                    save(file,value);calls.append({'tool':name,'file':file});return value
                for name in ('ejecutar_dinamica_motores','ejecutar_dinamica_arranque_suave'):
                    data={'manifest':{},'paquete_dinamico':{},'opciones':{}} if name.endswith('_motores') else {'manifest_referencia_dol':{},'paquete_dinamico':{},'opciones':{},'arrancador':{}}
                    retired=await call(name,data,name+'.json')
                    assert retired['execution_status']=='RETIRED_CUSTOM_BACKEND' and not retired['results']
                contract=await call('obtener_contrato_dinamica_modelica',{},'Contract.json')
                assert not contract['physical_solver_owned_by_mcp'] and not contract['professional_emission']
                package=json.loads((ROOT/'examples/msl_motor_dol.json').read_text())
                bad=deepcopy(package);del bad['motors'][0]['electrical']['rotor_resistance_ohm']
                blocked=await call('ejecutar_dinamica_modelica',{'paquete_estudio':bad,'directorio_salida':str(output/'Invalid')},'Incomplete.json')
                assert blocked['status']=='BLOCKED_MODELICA_READINESS' and not (output/'Invalid').exists()
                scr=deepcopy(package);scr['motors'][0]['starting']['method']='SCR'
                pending=await call('validar_dinamica_modelica',{'paquete_estudio':scr},'SCR-pending.json')
                assert not pending['ready_for_execution'] and pending['issues']
                two=json.loads((ROOT/'examples/msl_motor_scr_native_reference.json').read_text(encoding='utf8'))
                two['motors'].append(deepcopy(two['motors'][0]));two['motors'][1]['id']='SECOND-SCR'
                two_ready=await call('validar_dinamica_modelica',{'paquete_estudio':two},'SCR-two-readiness.json')
                assert two_ready['data_ready'] and not two_ready['qualification_blockers']
                assert two_ready['ready_for_execution']==bool(two_ready['runtime']['ready'])
                three=deepcopy(two);three['motors'].append(deepcopy(three['motors'][0]));three['motors'][2]['id']='THIRD-SCR'
                blocked=await call('ejecutar_dinamica_modelica',{'paquete_estudio':three,'directorio_salida':str(output/'Three-SCR')},'SCR-three-blocked.json')
                assert blocked['status']=='BLOCKED_MODELICA_READINESS' and blocked['readiness']['data_ready']
                assert 'MULTIMOTOR_SCR_NOT_QUALIFIED' in blocked['readiness']['qualification_blockers'] and not (output/'Three-SCR').exists()
                mixed=deepcopy(two);mixed['motors'][1]['starting']={'method':'DOL','time_s':.1,'controller':None}
                for key in ('refinement_voltage_absolute_tolerance_pu','refinement_torque_relative_tolerance','refinement_bypass_time_absolute_tolerance_s'):
                    del mixed['motors'][1]['criteria'][key]
                mixed_ready=await call('validar_dinamica_modelica',{'paquete_estudio':mixed},'Mixed-blocked.json')
                assert mixed_ready['data_ready'] and mixed_ready['qualification_blockers']==['MULTIMOTOR_SCR_NOT_QUALIFIED']
                if args.omc:
                    assert args.msl
                    await call('configurar_dinamica_modelica',{'ruta_omc':str(args.omc.resolve()),'directorio_msl':str(args.msl.resolve())},'Runtime.json')
                    cases={}
                    for tag in ('dol','two','locked_rotor'):
                        data=json.loads((ROOT/f'examples/msl_motor_{tag}.json').read_text())
                        ready=await call('validar_dinamica_modelica',{'paquete_estudio':data},tag+'-readiness.json')
                        assert ready['ready_for_execution'],ready
                        result=await call('ejecutar_dinamica_modelica',{'paquete_estudio':data,'directorio_salida':str(output/tag)},tag+'-result.json')
                        assert result['status']=='MODELICA_MOTOR_STUDIES_COMPLETED',result
                        assert all(m['verification']['passed'] for m in result['results'])
                        cases[tag]=result
                    # Independent sinusoidal nodal oracle including the RL source
                    # and the delta winding/line-current conversion.
                    import numpy as np
                    from math import pi,sqrt
                    e=data['motors'][0]['electrical'];n=data['network'];w=2*pi*n['frequency_hz']
                    zs=e['stator_resistance_ohm']+1j*w*e['stator_leakage_inductance_h']
                    zr=e['rotor_resistance_ohm']+1j*w*e['rotor_leakage_inductance_h']
                    zm=1j*w*e['magnetizing_inductance_h']
                    z_supply=n['r_ohm']+1j*n['x_ohm']
                    # KVL and KCL for delta stator phase and internal air-gap EMF.
                    stator,emf=np.linalg.solve(np.array([[zs+3*z_supply,1],[1,-1/zr-1/zm]],complex),[n['kv_ll']*1000*n['pu'],0])
                    expected_i=abs(stator)*sqrt(3)
                    expected_t=3*abs(emf/zr)**2*e['rotor_resistance_ohm']/(w/e['pole_pairs'])
                    measured=cases['locked_rotor']['results'][0]['trajectory'][-1]
                    errors={'current_relative_error':abs(measured['current_a']/expected_i-1),'torque_relative_error':abs(measured['torque_nm']/expected_t-1)}
                    assert max(errors.values())<.005,errors
                    assert cases['locked_rotor']['results'][0]['acceleration_time_s'] is None
                    assert not cases['locked_rotor']['results'][0]['criterion']['passed']
                    one=cases['dol']['results'][0];two=cases['two']['results'][0]
                    assert two['minimum_voltage_pu']<one['minimum_voltage_pu']-.05
                    assert two['acceleration_time_s']>one['acceleration_time_s']+.05
                    save('Independent-oracle.json',{'scope':'synthetic nearly locked rotor, fixed SI resistances, delta, balanced RL source','expected_current_a':expected_i,'expected_torque_nm':expected_t,'measured':measured,**errors,'illustrative_tolerance':.005,'production_solver':False})
    save('Calls.json',calls)
    save('Summary.json',{'real_mcp_transport':'stdio','tool_count':len(names),'calls':len(calls),'retired_physics_blocked':True,'incomplete_data_blocked':True,'incomplete_scr_data_blocked':True,'modelica_cases_executed':3 if args.omc else 0,'professional_emission':False})
    print(json.dumps({'ok':True,'calls':len(calls),'output':str(output)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--omc',type=Path);parser.add_argument('--msl',type=Path)
    asyncio.run(run(parser.parse_args()))
