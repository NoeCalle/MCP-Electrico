"""Test reference inheriting MSL SoftStarter, with documented specializations.

The original FundamentalWave machine and converter/control connections remain
inherited. Added snubber and bypass use native MSL components. This is a test
oracle, never a production backend or a manufacturer controller model.
"""
import json
import os
from pathlib import Path
import subprocess
import re

ORIGINAL = 'Modelica.Electrical.PowerConverters.Examples.ACAC.SoftStarter'
SOURCE = 'Modelica/Electrical/PowerConverters/Examples/ACAC/SoftStarter.mo'
ALIASES = 'speed|torque|ia|ib|ic|vab|vbc|vca|busvab|busvbc|busvca|bypass|vRef'


def verify_filter_pole(stdout, tau):
    match=re.search(r'filter\.r\[1\]=([-+0-9.eE]+)',stdout)
    if match is None:raise ValueError('Native filter pole was not emitted')
    actual=float(match.group(1));expected=-1/tau
    if abs(actual-expected)>abs(expected)*1e-10:
        raise ValueError(f'Native filter pole mismatch: {actual} versus {expected}')
    return {'actual_pole_per_s':actual,'expected_pole_per_s':expected,
            'native_normalization':False,'passed':True}


def build_reference(package):
    from math import pi
    n = package['network']; motor = package['motors'][0]
    c = motor['starting']['controller']; e = motor['electrical']
    if n['r_ohm'] or n['x_ohm'] or motor['connection'] != 'delta':
        raise ValueError('Native original reference admits ideal source, delta only')
    phase = ','.join(format(n['angle_deg']*pi/180-2*pi*k/3,'.17g') for k in range(3))
    return f'''within;
model NativeSCRReference
  extends {ORIGINAL}(
    VNominal={n['kv_ll']*1000*n['pu']:.17g}, fNominal={n['frequency_hz']:.17g},
    INominal={c['rated_current_a']:.17g}, TLoad=0,
    JLoad={motor['mechanical']['load_inertia_kg_m2']:.17g},
    sineVoltage(phase={{{phase}}}),
    filter(order=1, normalized=false, f_cut={1/(2*pi*c['current_filter_tau_s']):.17g},
      init=Modelica.Blocks.Types.Init.InitialOutput,y_start=0),
    softStartControl(tRampUp={c['ramp_up_s']:.17g},vStart={c['initial_voltage_pu']:.17g},
      iMax={c['maximum_current_pu']:.17g},iMin={c['resume_current_pu']:.17g},
      tRampDown={c['ramp_down_s']:.17g},vRef(start=0,fixed=true)),
    booleanTable(table={{{motor['starting']['time_s']:.17g},100}}));
  Modelica.Electrical.Polyphase.Basic.Resistor snubberR(m=3,
    R=fill({c['snubber_resistance_ohm']:.17g},3),alpha=fill(0,3));
  Modelica.Electrical.Polyphase.Basic.Capacitor snubberC(m=3,
    C=fill({c['snubber_capacitance_f']:.17g},3),v(each start=0,each fixed=true));
  Modelica.Electrical.Analog.Ideal.IdealClosingSwitch bypassSwitch[3](each Ron=1e-6,each Goff=1e-5);
  Modelica.Blocks.MathBoolean.OnDelay bypassDelay(delayTime={c['bypass_hold_s']:.17g});
  output Boolean m0bypass(start=false,fixed=true);
  output Real m0speed=imc.wMechanical;
  output Real m0torque=imc.tauElectrical;
  output Real m0ia=multiSensor.i[1];
  output Real m0ib=multiSensor.i[2];
  output Real m0ic=multiSensor.i[3];
  output Real m0vab=terminalBox.plugSupply.pin[1].v-terminalBox.plugSupply.pin[2].v;
  output Real m0vbc=terminalBox.plugSupply.pin[2].v-terminalBox.plugSupply.pin[3].v;
  output Real m0vca=terminalBox.plugSupply.pin[3].v-terminalBox.plugSupply.pin[1].v;
  output Real m0busvab=sineVoltage.plug_p.pin[1].v-sineVoltage.plug_p.pin[2].v;
  output Real m0busvbc=sineVoltage.plug_p.pin[2].v-sineVoltage.plug_p.pin[3].v;
  output Real m0busvca=sineVoltage.plug_p.pin[3].v-sineVoltage.plug_p.pin[1].v;
  output Real m0vRef=softStartControl.vRef;
equation
  connect(triac.plug_p,snubberR.plug_p);
  connect(snubberR.plug_n,snubberC.plug_p);
  connect(snubberC.plug_n,triac.plug_n);
  connect(bypassSwitch.p,triac.plug_p.pin);
  connect(bypassSwitch.n,triac.plug_n.pin);
  bypassDelay.u=(m0vRef>=1-1e-8 and m0speed>={c['bypass_speed_fraction']*2*pi*n['frequency_hz']/e['pole_pairs']:.17g});
  when bypassDelay.y then m0bypass=true; end when;
  for k in 1:3 loop bypassSwitch[k].control=m0bypass; end for;
end NativeSCRReference;
'''


