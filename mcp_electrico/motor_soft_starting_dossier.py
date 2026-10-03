"""Replay and portable artifacts for the explicitly limited SCR/RL surrogate."""
from __future__ import annotations

import csv
from html import escape
import json
from pathlib import Path

from . import motor_soft_starting as soft, motor_dynamics_dossier as dossier, motor_starting_dossier as files

INDEX = "soft_starter_integrity.json"
REQUIRED = dossier.REQUIRED | {"soft_starter.json"}


def render(execution):
    html = dossier.render(execution)
    old = 'Arranque directo trifásico equilibrado · Dinámica mecánica con red RMS cuasiestacionaria. No representa transitorios de flujo, formas de onda, VFD ni calentamiento.'
    new = ('Arranque suave · Aproximación SCR/RL por fase y red de componente fundamental. '
           'No validada contra un arrancador real ni representa la conmutación trifásica, '
           'armónicos en la red o calentamiento. La tensión del motor es su componente fundamental; '
           'la corriente es RMS total del equivalente RL. Aceptación del diseño no demostrada.')
    html = html.replace(old, new).replace('Corriente de línea', 'Corriente RMS · equivalente RL').replace('Tensión terminal', 'Tensión fundamental del motor')
    html = html.replace('Cumple criterios', 'Supera los umbrales declarados').replace('No cumple criterios', 'No supera los umbrales declarados')
    sections = []
    for study in execution['results']:
        rows = study['trajectory']
        ev = study['criterion']['evidence']
        proof = ' · '.join(escape(ev[k]) for k in ('kind', 'document', 'edition', 'clause', 'applicability'))
        bypass = 'No alcanzado' if study['bypass_time_s'] is None else f"{study['bypass_time_s']:g} s"
        charts = []
        for title, unit, curves in [
            ('Rampa solicitada y aplicada', 'fracción fundamental', [('requested_voltage_fraction', 'Solicitada'), ('voltage_gain', 'Aplicada')]),
            ('Par del motor y resistente de carga', 'N·m', [('torque_nm', 'Motor'), ('load_torque_nm', 'Carga, sin amortiguamiento')]),
        ]:
            maximum = max(max(row[key] for row in rows) for key, _ in curves)
            maximum = max(maximum, 1e-9)
            traces = []
            for (key, label), color in zip(curves, ('#087e8b', '#b45309')):
                points = ' '.join(f"{55+700*r['time_s']/rows[-1]['time_s']:.3f},{225-180*r[key]/maximum:.3f}" for r in rows)
                traces.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>')
            legend = ' · '.join(escape(label) for _, label in curves)
            charts.append(f'<figure><figcaption>{title} · {unit}</figcaption><svg viewBox="0 0 800 270" role="img" aria-label="{title}"><path d="M55 30 V225 H755" stroke="#94a3b8" fill="none"/><text x="8" y="35">{maximum:.4g}</text><text x="30" y="225">0</text><text x="55" y="252">0 s</text><text x="710" y="252">{rows[-1]["time_s"]:g} s</text>{"".join(traces)}</svg><p>{legend} (azul / naranja).</p></figure>')
        details = ''.join(f"<tr><td>{r['time_s']:.4f}</td><td>{r['supply_voltage_pu']:.5g}</td><td>{r['voltage_pu']:.5g}</td><td>{r['motor_voltage_rms_pu']:.5g}</td><td>{r['current_a']:.5g}</td><td>{escape(r['starter_state'])}</td></tr>" for r in rows)
        sections.append(f'<section><h2>Control · {escape(study["study_id"])}</h2><p>Bypass: {bypass}. Máxima corriente RMS del equivalente: {study["maximum_line_current_a"]:.5g} A.</p><div class="charts">{"".join(charts)}</div><p>Procedencia declarada: {proof}. La identidad y aplicabilidad del documento no se autentican automáticamente.</p><p>Potencia adicional RL contabilizada por separado; no es calentamiento real del motor ni pérdida en los SCR. I²t es un indicador integrado y requiere límites del fabricante.</p><details><summary>Ver control y tensiones</summary><div class="table"><table><thead><tr><th>Tiempo · s</th><th>Entrada · pu</th><th>Motor fundamental · pu</th><th>Motor RMS RL · pu</th><th>I RMS RL · A</th><th>Estado</th></tr></thead><tbody>{details}</tbody></table></div></details></section>')
    return html.replace('</main>', ''.join(sections)+'</main>')


