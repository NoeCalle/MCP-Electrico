"""Read-only comparison with externally executed Modelica motor traces.

This tool does not execute Modelica, certify a trace's producer, or qualify a
device. It verifies the evidence bytes and compares like physical quantities.
The initial recipe is deliberately restricted to the declared synthetic case.
"""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

SCHEMA = 'MCP_ELECTRICO_EXTERNAL_MOTOR_BENCHMARK_V1'
FIXTURE = 'MCP-REF-DYNAMIC-RMS-01'


def trace(path):
    """Keep the last event value at repeated times; never extrapolate a trace."""
    with Path(path).open(encoding='utf8') as stream:
        reader = csv.DictReader(stream)
        names = ['time', 'speed', 'torque', 'ia', 'ib', 'ic', 'alpha', 'supply_pu']
        if set(reader.fieldnames or []) != set(names):
            raise ValueError('EXTERNAL_TRACE_COLUMNS')
        rows = [[float(r[n]) for n in names] for r in reader]
    if not 2 <= len(rows) <= 2_000_000:
        raise ValueError('EXTERNAL_TRACE_SIZE')
    values = np.asarray(rows)
    if not np.isfinite(values).all() or np.any(np.diff(values[:, 0]) < 0):
        raise ValueError('EXTERNAL_TRACE_NONFINITE_OR_REVERSED_TIME')
    keep = np.r_[np.diff(values[:, 0]) > 0, True]
    result = {n: values[keep, k] for k, n in enumerate(names)}
    # Event insertion/restarts can interrupt the nominal output grid. Require
    # at least 80 samples per 60 Hz cycle even across the largest such gap;
    # accuracy is separately measured against the denser external run.
    if np.max(np.diff(result['time'])) > 1/(60*80):
        raise ValueError('EXTERNAL_TRACE_UNDERSAMPLED')
    return result


def cycle_observables(values, centres, frequency):
    """Full-cycle phase RMS, mean electromagnetic torque, midpoint speed.

    RMS is computed on each line separately, then mean/max are retained.
    Integral endpoints are interpolated, including nonuniform event samples.
    """
    period = 1/frequency
    if not centres or centres[0]-period/2 < values['time'][0]-1e-12 or centres[-1]+period/2 > values['time'][-1]+1e-12:
        raise ValueError('EXTERNAL_TRACE_WINDOW_OUTSIDE_SUPPORT')
    output = []
    for centre in centres:
        grid = np.linspace(centre-period/2, centre+period/2, 1001)
        currents = [float(np.sqrt(np.trapezoid(np.interp(grid, values['time'], values[n])**2, grid)/period)) for n in ('ia', 'ib', 'ic')]
        output.append(dict(time_s=float(centre), line_rms_mean_a=sum(currents)/3,
                           line_rms_max_a=max(currents), line_rms_a=currents,
                           torque_cycle_mean_nm=float(np.trapezoid(np.interp(grid, values['time'], values['torque']), grid)/period),
                           speed_rad_s=float(np.interp(centre, values['time'], values['speed']))))
    return output


def arrival(times, speeds, target):
    indices = np.flatnonzero(np.asarray(speeds) >= target)
    if not len(indices):
        return None
    k = int(indices[0])
    if k == 0:
        return float(times[0])
    return float(np.interp(target, speeds[k-1:k+1], times[k-1:k+1]))


def contract():
    return dict(schema=SCHEMA, fixture_id=FIXTURE,
                scope='SYNTHETIC_DELTA_MOTOR_60HZ_AMPLITUDE_AND_FIRING_ANGLE_REPLAY',
                external_solver='OpenModelica 1.27.1', library='Modelica Standard Library 4.0.0',
                interpretation='TRACE_COMPARISON_NOT_SOLVER_ATTESTATION',
                not_evaluated=['CLOSED_LOOP_NETWORK', 'REAL_STARTER_CONTROLLER', 'MANUFACTURER',
                               'PROTECTION', 'THERMAL_LIMITS', 'PROJECT_DESIGN_ACCEPTANCE'],
                device_validation_promoted=False, professional_emission=False,
                design_acceptance_status='NOT_DEMONSTRATED')


