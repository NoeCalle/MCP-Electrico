"""Explicit static capacitor scenarios solved by existing OpenDSS components.

Network materialization and SI conversions reuse the isolated P13 builder.
This module validates data and processes engine meters; it owns no solver.
"""
from copy import deepcopy
import hashlib
from html import escape
import json
from math import hypot, isfinite
from pathlib import Path
import re

from opendssdirect import dss
from . import motor_starting_static as network
from . import real_pilot_intake, professional_data
from . import module_qualification

SCHEMA = 'MCP_ELECTRICO_REACTIVE_COMPENSATION_V1'
SAFE = re.compile(r'^[A-Za-z_][A-Za-z0-9_-]*$')


def contract():
    return {'schema':SCHEMA,'engine':'OpenDSS','maturity':'VALIDATED_WITH_LIMITATIONS',
            'integration_verification':module_qualification.get('reactive_compensation'),
            'scope':'BALANCED_3PH_STATIC_PASSIVE_NETWORK_EXPLICIT_FIXED_STAGES',
            'connections':['wye','delta'],'load_models':[1,2],
            'network_builder':'SHARED_P13_ISOLATED_NETWORK_BUILDER',
            'capacitor_model':'OPENDSS_CAPACITOR_IDEAL_NO_REACTOR_NO_LOSSES',
            'stage_representation':'ONE_NATIVE_OPENDSS_CAPACITOR_PER_EXPLICIT_STAGE',
            'baseline':'ALL_BANKS_OFF_AT_THE_SAME_DEMAND_AS_EACH_SCENARIO',
            'not_supported':['harmonics','resonance','detuning_reactors','switching_transients','automatic_CapControl','unbalanced_network','generators','full_device_selection','tariff_energy_savings'],
            'criteria_reference_required':True,'automatic_defaults':False,
            'physical_solver_owned_by_mcp':False,'parent_model_mutated':False,
            'professional_emission':False}


