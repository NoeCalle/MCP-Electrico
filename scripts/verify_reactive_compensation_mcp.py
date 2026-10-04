"""Execute native OpenDSS banks through real MCP stdio and check independent references."""
import argparse
import asyncio
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from reactive_compensation_reference import reference_package,analytical_reference

ROOT=Path(__file__).resolve().parents[1]

async def verify(output):
    output.mkdir(parents=True,exist_ok=False)
    template=json.loads((ROOT/'examples/reactive_compensation_stage1.json').read_text(encoding='utf8'))
    calls=[];benchmarks=[]
    parameters=StdioServerParameters(command=sys.executable,args=['-X','utf8',str(ROOT/'server.py')],cwd=str(output),env=dict(os.environ,PYTHONUTF8='1'))
    with (output/'MCP-stderr.log').open('w',encoding='utf8') as err:
        async with stdio_client(parameters,errlog=err) as (read,write):
            async with ClientSession(read,write) as client:
                await client.initialize();listing=await client.list_tools()
                names={t.name for t in listing.tools}
                assert {'obtener_contrato_compensacion_reactiva','validar_compensacion_reactiva','ejecutar_compensacion_reactiva'}<=names
                async def call(tool,args):
                    response=await client.call_tool(tool,arguments=args)
                    assert not response.isError,str(response)
                    if response.structuredContent is not None:data=response.structuredContent
                    else:
                        text=next(c.text for c in response.content if c.type=='text')
                        try:data=json.loads(text)
                        except json.JSONDecodeError:data={'message':text}
                    calls.append({'tool':tool,'arguments':args,'result':data})
                    return data
                contract=await call('obtener_contrato_compensacion_reactiva',{})
                assert not contract['physical_solver_owned_by_mcp']
                selected=await call('seleccionar_motor_estudio',{'estudio':'bancos_capacitores','permitir_experimental':True})
                assert selected['selected_engine']=='opendss'
                assert selected['readiness']['overall_status']=='MISSING_DATA'
                assert not selected['executable']
                await call('crear_circuito',{'nombre':'parent_preserved','kv_base':12.47,'frecuencia':60,'bus_fuente':'parent_bus'})
                parent=await call('obtener_estado_workspace',{})
                invalid=deepcopy(template);invalid['banks'][0].pop('steps_kvar')
                blocked=await call('ejecutar_compensacion_reactiva',{'paquete_estudio':invalid,'directorio_salida':str(output/'must_not_exist')})
                assert blocked['status']=='BLOCKED_REACTIVE_COMPENSATION_INPUTS'
                assert not (output/'must_not_exist').exists()
                readiness=await call('validar_compensacion_reactiva',{'paquete_estudio':template})
                assert readiness['ready_for_execution'] and not readiness['electrical_calculation_performed']
                sample=await call('ejecutar_compensacion_reactiva',{'paquete_estudio':template,'directorio_salida':str(output/'Estudio-etapas')})
                assert sample['status']=='REACTIVE_COMPENSATION_COMPLETED',sample
                rows={r['id']:r for r in sample['results']}
                assert rows['nominal_100']['criteria']['passed']
                assert rows['light_50']['after']['source']['power_factor']>.999
                assert not rows['light_50']['criteria']['passed']
                for connection in ('wye','delta'):
                    for frequency in (50,60):
                        for pu in (.9,1.,1.1):
                            package=reference_package(template,connection,pu,frequency)
                            name=f'{connection}-{frequency}-{pu}'
                            result=await call('ejecutar_compensacion_reactiva',{'paquete_estudio':package,'directorio_salida':str(output/'References'/name)})
                            assert result['status']=='REACTIVE_COMPENSATION_COMPLETED',result
                            for state,enabled in [('before',False),('after',True)]:
                                metrics=result['results'][0][state];expected=analytical_reference(package,enabled)
                                actual={'p_kw':metrics['source']['p_kw'],'q_kvar':metrics['source']['q_kvar'],'voltage_pu':metrics['buses'][1]['minimum_pu'],
                                        'current_a':metrics['lines'][0]['maximum_phase_current_a'],'line_losses_kw':metrics['network_losses_kw'],'injected_kvar':metrics['banks'][0]['actual_injected_kvar']}
                                errors={key:abs(actual[key]-expected[key]) for key in expected}
                                limits={'voltage_pu':2e-6,'current_a':.002,'p_kw':.0002,'q_kvar':.0002,'line_losses_kw':.0002,'injected_kvar':.0002}
                                assert all(errors[k]<=limits[k] for k in errors),(name,state,errors)
                                benchmarks.append({'case':name,'state':state,'actual':actual,'independent_reference':expected,'absolute_error':errors,'tolerance':limits,'passed':True})
                overloaded=deepcopy(template);overloaded['base_model']['topology']['lines'][0]['normamps_a']=10
                result=await call('ejecutar_compensacion_reactiva',{'paquete_estudio':overloaded,'directorio_salida':str(output/'Overload')})
                assert result['results'][0]['after']['overload_evaluation']=='OVERLOADED'
                weak=deepcopy(overloaded);weak['options']['max_iterations']=1;weak['base_model']['source']['scc_max_mva']=1
                result=await call('ejecutar_compensacion_reactiva',{'paquete_estudio':weak,'directorio_salida':str(output/'Nonconvergence')})
                invalid_rows=[r for r in result['results'] if not r['after']['converged']]
                assert invalid_rows
                assert all(r['after']['overload_evaluation']=='NOT_EVALUABLE' for r in invalid_rows)
                assert parent==await call('obtener_estado_workspace',{})
    evidence={'ok':True,'transport':'MCP_STDIO','registered_tools':len(names),'call_count':len(calls),'checked_at_utc':datetime.now(timezone.utc).isoformat(),
              'independent_reference_depends_on_opendss':False,'benchmarks':benchmarks,'calls':calls,
              'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['mcp_electrico/reactive_compensation.py','mcp_electrico/motor_starting_static.py','scripts/reactive_compensation_reference.py']}}
    (output/'Evidencia-MCP.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    print(json.dumps({k:evidence[k] for k in ('ok','call_count','registered_tools')}|{'reference_comparisons':len(benchmarks)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    asyncio.run(verify(parser.parse_args().output.resolve()))
