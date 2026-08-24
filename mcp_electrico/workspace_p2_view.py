"""Extensión P2/V2 del workspace para cables y condiciones de instalación.

Consume exclusivamente ``conductor_assignment`` ya serializado en el snapshot.
No ejecuta OpenDSS, no calcula ampacidad y no convierte la ampacidad publicada
por fabricante en ``Iz`` normativo. P3 conserva esa responsabilidad.
"""

from __future__ import annotations

from typing import Any

MARKER = "<!-- MCP-P2-CABLE-V2 -->"


def _css() -> str:
    return r'''
/* MCP P2 cable inspector v2 */
.p2-cable-block { margin-top:12px; border-top:2px solid #dbeafe; padding-top:10px; }
.p2-cable-title { display:flex; justify-content:space-between; gap:8px; align-items:center; margin-bottom:4px; }
.p2-cable-title strong { color:var(--blue); font-size:12px; }
.p2-trace-badge { display:inline-block; border-radius:999px; padding:3px 7px; font-size:9px; font-weight:700; text-transform:uppercase; }
.p2-trace-ok { color:#166534; background:#dcfce7; }
.p2-trace-missing { color:#92400e; background:#fef3c7; }
.p2-cable-note { margin-top:8px; padding:8px 9px; border-radius:6px; background:#f8fafc; border-left:3px solid #64748b; color:#475569; font-size:10px; line-height:1.45; }
.p2-cable-link { overflow-wrap:anywhere; word-break:break-word; font-weight:500; }
.p2-table-trace { display:inline-block; margin-left:6px; padding:2px 5px; border-radius:999px; font-size:9px; font-weight:700; color:#166534; background:#dcfce7; vertical-align:middle; }
'''