def validate(package):
    issues=[]
    def issue(path,msg):issues.append({'path':path,'message':msg})
    def obj(raw,path,required,optional=()):
        if not isinstance(raw,dict):issue(path,'object required');return {}
        if not set(required)<=set(raw) or set(raw)-set(required)-set(optional):issue(path,'explicit fields required: '+', '.join(sorted(required)))
        return raw
    def num(v,path,minimum=0,strict=True):
        try:
            if type(v) in (int,float) and isfinite(v) and not (v<=minimum if strict else v<minimum):return float(v)
        except OverflowError:pass
        issue(path,'finite explicit number outside range');return None
    def ref(v,path):
        if not isinstance(v,str) or not v.strip():issue(path,'source reference required')
    def name(v,path,kind=None):
        try:
            if kind:return network._element_name(v,kind)
            if isinstance(v,str) and SAFE.fullmatch(v):return v
            raise ValueError('safe identifier required')
        except ValueError as exc:issue(path,str(exc));return None
    def collection(raw,path,maximum):
        if not isinstance(raw,list) or len(raw)>maximum:issue(path,'explicit bounded list required');return []
        return raw
    root=obj(package,'study',{'schema','id','source_reference','base_model','banks','scenarios','criteria','options'})
    if root.get('schema')!=SCHEMA:issue('schema',SCHEMA+' required')
    ref(root.get('id'),'id');ref(root.get('source_reference'),'source_reference')
    base=obj(root.get('base_model'),'base_model',{'project','source','topology'})
    project=obj(base.get('project'),'project',{'id','name','source_reference'})
    for key in project:ref(project[key],'project.'+key)
    source=obj(base.get('source'),'source',{'bus','kv_ll','frequency_hz','pu','angle_deg','scc_max_mva','x_r_max','source_reference'})
    name(source.get('bus'),'source.bus');ref(source.get('source_reference'),'source.source_reference')
    for key in ('kv_ll','frequency_hz','pu','scc_max_mva','x_r_max'):num(source.get(key),'source.'+key)
    num(source.get('angle_deg'),'source.angle_deg',minimum=-float('inf'))
    topo=obj(base.get('topology'),'topology',{'buses','lines','transformers','loads'})
    buses=collection(topo.get('buses'),'buses',200)
    for i,bus in enumerate(buses):name(bus,f'buses[{i}]')
    if not buses:issue('buses','at least one bus required')
    if len({str(b).casefold() for b in buses})!=len(buses):issue('buses','case-insensitive unique buses required')
    ids=set()
    specs={
        'lines':({'id','bus1','bus2','phases','length_km','r1_ohm_km','x1_ohm_km','c1_nf_km','normamps_a','source_reference'},set()),
        'loads':({'id','bus','phases','kv','kw','kvar','connection','model','vminpu','vmaxpu','source_reference'},set()),
        'transformers':({'id','bus_hv','bus_lv','kva','kv_hv','kv_lv','uk_percent','vector_group','no_load_loss_kw','i0_percent','tap_side','tap_neutral','tap_min','tap_max','tap_step_percent','tap_pos','source_reference'},{'x_r','load_loss_kw'})}
    for group,(fields,optional) in specs.items():
        rows=collection(topo.get(group),'topology.'+group,200)
        for i,raw in enumerate(rows):
            path=f'topology.{group}[{i}]';item=obj(raw,path,fields,optional)
            suffix=name(item.get('id'),path+'.id',{'lines':'Line','loads':'Load','transformers':'Transformer'}[group])
            identifier=group+'.'+str(suffix).casefold()
            if identifier in ids:issue(path+'.id','duplicate element')
            ids.add(identifier);ref(item.get('source_reference'),path+'.source_reference')
            for key in fields|optional:
                if key.startswith('bus') and key in item:name(item[key],path+'.'+key)
            if group in ('lines','loads') and (type(item.get('phases')) is not int or item.get('phases')!=3):issue(path+'.phases','balanced three phases required')
            if group=='lines':
                for key in ('length_km','normamps_a'):num(item.get(key),path+'.'+key)
                for key in ('r1_ohm_km','x1_ohm_km','c1_nf_km'):num(item.get(key),path+'.'+key,strict=False)
            elif group=='loads':
                num(item.get('kv'),path+'.kv');num(item.get('kw'),path+'.kw',strict=False)
                num(item.get('kvar'),path+'.kvar',minimum=-float('inf'))
                low=num(item.get('vminpu'),path+'.vminpu');high=num(item.get('vmaxpu'),path+'.vmaxpu')
                if low is not None and high is not None and not low<1<high:issue(path,'declare Vminpu < 1 < Vmaxpu; OpenDSS fallback boundary')
                if type(item.get('model')) is not int or item.get('model') not in (1,2):issue(path+'.model','explicit OpenDSS constant-PQ (1) or impedance (2) only')
                if item.get('connection') not in ('wye','delta'):issue(path+'.connection','wye/delta required')
            else:
                for key in ('kva','kv_hv','kv_lv','uk_percent','tap_step_percent'):num(item.get(key),path+'.'+key)
                for key in ('no_load_loss_kw','i0_percent'):num(item.get(key),path+'.'+key,strict=False)
                for key in ('tap_neutral','tap_min','tap_max','tap_pos'):
                    if type(item.get(key)) is not int:issue(path+'.'+key,'explicit integer required')
                if len(set(item)&optional)!=1:issue(path,'declare exactly one of X/R or load losses')
                if 'x_r' in item:num(item['x_r'],path+'.x_r')
                if 'load_loss_kw' in item:num(item['load_loss_kw'],path+'.load_loss_kw',strict=False)
                if not issues:
                    try:
                        professional_data._parse_vector_group(item['vector_group'])
                        professional_data._series_impedance(item['kva'],item['uk_percent'],item.get('x_r'),item.get('load_loss_kw'))
                        professional_data._tap_data(item['tap_side'],item['tap_neutral'],item['tap_min'],item['tap_max'],item['tap_step_percent'],item['tap_pos'])
                    except (ValueError,TypeError) as exc:issue(path,str(exc))
    if not isinstance(topo.get('loads'),list) or not topo['loads']:issue('loads','at least one explicit load required')
    bases={}
    if not issues:
        issues.extend(real_pilot_intake._topology_issues(base))
        preflight,bases=network._preflight_base(base,[]);issues.extend(preflight)
    banks=collection(root.get('banks'),'banks',8);bank_map={}
    if not banks:issue('banks','at least one bank required')
    for i,raw in enumerate(banks):
        path=f'banks[{i}]';bank=obj(raw,path,{'id','bus','phases','kv_ll','connection','steps_kvar','model','source_reference'})
        key=name(bank.get('id'),path+'.id');name(bank.get('bus'),path+'.bus')
        if key in bank_map or str(key).casefold() in {str(k).casefold() for k in bank_map}:issue(path+'.id','duplicate bank')
        if key is not None:bank_map[key]=bank
        if bank.get('bus') not in buses:issue(path+'.bus','bus must exist in declared network')
        if type(bank.get('phases')) is not int or bank.get('phases')!=3:issue(path+'.phases','three phases required')
        num(bank.get('kv_ll'),path+'.kv_ll')
        if bank.get('connection') not in ('wye','delta'):issue(path+'.connection','grounded wye or delta only')
        if bank.get('model')!='IDEAL_NO_REACTOR_NO_LOSSES':issue(path+'.model','explicit ideal-bank acknowledgement required; reactors/harmonics excluded')
        ref(bank.get('source_reference'),path+'.source_reference')
        steps=collection(bank.get('steps_kvar'),path+'.steps_kvar',16)
        if not steps:issue(path+'.steps_kvar','at least one explicitly rated step required')
        for j,v in enumerate(steps):num(v,f'{path}.steps_kvar[{j}]')
    scenarios=collection(root.get('scenarios'),'scenarios',32);scenario_ids=set()
    if not scenarios:issue('scenarios','at least one scenario required')
    for i,raw in enumerate(scenarios):
        path=f'scenarios[{i}]';scenario=obj(raw,path,{'id','load_multiplier','bank_states','source_reference'})
        ref(scenario.get('id'),path+'.id');ref(scenario.get('source_reference'),path+'.source_reference')
        key=str(scenario.get('id')).casefold()
        if key in scenario_ids:issue(path+'.id','duplicate scenario')
        scenario_ids.add(key);num(scenario.get('load_multiplier'),path+'.load_multiplier',strict=False)
        states=scenario.get('bank_states')
        if not isinstance(states,dict) or set(states)!=set(bank_map):issue(path+'.bank_states','explicit states required for every bank');continue
        for bank_id,vector in states.items():
            steps=bank_map[bank_id].get('steps_kvar')
            expected=len(steps) if isinstance(steps,list) else 0
            if not isinstance(vector,list) or len(vector)!=expected or any(type(s) is not int or s not in (0,1) for s in vector):issue(path+'.bank_states.'+bank_id,'one explicit integer 0/1 per step required')
    criteria=obj(root.get('criteria'),'criteria',{'minimum_source_power_factor','allow_leading','voltage_min_pu','voltage_max_pu','maximum_line_loading_pct','maximum_transformer_loading_pct','source_reference'})
    for key in set(criteria)-{'source_reference','allow_leading'}:num(criteria[key],'criteria.'+key)
    if type(criteria.get('allow_leading')) is not bool:issue('criteria.allow_leading','explicit boolean required')
    if type(criteria.get('minimum_source_power_factor')) in (int,float) and criteria['minimum_source_power_factor']>1:issue('criteria.minimum_source_power_factor','maximum one')
    if type(criteria.get('voltage_min_pu')) in (int,float) and type(criteria.get('voltage_max_pu')) in (int,float) and criteria['voltage_min_pu']>=criteria['voltage_max_pu']:issue('criteria','increasing voltage bounds required')
    ref(criteria.get('source_reference'),'criteria.source_reference')
    options=obj(root.get('options'),'options',{'allow_experimental','solver_tolerance','max_iterations','active_balance_tolerance_kw','reactive_balance_tolerance_kvar'})
    # V1 field retained for package compatibility; verified static scope needs
    # no experimental opt-in. Unimplemented extensions remain rejected.
    if type(options.get('allow_experimental')) is not bool:issue('options.allow_experimental','explicit boolean required; legacy V1 option, not an execution gate')
    for key in ('solver_tolerance','active_balance_tolerance_kw','reactive_balance_tolerance_kvar'):num(options.get(key),'options.'+key)
    if type(options.get('max_iterations')) is not int or not 1<=options['max_iterations']<=1000:issue('options.max_iterations','integer 1..1000 required')
    if type(options.get('solver_tolerance')) in (int,float) and not 1e-12<=options['solver_tolerance']<=1e-4:issue('options.solver_tolerance','supported range 1e-12..1e-4')
    return {'schema':SCHEMA,'ready_for_execution':not issues,'issues':issues,'bus_bases_kv_ll':bases,'electrical_calculation_performed':False,'automatic_defaults':False,'professional_emission':False,'contract':contract()}