def execute_native(runtime, output, package):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    compiler=Path(runtime['executable']);library=Path(runtime['library'])
    env=dict(os.environ,PYTHONUTF8='1',OPENMODELICAHOME=str(compiler.parent.parent),
             APPDATA=str(output),MODELICAPATH=str(library))
    env['PATH']=os.pathsep.join([str(compiler.parent),str(compiler.parent.parent/'tools/msys/ucrt64/bin'),env.get('PATH','')])
    source=output/'NativeSCRReference.mo';source.write_text(build_reference(package),encoding='utf8')
    sim=package['simulation'];step=sim['output_step_s']/2;tol=sim['solver_tolerance']/10
    loads='\n'.join(f'loadFile("{(library/p).as_posix()}");' for p in ['ModelicaServices/package.mo','Complex.mo','Modelica/package.mo'])
    script=output/'Native.mos'
    script.write_text(loads+f'\nloadFile("{source.as_posix()}");\ngetErrorString();\nbuildModel(NativeSCRReference,stopTime={sim["duration_s"]},numberOfIntervals={int(round(sim["duration_s"]/step))},tolerance={tol},outputFormat="csv",fileNamePrefix="Native",variableFilter="time|m0({ALIASES})");\ngetErrorString();\n',encoding='utf8')
    records=[]
    def run(command):
        try:
            p=subprocess.run(command,cwd=output,env=env,capture_output=True,text=True,encoding='utf8',errors='replace',stdin=subprocess.DEVNULL,timeout=sim['timeout_s'])
        except subprocess.TimeoutExpired as exc:
            def decode(value):return value.decode('utf8',errors='replace') if isinstance(value,bytes) else (value or '')
            records.append({'command':command,'returncode':None,'execution_status':'TIMEOUT',
                            'stdout':decode(exc.stdout),'stderr':decode(exc.stderr),'timeout_s':sim['timeout_s']})
            (output/'Native-execution.json').write_text(json.dumps(records,indent=2),encoding='utf8')
            raise
        records.append({'command':command,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        (output/'Native-execution.json').write_text(json.dumps(records,indent=2),encoding='utf8')
        if p.returncode:raise RuntimeError('Native MSL execution failed: '+p.stdout[-2000:])
        return p
    run([str(compiler),str(script)])
    binary=output/('Native.exe' if os.name=='nt' else 'Native')
    if not binary.is_file():raise RuntimeError('Native MSL compilation failed; inspect Native-execution.json')
    # Initialization-only probe: verify the original Filter's actual pole.
    # MSL normalized=true means -3.0 dB, not half power (-3.0103 dB), so even
    # order=1 does not exactly give FirstOrder T=1/(2*pi*f_cut).
    probe=run([str(binary),'-s=dassl','-nls=newton','-stopTime=0.000001',
               '-stepSize=0.000001','-r='+str(output/'Filter-initialization.csv'),'-output=filter.r[1]'])
    pole=verify_filter_pole(probe.stdout,package['motors'][0]['starting']['controller']['current_filter_tau_s'])
    (output/'Native-filter-pole.json').write_text(json.dumps(pole,indent=2),encoding='utf8')
    csv=output/'Native.csv'
    p=run([str(binary),'-s=dassl','-nls=newton','-r='+str(csv),f'-tolerance={tol}',f'-maxStepSize={sim["maximum_internal_step_s"]/2}',f'-stepSize={step}'])
    if not csv.is_file() or 'The simulation finished successfully.' not in p.stdout:
        raise RuntimeError('Native MSL incomplete simulation')
    return csv
