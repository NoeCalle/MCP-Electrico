'''Workspace HTML persistente e interactivo para MCP Eléctrico.

ChatGPT sigue siendo la interfaz conversacional. Este módulo genera una vista
HTML autocontenida del circuito activo, su estado de cálculo y una ficha
interactiva de los elementos. No llama a modelos de IA, no modifica OpenDSS y
no realiza cálculos eléctricos.
'''

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from typing import Any

from . import workspace_state
from .visualization import generar_diagrama_unifilar

_config: dict[str, Any] = {
    "path": Path("workspace.html"),
    "title": None,
    "auto_regenerate": True,
    "last_generation": None,
}


def configure(
    ruta_salida: str = "workspace.html",
    titulo: str | None = None,
    auto_regenerar: bool = True,
) -> dict[str, Any]:
    path = Path(ruta_salida).expanduser()
    if path.suffix.lower() != ".html":
        path = path.with_suffix(".html")
    _config["path"] = path
    _config["title"] = titulo.strip() if titulo else None
    _config["auto_regenerate"] = bool(auto_regenerar)
    if workspace_state.status()["circuit_name"]:
        safe_regenerate()
    return get_state()


def _title(snapshot: dict[str, Any]) -> str:
    if _config["title"]:
        return str(_config["title"])
    circuit = snapshot["model"].get("circuit") or "Circuito eléctrico"
    return f"{circuit} — Workspace eléctrico"


def _state_label(state: str) -> tuple[str, str]:
    mapping = {
        workspace_state.STATE_EMPTY: ("SIN MODELO", "neutral"),
        workspace_state.STATE_MODIFIED: ("MODELO MODIFICADO", "warning"),
        workspace_state.STATE_SOLVED: ("RESUELTO", "ok"),
        workspace_state.STATE_ERROR: ("ERROR ELÉCTRICO", "error"),
    }
    return mapping.get(state, (state, "neutral"))


def _engineering_name(name: str) -> str:
    text = name.strip()
    text = re.sub(r"_(\d+)$", r"-\1", text)
    return text.replace("_", " ").upper()


def _element_id(kind: str, name: str) -> str:
    prefixes = {
        "bus": "Bus",
        "line": "Line",
        "transformer": "Transformer",
        "load": "Load",
        "generator": "Generator",
    }
    return f"{prefixes[kind]}.{name}"


def _element_label(kind: str, item: dict[str, Any]) -> str:
    if kind == "bus":
        visual = item.get("visual", {})
        return str(visual.get("etiqueta") or _engineering_name(item["name"]))
    if kind == "line":
        visual = item.get("visual", {})
        return str(visual.get("etiqueta") or _engineering_name(item["name"]))
    if kind == "load":
        return str(item.get("label") or _engineering_name(item["name"]))
    return _engineering_name(str(item["name"]))