def _create_engine(package,scenario):
    base=deepcopy(package['base_model']);f=base['source']['frequency_hz']
    for load in base['topology']['loads']:
        load['kw']*=scenario['load_multiplier'];load['kvar']*=scenario['load_multiplier']
    engine,_=network._build_isolated_base(base,[],network._derive_bus_bases(base,[])[0])
    commands=[f'Edit Vsource.source BaseFreq={f} Phases=3']
    for group,kind in [('lines','Line'),('transformers','Transformer'),('loads','Load')]:
        for item in base['topology'][group]:
            name=network._element_name(item['id'],kind)
            command=f'Edit {kind}.{name} BaseFreq={f}'
            if kind=='Load':command+=f" Vminpu={item['vminpu']} Vmaxpu={item['vmaxpu']}"
            if kind=='Line':command+=f" NormAmps={item['normamps_a']}"
            commands.append(command)
    for bank in package['banks']:
        # Independent native objects avoid multi-step array reallocation and
        # implicit redistribution of unequal ratings during property edits.
        for i,kvar in enumerate(bank['steps_kvar'],1):
            commands.append(f"New Capacitor.rc_{bank['id']}_s{i} Bus1={bank['bus']} Bus2={bank['bus']}.0.0.0 Phases=3 Conn={bank['connection']} NumSteps=1 kV={bank['kv_ll']} BaseFreq={f} R=[0] XL=[0] kvar=[{kvar}] States=[0] Enabled=True")
    opt=package['options']
    commands.append(f"Set Mode=Snapshot ControlMode=Off Frequency={f} LoadMult=1 Algorithm=Normal Tolerance={opt['solver_tolerance']} MaxIterations={opt['max_iterations']}")
    for command in commands:engine(command)
    return engine,commands


