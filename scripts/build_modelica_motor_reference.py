import json
from pathlib import Path
import argparse
p=argparse.ArgumentParser(description='Build wrappers around unmodified MSL components for the synthetic motor reference')
p.add_argument('--output',type=Path,required=True)
p.add_argument('--msl-root',type=Path,required=True)
a=p.parse_args()
BASE=a.output.resolve()
MSL=a.msl_root.resolve().as_posix()
if 'version="4.0.0"' not in (a.msl_root/'Modelica/package.mo').read_text(encoding='utf8'):
    raise ValueError('Modelica Standard Library 4.0.0 required')
inputs=json.loads((BASE/'candidate/Inputs.json').read_text())
examples=Path(__file__).resolve().parents[1]/'examples'
for key,file in [('manifest','p13_dynamic_rms_manifest.json'),('package','p13_dynamic_rms_package.json'),('options','p13_dynamic_rms_options.json'),('starter','p13_soft_starter_controller.json')]:
    if inputs.get(key)!=json.loads((examples/file).read_text(encoding='utf8')):
        raise ValueError('This reference recipe supports only the declared synthetic fixture')
published=BASE/'published';published.mkdir(exist_ok=True)
loader='\n'.join(f'loadFile("{MSL}/{file}");' for file in ('ModelicaServices/package.mo','Complex.mo','Modelica/package.mo'))
(published/'run.mos').write_text(loader+'\ngetErrorString();\nsimulate(Modelica.Electrical.PowerConverters.Examples.ACAC.SoftStarter,stopTime=5,numberOfIntervals=50000,tolerance=1e-7,outputFormat="csv",fileNamePrefix="MSL_SoftStarter",variableFilter="time|imc.wMechanical|imc.tauElectrical|currentQuasiRMSSensor.I");\ngetErrorString();\n',encoding='utf8')
for case in ('DOL','SCR'):
    data=json.loads((BASE/f'candidate/{case}.json').read_text())['results'][0]
    rows=data['trajectory']
    table=';\n'.join(','.join(format(x,'.17g') for x in (r['time_s'],r.get('supply_voltage_pu',r['voltage_pu']),r.get('firing_angle_rad',0))) for r in rows)
    folder=BASE/case;folder.mkdir(exist_ok=True)
    bypass=data.get('bypass_time_s',1e30)
    model=f'''within;
model MCPReference{case}
  import pi=Modelica.Constants.pi;
  Modelica.Blocks.Sources.CombiTimeTable boundary(table=[{table}], columns={{2,3}}, smoothness=Modelica.Blocks.Types.Smoothness.LinearSegments);
  Modelica.Electrical.Polyphase.Sources.SignalVoltage source(m=3);
  Modelica.Electrical.Polyphase.Basic.Star sourceStar(m=3);
  Modelica.Electrical.Analog.Basic.Ground ground;
  Modelica.Electrical.Polyphase.Sensors.CurrentSensor lineSensor(m=3);
  Modelica.Electrical.Machines.Utilities.TerminalBox terminal(terminalConnection="D");
  Modelica.Electrical.Machines.BasicMachines.InductionMachines.IM_SquirrelCage motor(
    p=2, fsNominal=60, Rs=0.07, Rr=0.1, Lssigma=0.0008, Lszero=0.0008, Lrsigma=0.0008, Lm=0.008,
    TsRef=348.15,TrRef=348.15,TsOperational=348.15,TrOperational=348.15,alpha20s=0,alpha20r=0,
    Jr=2.5, Js=2.5, useSupport=false, useThermalPort=false,
    frictionParameters(PRef=0),statorCoreParameters(PRef=0,VRef=480),strayLoadParameters(PRef=0,IRef=800),
    phiMechanical(start=0,fixed=true),wMechanical(start=0,fixed=true));
  Modelica.Mechanics.Rotational.Components.Inertia loadInertia(J=7.5);
  Modelica.Mechanics.Rotational.Sources.Torque loadTorque;
  Modelica.Mechanics.Rotational.Components.Fixed fixed;
  Modelica.Mechanics.Rotational.Components.OneWayClutch restStop(fn_max=1, f_normalized=0);
  output Real speed=motor.wMechanical;
  output Real torque=motor.tauElectrical;
  output Real ia=lineSensor.i[1];
  output Real ib=lineSensor.i[2];
  output Real ic=lineSensor.i[3];
  output Real alpha=boundary.y[2];
  output Real supply_pu=boundary.y[1];
'''
    if case=='SCR':
        model+='''  Modelica.Electrical.PowerConverters.ACAC.PolyphaseTriac triac(m=3, useHeatPort=false, triac(each Ron=1e-5,each Goff=1e-5,each Vknee=0));
  Modelica.Electrical.PowerConverters.ACDC.Control.Signal2mPulse pulse(m=3,useConstantFiringAngle=false,useFilter=false,f=60);
  Modelica.Electrical.Analog.Ideal.IdealClosingSwitch bypass[3](each Ron=1e-6,each Goff=1e-9);
'''
    model+='''initial equation
  motor.is={0,0,0};
  motor.ir={0,0};
equation
  for k in 1:3 loop
    source.v[k]=sqrt(2)*480/sqrt(3)*supply_pu*sin(2*pi*60*time-2*pi*(k-1)/3);
  end for;
  connect(source.plug_n,sourceStar.plug_p);
  connect(sourceStar.pin_n,ground.p);
  connect(lineSensor.plug_n,terminal.plugSupply);
  connect(terminal.plug_sp,motor.plug_sp);
  connect(terminal.plug_sn,motor.plug_sn);
  connect(motor.flange,loadInertia.flange_a);
  connect(loadInertia.flange_b,loadTorque.flange);
  connect(fixed.flange,restStop.flange_a);
  connect(restStop.flange_b,motor.flange);
  loadTorque.tau=-(if speed < 100 then 100+2*speed else 300+3*(speed-100));
'''
    if case=='SCR':
        model+=f'''  connect(source.plug_p,triac.plug_p);
  connect(triac.plug_n,lineSensor.plug_p);
  pulse.v=source.v;
  pulse.firingAngle=alpha;
  connect(pulse.fire_p,triac.fire1);
  connect(pulse.fire_n,triac.fire2);
  connect(bypass.p,triac.plug_p.pin);
  connect(bypass.n,triac.plug_n.pin);
  for k in 1:3 loop
    bypass[k].control=time >= {bypass};
  end for;
'''
    else:model+='  connect(source.plug_p,lineSensor.plug_p);\n'
    model+=f'end MCPReference{case};\n'
    (folder/f'MCPReference{case}.mo').write_text(model,encoding='utf8')
    mos='\n'.join(f'loadFile("{MSL}/{f}");' for f in ('ModelicaServices/package.mo','Complex.mo','Modelica/package.mo'))
    mos+=f'\nloadFile("{(folder/f"MCPReference{case}.mo").as_posix()}");\ngetErrorString();\n'
    mos+=f'simulate(MCPReference{case}, stopTime=4, numberOfIntervals=80000, tolerance=1e-7, outputFormat="csv", fileNamePrefix="Reference", variableFilter="time|speed|torque|ia|ib|ic|alpha|supply_pu");\ngetErrorString();\n'
    (folder/'run.mos').write_text(mos,encoding='utf8')
print('Generated external component wrappers DOL/SCR')


