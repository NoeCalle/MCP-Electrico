"""Portable dynamic dossier: numerical replay, Python SVG, CSV and exact hashes."""
from __future__ import annotations

import csv
from hashlib import sha256
from html import escape
import json
from pathlib import Path

from . import motor_dynamics, motor_starting_dossier as files

INDEX = "dynamic_dossier_integrity.json"
REQUIRED = {"manifest.json", "dynamic_package.json", "dynamic_options.json", "dynamic_execution.json",
            "dynamic_replay.json", "dynamic_workspace.html", "dynamic_trajectory.csv", "dossier_manifest.json"}


def _hash(value):
    return sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def _write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def render(execution):
    sections=[]
    for study in execution['results']:
        rows=study['trajectory']; end=rows[-1]['time_s']
        charts=[]
        for field,title,unit in [('speed_rad_s','Velocidad','rad/s'),('current_a','Corriente de línea','A'),
                                 ('torque_nm','Par electromagnético','N·m'),('voltage_pu','Tensión terminal','pu')]:
            values=[r[field] for r in rows]; maximum=max(max(values),1e-9)
            points=' '.join(f"{55+700*r['time_s']/end:.3f},{225-180*r[field]/maximum:.3f}" for r in rows)
            charts.append(f'<figure><figcaption>{title} · {unit}</figcaption><svg viewBox="0 0 800 270" role="img" aria-label="{title}"><path d="M55 30 V225 H755" stroke="#94a3b8" fill="none"/><text x="8" y="35">{maximum:.4g}</text><text x="30" y="225">0</text><text x="55" y="252">0 s</text><text x="710" y="252">{end:g} s</text><polyline points="{points}" fill="none" stroke="#087e8b" stroke-width="2"/></svg></figure>')
        passed=study['criterion']['passed']; label='Cumple criterios' if passed else 'No cumple criterios'
        table=''.join(f"<tr><td>{r['time_s']:.4f}</td><td>{r['speed_rad_s']:.5g}</td><td>{r['current_a']:.5g}</td><td>{r['torque_nm']:.5g}</td><td>{r['voltage_pu']:.5g}</td></tr>" for r in rows)
        reached=study['acceleration_time_s']; text='Objetivo no alcanzado' if reached is None else f'{reached:g} s'
        sections.append(f'<section><h2>{escape(study["study_id"])} · {escape(study["motor_id"])}</h2><div class="metrics"><div><small>Resultado</small><strong>{label}</strong></div><div><small>Tiempo de aceleración</small><strong>{text}</strong></div><div><small>Tensión mínima</small><strong>{study["minimum_voltage_pu"]:.4f} pu</strong></div><div><small>Estado</small><strong>{escape(study["state"])}</strong></div></div><div class="charts">{"".join(charts)}</div><details><summary>Ver trayectoria completa · {len(rows)} muestras</summary><div class="table"><table><thead><tr><th>Tiempo · s</th><th>Velocidad · rad/s</th><th>Corriente · A</th><th>Par · N·m</th><th>Tensión · pu</th></tr></thead><tbody>{table}</tbody></table></div></details><p>Convergencia temporal y balance de energía comprobados. Error relativo máximo de energía: {study["verification"]["maximum_energy_relative_error"]:.3g}.</p><p>Criterio: {escape(study["criterion"]["reference"])}</p></section>')
    return '''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Dinámica de motores</title><style>
    *{box-sizing:border-box}body{margin:0;background:#edf3f7;color:#172c40;font:14px system-ui}main{max-width:1400px;margin:auto;padding:24px}h1{margin-bottom:4px}section{background:white;border:1px solid #d5e0e8;border-radius:14px;padding:24px;margin:18px 0}.scope{color:#456078;line-height:1.6}.metrics,.charts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.metrics>div{background:#f4f8fa;border-radius:9px;padding:16px}.metrics strong{display:block;font-size:20px;margin-top:6px}figure{margin:10px 0;border:1px solid #d5e0e8;border-radius:9px;padding:12px}svg{width:100%;height:auto;font:12px system-ui}figcaption{font-weight:700}.table{max-height:420px;overflow:auto}table{border-collapse:collapse;width:100%}th,td{padding:9px;text-align:right;border-bottom:1px solid #d5e0e8}summary,button{cursor:pointer;padding:12px}button{border:1px solid #b5c8d5;border-radius:8px;background:white}th{position:sticky;top:0;background:#eef4f7}@media(max-width:720px){.metrics,.charts{grid-template-columns:1fr}main{padding:12px}}@media print{body{background:white}main{padding:0}button{display:none}section,figure{break-inside:avoid}.charts{grid-template-columns:1fr 1fr}details{display:none}}
    </style><main><h1>Dinámica de motores</h1><p class="scope">Arranque directo trifásico equilibrado · Dinámica mecánica con red RMS cuasiestacionaria. No representa transitorios de flujo, formas de onda, VFD ni calentamiento. Engineering Preview · emisión profesional deshabilitada.</p><button id="print">Imprimir / PDF</button><a href="dynamic_trajectory.csv" download>Descargar trayectoria CSV</a>'''+''.join(sections)+'''</main><script>document.getElementById('print').addEventListener('click',()=>window.print());</script></html>'''