def _terminal_power(engine):
    n=engine.CktElement.NumConductors();values=engine.CktElement.Powers()[:2*n]
    return sum(values[::2]),sum(values[1::2])


def _measure(engine,package):
    engine.Solution.Solve()
    if not engine.Solution.Converged():
        return {'converged':False,'results_valid':False,'overload_evaluation':'NOT_EVALUABLE','iterations':engine.Solution.Iterations()}
    p,q=[-float(v) for v in engine.Circuit.TotalPower()]
    opt=package['options'];direction='LEADING' if q < -opt['reactive_balance_tolerance_kvar'] else ('LAGGING' if q>opt['reactive_balance_tolerance_kvar'] else 'UNITY_WITHIN_NUMERICAL_TOLERANCE')
    pf=abs(p)/hypot(p,q) if p>opt['active_balance_tolerance_kw'] else None
    buses=[]
    for bus in package['base_model']['topology']['buses']:
        values=network._bus_voltage_pu(engine,bus)
        buses.append({'bus':bus,'phase_voltage_pu':values,'minimum_pu':min(values),'maximum_pu':max(values)})
    loss_p=loss_q=load_p=load_q=0.;lines=[];trafos=[]
    for kind,group in [('Line','lines'),('Transformer','transformers')]:
        for item in package['base_model']['topology'][group]:
            engine.Circuit.SetActiveElement(kind+'.'+network._element_name(item['id'],kind));loss=engine.CktElement.Losses();loss_p+=loss[0]/1000;loss_q+=loss[1]/1000
            currents=list(engine.CktElement.CurrentsMagAng()[::2]);n=engine.CktElement.NumConductors()
            if kind=='Line':
                maximum=max(currents[:3]+currents[n:n+3]);lines.append({'id':item['id'],'maximum_phase_current_a':maximum,'rating_a':item['normamps_a'],'loading_pct':100*maximum/item['normamps_a']})
            else:
                powers=engine.CktElement.Powers();ratings=[]
                for t in range(engine.CktElement.NumTerminals()):
                    values=powers[t*2*n:(t+1)*2*n];ratings.append(hypot(sum(values[::2]),sum(values[1::2])))
                trafos.append({'id':item['id'],'terminal_apparent_kva':ratings,'rating_kva':item['kva'],'loading_pct':100*max(ratings)/item['kva']})
    fallback=[]
    for item in package['base_model']['topology']['loads']:
        engine.Circuit.SetActiveElement('Load.'+network._element_name(item['id'],'Load'));a,b=_terminal_power(engine);load_p+=a;load_q+=b
        bus_metrics=next(v for v in buses if v['bus']==item['bus'])
        if item['model']==1 and (bus_metrics['minimum_pu']<item['vminpu'] or bus_metrics['maximum_pu']>item['vmaxpu']):fallback.append(item['id'])
    banks=[];cap_p=cap_q=0
    for bank in package['banks']:
        states=[];a=b=0.
        for i in range(1,len(bank['steps_kvar'])+1):
            element='rc_'+bank['id']+'_s'+str(i)
            engine.Capacitors.Name(element);states.append(int(engine.Capacitors.States()[0]))
            engine.Circuit.SetActiveElement('Capacitor.'+element)
            step_p,step_q=_terminal_power(engine);a+=step_p;b+=step_q
        cap_p+=a;cap_q+=b
        banks.append({'id':bank['id'],'states':states,'nominal_connected_kvar':sum(v*s for v,s in zip(bank['steps_kvar'],states)),'actual_injected_kvar':-b,'active_loss_kw':a,'bus':bank['bus'],'rated_kv_ll':bank['kv_ll']})
    balance_p=p-load_p-cap_p-loss_p;balance_q=q-load_q-cap_q-loss_q
    valid=abs(balance_p)<=opt['active_balance_tolerance_kw'] and abs(balance_q)<=opt['reactive_balance_tolerance_kvar']
    all_metrics=[p,q,loss_p,loss_q,load_p,load_q]+[b['minimum_pu'] for b in buses]+[b['maximum_pu'] for b in buses]+[v['loading_pct'] for v in lines+trafos]
    valid=valid and all(isfinite(v) for v in all_metrics)
    if not all(isfinite(v) for v in all_metrics+[cap_p,cap_q,balance_p,balance_q]):
        return {'converged':True,'results_valid':False,'overload_evaluation':'NOT_EVALUABLE','reason':'NONFINITE_ENGINE_METERS'}
    source={'p_kw':p,'q_kvar':q,'apparent_kva':hypot(p,q),'power_factor':pf,'reactive_direction':direction}
    return {'converged':True,'results_valid':valid,'iterations':engine.Solution.Iterations(),'source':source,'buses':buses,'lines':lines,'transformers':trafos,'banks':banks,
            'network_losses_kw':loss_p,'network_losses_kvar':loss_q,'actual_load_kw':load_p,'actual_load_kvar':load_q,'power_balance':{'active_residual_kw':balance_p,'reactive_residual_kvar':balance_q,'passed':valid},
            'constant_pq_fallback_loads':fallback,
            'overload_evaluation':('OVERLOADED' if any(v['loading_pct']>100 for v in lines+trafos) else 'WITHIN_DECLARED_RATINGS') if valid else 'NOT_EVALUABLE'}


