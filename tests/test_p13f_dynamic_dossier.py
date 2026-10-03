from pathlib import Path
import json
import shutil
from copy import deepcopy

from mcp_electrico import motor_dynamics_dossier as dossier

ROOT=Path(__file__).resolve().parents[1]


def inputs():
    return tuple(json.loads((ROOT/'examples'/f'p13_dynamic_rms_{s}.json').read_text()) for s in ('manifest','package','options'))


def test_retired_backend_cannot_create_a_new_legacy_dossier(tmp_path):
    m,p,o=inputs()
    result=dossier.generate(m,p,o,tmp_path/'study')
    assert result['status']=='DYNAMIC_DOSSIER_BLOCKED'
    assert result['execution']['execution_status']=='RETIRED_CUSTOM_BACKEND'
    assert not (tmp_path/'study').exists()


def test_incomplete_physics_and_unsafe_index_cannot_create_ready_dossier(tmp_path):
    m,p,o=inputs();del p['motors'][0]['mechanical']['motor_inertia_kg_m2']
    result=dossier.generate(m,p,o,tmp_path/'blocked')
    assert result['status']=='DYNAMIC_DOSSIER_BLOCKED' and not (tmp_path/'blocked').exists()
    assert not dossier.verify(tmp_path/'missing.json')['ok']
    target=tmp_path/dossier.INDEX
    payload={'files':[{'path':'../outside.txt','size_bytes':0,'sha256':'0'}]}
    target.write_text(json.dumps({'payload':payload,'payload_sha256':dossier._hash(payload)}))
    assert not dossier.verify(target)['ok']
