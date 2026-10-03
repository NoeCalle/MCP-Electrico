import hashlib,json,os,shutil,subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
p=argparse.ArgumentParser()
p.add_argument('--workspace',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--runtime',type=Path,required=True)
p.add_argument('--msl-root',type=Path,required=True)
a=p.parse_args()
RUN=a.workspace.resolve()
OUT=a.output.resolve()
OUT.mkdir(parents=True,exist_ok=True)
runtime=a.runtime.resolve()
env=dict(os.environ,PATH=str(runtime/'bin')+';'+str(runtime/'tools/msys/ucrt64/bin')+';'+os.environ['PATH'])
compiler=subprocess.check_output([str(runtime/'bin/omc.exe'),'--version'],env=env,text=True).strip()
if compiler!='OpenModelica v1.27.1 (64-bit)':
    raise ValueError('Unsupported external compiler version')
if 'version="4.0.0"' not in (a.msl_root/'Modelica/package.mo').read_text(encoding='utf8'):
    raise ValueError('Modelica Standard Library 4.0.0 required')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
records=[]
def execute(case,refined):
    name=f'{case}-Modelica'+('-refined' if refined else '')+'.csv'
    args=[str(RUN/case/'Reference.exe'),'-r='+str(OUT/name)]
    if refined:args+=['-stepSize=2.5e-5','-tolerance=1e-9','-maxStepSize=0.00005']
    p=subprocess.run(args,cwd=RUN/case,env=env,capture_output=True,text=True,timeout=180)
    if p.returncode or 'The simulation finished successfully.' not in p.stdout:
        raise RuntimeError(p.stdout+p.stderr)
    return dict(case=case,refined=refined,command=args,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr,
                executable_sha256=digest(RUN/case/'Reference.exe'),setup_sha256=digest(RUN/case/'Reference_init.xml'))
with ThreadPoolExecutor(max_workers=2) as pool:
    futures=[pool.submit(execute,c,f) for c in ('DOL','SCR') for f in (False,True)]
    records=[f.result() for f in futures]
for case in ('DOL','SCR'):
    shutil.copy2(RUN/'candidate'/f'{case}.json',OUT/f'{case}-MCP.json')
    shutil.copy2(RUN/case/f'MCPReference{case}.mo',OUT/f'{case}.mo')
shutil.copy2(RUN/'candidate/Inputs.json',OUT/'Inputs.json')
library=a.msl_root.resolve()
sources=['Modelica/Electrical/Machines/BasicMachines/InductionMachines/IM_SquirrelCage.mo',
         'Modelica/Electrical/Machines/Interfaces/PartialBasicInductionMachine.mo',
         'Modelica/Electrical/Machines/Interfaces/PartialBasicMachine.mo',
         'Modelica/Electrical/Machines/BasicMachines/Components/AirGapS.mo',
         'Modelica/Electrical/Machines/BasicMachines/Components/SquirrelCage.mo',
         'Modelica/Electrical/PowerConverters/ACAC/PolyphaseTriac.mo',
         'Modelica/Electrical/PowerConverters/ACAC/SinglePhaseTriac.mo',
         'Modelica/Electrical/PowerConverters/ACDC/Control/Signal2mPulse.mo',
         'Modelica/Mechanics/Rotational/Components/OneWayClutch.mo',
         'Modelica/Electrical/PowerConverters/Examples/ACAC/SoftStarter.mo']
source_data=dict(library='Modelica Standard Library 4.0.0',source_url='https://github.com/modelica/ModelicaStandardLibrary/tree/v4.0.0',
                 zip_sha256=None,
                 components={p:digest(library/p) for p in sources},unmodified_library=True,
                 wrapper_author='MCP Electrico project; parameter and boundary adapter, not published MSL example')
(OUT/'Library-sources.json').write_text(json.dumps(source_data,indent=2),encoding='utf8')
execution=dict(compiler=compiler,library='4.0.0',
               runs_successful=['published','DOL','SCR','DOL_refined','SCR_refined'],
               runs=records,published_example_csv_sha256=digest(RUN/'published/MSL_SoftStarter_res.csv'),
               published_example_stop_time_s=5,published_example_warning='Controller vRef min/max roundoff warning at t=4.498110 s; solver completed.',
               installer_verified_md5=None,
               library_loading_warning='Official unpatched ModelicaServices and automatic package index network unavailable; explicitly loaded local Modelica/Complex/ModelicaServices 4.0.0; used models compiled and simulated.',
               initialization_warning='Compiler reports auxiliary initial conditions defaulted; motor stator/rotor current, shaft position and speed explicitly initialized to zero.',
               boundary_scope='Balanced supply RMS amplitude and firing-angle histories replayed linearly; source phase angles fixed; bypass forced at MCP time, not controlled by reference speed.')
(OUT/'Execution.json').write_text(json.dumps(execution,indent=2),encoding='utf8')
names=['Inputs.json','DOL-MCP.json','SCR-MCP.json','DOL-Modelica.csv','SCR-Modelica.csv',
       'DOL-Modelica-refined.csv','SCR-Modelica-refined.csv','DOL.mo','SCR.mo','Library-sources.json','Execution.json']
provenance=dict(schema='MCP_ELECTRICO_EXTERNAL_MOTOR_BENCHMARK_V1',fixture_id='MCP-REF-DYNAMIC-RMS-01',
                sha256={n:digest(OUT/n) for n in names})
(OUT/'Provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf8')
print(json.dumps(dict(ok=True,evidence=str(OUT),recorded_runs=len(records))))