def _element_catalog(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    model = snapshot["model"]
    catalog: list[dict[str, str]] = []
    specs = (
        ("bus", model.get("buses", [])),
        ("line", model.get("lines", [])),
        ("transformer", model.get("transformers", [])),
        ("load", model.get("loads", [])),
        ("generator", model.get("generators", [])),
    )
    for kind, items in specs:
        for item in items:
            catalog.append(
                {
                    "id": _element_id(kind, str(item["name"])),
                    "kind": kind,
                    "name": str(item["name"]),
                    "label": _element_label(kind, item),
                }
            )
    order = {"bus": 0, "line": 1, "transformer": 2, "load": 3, "generator": 4}
    return sorted(catalog, key=lambda x: (order[x["kind"]], x["label"]))


def _data_rows(snapshot: dict[str, Any]) -> str:
    model = snapshot["model"]
    rows: list[str] = []
    for line in model.get("lines", []):
        visual = line.get("visual", {})
        label = _element_label("line", line)
        conductor = visual.get("conductor") or "—"
        eid = _element_id("line", line["name"])
        rows.append(
            f'<tr class="selectable-row" data-element-id="{escape(eid, quote=True)}">'
            f"<td>{escape(label)}</td>"
            "<td>Alimentador</td>"
            f"<td>{escape(line['bus1'])} → {escape(line['bus2'])}</td>"
            f"<td>{line['length']:.4g} km</td>"
            f"<td>{escape(str(conductor))}</td>"
            f"<td>{'ABIERTO' if line['open'] else 'Cerrado'}</td>"
            "</tr>"
        )
    for tr in model.get("transformers", []):
        wdgs = tr.get("windings", [])
        kv = " / ".join(f"{w.get('kv', 0):g} kV" for w in wdgs) or "—"
        kva = wdgs[0].get("kva") if wdgs else None
        professional = tr.get("professional") or {}
        group = professional.get("vector_group", {}).get("grupo_vectorial") or kv
        eid = _element_id("transformer", tr["name"])
        rows.append(
            f'<tr class="selectable-row" data-element-id="{escape(eid, quote=True)}">'
            f"<td>{escape(_element_label('transformer', tr))}</td>"
            "<td>Transformador</td>"
            f"<td>{escape(' → '.join(tr.get('buses', [])))}</td>"
            f"<td>{f'{kva:g} kVA' if kva is not None else '—'}</td>"
            f"<td>{escape(str(group))}</td>"
            f"<td>{'P2 trazable' if professional else ('ABIERTO' if tr['open'] else 'Cerrado')}</td>"
            "</tr>"
        )
    for load in model.get("loads", []):
        eid = _element_id("load", load["name"])
        rows.append(
            f'<tr class="selectable-row" data-element-id="{escape(eid, quote=True)}">'
            f"<td>{escape(_element_label('load', load))}</td>"
            f"<td>{escape(str(load.get('visual_type', 'carga')).title())}</td>"
            f"<td>{escape(load.get('bus', ''))}</td>"
            f"<td>{load.get('kw', 0):g} kW</td>"
            f"<td>{load.get('kvar', 0):g} kvar</td>"
            f"<td>{'Crítica' if load.get('critical') else '—'}</td>"
            "</tr>"
        )
    for gen in model.get("generators", []):
        eid = _element_id("generator", gen["name"])
        rows.append(
            f'<tr class="selectable-row" data-element-id="{escape(eid, quote=True)}">'
            f"<td>{escape(_element_label('generator', gen))}</td>"
            "<td>Generador</td>"
            f"<td>{escape(gen.get('bus', ''))}</td>"
            f"<td>{gen.get('kw', 0):g} kW</td>"
            f"<td>{gen.get('kv', 0):g} kV</td>"
            "<td>—</td>"
            "</tr>"
        )
    return "".join(rows) or '<tr><td colspan="6">No hay elementos para mostrar.</td></tr>'


def _element_options(catalog: list[dict[str, str]]) -> str:
    kind_label = {
        "bus": "Barras / buses",
        "line": "Alimentadores",
        "transformer": "Transformadores",
        "load": "Cargas",
        "generator": "Generadores",
    }
    by_kind: dict[str, list[dict[str, str]]] = {}
    for item in catalog:
        by_kind.setdefault(item["kind"], []).append(item)
    chunks = ['<option value="">Selecciona un elemento…</option>']
    for kind in ("bus", "line", "transformer", "load", "generator"):
        items = by_kind.get(kind, [])
        if not items:
            continue
        chunks.append(f'<optgroup label="{escape(kind_label[kind], quote=True)}">')
        for item in items:
            chunks.append(
                f'<option value="{escape(item["id"], quote=True)}">'
                f'{escape(item["label"])}</option>'
            )
        chunks.append("</optgroup>")
    return "".join(chunks)


def _render_html(snapshot: dict[str, Any], svg: str) -> str:
    status = snapshot["status"]
    label, tone = _state_label(status["state"])
    studies = status.get("studies", {})
    powerflow = studies.get("powerflow", {})
    powerflow_valid = bool(powerflow.get("valid"))
    pf_result = powerflow.get("result", {}) if powerflow_valid else {}
    losses = pf_result.get("perdidas_totales_kw")
    title = _title(snapshot)
    serialized = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    catalog = _element_catalog(snapshot)
    catalog_json = json.dumps(catalog, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    notices: list[str] = []
    if status["state"] == workspace_state.STATE_MODIFIED:
        notices.append(
            '<div class="notice warning"><strong>Resultados desactualizados.</strong> '
            "El modelo cambió después de la última solución. Ejecute nuevamente el flujo de potencia antes de interpretar resultados eléctricos.</div>"
        )
    elif status["state"] == workspace_state.STATE_ERROR:
        notices.append(
            '<div class="notice error"><strong>Error eléctrico.</strong> '
            f"{escape(str(status.get('electrical_error') or 'Revise el último cálculo.'))}</div>"
        )
    if status.get("workspace_error"):
        notices.append(
            '<div class="notice error"><strong>Error de visualización.</strong> '
            f"{escape(str(status['workspace_error']))}. El estado eléctrico se conserva independiente de este fallo.</div>"
        )
    notices_html = "".join(notices)

    return f'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
<style>
:root {{ color-scheme:light; --ink:#111827; --muted:#6b7280; --line:#d1d5db; --blue:#0b3a6e; --blue-soft:#eff6ff; --ok:#166534; --warn:#92400e; --err:#b91c1c; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:Arial,Helvetica,sans-serif; color:var(--ink); background:#eef2f6; }}
.shell {{ max-width:1600px; margin:0 auto; padding:20px; }}
header {{ display:flex; gap:16px; justify-content:space-between; align-items:flex-start; margin-bottom:14px; }}
h1 {{ margin:0 0 4px; font-size:22px; color:var(--blue); }}
.meta {{ color:var(--muted); font-size:12px; }}
.status {{ border:1px solid var(--line); border-radius:999px; padding:7px 11px; font-size:11px; font-weight:700; white-space:nowrap; background:white; }}
.status.ok {{ color:var(--ok); border-color:#86efac; background:#f0fdf4; }}
.status.warning {{ color:var(--warn); border-color:#fcd34d; background:#fffbeb; }}
.status.error {{ color:var(--err); border-color:#fca5a5; background:#fef2f2; }}
.toolbar {{ display:flex; flex-wrap:wrap; gap:8px; margin:0 0 14px; }}
button {{ border:1px solid #cbd5e1; border-radius:7px; background:white; color:var(--ink); padding:9px 12px; font:inherit; cursor:pointer; }}
button.primary {{ background:var(--blue); color:white; border-color:var(--blue); }}
.workspace-layout {{ display:grid; grid-template-columns:minmax(0,1fr) 310px; gap:14px; align-items:start; }}
.workspace-content {{ min-width:0; }}
.tabs {{ display:flex; gap:4px; border-bottom:1px solid var(--line); }}
.tab {{ border:0; border-radius:7px 7px 0 0; background:transparent; padding:9px 14px; }}
.tab.active {{ background:white; color:var(--blue); font-weight:700; border:1px solid var(--line); border-bottom-color:white; margin-bottom:-1px; }}
.panel {{ display:none; background:white; border:1px solid var(--line); border-radius:0 8px 8px 8px; min-height:300px; }}
.panel.active {{ display:block; }}
.unifilar {{ padding:18px; overflow:auto; text-align:center; }}
.unifilar svg {{ width:100%; height:auto; max-height:980px; }}
#workspace-unifilar [data-element-id] {{ cursor:pointer; }}
#workspace-unifilar .workspace-selected {{ filter:drop-shadow(0 0 3px #2563eb); }}
#workspace-unifilar text[data-element-id] {{ font-weight:700; }}
.notice {{ margin:0 0 12px; padding:10px 12px; border-radius:7px; font-size:13px; }}
.notice.warning {{ color:var(--warn); background:#fffbeb; border:1px solid #fde68a; }}
.notice.error {{ color:var(--err); background:#fef2f2; border:1px solid #fecaca; }}
.summary {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin:0 0 12px; }}
.card {{ background:white; border:1px solid var(--line); border-radius:8px; padding:12px; }}
.card .k {{ color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.04em; }}
.card .v {{ margin-top:4px; font-size:18px; font-weight:700; }}
.table-wrap {{ overflow:auto; padding:14px; }}
table {{ width:100%; border-collapse:collapse; font-size:12px; }}
th,td {{ padding:9px 8px; border-bottom:1px solid #e5e7eb; text-align:left; white-space:nowrap; }}
th {{ color:var(--muted); font-size:11px; text-transform:uppercase; }}
.selectable-row {{ cursor:pointer; }}
.selectable-row:hover,.selectable-row.selected-row {{ background:var(--blue-soft); }}
.inspector {{ background:white; border:1px solid var(--line); border-radius:8px; padding:14px; position:sticky; top:12px; }}
.inspector h2 {{ margin:0 0 4px; font-size:16px; color:var(--blue); }}
.inspector .kind {{ color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.05em; margin-bottom:12px; }}
.inspector label {{ display:block; font-size:11px; font-weight:700; color:var(--muted); margin:0 0 5px; }}
.inspector select {{ width:100%; min-height:38px; border:1px solid #cbd5e1; border-radius:6px; background:white; padding:7px 8px; margin-bottom:14px; font:inherit; }}
.detail-grid {{ display:grid; grid-template-columns:1fr; gap:0; }}
.detail-row {{ display:grid; grid-template-columns:115px minmax(0,1fr); gap:8px; padding:8px 0; border-bottom:1px solid #eef2f7; font-size:12px; }}
.detail-row .dk {{ color:var(--muted); }}
.detail-row .dv {{ font-weight:600; overflow-wrap:anywhere; }}
.chat-hint {{ margin-top:14px; padding:10px; border-radius:7px; background:#f8fafc; border:1px solid #e2e8f0; font-size:11px; line-height:1.45; }}
.empty-inspector {{ color:var(--muted); font-size:12px; line-height:1.5; padding:6px 0 2px; }}
.footer {{ margin-top:10px; color:var(--muted); font-size:11px; }}
@media (max-width:980px) {{ .workspace-layout {{ grid-template-columns:1fr; }} .inspector {{ position:static; }} }}
@media (max-width:760px) {{ .summary {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} header {{ flex-direction:column; }} .shell {{ padding:10px; }} }}
@media print {{ body {{ background:white; }} .shell {{ max-width:none; padding:0; }} .toolbar,.tabs,.footer,.notice,.inspector {{ display:none !important; }} .workspace-layout {{ display:block; }} .panel {{ display:none !important; border:0; }} #panel-unifilar {{ display:block !important; }} header {{ margin-bottom:6mm; }} .summary {{ break-inside:avoid; }} .unifilar {{ padding:0; overflow:visible; }} .unifilar svg {{ max-height:none; }} }}
</style>
</head>
<body>
<div class="shell">
<header>
  <div><h1>{escape(title)}</h1><div class="meta">Circuito: {escape(str(snapshot['model'].get('circuit') or '—'))} · Revisión modelo: {status['model_revision']} · Revisión visual: {status['visual_revision']}</div></div>
  <div class="status {tone}">{escape(label)}</div>
</header>
{notices_html}
<div class="summary">
  <div class="card"><div class="k">Buses</div><div class="v">{len(snapshot['model'].get('buses', []))}</div></div>
  <div class="card"><div class="k">Alimentadores</div><div class="v">{len(snapshot['model'].get('lines', []))}</div></div>
  <div class="card"><div class="k">Cargas</div><div class="v">{len(snapshot['model'].get('loads', []))}</div></div>
  <div class="card"><div class="k">Pérdidas</div><div class="v">{f'{losses:g} kW' if losses is not None else '—'}</div></div>
</div>
<div class="toolbar">
  <button type="button" class="primary" id="printBtn">Imprimir / PDF</button>
  <button type="button" id="svgBtn">Descargar SVG</button>
  <button type="button" id="reloadBtn">Recargar archivo</button>
</div>
<div class="workspace-layout">
  <div class="workspace-content">
    <div class="tabs" role="tablist">
      <button type="button" class="tab active" data-tab="unifilar">Unifilar</button>
      <button type="button" class="tab" data-tab="datos">Datos</button>
    </div>
    <section class="panel active" id="panel-unifilar"><div class="unifilar" id="workspace-unifilar">{svg}</div></section>
    <section class="panel" id="panel-datos">
      <div class="table-wrap"><table><thead><tr><th>Elemento</th><th>Tipo</th><th>Conexión</th><th>Dato 1</th><th>Dato 2</th><th>Estado</th></tr></thead><tbody>{_data_rows(snapshot)}</tbody></table></div>
    </section>
  </div>
  <aside class="inspector" aria-live="polite">
    <label for="elementSelect">Elemento</label>
    <select id="elementSelect">{_element_options(catalog)}</select>
    <h2 id="inspectorTitle">Inspector técnico</h2>
    <div class="kind" id="inspectorKind">Sin selección</div>
    <div id="inspectorBody" class="empty-inspector">Haz clic en una etiqueta o símbolo del unifilar, selecciona una fila en Datos o usa la lista superior.</div>
    <div class="chat-hint" id="chatHint">Las modificaciones continúan haciéndose en ChatGPT. Selecciona un elemento para obtener una referencia inequívoca que puedas mencionar en la conversación.</div>
  </aside>
</div>
<div class="footer">Última actualización UTC: {escape(str(status.get('last_update') or '—'))} · El HTML es una vista; ChatGPT + MCP Eléctrico siguen siendo la interfaz de control.</div>
<script type="application/json" id="workspace-snapshot">{serialized}</script>
<script type="application/json" id="workspace-catalog">{catalog_json}</script>
<script>
(() => {{
  const snapshot = JSON.parse(document.getElementById('workspace-snapshot').textContent);
  const catalog = JSON.parse(document.getElementById('workspace-catalog').textContent);
  const byId = new Map(catalog.map(item => [item.id, item]));
  const model = snapshot.model || {{}};
  const tabs = [...document.querySelectorAll('.tab')];
  const panels = {{ unifilar: document.getElementById('panel-unifilar'), datos: document.getElementById('panel-datos') }};
  const select = document.getElementById('elementSelect');
  const titleNode = document.getElementById('inspectorTitle');
  const kindNode = document.getElementById('inspectorKind');
  const bodyNode = document.getElementById('inspectorBody');
  const hintNode = document.getElementById('chatHint');

  const esc = value => String(value ?? '—').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
  const kindName = kind => ({{bus:'Bus / barra',line:'Alimentador',transformer:'Transformador',load:'Carga',generator:'Generador'}}[kind] || kind);
  const rowsHtml = rows => `<div class="detail-grid">${{rows.filter(r => r[1] !== undefined && r[1] !== null && r[1] !== '').map(r => `<div class="detail-row"><div class="dk">${{esc(r[0])}}</div><div class="dv">${{esc(r[1])}}</div></div>`).join('')}}</div>`;

  function findRaw(meta) {{
    const name = meta.name.toLowerCase();
    const lists = {{
      bus: model.buses || [],
      line: model.lines || [],
      transformer: model.transformers || [],
      load: model.loads || [],
      generator: model.generators || []
    }};
    return (lists[meta.kind] || []).find(x => String(x.name).toLowerCase() === name) || null;
  }}

  function powerflowBus(name) {{
    const pf = snapshot.status?.studies?.powerflow;
    if (!pf?.valid) return null;
    const data = pf.result?.voltajes_por_bus || {{}};
    return Object.entries(data).find(([key]) => key.toLowerCase() === name.toLowerCase())?.[1] || null;
  }}

  function sourceRows() {{
    const s = model.source;
    if (!s) return [];
    const max = s.scenarios?.max;
    const min = s.scenarios?.min;
    const ref = s.provenance?.scc_max_mva?.reference;
    return [
      ['Fuente P2', s.mode],
      ['Escenario activo', s.active_scenario],
      ['Scc3 máxima', max ? `${{max.scc3_mva}} MVA` : 'NO DISPONIBLE'],
      ['X/R máximo', max?.x_r],
      ['Scc3 mínima', min ? `${{min.scc3_mva}} MVA` : 'NO DISPONIBLE'],
      ['X/R mínimo', min?.x_r],
      ['Secuencia cero', s.zero_sequence?.status || 'NOT_AVAILABLE'],
      ['Procedencia', ref]
    ];
  }}

  function inspectorRows(meta, raw) {{
    if (!raw) return [['ID', meta.id]];
    if (meta.kind === 'bus') {{
      const pf = powerflowBus(raw.name);
      const role = raw.visual?.rol || 'auto';
      const volts = pf?.voltajes_pu?.length ? pf.voltajes_pu.map(v => `${{Number(v).toFixed(4)}} pu`).join(' · ') : null;
      const base = [['Referencia MCP', meta.id],['Nombre OpenDSS', raw.name],['Rol visual', role],['Tensión base LN', pf ? `${{pf.kv_base}} kV` : null],['Voltajes', volts],['Resultado vigente', pf ? 'Sí' : 'No / no calculado']];
      return raw.name.toLowerCase() === 'sourcebus' ? base.concat(sourceRows()) : base;
    }}
    if (meta.kind === 'line') {{
      const v = raw.visual || {{}};
      let protection = String(v.proteccion || 'breaker').toUpperCase();
      if (v.corriente_nominal_a) protection += ` · ${{v.corriente_nominal_a}} A`;
      if (v.capacidad_ruptura_ka) protection += ` · ${{v.capacidad_ruptura_ka}} kA`;
      return [['Referencia MCP', meta.id],['Nombre OpenDSS', raw.name],['Desde', raw.bus1],['Hasta', raw.bus2],['Longitud', `${{raw.length}} km`],['R1', `${{raw.r1}} Ω/km`],['X1', `${{raw.x1}} Ω/km`],['Conductor', v.conductor || 'No especificado'],['Protección', protection],['Estado', raw.open ? 'ABIERTO' : 'Cerrado']];
    }}
    if (meta.kind === 'transformer') {{
      const w = raw.windings || [];
      const w1 = w[0] || {{}}, w2 = w[1] || {{}};
      const conn = x => x === 'delta' ? 'Δ' : (x === 'wye' ? 'Y' : x || '—');
      const p = raw.professional;
      const base = [['Referencia MCP', meta.id],['Nombre OpenDSS', raw.name],['Buses', (raw.buses || []).join(' → ')],['Potencia', w1.kva != null ? `${{w1.kva}} kVA` : null],['Relación', w1.kv != null && w2.kv != null ? `${{w1.kv}} / ${{w2.kv}} kV` : null],['Conexión', `${{conn(w1.connection)}} / ${{conn(w2.connection)}}`],['Estado', raw.open ? 'ABIERTO' : 'Cerrado']];
      if (!p) return base.concat([['Datos P2','NO DISPONIBLE — transformador legado']]);
      const t = p.tap || {{}};
      const sc = p.short_circuit || {{}};
      const losses = p.losses || {{}};
      const ref = p.provenance?.uk_percent?.reference;
      return base.concat([
        ['Grupo vectorial', p.vector_group?.grupo_vectorial],
        ['uk / %Z', sc.uk_percent != null ? `${{sc.uk_percent}} %` : 'NO DISPONIBLE'],
        ['X/R efectivo', sc.x_r_effective],
        ['R serie total', sc.r_percent_total != null ? `${{Number(sc.r_percent_total).toFixed(4)}} %` : null],
        ['X serie', sc.x_percent != null ? `${{Number(sc.x_percent).toFixed(4)}} %` : null],
        ['Pérdidas carga', sc.load_loss_kw != null ? `${{sc.load_loss_kw}} kW` : 'NO DISPONIBLE'],
        ['Pérdidas vacío', losses.no_load_loss_kw != null ? `${{losses.no_load_loss_kw}} kW` : 'NO DISPONIBLE'],
        ['I0', losses.i0_percent != null ? `${{losses.i0_percent}} %` : 'NO DISPONIBLE'],
        ['Tap', t.enabled ? `${{t.side}} · pos ${{t.position}} · ${{t.step_percent}} %/paso` : 'Sin cambiador declarado'],
        ['Procedencia', ref || 'dato_explicito_usuario'],
        ['Pandapower', p.projection?.pandapower_ready ? 'Datos suficientes P2' : 'No compatible'],
        ['Secuencia cero', p.projection?.zero_sequence_ready ? 'Disponible' : 'NO DISPONIBLE']
      ]);
    }}
    if (meta.kind === 'load') {{
      return [['Referencia MCP', meta.id],['Nombre OpenDSS', raw.name],['Bus', raw.bus],['Tipo visual', raw.visual_type],['Potencia activa', `${{raw.kw}} kW`],['Potencia reactiva', `${{raw.kvar}} kvar`],['Carga crítica', raw.critical ? 'Sí' : 'No']];
    }}
    if (meta.kind === 'generator') {{
      return [['Referencia MCP', meta.id],['Nombre OpenDSS', raw.name],['Bus', raw.bus],['Potencia', `${{raw.kw}} kW`],['Tensión', `${{raw.kv}} kV`]];
    }}
    return [['Referencia MCP', meta.id]];
  }}

  function clearSelectionStyles() {{
    document.querySelectorAll('#workspace-unifilar .workspace-selected').forEach(n => n.classList.remove('workspace-selected'));
    document.querySelectorAll('.selectable-row.selected-row').forEach(n => n.classList.remove('selected-row'));
  }}

  function selectElement(id) {{
    if (!id || !byId.has(id)) {{
      clearSelectionStyles();
      select.value = '';
      titleNode.textContent = 'Inspector técnico';
      kindNode.textContent = 'Sin selección';
      bodyNode.className = 'empty-inspector';
      bodyNode.textContent = 'Haz clic en una etiqueta o símbolo del unifilar, selecciona una fila en Datos o usa la lista superior.';
      hintNode.textContent = 'Las modificaciones continúan haciéndose en ChatGPT. Selecciona un elemento para obtener una referencia inequívoca que puedas mencionar en la conversación.';
      return;
    }}
    const meta = byId.get(id);
    const raw = findRaw(meta);
    clearSelectionStyles();
    document.querySelectorAll(`#workspace-unifilar [data-element-id="${{CSS.escape(id)}}"]`).forEach(n => n.classList.add('workspace-selected'));
    document.querySelectorAll(`.selectable-row[data-element-id="${{CSS.escape(id)}}"]`).forEach(n => n.classList.add('selected-row'));
    select.value = id;
    titleNode.textContent = meta.label;
    kindNode.textContent = kindName(meta.kind);
    bodyNode.className = '';
    bodyNode.innerHTML = rowsHtml(inspectorRows(meta, raw));
    hintNode.innerHTML = `Para modificar este elemento desde ChatGPT puedes referirte a <strong>${{esc(meta.label)}}</strong>. Identificador inequívoco: <strong>${{esc(id)}}</strong>.`;
  }}

  function annotateSvg() {{
    const svg = document.querySelector('#workspace-unifilar svg');
    if (!svg) return;
    const expectedSymbol = {{bus:'busbar',line:'breaker',transformer:'transformer',load:null,generator:'generator'}};
    const labelCandidates = [...svg.querySelectorAll('text')];
    catalog.forEach(meta => {{
      const target = meta.label.trim().toUpperCase();
      if (!target) return;
      const text = labelCandidates.find(node => (node.textContent || '').trim().toUpperCase().startsWith(target));
      if (!text) return;
      text.dataset.elementId = meta.id;
      text.setAttribute('role','button');
      text.setAttribute('tabindex','0');
      const expected = expectedSymbol[meta.kind];
      let sibling = text.previousElementSibling;
      let hops = 0;
      while (sibling && hops < 8) {{
        if (sibling.matches?.('[data-symbol]')) {{
          const symbol = sibling.getAttribute('data-symbol');
          const loadSymbols = ['motor','panel','load'];
          if ((meta.kind === 'load' && loadSymbols.includes(symbol)) || (!expected || symbol === expected)) {{
            sibling.dataset.elementId = meta.id;
            sibling.setAttribute('role','button');
            sibling.setAttribute('tabindex','0');
            break;
          }}
        }}
        sibling = sibling.previousElementSibling;
        hops += 1;
      }}
    }});
    svg.addEventListener('click', event => {{
      const hit = event.target.closest?.('[data-element-id]');
      if (hit) selectElement(hit.dataset.elementId);
    }});
    svg.addEventListener('keydown', event => {{
      if (event.key !== 'Enter' && event.key !== ' ') return;
      const hit = event.target.closest?.('[data-element-id]');
      if (!hit) return;
      event.preventDefault();
      selectElement(hit.dataset.elementId);
    }});
  }}

  tabs.forEach(btn => btn.addEventListener('click', () => {{
    tabs.forEach(x => x.classList.toggle('active', x === btn));
    Object.entries(panels).forEach(([name, panel]) => panel.classList.toggle('active', name === btn.dataset.tab));
  }}));
  select.addEventListener('change', () => selectElement(select.value));
  document.querySelectorAll('.selectable-row').forEach(row => row.addEventListener('click', () => selectElement(row.dataset.elementId)));

  document.getElementById('printBtn').addEventListener('click', () => window.print());
  document.getElementById('reloadBtn').addEventListener('click', () => location.reload());
  document.getElementById('svgBtn').addEventListener('click', () => {{
    const node = document.querySelector('#workspace-unifilar svg');
    if (!node) return;
    const blob = new Blob([node.outerHTML], {{type:'image/svg+xml;charset=utf-8'}});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'unifilar.svg'; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }}));

  annotateSvg();
}})();
</script>
</div>
</body>
</html>'''


def regenerate() -> dict[str, Any]:
    '''Regenera el workspace a partir del circuito y estado actuales.'''
    workspace_state.clear_workspace_error()
    snapshot = workspace_state.snapshot()
    path: Path = _config["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    companion_svg = path.with_name(f"{path.stem}_unifilar.svg")

    if snapshot["model"].get("buses"):
        generar_diagrama_unifilar(
            ruta_salida=str(companion_svg),
            mostrar_leyenda=False,
            titulo=_config["title"] or snapshot["model"].get("circuit") or "Diagrama unifilar",
            modo="ingenieria",
            orientacion="vertical",
            mostrar_marca=False,
            mostrar_reglas=False,
        )
        svg = companion_svg.read_text(encoding="utf-8")
    else:
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 300"><text x="400" y="150" text-anchor="middle" font-family="Arial" fill="#6b7280">Circuito vacío</text></svg>'

    path.write_text(_render_html(snapshot, svg), encoding="utf-8")
    _config["last_generation"] = str(path.resolve())
    return {
        "ok": True,
        "archivo_html": str(path.resolve()),
        "archivo_svg": str(companion_svg.resolve()) if companion_svg.exists() else None,
        "estado": workspace_state.status(),
    }


def safe_regenerate() -> dict[str, Any]:
    '''Actualiza la vista sin permitir que un fallo visual rompa OpenDSS.'''
    if not _config["auto_regenerate"]:
        return {"ok": True, "skipped": True, "reason": "auto_regenerate desactivado"}
    try:
        return regenerate()
    except Exception as exc:
        workspace_state.record_workspace_error(str(exc))
        return {"ok": False, "error": str(exc)}


def new_circuit(action: str = "crear_circuito") -> dict[str, Any]:
    workspace_state.reset_for_circuit(action)
    return safe_regenerate()


def model_changed(action: str) -> dict[str, Any]:
    workspace_state.mark_model_changed(action)
    return safe_regenerate()


def visual_changed(action: str) -> dict[str, Any]:
    workspace_state.mark_visual_changed(action)
    return safe_regenerate()


def solved(
    result: dict[str, Any],
    study: str = "powerflow",
    action: str = "resolver_modelo",
) -> dict[str, Any]:
    workspace_state.record_solution(result, study=study, action=action)
    return safe_regenerate()


def study(
    name: str,
    result: dict[str, Any],
    action: str | None = None,
    regenerate_view: bool = True,
) -> dict[str, Any]:
    workspace_state.record_study(name, result, action=action)
    return safe_regenerate() if regenerate_view else {"ok": True, "skipped": True}


def get_state() -> dict[str, Any]:
    return {
        "config": {
            "ruta_salida": str(_config["path"]),
            "titulo": _config["title"],
            "auto_regenerar": _config["auto_regenerate"],
            "ultima_generacion": _config["last_generation"],
        },
        "workspace": workspace_state.status(),
    }