def _criteria(metrics,criteria):
    if not metrics.get('results_valid'):return {'evaluated':False,'passed':False,'reason':'NONCONVERGENCE_OR_POWER_BALANCE_FAILURE','source_reference':criteria['source_reference']}
    checks={'constant_pq_representation':not metrics['constant_pq_fallback_loads'],
            'source_power_factor':metrics['source']['power_factor'] is not None and metrics['source']['power_factor']>=criteria['minimum_source_power_factor'],
            'reactive_direction':criteria['allow_leading'] or metrics['source']['reactive_direction']!='LEADING',
            'bus_voltages':all(b['minimum_pu']>=criteria['voltage_min_pu'] and b['maximum_pu']<=criteria['voltage_max_pu'] for b in metrics['buses']),
            'line_loading':all(v['loading_pct']<=criteria['maximum_line_loading_pct'] for v in metrics['lines']),
            'transformer_loading':all(v['loading_pct']<=criteria['maximum_transformer_loading_pct'] for v in metrics['transformers'])}
    return {'evaluated':True,'passed':all(checks.values()),'checks':checks,'source_reference':criteria['source_reference']}


def _render_html(package,results):
    sections=[]
    labels={'power_factor':'Factor de potencia','q_kvar':'Reactiva de fuente (kvar)',
            'apparent_kva':'Potencia de fuente (kVA)'}
    for row in results:
        before,after=row.get('before',{}),row.get('after',{})
        cells=[]
        def fmt(v):return 'No evaluable' if v is None else f'{v:.5g}'
        for key,label in labels.items():
            cells.append(f'<tr><td>{label}</td><td>{fmt(before.get("source",{}).get(key))}</td><td>{fmt(after.get("source",{}).get(key))}</td></tr>')
        for key,label in [('network_losses_kw','Pérdidas de red (kW)')]:
            cells.append(f'<tr><td>{label}</td><td>{fmt(before.get(key))}</td><td>{fmt(after.get(key))}</td></tr>')
        for group,key,label,aggregation in [('buses','minimum_pu','Tensión mínima (pu)',min),('lines','loading_pct','Carga máxima de líneas (%)',max),('transformers','loading_pct','Carga máxima de transformadores (%)',max)]:
            values=[aggregation((v[key] for v in state.get(group,[])),default=None) for state in (before,after)]
            cells.append(f'<tr><td>{label}</td><td>{fmt(values[0])}</td><td>{fmt(values[1])}</td></tr>')
        status='Cumple criterios declarados' if row['criteria']['passed'] and row['comparison_valid'] else 'No cumple / no evaluable'
        details='<br>'.join(escape(b['id'])+': '+str(b['states'])+' · '+fmt(b['actual_injected_kvar'])+' kvar reales' for b in after.get('banks',[]))
        checks=', '.join(k for k,v in row['criteria'].get('checks',{}).items() if not v)
        sections.append('<section><h2>'+escape(str(row['id']))+'</h2><p>Demanda: '+str(row['load_multiplier'])+' pu · <strong>'+status+'</strong></p><table><tr><th>Magnitud</th><th>Sin banco</th><th>Etapas elegidas</th></tr>'+''.join(cells)+'</table><p>'+details+'</p><p>Sentido de reactiva: '+escape(after.get('source',{}).get('reactive_direction','No evaluable'))+'</p><p>Criterios incumplidos: '+escape(checks or 'ninguno / no evaluable')+'</p></section>')
    return '<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Compensación reactiva</title><style>body{font:16px system-ui;margin:2rem;max-width:1200px;color:#18354a;background:#f6f9fc}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:1rem}section{background:white;padding:1rem;border:1px solid #ccd;border-radius:12px}table{border-collapse:collapse;width:100%}td,th{padding:.5rem;border-bottom:1px solid #ccd;text-align:left}th{background:#edf4f8}h2{font-size:1.2rem}</style></head><body><h1>Bancos de capacitores: comparación estática</h1><p>OpenDSS · integración verificada en alcance estático declarado · red equilibrada · cada comparación conserva la misma demanda.</p><p>Q positivo: inductivo; Q negativo: capacitivo. Un FP alto con Q negativo puede incumplir el criterio de operación adelantada.</p><main>'+''.join(sections)+'</main><p>Criterios: '+escape(package['criteria']['source_reference'])+'</p><p>Son criterios declarados; no se acredita un mínimo normativo. Este estudio no evalúa armónicos, resonancia, transitorios ni selecciona protecciones del banco. Las cargas PQ que salen de Vminpu/Vmaxpu se identifican y no se aceptan como representación PQ.</p><p><a href="Results.json">Resultados y balances por elemento</a> · <a href="Inputs.json">Datos explícitos</a> · <a href="Integrity.json">Integridad</a></p></body></html>'


