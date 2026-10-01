from pathlib import Path
import json
import shutil
from copy import deepcopy

from mcp_electrico import motor_dynamics_dossier as dossier

ROOT=Path(__file__).resolve().parents[1]


def inputs():
    return tuple(json.loads((ROOT/'examples'/f'p13_dynamic_rms_{s}.json').read_text()) for s in ('manifest','package','options'))


def test_dynamic_dossier_is_portable_collision_safe_and_detects_all_tampering(tmp_path):
    m,p,o=inputs()
    first=dossier.generate(m,p,o,tmp_path/'study')
    assert first['status']=='DYNAMIC_DOSSIER_READY'
    second=dossier.generate(m,p,o,tmp_path/'study')
    assert second['collision_suffix_used'] and first['directory']!=second['directory']
    root=Path(first['directory'])
    html=(root/'dynamic_workspace.html').read_text(encoding='utf-8')
    assert '<polyline' in html and '400' in html
    assert '<script src=' not in html
    moved=tmp_path/'portable';shutil.copytree(root,moved)
    assert dossier.verify(moved/dossier.INDEX)['ok']
    (moved/'extra.txt').write_text('unexpected')
    assert not dossier.verify(moved/dossier.INDEX)['ok']
    (moved/'extra.txt').unlink()
    (moved/'dynamic_trajectory.csv').write_text('tampered')
    assert not dossier.verify(moved/dossier.INDEX)['ok']
    assert dossier.verify(first['index_path'])['ok']


def test_incomplete_physics_and_unsafe_index_cannot_create_ready_dossier(tmp_path):
    m,p,o=inputs();del p['motors'][0]['mechanical']['motor_inertia_kg_m2']
    result=dossier.generate(m,p,o,tmp_path/'blocked')
    assert result['status']=='DYNAMIC_DOSSIER_BLOCKED' and not (tmp_path/'blocked').exists()
    assert not dossier.verify(tmp_path/'missing.json')['ok']
    target=tmp_path/dossier.INDEX
    payload={'files':[{'path':'../outside.txt','size_bytes':0,'sha256':'0'}]}
    target.write_text(json.dumps({'payload':payload,'payload_sha256':dossier._hash(payload)}))
    assert not dossier.verify(target)['ok']
