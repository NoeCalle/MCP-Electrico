"""TEST ONLY: closed-form balanced impedance circuit, no engine imports.

This oracle is not imported by server.py or any operational adapter.
"""
from copy import deepcopy
from math import sqrt


def reference_package(template, connection='delta', pu=1., frequency=60):
    p=deepcopy(template)
    base=p['base_model']
    base['source'].update(bus='supply',kv_ll=.48,frequency_hz=frequency,pu=pu,scc_max_mva=20,x_r_max=5)
    base['topology']={'buses':['supply','consumer'],'transformers':[],
        'lines':[{'id':'feeder','bus1':'supply','bus2':'consumer','phases':3,'length_km':.1,'r1_ohm_km':.08,'x1_ohm_km':.05,'c1_nf_km':0,'normamps_a':500,'source_reference':'ANALYTIC_TEST_LINE'}],
        'loads':[{'id':'impedance_load','bus':'consumer','phases':3,'kv':.48,'kw':200,'kvar':120,'connection':connection,'model':2,'vminpu':.5,'vmaxpu':1.5,'source_reference':'ANALYTIC_CONSTANT_IMPEDANCE'}]}
    p['banks']=[dict(id='unequal_bank',bus='consumer',phases=3,kv_ll=.525,connection=connection,steps_kvar=[25,50,75],model='IDEAL_NO_REACTOR_NO_LOSSES',source_reference='ANALYTIC_IDEAL_CAPACITORS_AT_RATED_VOLTAGE')]
    p['scenarios']=[dict(id='stages_25_75',load_multiplier=1,bank_states={'unequal_bank':[1,0,1]},source_reference='ANALYTIC_TEST')]
    return p


def analytical_reference(p, compensated=True):
    source=p['base_model']['source'];line=p['base_model']['topology']['lines'][0];load=p['base_model']['topology']['loads'][0];bank=p['banks'][0]
    zabs=source['kv_ll']**2/source['scc_max_mva']
    r=zabs/sqrt(1+source['x_r_max']**2);zs=complex(r,r*source['x_r_max'])
    zl=complex(line['r1_ohm_km'],line['x1_ohm_km'])*line['length_km']
    yload=complex(load['kw'],-load['kvar'])*1000/(load['kv']*1000)**2
    rated_q=sum(v*s for v,s in zip(bank['steps_kvar'],p['scenarios'][0]['bank_states'][bank['id']])) if compensated else 0
    ycap=complex(0,rated_q*1000/(bank['kv_ll']*1000)**2)
    vs=source['pu']*source['kv_ll']*1000/sqrt(3)
    vr=vs/(1+(zs+zl)*(yload+ycap));current=vr*(yload+ycap)
    # Circuit.TotalPower meters the external source terminal, after its
    # Thevenin impedance; internal source losses are not plant losses.
    supplied=3*(vs-zs*current)*current.conjugate()/1000
    return {'voltage_pu':abs(vr)/(load['kv']*1000/sqrt(3)),
            'p_kw':supplied.real,'q_kvar':supplied.imag,'current_a':abs(current),
            'line_losses_kw':3*abs(current)**2*zl.real/1000,
            'injected_kvar':rated_q*(abs(vr)*sqrt(3)/(bank['kv_ll']*1000))**2}
