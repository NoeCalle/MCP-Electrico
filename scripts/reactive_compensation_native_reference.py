"""Test-only native OpenDSS netlist, authored independently of the MCP builder.

Fixed fixture: 13.8/.48 kV, 1500 kVA, explicit winding resistance and taps,
two PQ loads, one feeder, unequal capacitor stages at HV and LV.
"""
from math import sqrt
from opendssdirect import dss


def native_reference(package, scenario, compensated):
    t=package['base_model']['topology']['transformers'][0]
    conn={'Dyn11':('delta','wye','Lead'),'Dyn1':('delta','wye','Lag'),'Yy0':('wye','wye',None)}[t['vector_group']]
    r=5.75/sqrt(65);x=8*r
    engine=dss.NewContext();engine.Basic.AllowChangeDir(False)
    commands=['Clear','New Circuit.native_closure basekv=13.8 frequency=60',
              f'Edit Vsource.source Bus1=utility_13k8 BasekV=13.8 pu=1 angle=0 R1={13.8**2/200/sqrt(101)} X1={10*13.8**2/200/sqrt(101)} BaseFreq=60',
              f'New Transformer.t1 Phases=3 Windings=2 Buses=[utility_13k8,bus_480] Conns=[{conn[0]},{conn[1]}] kVs=[13.8,.48] kVAs=[1500,1500] %Rs=[{r/2},{r/2}] XHL={x} %Noloadloss={100*2/1500} %imag=.8 Taps=[{1+.025*t["tap_pos"]},1] BaseFreq=60'+(f' LeadLag={conn[2]}' if conn[2] else ''),
              'Edit Transformer.t1 Wdg=1 MinTap=.95 MaxTap=1.05 NumTaps=4',
              'New Line.mcc_feeder Bus1=bus_480 Bus2=mcc_480 Phases=3 Length=.03 Units=km R1=.08 X1=.05 C1=0 NormAmps=700 BaseFreq=60']
    mult=scenario['load_multiplier']
    commands.extend([f'New Load.background Bus1=mcc_480 Phases=3 kV=.48 kW={250*mult} kvar={100*mult} Conn=wye Model=1 Vminpu=.5 Vmaxpu=1.5 BaseFreq=60',
                     f'New Load.m01_run Bus1=mcc_480 Phases=3 kV=.48 kW={165*mult} kvar={80*mult} Conn=delta Model=1 Vminpu=.5 Vmaxpu=1.5 BaseFreq=60',
                     'Set VoltageBases=[13.8,.48]','CalcVoltageBases','SetkVBase Bus=utility_13k8 kVLL=13.8','SetkVBase Bus=bus_480 kVLL=.48','SetkVBase Bus=mcc_480 kVLL=.48'])
    for bank in package['banks']:
        for i,kvar in enumerate(bank['steps_kvar']):
            state=scenario['bank_states'][bank['id']][i] if compensated else 0
            commands.append(f'New Capacitor.ref_{bank["id"]}_{i} Bus1={bank["bus"]} Bus2={bank["bus"]}.0.0.0 Phases=3 Conn={bank["connection"]} kV={bank["kv_ll"]} BaseFreq=60 kvar={kvar} R=0 XL=0 States=[{state}]')
    commands.extend(['Set Mode=Snapshot ControlMode=Off Frequency=60 LoadMult=1 Algorithm=Normal Tolerance=1e-10 MaxIterations=100','Solve'])
    for command in commands:engine(command)
    assert engine.Solution.Converged()
    p,q=(-float(v) for v in engine.Circuit.TotalPower())
    voltages={}
    for bus in ['utility_13k8','bus_480','mcc_480']:
        assert engine.Circuit.SetActiveBus(bus)>=0
        voltages[bus]=list(engine.Bus.puVmagAngle()[::2])
    loss_p=loss_q=0.
    for element in ['Line.mcc_feeder','Transformer.t1']:
        engine.Circuit.SetActiveElement(element);lp,lq=engine.CktElement.Losses();loss_p+=lp/1000;loss_q+=lq/1000
    return {'p_kw':p,'q_kvar':q,'voltages':voltages,'losses_kw':loss_p,'losses_kvar':loss_q,'commands':commands}