def verify(path):
    target=Path(path).expanduser()
    if target.is_symlink(): return {'ok':False,'issues':['SYMLINK_INDEX'],'professional_emission':False}
    target=target.resolve(); root=target.parent; issues=[]
    try:
        data=json.loads(target.read_text(encoding='utf-8')); payload=data['payload']
        if data['payload_sha256']!=_hash(payload): issues.append('INDEX_HASH_MISMATCH')
        entries=payload['files']
        names=[record['path'] for record in entries]
        if set(names)!=REQUIRED or len(names)!=len(REQUIRED): issues.append('UNSAFE_OR_INCOMPLETE_FILE_SET')
        actual={p.name for p in root.iterdir() if p.name!=INDEX}
        if actual!=REQUIRED: issues.append('EXACT_FILE_SET_MISMATCH')
        for record in entries:
            if record['path'] not in REQUIRED: continue
            file=root/record['path']
            if file.is_symlink() or not file.is_file(): issues.append('MISSING_OR_UNSAFE_FILE'); continue
            if file.stat().st_size!=record['size_bytes'] or files._file_sha256(file)!=record['sha256']: issues.append('FILE_HASH_MISMATCH')
    except (OSError,ValueError,KeyError,TypeError): issues.append('INVALID_INDEX')
    return {'schema':'MCP_ELECTRICO_P13F_DYNAMIC_INTEGRITY_V1','ok':not issues,'issues':sorted(set(issues)), 'professional_emission':False}


def generate(manifest,package,options,directory):
    execution=motor_dynamics.execute(manifest,package,options)
    if execution['execution_status']!='DYNAMIC_STUDIES_COMPLETED':
        return {'status':'DYNAMIC_DOSSIER_BLOCKED','execution':execution,'professional_emission':False}
    replay=motor_dynamics.execute(manifest,package,options)
    if execution!=replay:
        return {'status':'DYNAMIC_REPLAY_MISMATCH','professional_emission':False}
    root,collision=files._safe_dir(directory)
    saved={'manifest.json':manifest,'dynamic_package.json':package,'dynamic_options.json':options,
           'dynamic_execution.json':execution,'dynamic_replay.json':{'match':True,'execution_sha256':_hash(execution)},
           'dossier_manifest.json':{'schema':'MCP_ELECTRICO_P13F_DYNAMIC_DOSSIER_V1','backend':motor_dynamics.BACKEND,
                                    'runtime':execution['runtime'],'parent_context_mutated':False,'professional_emission':False}}
    for name,value in saved.items(): _write(root/name,value)
    (root/'dynamic_workspace.html').write_text(render(execution),encoding='utf-8')
    columns=['time_s','speed_rad_s','current_a','torque_nm','voltage_pu','kinetic_energy_j','electrical_input_energy_j','energy_residual_j']
    with (root/'dynamic_trajectory.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['study_index']+columns)
        for j,study in enumerate(execution['results']):
            for row in study['trajectory']: writer.writerow([j]+[row[key] for key in columns])
    records=[{'path':name,'size_bytes':(root/name).stat().st_size,'sha256':files._file_sha256(root/name)} for name in sorted(REQUIRED)]
    payload={'schema':'MCP_ELECTRICO_P13F_DYNAMIC_INTEGRITY_V1','files':records,'execution_sha256':_hash(execution)}
    _write(root/INDEX,{'payload':payload,'payload_sha256':_hash(payload)})
    integrity=verify(root/INDEX)
    return {'status':'DYNAMIC_DOSSIER_READY' if integrity['ok'] else 'DYNAMIC_ARTIFACT_VERIFICATION_FAILED',
            'directory':str(root),'workspace':str(root/'dynamic_workspace.html'),'index_path':str(root/INDEX),
            'replay_match':True,'integrity':integrity,'collision_suffix_used':collision,
            'parent_context_mutated':False,'professional_emission':False}