def compare(directory):
    """Verify SHA-256 first, then compare candidate and external cycle traces."""
    root = Path(directory).resolve()
    result = dict(contract(), status='BLOCKED_EXTERNAL_REFERENCE')
    try:
        provenance = json.loads((root/'Provenance.json').read_text(encoding='utf8'))
        expected = {'Inputs.json', 'DOL-MCP.json', 'SCR-MCP.json',
                    'DOL-Modelica.csv', 'SCR-Modelica.csv',
                    'DOL-Modelica-refined.csv', 'SCR-Modelica-refined.csv',
                    'DOL.mo', 'SCR.mo', 'Library-sources.json', 'Execution.json'}
        if provenance.get('schema') != SCHEMA or provenance.get('fixture_id') != FIXTURE or set(provenance.get('sha256', {})) != expected:
            raise ValueError('EXTERNAL_EVIDENCE_SCHEMA_OR_FILE_SET')
        for name in sorted(expected):
            path = root/name
            if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != provenance['sha256'][name]:
                raise ValueError(f'EXTERNAL_EVIDENCE_HASH_MISMATCH:{name}')
        inputs = json.loads((root/'Inputs.json').read_text(encoding='utf8'))
        examples = Path(__file__).resolve().parents[1]/'examples'
        for key, file in [('manifest','p13_dynamic_rms_manifest.json'), ('package','p13_dynamic_rms_package.json'),
                          ('options','p13_dynamic_rms_options.json'), ('starter','p13_soft_starter_controller.json')]:
            if inputs.get(key) != json.loads((examples/file).read_text(encoding='utf8')):
                raise ValueError('EXTERNAL_REFERENCE_UNSUPPORTED_INPUTS')
        execution = json.loads((root/'Execution.json').read_text(encoding='utf8'))
        if execution.get('compiler') != 'OpenModelica v1.27.1 (64-bit)' or execution.get('library') != '4.0.0' or execution.get('runs_successful') != ['published', 'DOL', 'SCR', 'DOL_refined', 'SCR_refined']:
            raise ValueError('EXTERNAL_EXECUTION_DECLARATION')
        frequency = 60
        centres = [(k+.5)/frequency for k in range(240)]
        cases = []
        for case in ('DOL', 'SCR'):
            payload = json.loads((root/f'{case}-MCP.json').read_text(encoding='utf8'))
            required = 'DYNAMIC_STUDIES_COMPLETED' if case == 'DOL' else 'SOFT_STARTER_STUDIES_COMPLETED'
            if payload.get('execution_status') != required or len(payload.get('results', [])) != 1:
                raise ValueError('EXTERNAL_CANDIDATE_EXECUTION_NOT_COMPLETE')
            candidate = payload['results'][0]
            rows = candidate['trajectory']
            times = np.array([r['time_s'] for r in rows])
            if not np.isfinite(times).all() or np.any(np.diff(times) <= 0) or times[0] != 0 or times[-1] != 4:
                raise ValueError('EXTERNAL_CANDIDATE_TIME_GRID')
            refined = trace(root/f'{case}-Modelica-refined.csv')
            coarse = trace(root/f'{case}-Modelica.csv')
            # Verify the declared replay at every stored external sample.
            for data in (refined, coarse):
                for reference, field in [('alpha','firing_angle_rad'), ('supply_pu','supply_voltage_pu' if case == 'SCR' else 'voltage_pu')]:
                    target = np.interp(data['time'], times, [r.get(field,0) for r in rows])
                    if np.max(abs(data[reference]-target)) > 1e-9:
                        raise ValueError('EXTERNAL_BOUNDARY_REPLAY_MISMATCH')
            observed = cycle_observables(refined, centres, frequency)
            original = cycle_observables(coarse, centres, frequency)
            stats = {}
            for own, ref in [('current_a','line_rms_mean_a'), ('torque_nm','torque_cycle_mean_nm'), ('speed_rad_s','speed_rad_s')]:
                own_values = np.asarray([r[own] for r in rows])
                if not np.isfinite(own_values).all(): raise ValueError('EXTERNAL_CANDIDATE_NONFINITE')
                a = np.interp(centres,times,own_values)
                b = np.asarray([r[ref] for r in observed])
                old = np.asarray([r[ref] for r in original])
                stats[own] = dict(maximum_absolute_difference=float(np.max(abs(a-b))),
                                  rms_difference=float(np.sqrt(np.mean((a-b)**2))),
                                  reference_rms=float(np.sqrt(np.mean(b**2))),
                                  relative_l2_difference=float(np.linalg.norm(a-b)/max(np.linalg.norm(b),1e-12)),
                                  reference_refinement_maximum_absolute_difference=float(np.max(abs(b-old))))
                for k, row in enumerate(observed): row['mcp_'+own] = float(a[k])
            target = .9*2*np.pi*frequency/2
            external_time = arrival(refined['time'],refined['speed'],target)
            coarse_time = arrival(coarse['time'],coarse['speed'],target)
            mcp_time = arrival(times,[r['speed_rad_s'] for r in rows],target)
            cases.append(dict(case=case, metrics=stats, cycles=observed,
                              mcp_reported_time_90_s=candidate['acceleration_time_s'],
                              mcp_interpolated_time_90_s=mcp_time, reference_time_90_s=external_time,
                              reference_refinement_time_90_difference_s=None if None in (external_time,coarse_time) else abs(external_time-coarse_time),
                              time_90_difference_s=None if None in (mcp_time,external_time) else mcp_time-external_time,
                              reference_maximum_cycle_line_rms_a=max(r['line_rms_max_a'] for r in observed),
                              reference_maximum_pre_replayed_bypass_line_rms_a=max(r['line_rms_max_a'] for r in observed if r['time_s'] < candidate.get('bypass_time_s',1e30)),
                              bypass_time_replayed_s=candidate.get('bypass_time_s')))
            cases[-1]['reference_maximum_actual_output_gap_s'] = float(np.max(np.diff(refined['time'])))
            cases[-1]['coarse_reference_maximum_actual_output_gap_s'] = float(np.max(np.diff(coarse['time'])))
        result.update(status='EXTERNAL_TRACE_COMPARISON_COMPLETED',cases=cases,
                      evidence_sha256=provenance['sha256'],
                      numerical_reference=dict(coarse_tolerance=1e-7, refined_tolerance=1e-9,
                                               coarse_output_step_s=5e-5, refined_output_step_s=2.5e-5,
                                               refined_maximum_internal_step_s=5e-5),
                      comparison_acceptance='NO_NORMATIVE_OR_DEVICE_PASS_ASSIGNED',
                      controller_feedback='MCP_FIRING_ANGLE_REPLAY_OPEN_LOOP_FOR_REFERENCE',
                      includes_initial_flux_transient=True, external_fixed_source_phase_angles=True,
                      parent_context_mutated=False)
    except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError) as error:
        result['reason'] = str(error)
    return result
