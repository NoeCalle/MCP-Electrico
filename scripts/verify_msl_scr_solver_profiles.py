"""Investigate native OpenModelica numerical profiles using an MCP-built case.

This is a test utility, not an alternate production solver or a fallback.
It never modifies the compiled reference, MSL or module qualification.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from mcp_electrico import modelica_motor_adapter as adapter


def verify(reference, output, solvers, timeout):
    reference=reference.resolve();output=output.resolve()
    package=json.loads((reference/'Inputs.json').read_text(encoding='utf8'))
    assert [m['starting']['method'] for m in package['motors']]==['SCR']
    model=reference/'MCPMSLMotorStudy.mo'
    assert model.read_text(encoding='utf8')==adapter.build_model(package), 'Reference does not match current adapter'
    rt=adapter.runtime();assert rt['ready'],rt
    output.mkdir(parents=True,exist_ok=False)
    exe='MotorStudy.exe' if sys.platform=='win32' else 'MotorStudy'
    files=[p for p in reference.iterdir() if p.name in [exe,'MotorStudy_init.xml','MotorStudy_info.json'] or p.suffix=='.bin']
    assert (reference/exe).is_file()
    source_hashes={p.name:sha256(p.read_bytes()).hexdigest() for p in files+[model,reference/'Inputs.json']}
    sim=package['simulation']
    windows=list(dict.fromkeys([min(.2,sim['duration_s']),sim['duration_s']]))
    plan={'test_only':True,'production_fallback':False,'qualification_automatically_changed':False,
          'reference_directory':str(reference),'reference_source_sha256':source_hashes,'runtime':rt,
          'profile_timeout_s':timeout,'integrator':'dassl','solvers':solvers,
          'observation_windows_s':windows,
          'required_completion':'EXIT_ZERO_SUCCESS_MARKER_AND_FINAL_TRACE_TIME_EQUALS_REQUESTED_STOP',
          'failed_trial_design_assessment':'NOT_EVALUATED'}
    (output/'Predeclared-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf8')
    results=[]
    for solver in solvers:
        for stop in windows:
            folder=output/f'{solver}-{stop:g}s';folder.mkdir()
            for file in files:shutil.copyfile(file,folder/file.name)
            trace=folder/'Trial.csv'
            cmd=[str(folder/exe),'-s=dassl','-nls='+solver,'-stopTime='+str(stop),'-r='+str(trace),
                 '-tolerance='+str(sim['solver_tolerance']),'-maxStepSize='+str(sim['maximum_internal_step_s']),
                 '-stepSize='+str(sim['output_step_s'])]
            record=adapter._run(cmd,folder,adapter._environment(rt['executable']),timeout)
            last=adapter._trace_endpoint(trace)
            completed=(record['returncode']==0 and 'The simulation finished successfully.' in record['stdout']
                       and last is not None and abs(last-stop)<1e-8)
            result={'solver':solver,'stop_time_s':stop,'completed':completed,'last_emitted_time_s':last,
                    'execution_status':record['execution_status'],'design_assessment':'NOT_EVALUATED_TEST_ONLY',
                    'full_observation_window':stop==sim['duration_s']}
            (folder/'Execution.json').write_text(json.dumps(record,indent=2),encoding='utf8')
            results.append(result);print(json.dumps(result),flush=True)
    assert source_hashes=={p.name:sha256(p.read_bytes()).hexdigest() for p in files+[model,reference/'Inputs.json']}
    (output/'Results.json').write_text(json.dumps({'plan':plan,'trials':results,'technical_qualification_unchanged':True},indent=2),encoding='utf8')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--solvers',nargs='+',choices=['kinsol','mixed','homotopy','hybrid'],default=['kinsol'])
    p.add_argument('--timeout',type=float,default=90)
    args=p.parse_args()
    if not 0<args.timeout<=600:p.error('timeout must be in (0,600] seconds')
    verify(args.reference,args.output,args.solvers,args.timeout)
