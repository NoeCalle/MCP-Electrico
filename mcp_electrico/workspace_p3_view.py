"""Vista V3 para resultados P3/P3A/P3B de ampacidad.

Consume exclusivamente resultados ya calculados y versionados en el snapshot.
El navegador no deriva Iz, no multiplica factores, no resuelve tablas normativas
y no evalúa Ib/In/Iz. La clasificación visual de evidencia y el resumen de
factores aplicados también se preparan en Python a partir de metadatos ya
presentes en el resultado P3.
"""

from __future__ import annotations

from html import escape
from typing import Any

MARKER = "<!-- MCP-P3-AMPACITY-V3 -->"


def _fmt(value: Any, decimals: int = 2, suffix: str = "") -> str:
    if value is None:
        return "—"
    try:
        text = f"{float(value):.{decimals}f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        text = str(value)
    return f"{text}{suffix}"


def _study(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    item = snapshot.get("status", {}).get("studies", {}).get("ampacity")
    if not item or not item.get("valid"):
        return None
    return item.get("result") or {}


def _routing_label(item: dict[str, Any]) -> tuple[str, str]:
    route = item.get("normative_applicability") or {}
    sources = item.get("sources", {})
    norm = sources.get("norm", {}) if isinstance(sources, dict) else {}
    profile = str(route.get("profile_id") or norm.get("id") or "—")
    method = str(route.get("installation_method") or "").strip()
    profile_method = f"{profile} / {method}" if method else profile
    route_status = str(route.get("status") or "MANUAL_FOUNDATION")
    return profile_method, route_status


def _evidence_label(item: dict[str, Any]) -> tuple[str, str]:
    """Devuelve etiqueta/clase visual sin inferir valores normativos."""
    installation = item.get("installation") or {}
    if str(installation.get("correction_mode") or "") == "BASE_CONDITIONS_CONFIRMED":
        return "BASE", "p3-evidence-base"

    evidence = item.get("factor_evidence") or {}
    manual = int(evidence.get("manual") or 0)
    primary = int(evidence.get("dataset_primary") or 0)
    secondary = int(evidence.get("dataset_secondary") or 0)
    total = int(evidence.get("total") or 0)
    kinds = sum(bool(value) for value in (manual, primary, secondary))

    if kinds > 1:
        return "MIXTA", "p3-evidence-mixed"
    if secondary:
        return "SECUNDARIA", "p3-evidence-secondary"
    if manual:
        return "MANUAL", "p3-evidence-manual"
    if primary and primary == total and bool(item.get("automatic_normative_lookup")):
        return "PRIMARIA", "p3-evidence-primary"
    return "INCOMPLETA", "p3-evidence-incomplete"


def _base_evidence_label(item: dict[str, Any]) -> tuple[str, str]:
    evidence = item.get("base_evidence") or {}
    if str(evidence.get("origin") or "") == "P2_CATALOG":
        return "CATÁLOGO P2", "p3-evidence-base"
    if bool(evidence.get("primary")):
        return "PRIMARIA", "p3-evidence-primary"
    if bool(evidence.get("normative_base")):
        return "SECUNDARIA", "p3-evidence-secondary"
    return "INCOMPLETA", "p3-evidence-incomplete"


def _base_evidence_detail(item: dict[str, Any]) -> str:
    """Resume tabla/columna/dataset ya resueltos por Python."""
    evidence = item.get("base_evidence") or {}
    table = str(evidence.get("table") or "").strip()
    column = evidence.get("table_column")
    dataset_id = str(evidence.get("dataset_id") or "").strip()
    parts: list[str] = []
    if table:
        parts.append(f"{table} col. {column}" if column is not None else table)
    if dataset_id:
        parts.append(dataset_id)
    return " · ".join(parts) or "—"


def _factor_detail(item: dict[str, Any]) -> str:
    """Resume factores ya revalidados por Python; no calcula ni hace lookup."""
    factors = (item.get("sources") or {}).get("factors") or []
    if not factors:
        return "—"
    details: list[str] = []
    for factor in factors:
        axis = str(factor.get("axis") or "factor")
        value = _fmt(factor.get("value"), 4)
        table = str(factor.get("table_or_clause") or "").strip()
        meta = factor.get("dataset") or {}
        dataset_id = str(meta.get("id") or "").strip()
        query = meta.get("query") or {}
        context: list[str] = []
        if query.get("ambient_temperature_c") is not None:
            context.append(f"{_fmt(query.get('ambient_temperature_c'), 1)} °C")
        if query.get("circuits_grouped") is not None:
            context.append(f"{query.get('circuits_grouped')} circuitos")
        if query.get("soil_thermal_resistivity_k_m_per_w") is not None:
            context.append(f"ρ={_fmt(query.get('soil_thermal_resistivity_k_m_per_w'), 2)} K·m/W")
        if query.get("burial_depth_scope") == "up_to_0_8_m":
            context.append("prof. ≤0.8 m")
        if query.get("table5d_branch") is not None:
            branch_labels = {
                "A_DIRECT_BURIED_CABLES": "5D-A directa",
                "B_MULTICORE_SINGLE_WAY_DUCTS": "5D-B multipolar/ducto",
                "C_SINGLE_CORE_SINGLE_WAY_DUCT_CIRCUITS": "5D-C unipolar/ducto",
            }
            context.append(branch_labels.get(str(query.get("table5d_branch")), str(query.get("table5d_branch"))))
        if query.get("spacing_id") is not None:
            spacing_labels = {
                "contact": "sep. contacto", "one_cable_diameter": "sep. 1 diámetro",
                "0_125_m": "sep. 0.125 m", "0_25_m": "sep. 0.25 m",
                "0_5_m": "sep. 0.5 m", "1_0_m": "sep. 1.0 m",
            }
            context.append(spacing_labels.get(str(query.get("spacing_id")), str(query.get("spacing_id"))))
        if query.get("burial_depth_m") is not None:
            context.append(f"prof.={_fmt(query.get('burial_depth_m'), 2)} m")
        parts = [f"{axis}: k={value}"]
        if table:
            parts.append(table)
        parts.extend(context)
        if dataset_id:
            parts.append(dataset_id)
        details.append(" · ".join(parts))
    return " | ".join(details)


def _panel(snapshot: dict[str, Any]) -> str:
    study = _study(snapshot)
    if not study:
        return '''<section class="panel p3-panel" id="panel-ampacidad">
<div class="p3-empty"><strong>Ampacidad P3 no evaluada.</strong><br>
Configura un perfil trazable de conductor, Ib, In y factores/condiciones y ejecuta “evaluar ampacidad”.</div>
</section>'''

    rows: list[str] = []
    for item in study.get("alimentadores", []):
        values = item.get("values", {})
        status = str(item.get("status") or "DATOS_INSUFICIENTES")
        css = {
            "CUMPLE": "p3-ok",
            "NO_CUMPLE": "p3-fail",
            "DATOS_INSUFICIENTES": "p3-missing",
        }.get(status, "p3-missing")
        profile_method, route_status = _routing_label(item)
        evidence_label, evidence_css = _evidence_label(item)
        base_label, base_css = _base_evidence_label(item)
        base_detail = _base_evidence_detail(item)
        factor_detail = _factor_detail(item)
        rows.append(
            f'<tr class="{css}" data-p3-element="{escape(str(item.get("element") or ""), quote=True)}">'
            f'<td>{escape(str(item.get("element") or "—"))}</td>'
            f'<td>{escape(profile_method)}</td>'
            f'<td>{escape(route_status)}</td>'
            f'<td>{_fmt(values.get("ib_a"), 2, " A")}</td>'
            f'<td>{_fmt(values.get("in_a"), 2, " A")}</td>'
            f'<td>{_fmt(values.get("iz_base_a"), 2, " A")}</td>'
            f'<td><span class="p3-evidence-badge {base_css}">{escape(base_label)}</span></td>'
            f'<td class="p3-base-detail">{escape(base_detail)}</td>'
            f'<td>{_fmt(values.get("factor_total"), 4)}</td>'
            f'<td class="p3-factor-detail">{escape(factor_detail)}</td>'
            f'<td>{_fmt(values.get("iz_a"), 2, " A")}</td>'
            f'<td><span class="p3-evidence-badge {evidence_css}">{escape(evidence_label)}</span></td>'
            f'<td><span class="p3-badge {css}">{escape(status)}</span></td>'
            "</tr>"
        )

    summary = study.get("summary", {})
    return f'''<section class="panel p3-panel" id="panel-ampacidad">
<div class="p3-header">
  <div><h3>Ampacidad — P3/P3A/P3B</h3><p>Criterio calculado por MCP Eléctrico: <strong>Ib ≤ In ≤ Iz</strong>.</p></div>
  <div class="p3-kpis">
    <span>Total <strong>{summary.get('total', 0)}</strong></span>
    <span>Cumple <strong>{summary.get('cumple', 0)}</strong></span>
    <span>No cumple <strong>{summary.get('no_cumple', 0)}</strong></span>
    <span>Datos insuf. <strong>{summary.get('datos_insuficientes', 0)}</strong></span>
  </div>
</div>
<div class="p3-note"><strong>UNDER_VALIDATION.</strong> V3 muestra el origen de Iz base y los factores realmente revalidados por Python. Los factores <code>exact_rows_v1</code> solo llegan a esta tabla después de pasar compatibilidad con routing e Iz base normativa. El navegador no resuelve tablas, multiplica factores ni clasifica evidencia.</div>
<div class="table-wrap"><table class="study-table"><thead><tr><th>Alimentador</th><th>Perfil / método</th><th>Routing</th><th>Ib</th><th>In</th><th>Iz base</th><th>Origen Iz base</th><th>Tabla / dataset base</th><th>∏k</th><th>Factores aplicados</th><th>Iz</th><th>Evidencia factores</th><th>Estado</th></tr></thead><tbody>{''.join(rows) or '<tr><td colspan="13">No existen perfiles P3 evaluados.</td></tr>'}</tbody></table></div>
</section>'''


def _css() -> str:
    return r'''
/* MCP P3 ampacity V3 */
.p3-panel { padding:0; }
.p3-panel.active { display:block; margin-top:12px; border-radius:8px; }
.p3-header { display:flex; justify-content:space-between; gap:18px; align-items:flex-start; padding:16px 16px 8px; }
.p3-header h3 { margin:0 0 4px; color:var(--blue); font-size:16px; }
.p3-header p { margin:0; color:var(--muted); font-size:12px; }
.p3-kpis { display:flex; flex-wrap:wrap; gap:8px; justify-content:flex-end; }
.p3-kpis span { background:#f8fafc; border:1px solid #e2e8f0; border-radius:7px; padding:7px 9px; font-size:11px; white-space:nowrap; }
.p3-note { margin:0 16px 6px; padding:9px 10px; background:#fffbeb; border-left:3px solid #d97706; color:#78350f; font-size:11px; line-height:1.45; }
.p3-empty { margin:16px; padding:18px; border:1px dashed #cbd5e1; border-radius:8px; color:var(--muted); line-height:1.55; }
.p3-panel tr[data-p3-element] { cursor:pointer; }
.p3-panel tr[data-p3-element]:hover { background:var(--blue-soft); }
.p3-base-detail,.p3-factor-detail { max-width:300px; overflow-wrap:anywhere; font-size:10px; line-height:1.35; }
.p3-badge,.p3-evidence-badge { display:inline-block; border-radius:999px; padding:4px 7px; font-size:9px; font-weight:700; }
.p3-badge.p3-ok { color:#166534; background:#dcfce7; }
.p3-badge.p3-fail { color:#b91c1c; background:#fee2e2; }
.p3-badge.p3-missing { color:#92400e; background:#fef3c7; }
.p3-evidence-primary { color:#166534; background:#dcfce7; }
.p3-evidence-secondary { color:#92400e; background:#fef3c7; }
.p3-evidence-manual { color:#1e40af; background:#dbeafe; }
.p3-evidence-base { color:#475569; background:#e2e8f0; }
.p3-evidence-mixed { color:#6b21a8; background:#f3e8ff; }
.p3-evidence-incomplete { color:#b91c1c; background:#fee2e2; }
.p3-panel tr.p3-fail td:first-child { border-left:3px solid #dc2626; }
.p3-panel tr.p3-ok td:first-child { border-left:3px solid #16a34a; }
@media (max-width:760px) { .p3-header { flex-direction:column; } .p3-kpis { justify-content:flex-start; } }
@media print { .p3-panel { display:block !important; break-inside:avoid; } }
'''


def _script() -> str:
    return r'''
<script data-module="mcp-p3-ampacity-v3">
(() => {
  const panel = document.getElementById('panel-ampacidad');
  const tab = document.querySelector('.tab[data-tab="ampacidad"]');
  if (!panel || !tab) return;

  document.querySelectorAll('.tab').forEach(btn => btn.addEventListener('click', () => {
    panel.classList.toggle('active', btn === tab);
  }));

  document.querySelectorAll('[data-p3-element]').forEach(row => row.addEventListener('click', () => {
    const id = row.dataset.p3Element;
    const select = document.getElementById('elementSelect');
    if (select && [...select.options].some(option => option.value === id)) {
      select.value = id;
      select.dispatchEvent(new Event('change', {bubbles:true}));
    }
  }));
})();
</script>
'''


def enhance_html(html: str, snapshot: dict[str, Any]) -> str:
    if MARKER in html:
        return html

    tab_anchor = '<button type="button" class="tab" data-tab="caida">Caída V</button>'
    if tab_anchor not in html:
        raise ValueError("V3: no se encontró la pestaña Caída V para insertar Ampacidad.")
    html = html.replace(
        tab_anchor,
        tab_anchor + '\n      <button type="button" class="tab" data-tab="ampacidad">Ampacidad</button>',
        1,
    )

    panel_anchor = '  </div>\n  <aside class="inspector"'
    if panel_anchor not in html:
        raise ValueError("V3: no se encontró el ancla de paneles del workspace.")
    html = html.replace(panel_anchor, _panel(snapshot) + '\n  </div>\n  <aside class="inspector"', 1)
    html = html.replace('</style>', _css() + '\n</style>', 1)
    html = html.replace('</body>', MARKER + _script() + '\n</body>', 1)
    return html