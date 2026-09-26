"""Vista transversal de preparación de ingeniería para el Workspace V5.

No calcula ingeniería en el navegador. Consume snapshot + auditoría QA preparada
en Python y muestra, de forma read-only, si el modelo está modificado/resuelto,
qué placeholders TBC existen y qué findings bloquean el uso del modelo.
"""

from __future__ import annotations

from html import escape
from typing import Any

MARKER = "<!-- MCP-WORKSPACE-ENGINEERING-READINESS -->"


def _fmt(value: Any) -> str:
    if value is None or value == "":
        return "—"
    return str(value)


def _severity_class(severity: str) -> str:
    value = str(severity or "").upper()
    return {
        "BLOCKER": "readiness-sev-blocker",
        "ERROR": "readiness-sev-error",
        "WARNING": "readiness-sev-warning",
        "INFO": "readiness-sev-info",
    }.get(value, "readiness-sev-info")


def _status_label(snapshot: dict[str, Any]) -> tuple[str, str]:
    status = snapshot.get("status") or {}
    state = str(status.get("state") or "EMPTY")
    current = bool(status.get("results_current"))
    if state == "SOLVED" and current:
        return "RESUELTO · RESULTADOS VIGENTES", "readiness-state-ok"
    if state == "MODIFIED":
        return "CONSTRUIDO / MODIFICADO", "readiness-state-warning"
    if state == "ERROR":
        return "ERROR ELÉCTRICO", "readiness-state-error"
    return "SIN MODELO RESUELTO", "readiness-state-neutral"


def _summary(snapshot: dict[str, Any], qa: dict[str, Any]) -> str:
    status = snapshot.get("status") or {}
    placeholders = snapshot.get("model_placeholders") or {}
    qa_summary = qa.get("summary") or {}
    state_text, state_class = _status_label(snapshot)

    cards = [
        ("Estado", state_text, state_class),
        ("Revisión modelo", _fmt(status.get("model_revision")), ""),
        ("Revisión resuelta", _fmt(status.get("solved_revision")), ""),
        ("Resultados vigentes", "SÍ" if status.get("results_current") else "NO", ""),
        ("TBC / placeholders", _fmt(placeholders.get("count", 0)), "readiness-state-error" if placeholders.get("count") else "readiness-state-ok"),
        ("Blockers QA", _fmt(qa_summary.get("blockers", 0)), "readiness-state-error" if qa_summary.get("blockers") else "readiness-state-ok"),
        ("Errores QA", _fmt(qa_summary.get("errors", 0)), "readiness-state-error" if qa_summary.get("errors") else ""),
        ("Warnings QA", _fmt(qa_summary.get("warnings", 0)), "readiness-state-warning" if qa_summary.get("warnings") else ""),
    ]
    return '<div class="readiness-summary">' + "".join(
        f'<div class="readiness-card {escape(css)}"><span>{escape(label)}</span><strong>{escape(str(value))}</strong></div>'
        for label, value, css in cards
    ) + "</div>"


