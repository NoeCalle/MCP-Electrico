"""Workspace HTML persistente para MCP Eléctrico.

ChatGPT sigue siendo la interfaz conversacional. Este módulo genera una vista
HTML autocontenida del circuito activo y de su estado de cálculo. No llama a
modelos de IA, no modifica impedancias y no realiza cálculos eléctricos.
"""

from __future__ import annotations

import json
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


def _data_rows(snapshot: dict[str, Any]) -> str:
    model = snapshot["model"]
    rows: list[str] = []
    for line in model.get("lines", []):
        visual = line.get("visual", {})
        label = visual.get("etiqueta") or line["name"]
        conductor = visual.get("conductor") or "—"
        rows.append(
            "<tr>"
            f"<td>{escape(str(label))}</td>"
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
        rows.append(
            "<tr>"
            f"<td>{escape(tr['name'])}</td>"
            "<td>Transformador</td>"
            f"<td>{escape(' → '.join(tr.get('buses', [])))}</td>"
            f"<td>{f'{kva:g} kVA' if kva is not None else '—'}</td>"
            f"<td>{escape(kv)}</td>"
            f"<td>{'ABIERTO' if tr['open'] else 'Cerrado'}</td>"
            "</tr>"
        )
    for load in model.get("loads", []):
        label = load.get("label") or load["name"]
        rows.append(
            "<tr>"
            f"<td>{escape(str(label))}</td>"
            f"<td>{escape(str(load.get('visual_type', 'carga')).title())}</td>"
            f"<td>{escape(load.get('bus', ''))}</td>"
            f"<td>{load.get('kw', 0):g} kW</td>"
            f"<td>{load.get('kvar', 0):g} kvar</td>"
            f"<td>{'Crítica' if load.get('critical') else '—'}</td>"
            "</tr>"
        )
    return "".join(rows) or '<tr><td colspan="6">No hay elementos para mostrar.</td></tr>'


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
:root {{ color-scheme: light; --ink:#111827; --muted:#6b7280; --line:#d1d5db; --blue:#0b3a6e; --ok:#166534; --warn:#92400e; --err:#b91c1c; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:Arial,Helvetica,sans-serif; color:var(--ink); background:#eef2f6; }}
.shell {{ max-width:1500px; margin:0 auto; padding:20px; }}
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
.tabs {{ display:flex; gap:4px; border-bottom:1px solid var(--line); margin-bottom:12px; }}
.tab {{ border:0; border-radius:7px 7px 0 0; background:transparent; padding:9px 14px; }}
.tab.active {{ background:white; color:var(--blue); font-weight:700; border:1px solid var(--line); border-bottom-color:white; margin-bottom:-1px; }}
.panel {{ display:none; background:white; border:1px solid var(--line); border-radius:0 8px 8px 8px; min-height:300px; }}
.panel.active {{ display:block; }}
.unifilar {{ padding:18px; overflow:auto; text-align:center; }}
.unifilar svg {{ width:100%; height:auto; max-height:980px; }}
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
.footer {{ margin-top:10px; color:var(--muted); font-size:11px; }}
@media (max-width:760px) {{ .summary {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} header {{ flex-direction:column; }} .shell {{ padding:10px; }} }}
@media print {{ body {{ background:white; }} .shell {{ max-width:none; padding:0; }} .toolbar,.tabs,.footer,.notice {{ display:none !important; }} .panel {{ display:none !important; border:0; }} #panel-unifilar {{ display:block !important; }} header {{ margin-bottom:6mm; }} .summary {{ break-inside:avoid; }} .unifilar {{ padding:0; overflow:visible; }} .unifilar svg {{ max-height:none; }} }}
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
<div class="tabs" role="tablist">
  <button type="button" class="tab active" data-tab="unifilar">Unifilar</button>
  <button type="button" class="tab" data-tab="datos">Datos</button>
</div>
<section class="panel active" id="panel-unifilar"><div class="unifilar" id="workspace-unifilar">{svg}</div></section>
<section class="panel" id="panel-datos">
  <div class="table-wrap"><table><thead><tr><th>Elemento</th><th>Tipo</th><th>Conexión</th><th>Dato 1</th><th>Dato 2</th><th>Estado</th></tr></thead><tbody>{_data_rows(snapshot)}</tbody></table></div>
</section>
<div class="footer">Última actualización UTC: {escape(str(status.get('last_update') or '—'))} · El HTML es una vista; ChatGPT + MCP Eléctrico siguen siendo la interfaz de control.</div>
<script type="application/json" id="workspace-snapshot">{serialized}</script>
<script>
(() => {{
  const tabs = [...document.querySelectorAll('.tab')];
  const panels = {{ unifilar: document.getElementById('panel-unifilar'), datos: document.getElementById('panel-datos') }};
  tabs.forEach(btn => btn.addEventListener('click', () => {{
    tabs.forEach(x => x.classList.toggle('active', x === btn));
    Object.entries(panels).forEach(([name, panel]) => panel.classList.toggle('active', name === btn.dataset.tab));
  }}));
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
  }});
}})();
</script>
</div>
</body>
</html>'''


def regenerate() -> dict[str, Any]:
    """Regenera el workspace a partir del circuito y estado actuales."""
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
    workspace_state.clear_workspace_error()
    _config["last_generation"] = str(path.resolve())
    return {
        "ok": True,
        "archivo_html": str(path.resolve()),
        "archivo_svg": str(companion_svg.resolve()) if companion_svg.exists() else None,
        "estado": workspace_state.status(),
    }


def safe_regenerate() -> dict[str, Any]:
    """Actualiza la vista sin permitir que un fallo visual rompa OpenDSS."""
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


def solved(result: dict[str, Any], study: str = "powerflow", action: str = "resolver_modelo") -> dict[str, Any]:
    workspace_state.record_solution(result, study=study, action=action)
    return safe_regenerate()


def study(name: str, result: dict[str, Any], action: str | None = None, regenerate_view: bool = True) -> dict[str, Any]:
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
