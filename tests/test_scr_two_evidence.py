"""Do not publish multi-SCR scope without passing evidence tied to its sources."""
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_two_scr_published_evidence_checks_every_motor_and_shared_bus():
    data=json.loads((ROOT/'mcp_electrico/data/msl_two_scr_evidence_v1.json').read_text(encoding='utf8'))
    assert data['physical_cases']==7 and data['two_motor_cases']==6
    assert data['calls']==18 and not data['physical_solver_owned_by_mcp']
    assert not data['manufacturer_qualified'] and data['not_all_parameter_combinations_qualified']
    for path,expected in data['source_lf_sha256'].items():
        assert sha256((ROOT/path).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==expected,path
    assert len(data['symmetry_parity'])==2 and all(c['passed'] for c in data['symmetry_parity'])
    checks=0
    for name,case in data['cases'].items():
        assert case['passed'],name
        for motor in case['motors']:
            assert motor['verification']['passed'] and motor['bypass_time_s'] is not None
            assert motor['acceleration_time_s'] is not None
        for trace in case['checks'].values():
            kvl=trace['kvl']
            assert kvl['passed'] and kvl['includes_all_motor_currents'] and kvl['includes_inductive_boundary_term']
            assert kvl['maximum_integral_kvl_residual_pu']<=kvl['limit_pu']
            for motor in trace['motors']:
                checks+=1
                assert motor['passed'] and motor['latched']
                assert motor['energy_relative_error']<=motor['energy_limit']
                assert motor['bypass_error_s']<=motor['bypass_limit_s']
        assert all(row['passed'] for row in case['independent_reader_parity'])
    assert checks==data['per_motor_nominal_refined_checks']==26
    assert data['failed_attempts'] and all(not row['accepted_as_verified_result'] and not row['limits_relaxed'] for row in data['failed_attempts'])
