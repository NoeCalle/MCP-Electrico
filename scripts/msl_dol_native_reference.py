"""Test-only execution of the original, unmodified MSL IMC_DOL example.

This wraps the original class; it does not call the MCP model builder or add
electrical equations. Parameters explicitly specialize the example to no load
so its native quadratic load is exactly equivalent to the admitted zero table.
"""
import json
import os
from pathlib import Path
import subprocess

ORIGINAL = 'Modelica.Electrical.Machines.Examples.InductionMachines.IMC_DOL'
SOURCE = 'Modelica/Electrical/Machines/Examples/InductionMachines/IMC_DOL.mo'


def build_reference(connection, line_voltage, load_inertia=.29, temperature=293.15):
    terminal = 'D' if connection == 'delta' else 'Y'
    return f'''within;
model NativeDOLReference
  extends {ORIGINAL}(
    VNominal={line_voltage:.17g}, fNominal=50, tStart1=0.1,
    TLoad=0, JLoad={load_inertia:.17g},
    terminalBox(terminalConnection="{terminal}"),
    idealCloser(Ron=fill(1e-6,3),Goff=fill(1e-5,3)),
    aimc(TsRef={temperature:.17g}, TrRef={temperature:.17g},
         TsOperational={temperature:.17g},TrOperational={temperature:.17g}));
  output Real m0speed=aimc.wMechanical;
  output Real m0torque=aimc.tauElectrical;
  output Real m0ia=currentQuasiRMSSensor.CurrentSensor1.i[1];
  output Real m0ib=currentQuasiRMSSensor.CurrentSensor1.i[2];
  output Real m0ic=currentQuasiRMSSensor.CurrentSensor1.i[3];
  output Real m0vab=terminalBox.plugSupply.pin[1].v-terminalBox.plugSupply.pin[2].v;
  output Real m0vbc=terminalBox.plugSupply.pin[2].v-terminalBox.plugSupply.pin[3].v;
  output Real m0vca=terminalBox.plugSupply.pin[3].v-terminalBox.plugSupply.pin[1].v;
  output Real m0busvab=sineVoltage.plug_p.pin[1].v-sineVoltage.plug_p.pin[2].v;
  output Real m0busvbc=sineVoltage.plug_p.pin[2].v-sineVoltage.plug_p.pin[3].v;
  output Real m0busvca=sineVoltage.plug_p.pin[3].v-sineVoltage.plug_p.pin[1].v;
  output Boolean m0bypass=false;
  output Real m0vRef=1;
end NativeDOLReference;
'''


def execute_native(runtime, output, connection, line_voltage, load_inertia=.29, temperature=293.15):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    compiler=Path(runtime['executable']);library=Path(runtime['library'])
    env=dict(os.environ,PYTHONUTF8='1',OPENMODELICAHOME=str(compiler.parent.parent),
             APPDATA=str(output),MODELICAPATH=str(library))
    env['PATH']=os.pathsep.join([str(compiler.parent),str(compiler.parent.parent/'tools/msys/ucrt64/bin'),env.get('PATH','')])
    source=output/'NativeDOLReference.mo'
    source.write_text(build_reference(connection,line_voltage,load_inertia,temperature),encoding='utf8')
    loads='\n'.join(f'loadFile("{(library/p).as_posix()}");' for p in ['ModelicaServices/package.mo','Complex.mo','Modelica/package.mo'])
    script=output/'Native.mos'
    script.write_text(loads+f'\nloadFile("{source.as_posix()}");\ngetErrorString();\nbuildModel(NativeDOLReference,stopTime=1.5,numberOfIntervals=30000,tolerance=1e-8,outputFormat="csv",fileNamePrefix="Native",variableFilter="time|m0(speed|torque|ia|ib|ic|vab|vbc|vca|busvab|busvbc|busvca|bypass|vRef)");\ngetErrorString();\n',encoding='utf8')
    records=[]
    def run(command):
        p=subprocess.run(command,cwd=output,env=env,capture_output=True,text=True,encoding='utf8',errors='replace',stdin=subprocess.DEVNULL,timeout=240)
        records.append({'command':command,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        (output/'Native-execution.json').write_text(json.dumps(records,indent=2),encoding='utf8')
        if p.returncode:raise RuntimeError('Native MSL execution failed: '+p.stdout[-2000:])
        return p
    run([str(compiler),str(script)])
    binary=output/('Native.exe' if os.name=='nt' else 'Native')
    if not binary.is_file():raise RuntimeError('Native MSL compilation failed; inspect Native-execution.json')
    csv=output/'Native.csv'
    p=run([str(binary),'-s=dassl','-r='+str(csv),'-tolerance=1e-8','-maxStepSize=2.5e-5','-stepSize=2.5e-5'])
    if not csv.is_file() or 'The simulation finished successfully.' not in p.stdout:
        raise RuntimeError('Native MSL incomplete simulation')
    return csv