def execute(package,directory):
    readiness=validate(package)
    if not readiness['ready_for_execution']:return {'status':'BLOCKED_REACTIVE_COMPENSATION_INPUTS','readiness':readiness,'results':[],'professional_emission':False}
    parent=network._parent_signature();folder=Path(directory).expanduser().resolve()
    try:folder.mkdir(parents=True,exist_ok=False)
    except OSError as exc:return {'status':'BLOCKED_OUTPUT_DIRECTORY','message':str(exc),'results':[],'professional_emission':False}
    (folder/'Inputs.json').write_text(json.dumps(package,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    results=[];records=[]
    for scenario in package['scenarios']:
        row={'id':scenario['id'],'load_multiplier':scenario['load_multiplier'],'source_reference':scenario['source_reference']}
        try:
            engine,commands=_create_engine(package,scenario)
            before=_measure(engine,package)
            for bank in package['banks']:
                for i,state in enumerate(scenario['bank_states'][bank['id']],1):
                    command=f"Edit Capacitor.rc_{bank['id']}_s{i} States=[{state}]"
                    commands.append(command);engine(command)
            after=_measure(engine,package)
            observed={b['id']:b['states'] for b in after.get('banks',[])}
            if after.get('results_valid') and observed!=scenario['bank_states']:after.update(results_valid=False,overload_evaluation='NOT_EVALUABLE',state_verification_failed=True)
            row.update(before=before,after=after,criteria=_criteria(after,package['criteria']))
            row['comparison_valid']=bool(before.get('results_valid') and after.get('results_valid'))
            row['delta']={'source_kvar':after['source']['q_kvar']-before['source']['q_kvar'],'network_losses_kw':after['network_losses_kw']-before['network_losses_kw']} if row['comparison_valid'] else None
            records.append({'id':scenario['id'],'load_multiplier':scenario['load_multiplier'],'commands':commands})
        except Exception as exc:row.update(error=f'{type(exc).__name__}: {exc}',comparison_valid=False,criteria={'evaluated':False,'passed':False},after={'converged':False,'results_valid':False,'overload_evaluation':'NOT_EVALUABLE'})
        results.append(row)
    unchanged=network._parent_signature()==parent
    recommendations=[]
    for multiplier in sorted({s['load_multiplier'] for s in package['scenarios']}):
        accepted=[r for r in results if r['load_multiplier']==multiplier and r['comparison_valid'] and r['criteria']['passed'] and unchanged]
        accepted.sort(key=lambda r:(sum(b['nominal_connected_kvar'] for b in r['after']['banks']),r['after']['network_losses_kw']))
        recommendations.append({'load_multiplier':multiplier,'selected_scenario_id':accepted[0]['id'] if accepted else None,'basis':'SMALLEST_CONNECTED_NOMINAL_KVAR_AMONG_EVALUATED_PASSING_SCENARIOS_ONLY'})
    result={'status':'REACTIVE_COMPENSATION_COMPLETED' if unchanged and all(r['comparison_valid'] for r in results) else 'REACTIVE_COMPENSATION_PARTIAL_OR_INVALID','engine':'OpenDSS','engine_version':dss.Basic.Version(),'contract':contract(),'results':results,'recommendations':recommendations,'parent_model_mutated':not unchanged,'professional_emission':False}
    (folder/'Execution.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
    (folder/'Results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    (folder/'Informe.html').write_text(_render_html(package,results),encoding='utf8')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}
    dependencies=[Path(__file__),Path(network.__file__),Path(professional_data.__file__)]
    (folder/'Integrity.json').write_text(json.dumps({'files_sha256':hashes,'adapter_sources_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in dependencies}},indent=2),encoding='utf8')
    return {**result,'output_directory':str(folder),'files_sha256':hashes}


def register(mcp):
    @mcp.tool()
    def obtener_contrato_compensacion_reactiva() -> dict:
        """Alcance estático de bancos por etapas con OpenDSS; no armónicos ni control automático."""
        return contract()
    @mcp.tool()
    def validar_compensacion_reactiva(paquete_estudio: dict) -> dict:
        """Revisa red, etapas, demanda, criterios y límites explícitos sin resolver."""
        return validate(paquete_estudio)
    @mcp.tool()
    def ejecutar_compensacion_reactiva(paquete_estudio: dict, directorio_salida: str) -> dict:
        """Compara sin/con banco a igual demanda en OpenDSS aislado; guarda informe y trazabilidad."""
        return execute(paquete_estudio,directorio_salida)
