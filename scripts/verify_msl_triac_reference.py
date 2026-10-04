"""Isolated MSL converter test against the resistive phase-angle integral.

No motor is represented; the algebraic oracle is verification-only.
The operational closed-loop motor studies are tested separately over MCP.
"""
import argparse
import csv
import hashlib
import json
from math import pi,sin,sqrt
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from mcp_electrico import modelica_motor_adapter as adapter

def run(output):
    import numpy as np
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    runtime=adapter.runtime();assert runtime['ready'],runtime
    library=Path(runtime['library']);compiler=runtime['executable']
    # Connections of existing components only, no new device equations.
    model='''within;
model TriacReference
  Modelica.Electrical.Polyphase.Sources.SineVoltage source(m=3,V=fill(100*sqrt(2),3),f=fill(60,3),phase={0.2617993877991494,0.2617993877991494-2*Modelica.Constants.pi/3,0.2617993877991494-4*Modelica.Constants.pi/3});
  Modelica.Electrical.Polyphase.Basic.Star sourceStar(m=3);
  Modelica.Electrical.Polyphase.Basic.Star loadStar(m=3);
  Modelica.Electrical.Analog.Basic.Ground ground;
  Modelica.Electrical.PowerConverters.ACAC.PolyphaseTriac triac(m=3,useHeatPort=false,triac(each Ron=1e-5,each Goff=1e-5,each Vknee=0));
  Modelica.Electrical.PowerConverters.ACDC.Control.Signal2mPulse pulse(m=3,useConstantFiringAngle=true,constantFiringAngle=Modelica.Constants.pi/3,useFilter=false,f=60);
  Modelica.Electrical.Polyphase.Basic.Resistor load(m=3,R=fill(25,3),alpha=fill(0,3));
  output Real va=load.v[1];
  output Real vb=load.v[2];
  output Real vc=load.v[3];
equation
  connect(source.plug_n,sourceStar.plug_p);
  connect(sourceStar.pin_n,ground.p);
  connect(source.plug_p,triac.plug_p);
  connect(triac.plug_n,load.plug_p);
  connect(load.plug_n,loadStar.plug_p);
  connect(loadStar.pin_n,ground.p);
  pulse.v=source.v;
  connect(pulse.fire_p,triac.fire1);
  connect(pulse.fire_n,triac.fire2);
end TriacReference;
'''
    source=output/'TriacReference.mo';source.write_text(model,encoding='utf8')
    loader='\n'.join(f'loadFile("{adapter._quote(library/f)}");' for f in ('ModelicaServices/package.mo','Complex.mo','Modelica/package.mo'))
    mos=output/'run.mos';mos.write_text(loader+f'\nloadFile("{adapter._quote(source)}");\nbuildModel(TriacReference,stopTime=0.2,numberOfIntervals=20000,tolerance=1e-8,outputFormat="csv",fileNamePrefix="TriacReference",variableFilter="time|va|vb|vc");\ngetErrorString();',encoding='utf8')
    env=adapter._environment(compiler);env['APPDATA']=str(output);env['MODELICAPATH']=str(library)
    records=[adapter._run([compiler,str(mos)],output,env,180)]
    executable=output/('TriacReference.exe' if sys.platform=='win32' else 'TriacReference')
    assert executable.is_file(),records[0]
    expected=100*sqrt(1-(pi/3)/pi+sin(2*pi/3)/(2*pi))
    metrics=[]
    for tag,dt,tol in [('Nominal',1e-5,1e-8),('Refined',5e-6,1e-9)]:
        file=output/(tag+'.csv')
        record=adapter._run([str(executable),'-r='+str(file),'-s=dassl','-nls=newton',f'-maxStepSize={dt}',f'-stepSize={dt}',f'-tolerance={tol}'],output,env,180)
        records.append(record);assert record['returncode']==0 and 'The simulation finished successfully.' in record['stdout'],record
        with file.open(encoding='utf8') as stream:rows=list(csv.DictReader(stream))
        t=np.array([float(r['time']) for r in rows]);sel=(t>=.1)&(t<=.2)
        times=t[sel];assert abs(times[0]-.1)<1e-9 and abs(times[-1]-.2)<1e-9
        values=[]
        for key in ('va','vb','vc'):
            v=np.array([float(r[key]) for r in rows])[sel]
            rms=sqrt(float(np.sum(np.diff(times)*(v[:-1]**2+v[:-1]*v[1:]+v[1:]**2)/3))/.1)
            values.append(rms)
        errors=[abs(v/expected-1) for v in values]
        assert max(errors)<.001,errors
        metrics.append({'trace':tag,'phase_rms_v':values,'relative_error':errors})
    result={'scope':'THREE_INDEPENDENT_RESISTIVE_PHASES_WITH_NEUTRAL_NO_MOTOR','formula':'Vrms/V= sqrt(1-alpha/pi+sin(2*alpha)/(2*pi))','firing_angle_deg':60,'phase_rms_supply_v':100,'resistance_ohm':25,'expected_rms_v':expected,'illustrative_relative_tolerance':.001,'metrics':metrics,'oracle_production_backend':False,'library_modified':False,'runtime':runtime,'files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.suffix in ('.csv','.mo','.mos')}}
    (output/'Execution.json').write_text(json.dumps(records,indent=2),encoding='utf8')
    (output/'Reference.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps({'ok':True,'expected_rms_v':expected,'metrics':metrics}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