def _script() -> str:
    return r'''
<script data-module="mcp-p2-cable-v2">
(() => {
  const snapNode = document.getElementById('workspace-snapshot');
  const select = document.getElementById('elementSelect');
  const body = document.getElementById('inspectorBody');
  if (!snapNode || !select || !body) return;

  const snapshot = JSON.parse(snapNode.textContent);
  const lines = snapshot.model?.lines || [];
  const esc = value => String(value ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = (value, suffix='') => value === undefined || value === null || value === '' ? '—' : `${value}${suffix}`;

  function lineForId(id) {
    if (!id?.toLowerCase().startsWith('line.')) return null;
    return lines.find(line => String(line.id || `Line.${line.name}`).toLowerCase() === id.toLowerCase()) || null;
  }

  function conditionText(a) {
    const c = a?.condiciones_ampacidad || {};
    const parts = [];
    if (c.medium) parts.push(`medio: ${c.medium}`);
    if (c.formation) parts.push(`formación: ${c.formation}`);
    if (c.ambient_c != null) parts.push(`ambiente: ${c.ambient_c} °C`);
    if (c.ground_c != null) parts.push(`suelo: ${c.ground_c} °C`);
    return parts.join(' · ') || 'Condición publicada en catálogo';
  }

  function detailRows(rows) {
    return `<div class="detail-grid">${rows.map(([k,v,extra='']) => `<div class="detail-row"><div class="dk">${esc(k)}</div><div class="dv ${extra}">${esc(v)}</div></div>`).join('')}</div>`;
  }

  function renderCableBlock(line, selectedId) {
    const previous = body.querySelector('.p2-cable-block');
    if (previous?.dataset.for === selectedId) return;
    previous?.remove();

    const assignment = line?.conductor_assignment;
    const visualText = line?.visual?.conductor || null;
    const block = document.createElement('section');
    block.className = 'p2-cable-block';
    block.dataset.for = selectedId;

    if (!assignment) {
      block.innerHTML = `
        <div class="p2-cable-title"><strong>Cable / instalación P2</strong><span class="p2-trace-badge p2-trace-missing">sin trazabilidad</span></div>
        ${detailRows([
          ['Asignación de biblioteca', 'NO DISPONIBLE'],
          ['Anotación visual', visualText || 'No especificada'],
          ['R1 activo', fmt(line?.r1, ' Ω/km')],
          ['X1 activo', fmt(line?.x1, ' Ω/km')]
        ])}
        <div class="p2-cable-note">La anotación visual no equivale a una ficha técnica trazable. Asigna un conductor de biblioteca antes de usar sus datos como entrada profesional.</div>`;
      body.appendChild(block);
      return;
    }

    const p = assignment.producto || {};
    const source = assignment.fuente || {};
    const applied = assignment.impedancia_actualizada;
    const impedanceState = applied
      ? `Sí · R1 ${fmt(assignment.r1_aplicado_ohm_km, ' Ω/km')} · X1 ${fmt(assignment.x1_aplicado_ohm_km, ' Ω/km')}`
      : `No · ${assignment.motivo_impedancia_no_actualizada || 'se conserva la impedancia previa del modelo'}`;

    block.innerHTML = `
      <div class="p2-cable-title"><strong>Cable / instalación P2</strong><span class="p2-trace-badge p2-trace-ok">biblioteca trazable</span></div>
      ${detailRows([
        ['Código', assignment.codigo],
        ['Descripción', assignment.descripcion],
        ['Familia', p.familia],
        ['Fabricante', p.fabricante],
        ['Referencia', p.referencia],
        ['Nivel', p.nivel],
        ['Sección', fmt(p.seccion_mm2, ' mm²')],
        ['Pantalla', p.pantalla_mm2 != null ? fmt(p.pantalla_mm2, ' mm²') : 'No publicada / no aplica'],
        ['Instalación', assignment.instalacion],
        ['Condición catálogo', conditionText(assignment)],
        ['Ampacidad catálogo', fmt(assignment.ampacidad_aplicada_a, ' A')],
        ['Rdc20', p.rdc20_ohm_km != null ? fmt(p.rdc20_ohm_km, ' Ω/km') : 'NO DISPONIBLE'],
        ['R1/X1 aplicados', impedanceState],
        ['R1 activo modelo', fmt(line?.r1, ' Ω/km')],
        ['X1 activo modelo', fmt(line?.x1, ' Ω/km')],
        ['Fuente', `${source.type || '—'} · confianza ${source.confidence || '—'}`],
        ['URL fuente', source.url || 'NO DISPONIBLE']
      ])}
      <div class="p2-cable-note"><strong>Ampacidad de catálogo.</strong> El valor mostrado corresponde a la condición publicada/asignada y todavía <strong>no es Iz normativo P3</strong>. P3 incorporará método de instalación, agrupamiento y factores de corrección versionados.</div>`;
    body.appendChild(block);
  }

  function enhanceTable() {
    document.querySelectorAll('.selectable-row[data-element-id^="Line."]').forEach(row => {
      const line = lineForId(row.dataset.elementId);
      if (!line) return;
      const cells = row.querySelectorAll('td');
      if (cells.length < 5) return;
      const a = line.conductor_assignment;
      if (a) {
        cells[4].innerHTML = `${esc(a.descripcion || a.codigo)}<span class="p2-table-trace">trazable</span>`;
        cells[4].title = `Biblioteca: ${a.codigo} · instalación: ${a.instalacion}`;
      } else if (line.visual?.conductor) {
        cells[4].title = 'Anotación visual sin asignación de biblioteca trazable';
      }
    });
  }

  function syncInspector() {
    const id = select.value;
    const line = lineForId(id);
    if (!line) {
      body.querySelector('.p2-cable-block')?.remove();
      return;
    }
    renderCableBlock(line, id);
  }

  let scheduled = false;
  const observer = new MutationObserver(() => {
    if (scheduled) return;
    scheduled = true;
    queueMicrotask(() => {
      scheduled = false;
      syncInspector();
    });
  });
  observer.observe(body, {childList:true, subtree:false});
  select.addEventListener('change', () => queueMicrotask(syncInspector));

  enhanceTable();
  syncInspector();
})();
</script>
'''


def enhance_html(html: str, snapshot: dict[str, Any]) -> str:
    """Añade la ficha P2 de cable a un workspace ya generado, idempotentemente."""
    if MARKER in html:
        return html
    html = html.replace("</style>", _css() + "\n</style>", 1)
    html = html.replace("</body>", MARKER + _script() + "\n</body>", 1)
    return html
