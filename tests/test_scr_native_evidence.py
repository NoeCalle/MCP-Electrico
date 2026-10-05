"""A scoped qualification must retain passing evidence for the current adapter."""
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_published_scr_evidence_matches_sources_and_all_declared_limits():
    data=json.loads((ROOT/'mcp_electrico/data/msl_scr_native_evidence_v1.json').read_text(encoding='utf8'))
    assert set(data['cases'])=={'base','phase-positive','phase-negative','inertia','frequency-60','initial-voltage'}
    assert not data['physical_solver_owned_by_mcp'] and not data['manufacturer_qualified']
    assert not data['limits_relaxed_after_failure']
    # Git checks out CRLF on Windows and LF on Linux. Retain the original raw
    # hashes as run provenance; compare the same source text across platforms.
    assert set(data['source_lf_sha256'])==set(data['source_sha256'])
    for path,digest in data['source_lf_sha256'].items():
        assert sha256((ROOT/path).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==digest,path
    checker=ROOT/'scripts/check_msl_scr_trace.py'
    assert sha256(checker.read_bytes().replace(b'\r\n',b'\n')).hexdigest()==data['independent_trace_checker_lf_sha256']
    for name,case in data['cases'].items():
        comparison=case['comparison']
        assert comparison['passed'] and case['mcp_refinement']['passed'],name
        assert all(value is not None and value<=comparison['predeclared_limits'][key]
                   for key,value in comparison['errors'].items()),name
        assert case['bypass_time_s'] is not None
        pole=case['native_filter_pole']
        assert pole['passed'] and pole['actual_pole_per_s']==pole['expected_pole_per_s']
        assert pole['native_normalization'] is False
        for trace in case['energy_and_bypass'].values():
            assert trace['passed'] and trace['energy']['passed'] and trace['bypass']['passed'],name
            assert trace['energy']['relative_error']<=trace['energy']['predeclared_limit']
            assert trace['bypass']['absolute_error_s']<=trace['bypass']['predeclared_limit_s']
