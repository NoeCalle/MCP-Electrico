"""Public MCP closure evidence for qualified static banks, P5 and P7.

This does not change MSL qualification; DOL is qualified and SCR has open gates.
"""
import argparse
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import sqrt
import os
from pathlib import Path
import sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from reactive_compensation_native_reference import native_reference

ROOT=Path(__file__).resolve().parents[1]

async def verify(output):
    output.mkdir(parents=True,exist_ok=False);calls=[];references=[]
    params=StdioServerParameters(command=sys.executable,args=['-X','utf8',str(ROOT/'server.py')],cwd=str(output),env=dict(os.environ,PYTHONUTF8='1'))
    with (output/'MCP-stderr.log').open('w',encoding='utf8') as err:
        async with stdio_client(params,errlog=err) as (read,write):
            async with ClientSession(read,write) as client:
                await client.initialize();listing=await client.list_tools()
                async def call(name,args):
                    raw=await client.call_tool(name,arguments=args);assert not raw.isError,str(raw)
                    if raw.structuredContent is not None:result=raw.structuredContent
                    else:
                        txt=next(c.text for c in raw.content if c.type=='text')
                        try:result=json.loads(txt)
                        except json.JSONDecodeError:result={'text':txt}
                    calls.append({'tool':name,'arguments':args,'result':result});return result
                closure=await call('obtener_estado_cierre_modulos',{})
                maturity=await call('obtener_matriz_validacion',{})
                assert maturity['professional_report']['status']=='EXTERNAL_RESPONSIBILITY'
                assert maturity['professional_report']['software_module'] is False
                assert closure['responsibilities']['signature_workflow_required_for_calculation'] is False
                for name in ['reactive_compensation','protection_data','tcc_curve_evaluation','protection_checks','protection_clearing_time','protection_coordination','reproducible_project','project_reconstruction','technical_report']:
                    assert closure['modules'][name]['verification_status']=='VERIFIED_IN_SCOPE'
                    assert maturity[name]['status']=='VALIDATED_WITH_LIMITATIONS'
                assert closure['modules']['modelica_scr']['closure_gates']
                template=json.loads((ROOT/'examples/reactive_compensation_stage1.json').read_text(encoding='utf8'))
                template['options']['allow_experimental']=False
                template['banks'].append(dict(id='hv_bank',bus='utility_13k8',phases=3,kv_ll=13.8,connection='wye',steps_kvar=[20,35],model='IDEAL_NO_REACTOR_NO_LOSSES',source_reference='CONTROLLED_NATIVE_REFERENCE'))
                template['scenarios']=[dict(id='both_banks',load_multiplier=m,bank_states={'bank1':[1,0,1],'hv_bank':[0,1]},source_reference='CONTROLLED_NATIVE_REFERENCE') for m in [1]]
                for group in ['Dyn11','Dyn1','Yy0']:
                    for tap in [-1,1]:
                        for mult in [.2,1]:
                            p=deepcopy(template);p['base_model']['topology']['transformers'][0].update(vector_group=group,tap_pos=tap)
                            p['scenarios'][0]['load_multiplier']=mult
                            result=await call('ejecutar_compensacion_reactiva',{'paquete_estudio':p,'directorio_salida':str(output/f'Native-{group}-{tap}-{mult}')})
                            assert result['status']=='REACTIVE_COMPENSATION_COMPLETED',result
                            for label,connected in [('before',False),('after',True)]:
                                expected=native_reference(p,p['scenarios'][0],connected);actual=result['results'][0][label]
                                errors={'p_kw':abs(actual['source']['p_kw']-expected['p_kw']),'q_kvar':abs(actual['source']['q_kvar']-expected['q_kvar']),
                                        'losses_kw':abs(actual['network_losses_kw']-expected['losses_kw']),'losses_kvar':abs(actual['network_losses_kvar']-expected['losses_kvar']),
                                        'voltage_pu':max(abs(v-ev) for bus in actual['buses'] for v,ev in zip(bus['phase_voltage_pu'],expected['voltages'][bus['bus']]))}
                                limits={'p_kw':.0005,'q_kvar':.0005,'losses_kw':.0005,'losses_kvar':.0005,'voltage_pu':2e-6}
                                assert all(errors[k]<=limits[k] for k in errors),(group,tap,mult,label,errors)
                                references.append({'case':f'{group}-{tap}-{mult}-{label}','reference':expected,'absolute_errors':errors,'limits':limits,'passed':True})
                await call('crear_circuito',{'nombre':'qualification','kv_base':.48,'frecuencia':60,'bus_fuente':'sourcebus'})
                for name,b1,b2 in [('up','sourcebus','b1'),('down','b1','b2')]:
                    await call('agregar_linea',{'nombre':name,'bus1':b1,'bus2':b2,'longitud_km':.02,'fases':3,'r1_ohm_km':.2,'x1_ohm_km':.08})
                    await call('definir_dispositivo_proteccion_p5a',{'nombre':name,'tipo':'circuit_breaker','elemento_protegido':'Line.'+name,'in_a':250,'ue_kv':.48,'icu_ka':36,'ics_ka':27,'norma_referencia':'TEST_DATA_NOT_NORMATIVE','fuente_referencia':'CONTROLLED_CLOSURE_TEST'})
                    await call('vincular_curva_proteccion_p5a',{'dispositivo':name,'curva_id':'curve_'+name,'tipo_curva':'TEST_CURVE','fuente_referencia':'ANALYTIC_I_MINUS_2','revision':'1'})
                    factor=2 if name=='up' else 1
                    await call('registrar_dataset_curva_tcc_p5b',{'dataset_id':'ds_'+name,'curve_id':'curve_'+name,'shape':'BAND','time_semantics':'TOTAL_CLEARING_TIME','segments':[{'id':'inverse','points':[{'current_a':100,'time_min_s':8*factor,'time_max_s':12*factor},{'current_a':1000,'time_min_s':.08*factor,'time_max_s':.12*factor}]}],'source_type':'TEST_DATA','source_reference':'ANALYTIC_I_MINUS_2'})
                    await call('vincular_dataset_curva_tcc_p5b',{'dispositivo':name,'dataset_id':'ds_'+name})
                current=sqrt(100*1000)
                curve=await call('evaluar_curva_tcc_p5b',{'dispositivo':'down','current_a':current})
                assert abs(curve['values']['time_min_s']-.8)<1e-10 and abs(curve['values']['time_max_s']-1.2)<1e-10
                outside=await call('evaluar_curva_tcc_p5b',{'dispositivo':'down','current_a':10})
                assert outside['status']!='RESOLVED_INTERPOLATED'
                clearing=await call('evaluar_tiempo_despeje_p5d',{'dispositivo':'down','current_a':current})
                assert clearing['status']=='CLEARING_TIME_READY' and abs(clearing['clearing_time']['conservative_time_s']-1.2)<1e-10
                (output/'Clearing.json').write_text(json.dumps(clearing,indent=2),encoding='utf8')
                coord=await call('evaluar_coordinacion_temporal_p5e',{'dispositivo_downstream':'down','corriente_downstream_a':current,'dispositivo_upstream':'up','corriente_upstream_a':current,'margen_minimo_s':.3,'fuente_relacion':'DECLARED_DOWNSTREAM_UPSTREAM','fuente_corrientes':'ANALYTIC_TEST_CURRENT'})
                assert coord['status']=='PASS' and abs(coord['conservative_margin_s']-.4)<1e-10
                assert coord['claims']['selectivity']=='NOT_EVALUATED'
                cut=await call('evaluar_capacidad_corte_p5c',{'dispositivo':'down','corriente_falla_ka':10,'tension_operacion_kv':.48,'fuente_corriente':'CONTROLLED_EXPLICIT_REFERENCE'})
                assert cut['status']=='PASS' and cut['margin_ka']==26
                thermal=await call('evaluar_soportabilidad_termica_conductor_p5c',{'elemento':'Line.down','corriente_falla_ka':1,'tiempo_despeje_s':.1,'seccion_mm2':50,'k_a_sqrt_s_per_mm2':115,'fuente_k':'TEST_DATA_EXPLICIT_K','fuente_tiempo':'TEST_DATA_TOTAL_CLEARING_TIME','fuente_seccion':'TEST_DATA_EXPLICIT_SECTION'})
                assert thermal['status']=='PASS' and thermal['results']['actual_i2t_a2s']==100000 and thermal['results']['limit_k2s2_a2s']==33062500
                p5=await call('evaluar_cierre_p5',{});assert p5['phase_status']=='READY_WITH_LIMITATIONS'
                p7=await call('evaluar_cierre_p7d_engineering_preview',{});assert p7['engineering_preview_ready'] and not p7['professional_emission']
                snapshot=await call('construir_snapshot_proyecto_p7a',{'directorio_netlist':str(output/'Snapshot-netlist')})
                checked=await call('verificar_snapshot_proyecto_p7a',{'snapshot':snapshot});assert checked['ok']
                corrupt=deepcopy(snapshot);corrupt['payload']['project']['circuit']='tampered'
                rejected=await call('verificar_snapshot_proyecto_p7a',{'snapshot':corrupt});assert not rejected['ok']
                restored=await call('reconstruir_snapshot_proyecto_p7b',{'snapshot':snapshot,'directorio_reconstruccion':str(output/'Reconstructed')})
                assert restored['status']=='RECONSTRUCTED_NETLIST_VERIFIED_WITH_REBIND_REQUIRED',restored
                assert restored['roundtrip']['canonical_netlist_match'] and not restored['stored_results_promoted_to_current']
                report=await call('exportar_reporte_tecnico_p7c',{'snapshot':snapshot,'ruta_salida':str(output/'Informe-P7.html')})
                assert report['ok'] and not report['professional_emission']
                html=(output/'Informe-P7.html').read_text(encoding='utf8')
                assert 'Revisión, aprobación y firma del estudio a cargo del ingeniero responsable' in html
                assert 'NO APTO PARA EMISIÓN PROFESIONAL' not in html
    evidence={'ok':True,'transport':'MCP_STDIO','registered_tools':len(listing.tools),'calls':calls,'call_count':len(calls),'native_comparisons':references,'professional_emission':False,
              'checked_at_utc':datetime.now(timezone.utc).isoformat(),'qualification_revision':closure['revision'],
              'source_sha256':{path:sha256((ROOT/path).read_bytes()).hexdigest() for path in [
                  'mcp_electrico/data/module_qualification_v1.json','mcp_electrico/module_qualification.py',
                  'mcp_electrico/reactive_compensation.py','mcp_electrico/motor_starting_static.py',
                  'scripts/reactive_compensation_native_reference.py','scripts/verify_module_qualification_mcp.py']}}
    (output/'Evidencia-cierre-MCP.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    print(json.dumps({'ok':True,'calls':len(calls),'native_comparisons':len(references),'tools':len(listing.tools)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    asyncio.run(verify(parser.parse_args().output.resolve()))