def _placeholders(snapshot: dict[str, Any]) -> str:
    items = (snapshot.get("model_placeholders") or {}).get("items") or []
    if not items:
        return '<div class="readiness-empty readiness-ok-box"><strong>Sin MODEL_PLACEHOLDER_TBC.</strong><br>No hay elementos TBC registrados en la revisión actual.</div>'

    rows = []
    for item in items:
        missing = ", ".join(str(x) for x in item.get("missing_fields") or []) or "—"
        known = item.get("known_data") or {}
        known_text = " · ".join(f"{k}={v}" for k, v in sorted(known.items())) or "—"
        rows.append(
            "<tr>"
            f"<td><strong>{escape(_fmt(item.get('id')))}</strong></td>"
            f"<td>{escape(_fmt(item.get('element_type')))}</td>"
            f"<td>{escape(missing)}</td>"
            f"<td>{escape(known_text)}</td>"
            f"<td>{escape(_fmt(item.get('source_reference')))}</td>"
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table class="study-table readiness-table">'
        "<thead><tr><th>Elemento TBC</th><th>Tipo</th><th>Datos faltantes</th><th>Datos conocidos</th><th>Fuente</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _findings(qa: dict[str, Any]) -> str:
    findings = qa.get("findings") or []
    if not findings:
        return '<div class="readiness-empty readiness-ok-box"><strong>QA base sin findings.</strong><br>No se detectaron blockers, errores ni warnings para el alcance auditado.</div>'

    rows = []
    for item in findings:
        sev = str(item.get("severity") or "INFO").upper()
        css = _severity_class(sev)
        rows.append(
            "<tr>"
            f'<td><span class="readiness-sev {escape(css)}">{escape(sev)}</span></td>'
            f"<td><strong>{escape(_fmt(item.get('code')))}</strong></td>"
            f"<td>{escape(_fmt(item.get('element')))}</td>"
            f"<td>{escape(_fmt(item.get('message')))}</td>"
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table class="study-table readiness-table">'
        "<thead><tr><th>Severidad</th><th>Código</th><th>Elemento</th><th>Hallazgo</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _module_checks(qa: dict[str, Any]) -> str:
    checks = qa.get("module_checks") or []
    if not checks:
        return "—"
    parts = []
    for item in checks:
        parts.append(
            f"{item.get('module')}: {item.get('status')}"
        )
    return " · ".join(parts)


def _panel(snapshot: dict[str, Any], qa: dict[str, Any]) -> str:
    qa_summary = qa.get("summary") or {}
    audit_ok = bool(qa_summary.get("model_data_ok"))
    audit_label = "QA BASE SIN BLOCKERS/ERRORES" if audit_ok else "QA BASE CON BLOQUEOS"
    audit_class = "readiness-state-ok" if audit_ok else "readiness-state-error"

    return f'''<section class="panel readiness-panel" id="panel-preparacion">
<div class="readiness-head">
  <div>
    <h3>Preparación de ingeniería</h3>
    <p>Estado del modelo, placeholders TBC y auditoría base preparada por Python/MCP.</p>
  </div>
  <span class="readiness-badge {audit_class}">{escape(audit_label)}</span>
</div>
<div class="readiness-policy">
  <strong>Lectura correcta:</strong> construido ≠ resuelto ≠ apto para cualquier estudio ≠ emisión profesional.
  Esta vista no ejecuta estudios ni completa datos faltantes.
</div>
{_summary(snapshot, qa)}
<div class="readiness-section">
  <div class="readiness-section-title"><h3>Placeholders TBC</h3><span>solver_materialized=false</span></div>
  {_placeholders(snapshot)}
</div>
<div class="readiness-section">
  <div class="readiness-section-title"><h3>Auditoría QA base</h3><span>{escape(_module_checks(qa))}</span></div>
  {_findings(qa)}
</div>
<div class="readiness-footer">
  <strong>Frontera:</strong> la auditoría mostrada corresponde al alcance base solicitado por el backend.
  No equivale a readiness universal ni cambia <code>professional_emission=false</code>.
</div>
</section>'''


def _css() -> str:
    return r'''
/* MCP engineering readiness view */
.readiness-panel{padding:0}
.readiness-panel.active{display:block;margin-top:12px;border-radius:8px}
.readiness-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;padding:15px 16px 10px;border-bottom:1px solid #e2e8f0}
.readiness-head h3,.readiness-section h3{margin:0 0 4px;color:var(--blue);font-size:16px}
.readiness-head p{margin:0;color:var(--muted);font-size:11px}
.readiness-badge{border-radius:999px;padding:5px 8px;font-size:9px;font-weight:800;white-space:nowrap;border:1px solid #cbd5e1}
.readiness-policy{margin:10px 16px 0;padding:9px 10px;background:#f8fafc;border-left:3px solid #334155;color:#334155;font-size:11px;line-height:1.45}
.readiness-summary{padding:12px 16px;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
.readiness-card{border:1px solid #e2e8f0;border-radius:8px;background:#fff;padding:9px 10px;display:flex;flex-direction:column;gap:4px;min-width:0}
.readiness-card span{font-size:9px;text-transform:uppercase;letter-spacing:.04em;color:#64748b;font-weight:700}
.readiness-card strong{font-size:13px;color:#0f172a;overflow-wrap:anywhere}
.readiness-state-ok{color:#166534!important;background:#f0fdf4!important;border-color:#bbf7d0!important}
.readiness-state-warning{color:#92400e!important;background:#fffbeb!important;border-color:#fde68a!important}
.readiness-state-error{color:#991b1b!important;background:#fef2f2!important;border-color:#fecaca!important}
.readiness-state-neutral{color:#475569!important;background:#f8fafc!important;border-color:#cbd5e1!important}
.readiness-section{padding:4px 16px 14px}
.readiness-section-title{display:flex;justify-content:space-between;gap:12px;align-items:end;margin-bottom:7px}
.readiness-section-title h3{font-size:13px;margin:0}
.readiness-section-title span{font-size:9px;color:#64748b;text-align:right}
.readiness-table td{vertical-align:top}
.readiness-sev{display:inline-block;border-radius:999px;padding:3px 6px;font-size:9px;font-weight:800}
.readiness-sev-blocker{color:#991b1b;background:#fee2e2}
.readiness-sev-error{color:#9a3412;background:#ffedd5}
.readiness-sev-warning{color:#92400e;background:#fef3c7}
.readiness-sev-info{color:#1e40af;background:#dbeafe}
.readiness-empty{padding:12px;border:1px dashed #cbd5e1;border-radius:7px;color:#475569;font-size:10px;line-height:1.5}
.readiness-ok-box{background:#f0fdf4;border-color:#bbf7d0}
.readiness-footer{margin:0 16px 16px;padding:9px 10px;border-radius:7px;background:#eff6ff;color:#1e3a8a;font-size:10px;line-height:1.45}
@media(max-width:900px){.readiness-summary{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:620px){.readiness-head,.readiness-section-title{flex-direction:column;align-items:flex-start}.readiness-summary{grid-template-columns:1fr}}
@media print{.readiness-panel{display:block!important;break-inside:avoid}.readiness-summary{grid-template-columns:repeat(4,minmax(0,1fr))}}
'''


def _script() -> str:
    return r'''
<script data-module="mcp-engineering-readiness">
(() => {
  const panel = document.getElementById('panel-preparacion');
  const tab = document.querySelector('.tab[data-tab="preparacion"]');
  if (!panel || !tab) return;
  document.querySelectorAll('.tab').forEach(btn => btn.addEventListener('click', () => {
    panel.classList.toggle('active', btn === tab);
  }));
})();
</script>
'''


def enhance_html(html: str, snapshot: dict[str, Any], qa: dict[str, Any]) -> str:
    """Añade la pestaña Preparación de forma idempotente."""
    if MARKER in html:
        return html

    tab_anchor = '<button type="button" class="tab" data-tab="protecciones">Protecciones / TCC</button>'
    if tab_anchor not in html:
        raise ValueError("Readiness view: no se encontró la pestaña Protecciones / TCC.")

    html = html.replace(
        tab_anchor,
        tab_anchor + '\n      <button type="button" class="tab" data-tab="preparacion">Preparación</button>',
        1,
    )

    panel_anchor = '  </div>\n  <aside class="inspector"'
    if panel_anchor not in html:
        raise ValueError("Readiness view: no se encontró el ancla de paneles.")

    html = html.replace(
        panel_anchor,
        _panel(snapshot, qa) + '\n  </div>\n  <aside class="inspector"',
        1,
    )
    html = html.replace("</style>", _css() + "\n</style>", 1)
    html = html.replace("</body>", MARKER + _script() + "\n</body>", 1)
    return html