def verify(path):
    target = Path(path).expanduser()
    if target.is_symlink(): return {'ok': False, 'issues': ['SYMLINK_INDEX'], 'professional_emission': False}
    target = target.resolve(); root = target.parent; issues = []
    try:
        data = json.loads(target.read_text(encoding='utf-8')); payload = data['payload']
        if payload['schema'] != 'MCP_ELECTRICO_P13G_INTEGRITY_V1': issues.append('INVALID_SCHEMA')
        if data['payload_sha256'] != dossier._hash(payload): issues.append('INDEX_HASH_MISMATCH')
        names = [r['path'] for r in payload['files']]
        if set(names) != REQUIRED or len(names) != len(REQUIRED): issues.append('UNSAFE_OR_INCOMPLETE_FILE_SET')
        if {p.name for p in root.iterdir() if p.name != INDEX} != REQUIRED: issues.append('EXACT_FILE_SET_MISMATCH')
        for record in payload['files']:
            if record['path'] not in REQUIRED: continue
            file = root/record['path']
            if file.is_symlink() or not file.is_file(): issues.append('MISSING_OR_UNSAFE_FILE'); continue
            if file.stat().st_size != record['size_bytes'] or files._file_sha256(file) != record['sha256']: issues.append('FILE_HASH_MISMATCH')
    except (OSError, ValueError, KeyError, TypeError): issues.append('INVALID_INDEX')
    return {'schema': 'MCP_ELECTRICO_P13G_INTEGRITY_V1', 'ok': not issues,
            'issues': sorted(set(issues)), 'professional_emission': False}


def generate(manifest, package, options, starter, directory):
    execution = soft.execute(manifest, package, options, starter)
    if execution['execution_status'] != 'SOFT_STARTER_STUDIES_COMPLETED':
        return {'status': 'SOFT_STARTER_DOSSIER_BLOCKED', 'execution': execution, 'professional_emission': False}
    replay = soft.execute(manifest, package, options, starter)
    if execution != replay: return {'status': 'SOFT_STARTER_REPLAY_MISMATCH', 'professional_emission': False}
    root, collision = files._safe_dir(directory)
    saved = {'manifest.json': manifest, 'dynamic_package.json': package, 'dynamic_options.json': options,
             'soft_starter.json': starter, 'dynamic_execution.json': execution,
             'dynamic_replay.json': {'match': True, 'execution_sha256': dossier._hash(execution)},
             'dossier_manifest.json': {'schema': 'MCP_ELECTRICO_P13G_DOSSIER_V1', 'backend': soft.BACKEND,
                                      'runtime': execution['runtime'], 'parent_context_mutated': False,
                                      'professional_emission': False}}
    for name, value in saved.items(): dossier._write(root/name, value)
    (root/'dynamic_workspace.html').write_text(render(execution), encoding='utf-8')
    columns = ['time_s', 'speed_rad_s', 'current_a', 'fundamental_line_current_a', 'torque_nm',
               'supply_voltage_pu', 'voltage_pu', 'motor_voltage_rms_pu', 'voltage_gain',
               'firing_angle_rad', 'starter_state', 'current_limit_active', 'line_current_i2t_a2_s',
               'kinetic_energy_j', 'electrical_input_energy_j', 'rl_surrogate_extra_energy_j', 'energy_residual_j']
    with (root/'dynamic_trajectory.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream); writer.writerow(['study_index']+columns)
        for j, study in enumerate(execution['results']):
            for row in study['trajectory']: writer.writerow([j]+[row[k] for k in columns])
    records = [{'path': name, 'size_bytes': (root/name).stat().st_size, 'sha256': files._file_sha256(root/name)} for name in sorted(REQUIRED)]
    payload = {'schema': 'MCP_ELECTRICO_P13G_INTEGRITY_V1', 'files': records, 'execution_sha256': dossier._hash(execution)}
    dossier._write(root/INDEX, {'payload': payload, 'payload_sha256': dossier._hash(payload)})
    integrity = verify(root/INDEX)
    return {'status': 'SOFT_STARTER_DOSSIER_READY' if integrity['ok'] else 'SOFT_STARTER_ARTIFACT_VERIFICATION_FAILED',
            'directory': str(root), 'workspace': str(root/'dynamic_workspace.html'), 'index_path': str(root/INDEX),
            'replay_match': True, 'integrity': integrity, 'collision_suffix_used': collision,
            'design_acceptance_status': 'NOT_DEMONSTRATED', 'professional_emission': False}
