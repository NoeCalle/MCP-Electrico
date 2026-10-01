from pathlib import Path
import re

import pytest

from mcp_electrico import core, visual_sheets,workspace_state,visual_state,visualization


def test_large_network_sheets_cover_full_diagram_without_solving_or_overwriting(tmp_path):
    core.crear_circuito('large_network_visual',.48,frecuencia=60)
    for j in range(24):
        core.agregar_linea(f'feeder_{j:02d}','sourcebus',f'bus_{j:02d}',.02)
        core.agregar_carga(f'load_{j:02d}',f'bus_{j:02d}',8,2,kv=.48)
    workspace_state.reset_for_circuit('large_network_visual')
    before=workspace_state.status()
    result=visual_sheets.export(str(tmp_path/'sheets.html'))
    assert result['sheet_count']>1
    html=Path(result['html_path']).read_text(encoding='utf-8')
    assert html.count('class="sheet"')==result['sheet_count']
    views=[list(map(float,v.split())) for v in re.findall('viewBox="([^"]+)"',html)]
    assert len(views)==result['sheet_count']
    full=Path(result['svg_path']).read_text(encoding='utf-8')
    original=list(map(float,re.search('viewBox="([^"]+)"',full)[1].split()))
    assert max(v[0]+v[2] for v in views)>=original[2]
    assert max(v[1]+v[3] for v in views)>=original[3]
    assert '@page{size:A3 landscape' in html and '<svg ' in html
    assert workspace_state.status()==before
    with pytest.raises(ValueError): visual_sheets.export(result['html_path'])


def test_duplicate_visual_labels_keep_equipment_identity_and_real_feeder_names(tmp_path):
    import xml.etree.ElementTree as ET
    core.crear_circuito('duplicate_labels',.48,frecuencia=60)
    visual_state.reset()
    for j in range(2):
        core.agregar_linea(f'f_{j:02d}','sourcebus',f'bus_{j}',.02)
        core.agregar_carga(f'motor_{j}',f'bus_{j}',8,2,kv=.48)
        visual_state.set_load_label(f'motor_{j}','BOMBA')
    result=visualization.generar_diagrama_unifilar(str(tmp_path/'identity.svg'))
    labels={n.attrib['data-element-id'].lower(): ''.join(n.itertext())
            for n in ET.parse(result['archivo_svg']).iter()
            if 'data-element-id' in n.attrib}
    assert 'BOMBA' in labels['load.motor_0'] and 'BOMBA' in labels['load.motor_1']
    assert labels['line.f_00']=='F-00' and labels['line.f_01']=='F-01'
