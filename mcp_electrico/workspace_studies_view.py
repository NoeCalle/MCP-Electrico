"""Extensión de vistas de estudios para el workspace HTML.

La vista consume exclusivamente el snapshot versionado. No ejecuta OpenDSS,
no recalcula magnitudes en JavaScript y no modifica el circuito. Se aplica
sobre el HTML base después de cada regeneración orquestada por `server.py`.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from . import workspace_p2_view

MARKER = "<!-- MCP-STUDIES-V1 -->"

# PR #5 dejó un cierre extra en el listener del botón SVG del HTML base. La
# extensión se ejecuta sobre todo workspace generado por `server.py`, por lo
# que normalizamos aquí ese HTML antes de añadir vistas. Se conserva como
# reparación explícita y verificable hasta mover el fix al renderer base.
_BASE_JS_BAD = "setTimeout(() => URL.revokeObjectURL(url), 1000);\n  }));\n\n  annotateSvg();"
_BASE_JS_FIXED = "setTimeout(() => URL.revokeObjectURL(url), 1000);\n  });\n\n  annotateSvg();"


def _repair_base_javascript(html: str) -> str:
    """Corrige una regresión sintáctica conocida del workspace interactivo."""
    return html.replace(_BASE_JS_BAD, _BASE_JS_FIXED)


def _fmt(value: Any, decimals: int = 3, suffix: str = "") -> str:
    if value is None:
        return "—"
    try:
        text = f"{float(value):.{decimals}f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        text = str(value)
    return f"{text}{suffix}"


def _study(snapshot: dict[str, Any], name: str) -> dict[str, Any] | None:
    item = snapshot.get("status", {}).get("studies", {}).get(name)
    if not item or not item.get("valid"):
        return None
    return item.get("result") or {}


def _flow_panel(snapshot: dict[str, Any]) -> str:
    flow = _study(snapshot, "flow")
    if not flow:
        return (
            '<section class="panel study-panel" id="panel-flujo">'
            '<div class="study-empty"><strong>Flujo detallado no calculado.</strong><br>'
            'Pídeme en ChatGPT: “ejecuta el flujo de potencia” para actualizar esta vista.</div>'
            "</section>"
        )

    rows = []
    for item in flow.get("alimentadores", []):
        loading = item.get("cargabilidad_pct")
        loading_text = _fmt(loading, 2, " %") if loading is not None else "—"
        rows.append(
            f'<tr data-study-element="{escape(str(item.get("id", "")), quote=True)}">'
            f'<td>{escape(str(item.get("label") or item.get("name") or "—"))}</td>'
            f'<td>{escape(str(item.get("bus1", "—")))} → {escape(str(item.get("bus2", "—")))}</td>'
            f'<td>{_fmt(item.get("corriente_max_a"), 2, " A")}</td>'
            f'<td>{_fmt(item.get("flujo_kw_terminal1"), 2, " kW")}</td>'
            f'<td>{_fmt(item.get("flujo_kvar_terminal1"), 2, " kvar")}</td>'
            f'<td>{loading_text}</td>'
            "</tr>"
        )
    summary = flow.get("resumen", {})
    return f'''<section class="panel study-panel" id="panel-flujo">
<div class="study-header">
  <div><h3>Flujo de potencia</h3><p>Resultados calculados por OpenDSS para la revisión vigente.</p></div>
  <div class="study-kpis">
    <span>Pérdidas <strong>{_fmt(summary.get('perdidas_totales_kw'), 3, ' kW')}</strong></span>
    <span>I máx. <strong>{_fmt(summary.get('corriente_max_alimentador_a'), 2, ' A')}</strong></span>
    <span>Carga máx. <strong>{_fmt(summary.get('cargabilidad_max_pct'), 2, ' %')}</strong></span>
  </div>
</div>
<div class="study-note">La cargabilidad solo aparece cuando existe una corriente nominal explícita en el modelo visual; no constituye por sí sola una verificación normativa de ampacidad.</div>
<div class="table-wrap"><table class="study-table"><thead><tr><th>Alimentador</th><th>Trayecto</th><th>Corriente máx.</th><th>kW T1</th><th>kvar T1</th><th>Cargabilidad</th></tr></thead><tbody>{''.join(rows) or '<tr><td colspan="6">No hay alimentadores.</td></tr>'}</tbody></table></div>
</section>'''


def _voltage_panel(snapshot: dict[str, Any]) -> str:
    study = _study(snapshot, "voltage_drop")
    if not study:
        return (
            '<section class="panel study-panel" id="panel-caida">'
            '<div class="study-empty"><strong>Caída de tensión no calculada.</strong><br>'
            'Pídeme en ChatGPT: “analiza la caída de tensión” y, si quieres, indica el límite porcentual.</div>'
            "</section>"
        )

    criterion = study.get("criterio", {})
    rows = []
    for item in study.get("alimentadores", []):
        state = str(item.get("estado_criterio") or "")
        cls = "study-exceeds" if state == "EXCEDE" else "study-ok"
        rows.append(
            f'<tr class="{cls}" data-study-element="{escape(str(item.get("id", "")), quote=True)}">'
            f'<td>{escape(str(item.get("label") or item.get("name") or "—"))}</td>'
            f'<td>{escape(str(item.get("bus_origen", "—")))} → {escape(str(item.get("bus_destino", "—")))}</td>'
            f'<td>{_fmt(item.get("vpu_origen_promedio"), 4, " pu")}</td>'
            f'<td>{_fmt(item.get("vpu_destino_promedio"), 4, " pu")}</td>'
            f'<td>{_fmt(item.get("caida_evaluada_pct"), 3, " %")}</td>'
            f'<td><span class="criterion-badge {cls}">{escape(state or "—")}</span></td>'
            "</tr>"
        )
    summary = study.get("resumen", {})
    return f'''<section class="panel study-panel" id="panel-caida">
<div class="study-header">
  <div><h3>Caída de tensión</h3><p>Comparación bus1 → bus2 por cada elemento Line.</p></div>
  <div class="study-kpis">
    <span>Límite <strong>{_fmt(criterion.get('limite_pct'), 2, ' %')}</strong></span>
    <span>Exceden <strong>{summary.get('alimentadores_que_exceden', 0)}</strong></span>
    <span>Vmin <strong>{_fmt(summary.get('vpu_min_sistema'), 4, ' pu')}</strong></span>
  </div>
</div>
<div class="study-note"><strong>Criterio configurable.</strong> El límite mostrado fue suministrado al estudio y no se presenta como requisito normativo universal. La caída evaluada es la mayor caída positiva entre fases disponibles; también se conserva el valor promedio firmado en el snapshot.</div>
<div class="table-wrap"><table class="study-table"><thead><tr><th>Alimentador</th><th>Trayecto</th><th>V origen</th><th>V destino</th><th>ΔV evaluada</th><th>Criterio</th></tr></thead><tbody>{''.join(rows) or '<tr><td colspan="6">No hay alimentadores.</td></tr>'}</tbody></table></div>
</section>'''


def _css() -> str:
    return '''
/* MCP studies v1 */
.study-panel { padding:0; }
.study-panel.active { margin-top:12px; border-radius:8px; }
.study-header { display:flex; justify-content:space-between; gap:18px; align-items:flex-start; padding:16px 16px 8px; }
.study-header h3 { margin:0 0 4px; color:var(--blue); font-size:16px; }
.study-header p { margin:0; color:var(--muted); font-size:12px; }
.study-kpis { display:flex; flex-wrap:wrap; gap:8px; justify-content:flex-end; }
.study-kpis span { background:#f8fafc; border:1px solid #e2e8f0; border-radius:7px; padding:7px 9px; font-size:11px; white-space:nowrap; }
.study-note { margin:0 16px 6px; padding:9px 10px; background:#f8fafc; border-left:3px solid #94a3b8; color:#475569; font-size:11px; line-height:1.45; }
.study-empty { margin:16px; padding:18px; border:1px dashed #cbd5e1; border-radius:8px; color:var(--muted); line-height:1.55; }
.study-table tr[data-study-element] { cursor:pointer; }
.study-table tr[data-study-element]:hover { background:var(--blue-soft); }
.criterion-badge { display:inline-block; min-width:58px; text-align:center; border-radius:999px; padding:4px 7px; font-size:10px; font-weight:700; }
.criterion-badge.study-ok { color:#166534; background:#dcfce7; }
.criterion-badge.study-exceeds { color:#b91c1c; background:#fee2e2; }
.study-table tr.study-exceeds td:first-child { border-left:3px solid #dc2626; }
.study-table tr.study-ok td:first-child { border-left:3px solid #16a34a; }
#workspace-unifilar .overlay-drop-ok { filter:drop-shadow(0 0 3px #16a34a); }
#workspace-unifilar .overlay-drop-exceeds { filter:drop-shadow(0 0 4px #dc2626); }
#workspace-unifilar .overlay-flow { filter:drop-shadow(0 0 3px #2563eb); }
#workspace-unifilar .overlay-overload { filter:drop-shadow(0 0 4px #dc2626); }
@media (max-width:760px) { .study-header { flex-direction:column; } .study-kpis { justify-content:flex-start; } }
@media print { .study-panel { display:none !important; } }
'''


def _script() -> str:
    return r'''
<script data-module="mcp-studies-v1">
(() => {
  const snapNode = document.getElementById('workspace-snapshot');
  if (!snapNode) return;
  const snapshot = JSON.parse(snapNode.textContent);
  const studies = snapshot.status?.studies || {};
  const allTabs = [...document.querySelectorAll('.tab')];
  const studyPanels = {
    flujo: document.getElementById('panel-flujo'),
    caida: document.getElementById('panel-caida')
  };

  function clearOverlay() {
    document.querySelectorAll('#workspace-unifilar .overlay-drop-ok,#workspace-unifilar .overlay-drop-exceeds,#workspace-unifilar .overlay-flow,#workspace-unifilar .overlay-overload')
      .forEach(n => n.classList.remove('overlay-drop-ok','overlay-drop-exceeds','overlay-flow','overlay-overload'));
  }

  function nodesFor(id) {
    return [...document.querySelectorAll('#workspace-unifilar [data-element-id]')]
      .filter(n => n.dataset.elementId === id);
  }

  function applyOverlay(mode) {
    clearOverlay();
    if (mode === 'caida') {
      const study = studies.voltage_drop;
      if (!study?.valid) return;
      (study.result?.alimentadores || []).forEach(item => {
        const cls = item.estado_criterio === 'EXCEDE' ? 'overlay-drop-exceeds' : 'overlay-drop-ok';
        nodesFor(item.id).forEach(n => n.classList.add(cls));
      });
    }
    if (mode === 'flujo') {
      const study = studies.flow;
      if (!study?.valid) return;
      (study.result?.alimentadores || []).forEach(item => {
        const cls = item.cargabilidad_pct != null && Number(item.cargabilidad_pct) > 100 ? 'overlay-overload' : 'overlay-flow';
        nodesFor(item.id).forEach(n => n.classList.add(cls));
      });
    }
  }

  allTabs.forEach(btn => btn.addEventListener('click', () => {
    const name = btn.dataset.tab;
    Object.entries(studyPanels).forEach(([key, panel]) => panel?.classList.toggle('active', key === name));
    if (name === 'flujo' || name === 'caida') {
      document.getElementById('panel-unifilar')?.classList.add('active');
      document.getElementById('panel-datos')?.classList.remove('active');
      applyOverlay(name);
    } else {
      Object.values(studyPanels).forEach(panel => panel?.classList.remove('active'));
      clearOverlay();
    }
  }));

  document.querySelectorAll('[data-study-element]').forEach(row => row.addEventListener('click', () => {
    const id = row.dataset.studyElement;
    const select = document.getElementById('elementSelect');
    if (select && [...select.options].some(o => o.value === id)) {
      select.value = id;
      select.dispatchEvent(new Event('change', {bubbles:true}));
    }
  }));
})();
</script>
'''


def enhance_html(html: str, snapshot: dict[str, Any]) -> str:
    """Añade pestañas de estudios y extensiones P2 al HTML base idempotentemente."""
    html = _repair_base_javascript(html)
    if MARKER in html:
        return workspace_p2_view.enhance_html(html, snapshot)

    tabs_anchor = '      <button type="button" class="tab" data-tab="datos">Datos</button>'
    tabs = tabs_anchor + '\n      <button type="button" class="tab" data-tab="flujo">Flujo</button>\n      <button type="button" class="tab" data-tab="caida">Caída V</button>'
    if tabs_anchor not in html:
        raise ValueError("No se encontró el ancla de pestañas del workspace base.")
    html = html.replace(tabs_anchor, tabs, 1)

    panel_anchor = '    </section>\n  </div>\n  <aside class="inspector"'
    panels = '    </section>\n' + _flow_panel(snapshot) + '\n' + _voltage_panel(snapshot) + '\n  </div>\n  <aside class="inspector"'
    if panel_anchor not in html:
        raise ValueError("No se encontró el ancla de paneles del workspace base.")
    html = html.replace(panel_anchor, panels, 1)

    html = html.replace('</style>', _css() + '\n</style>', 1)
    html = html.replace('</body>', MARKER + _script() + '\n</body>', 1)
    return workspace_p2_view.enhance_html(html, snapshot)


def enhance_file(path: str | Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    """Enriquece un workspace ya regenerado y devuelve un resumen."""
    target = Path(path).expanduser()
    if not target.exists():
        return {"ok": False, "error": f"Workspace no encontrado: {target}"}
    original = target.read_text(encoding="utf-8")
    enhanced = enhance_html(original, snapshot)
    target.write_text(enhanced, encoding="utf-8")
    return {
        "ok": True,
        "archivo_html": str(target.resolve()),
        "flujo_vigente": bool(_study(snapshot, "flow")),
        "caida_tension_vigente": bool(_study(snapshot, "voltage_drop")),
        "p2_cable_inspector": workspace_p2_view.MARKER in enhanced,
    }
