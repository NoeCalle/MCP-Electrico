"""Vista V5 read-only para protección y TCC P5.

Toda transformación eléctrica/gráfica de la TCC se prepara en Python. El
JavaScript añadido por esta vista solo gestiona navegación y selección del
elemento protegido; no interpola curvas, no calcula clearing time ni margen de
coordinación.
"""

from __future__ import annotations

from html import escape
from math import isfinite, log10
from typing import Any

MARKER = "<!-- MCP-P5-PROTECTION-V5 -->"
STUDY_KEYS = (
    "protection_tcc_evaluation",
    "protection_breaking_capacity",
    "protection_conductor_thermal",
    "protection_clearing_time",
    "protection_coordination",
)

_CHART_X0 = 48.0
_CHART_Y0 = 18.0
_CHART_W = 450.0
_CHART_H = 230.0


def _fmt(value: Any, decimals: int = 3, suffix: str = "") -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
        if not isfinite(number):
            return "—"
        text = f"{number:.{decimals}f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        text = str(value)
    return f"{text}{suffix}"


def _valid_study(snapshot: dict[str, Any], key: str) -> dict[str, Any] | None:
    item = snapshot.get("status", {}).get("studies", {}).get(key)
    if not item or not item.get("valid"):
        return None
    return item.get("result") or {}


def _dataset_map(datasets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("dataset_id") or ""): item for item in datasets if item.get("dataset_id")}


def _time_values(dataset: dict[str, Any]) -> list[float]:
    values: list[float] = []
    for segment in dataset.get("segments") or []:
        for point in segment.get("points") or []:
            for key in ("time_s", "time_min_s", "time_max_s"):
                raw = point.get(key)
                if raw is not None:
                    try:
                        value = float(raw)
                    except (TypeError, ValueError):
                        continue
                    if value > 0 and isfinite(value):
                        values.append(value)
    return values


def _current_values(dataset: dict[str, Any]) -> list[float]:
    values: list[float] = []
    for segment in dataset.get("segments") or []:
        for point in segment.get("points") or []:
            try:
                value = float(point.get("current_a"))
            except (TypeError, ValueError):
                continue
            if value > 0 and isfinite(value):
                values.append(value)
    return values


def _coord(value: float, low: float, high: float, start: float, span: float, invert: bool = False) -> float:
    lv = log10(value)
    lo = log10(low)
    hi = log10(high)
    ratio = 0.5 if hi == lo else (lv - lo) / (hi - lo)
    ratio = max(0.0, min(1.0, ratio))
    if invert:
        ratio = 1.0 - ratio
    return start + ratio * span


def _path(points: list[tuple[float, float]]) -> str:
    if not points:
        return ""
    return " ".join(
        ("M" if index == 0 else "L") + f"{x:.2f},{y:.2f}"
        for index, (x, y) in enumerate(points)
    )


def _chart(dataset: dict[str, Any]) -> str:
    currents = _current_values(dataset)
    times = _time_values(dataset)
    if not currents or not times:
        return '<div class="p5-chart-empty">Dataset sin puntos graficables.</div>'

    xmin, xmax = min(currents), max(currents)
    ymin, ymax = min(times), max(times)
    if xmin == xmax:
        xmin *= 0.9
        xmax *= 1.1
    if ymin == ymax:
        ymin *= 0.9
        ymax *= 1.1

    paths: list[str] = []
    shape = str(dataset.get("shape") or "").upper()
    for segment_index, segment in enumerate(dataset.get("segments") or []):
        raw_points = segment.get("points") or []
        if shape == "BAND":
            minimum: list[tuple[float, float]] = []
            maximum: list[tuple[float, float]] = []
            for point in raw_points:
                current = float(point["current_a"])
                minimum.append((
                    _coord(current, xmin, xmax, _CHART_X0, _CHART_W),
                    _coord(float(point["time_min_s"]), ymin, ymax, _CHART_Y0, _CHART_H, invert=True),
                ))
                maximum.append((
                    _coord(current, xmin, xmax, _CHART_X0, _CHART_W),
                    _coord(float(point["time_max_s"]), ymin, ymax, _CHART_Y0, _CHART_H, invert=True),
                ))
            paths.append(
                f'<path class="p5-tcc-line p5-tcc-min" data-segment="{segment_index}" d="{_path(minimum)}" />'
            )
            paths.append(
                f'<path class="p5-tcc-line p5-tcc-max" data-segment="{segment_index}" d="{_path(maximum)}" />'
            )
        else:
            single: list[tuple[float, float]] = []
            for point in raw_points:
                current = float(point["current_a"])
                single.append((
                    _coord(current, xmin, xmax, _CHART_X0, _CHART_W),
                    _coord(float(point["time_s"]), ymin, ymax, _CHART_Y0, _CHART_H, invert=True),
                ))
            paths.append(
                f'<path class="p5-tcc-line p5-tcc-single" data-segment="{segment_index}" d="{_path(single)}" />'
            )

    legend = (
        '<span><i class="p5-key p5-key-min"></i>t min</span><span><i class="p5-key p5-key-max"></i>t max</span>'
        if shape == "BAND"
        else '<span><i class="p5-key p5-key-single"></i>curva</span>'
    )
    return f'''<div class="p5-chart-wrap" data-p5-chart-precomputed="true">
<svg class="p5-tcc-chart" viewBox="0 0 530 280" role="img" aria-label="Curva TCC preparada en Python">
  <line class="p5-axis" x1="{_CHART_X0}" y1="{_CHART_Y0 + _CHART_H}" x2="{_CHART_X0 + _CHART_W}" y2="{_CHART_Y0 + _CHART_H}" />
  <line class="p5-axis" x1="{_CHART_X0}" y1="{_CHART_Y0}" x2="{_CHART_X0}" y2="{_CHART_Y0 + _CHART_H}" />
  {''.join(paths)}
  <text class="p5-axis-label" x="{_CHART_X0}" y="270">{escape(_fmt(xmin, 2, ' A'))}</text>
  <text class="p5-axis-label" x="{_CHART_X0 + _CHART_W}" y="270" text-anchor="end">{escape(_fmt(xmax, 2, ' A'))}</text>
  <text class="p5-axis-label" x="6" y="{_CHART_Y0 + 7}">{escape(_fmt(ymax, 3, ' s'))}</text>
  <text class="p5-axis-label" x="6" y="{_CHART_Y0 + _CHART_H}">{escape(_fmt(ymin, 3, ' s'))}</text>
</svg>
<div class="p5-chart-legend">{legend}<span>escala log-log preparada en Python</span></div>
</div>'''


def _rating_text(device: dict[str, Any]) -> str:
    ratings = device.get("ratings") or {}
    if device.get("device_type") == "fuse":
        return f"In {_fmt(ratings.get('in_a'), 1, ' A')} · poder corte {_fmt(ratings.get('breaking_capacity_ka'), 2, ' kA')}"
    return (
        f"In {_fmt(ratings.get('in_a'), 1, ' A')} · Icu {_fmt(ratings.get('icu_ka'), 2, ' kA')} · "
        f"Ics {_fmt(ratings.get('ics_ka'), 2, ' kA')} · Icw {_fmt(ratings.get('icw_ka'), 2, ' kA')}"
    )


def _device_card(device: dict[str, Any], datasets: dict[str, dict[str, Any]]) -> str:
    curve = device.get("curve") or {}
    dataset = datasets.get(str(curve.get("dataset_id") or ""))
    protected = str(device.get("protected_element") or "—")
    settings = device.get("settings") or {}
    source = (dataset or {}).get("source") or {}
    chart = _chart(dataset) if dataset else '<div class="p5-chart-empty">Sin dataset TCC numérico vinculado.</div>'
    return f'''<article class="p5-device-card" data-p5-device="{escape(str(device.get('id') or ''), quote=True)}" data-protected-element="{escape(protected, quote=True)}">
<div class="p5-device-head">
  <div><h3>{escape(str(device.get('id') or 'Protection.?'))}</h3><p>{escape(str(device.get('device_type') or '—'))} · protege <strong>{escape(protected)}</strong></p></div>
  <button type="button" class="p5-select-element" data-p5-select="{escape(protected, quote=True)}">Ver elemento</button>
</div>
<div class="p5-device-grid">
  <div><strong>Ratings</strong><span>{escape(_rating_text(device))}</span><span>Ue {_fmt((device.get('ratings') or {}).get('ue_kv'), 3, ' kV')}</span></div>
  <div><strong>Ajustes</strong><span>Ir {_fmt(settings.get('ir_a'), 1, ' A')} · Isd {_fmt(settings.get('isd_a'), 1, ' A')} · Ii {_fmt(settings.get('ii_a'), 1, ' A')}</span><span>base {escape(str(settings.get('basis') or '—'))}</span></div>
  <div><strong>Curva</strong><span>{escape(str(curve.get('id') or '—'))}</span><span>dataset {escape(str(curve.get('dataset_id') or '—'))} · {escape(str(curve.get('time_semantics') or '—'))}</span></div>
  <div><strong>Procedencia TCC</strong><span>{escape(str(source.get('reference') or '—'))}</span><span>{escape(str(source.get('revision') or 'sin revisión declarada'))}</span></div>
</div>
{chart}
</article>'''


def _study_summary(snapshot: dict[str, Any]) -> str:
    labels = {
        "protection_tcc_evaluation": "TCC",
        "protection_breaking_capacity": "Capacidad de corte",
        "protection_conductor_thermal": "Térmica conductor",
        "protection_clearing_time": "Clearing time",
        "protection_coordination": "Coordinación temporal",
    }
    rows: list[str] = []
    for key in STUDY_KEYS:
        result = _valid_study(snapshot, key)
        if result is None:
            continue
        status = str(result.get("status") or "REGISTRADO")
        device = result.get("device_id") or (result.get("relationship") or {}).get("downstream_device") or "—"
        detail = ""
        if key == "protection_coordination":
            detail = f"margen conservador {_fmt(result.get('conservative_margin_s'), 3, ' s')}"
        elif key == "protection_clearing_time":
            detail = f"t conservador {_fmt((result.get('clearing_time') or {}).get('conservative_time_s'), 3, ' s')}"
        elif key == "protection_breaking_capacity":
            detail = f"margen {_fmt(result.get('margin_ka'), 3, ' kA')}"
        elif key == "protection_conductor_thermal":
            detail = f"utilización {_fmt((result.get('results') or {}).get('utilization_ratio'), 3)}"
        elif key == "protection_tcc_evaluation":
            detail = f"I {_fmt(result.get('current_a'), 1, ' A')}"
        rows.append(
            f'<tr><td>{escape(labels[key])}</td><td>{escape(str(device))}</td><td><strong>{escape(status)}</strong></td><td>{escape(detail)}</td></tr>'
        )
    if not rows:
        return '<div class="p5-results-empty">No hay evaluaciones P5 registradas en la revisión vigente. Las curvas/datos pueden existir sin que se haya ejecutado todavía un check.</div>'
    return '<div class="table-wrap"><table class="study-table p5-results"><thead><tr><th>Estudio</th><th>Dispositivo</th><th>Estado</th><th>Detalle</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'


def _panel(snapshot: dict[str, Any], protection_snapshot: dict[str, Any], datasets: list[dict[str, Any]]) -> str:
    devices = protection_snapshot.get("devices") or []
    dmap = _dataset_map(datasets)
    cards = "\n".join(_device_card(device, dmap) for device in devices)
    if not cards:
        cards = '<div class="p5-empty"><strong>Protecciones P5 no configuradas.</strong><br>Registra interruptores/fusibles, curva y dataset TCC para habilitar la vista.</div>'
    return f'''<section class="panel p5-panel" id="panel-protecciones">
<div class="p5-panel-title"><div><h3>Protecciones y TCC — Workspace V5</h3><p>P5A–P5E · resultados y coordenadas preparados en Python/MCP.</p></div><span class="p5-maturity">EXPERIMENTAL · SIN EMISIÓN PROFESIONAL</span></div>
<div class="p5-policy"><strong>Política V5:</strong> no hay curvas sintéticas, extrapolación, promedios de bandas ni cálculo eléctrico en JavaScript. Un PASS P5E significa coordinación temporal puntual, no selectividad total.</div>
<div class="p5-device-list">{cards}</div>
<div class="p5-results-section"><h3>Resultados P5 vigentes</h3>{_study_summary(snapshot)}</div>
</section>'''


def _css() -> str:
    return r'''
/* MCP P5 protection/TCC V5 */
.p5-panel { padding:0; }
.p5-panel.active { display:block; margin-top:12px; border-radius:8px; }
.p5-panel-title { display:flex; justify-content:space-between; gap:12px; align-items:flex-start; padding:15px 16px 10px; border-bottom:1px solid #e2e8f0; }
.p5-panel-title h3,.p5-results-section h3 { margin:0 0 4px; color:var(--blue); font-size:16px; }
.p5-panel-title p { margin:0; color:var(--muted); font-size:11px; }
.p5-maturity { border:1px solid #f59e0b; background:#fffbeb; color:#92400e; border-radius:999px; padding:5px 8px; font-size:9px; font-weight:700; white-space:nowrap; }
.p5-policy { margin:10px 16px 0; padding:9px 10px; background:#eff6ff; border-left:3px solid #2563eb; color:#1e3a8a; font-size:11px; line-height:1.45; }
.p5-device-list { padding:12px 16px; display:grid; gap:12px; }
.p5-device-card { border:1px solid #dbe4ee; border-radius:9px; background:#fff; overflow:hidden; }
.p5-device-head { display:flex; justify-content:space-between; gap:12px; align-items:flex-start; padding:12px 13px 8px; background:#f8fafc; }
.p5-device-head h3 { margin:0 0 3px; color:#0f3b63; font-size:14px; }
.p5-device-head p { margin:0; color:var(--muted); font-size:11px; }
.p5-select-element { border:1px solid #cbd5e1; border-radius:6px; background:white; padding:5px 8px; cursor:pointer; font-size:10px; }
.p5-device-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:8px; padding:10px 13px; }
.p5-device-grid>div { display:flex; flex-direction:column; gap:3px; min-width:0; background:#f8fafc; border-radius:7px; padding:8px; font-size:10px; overflow-wrap:anywhere; }
.p5-device-grid strong { color:#334155; font-size:9px; text-transform:uppercase; letter-spacing:.04em; }
.p5-chart-wrap { padding:4px 13px 12px; }
.p5-tcc-chart { width:100%; max-height:300px; background:#fff; border:1px solid #e2e8f0; border-radius:7px; }
.p5-axis { stroke:#64748b; stroke-width:1; }
.p5-axis-label { fill:#64748b; font-size:9px; }
.p5-tcc-line { fill:none; stroke-width:2.2; stroke-linejoin:round; stroke-linecap:round; }
.p5-tcc-single { stroke:#2563eb; }
.p5-tcc-min { stroke:#16a34a; }
.p5-tcc-max { stroke:#dc2626; }
.p5-chart-legend { display:flex; flex-wrap:wrap; gap:12px; align-items:center; padding-top:5px; color:#64748b; font-size:9px; }
.p5-key { display:inline-block; width:14px; height:2px; margin-right:4px; vertical-align:middle; }
.p5-key-single { background:#2563eb; }.p5-key-min { background:#16a34a; }.p5-key-max { background:#dc2626; }
.p5-chart-empty,.p5-results-empty,.p5-empty { margin:10px 13px 13px; padding:14px; border:1px dashed #cbd5e1; border-radius:7px; color:var(--muted); font-size:11px; line-height:1.5; }
.p5-results-section { padding:4px 16px 16px; }
.p5-results-section h3 { font-size:13px; }
@media (max-width:900px) { .p5-device-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media (max-width:620px) { .p5-panel-title,.p5-device-head { flex-direction:column; } .p5-device-grid { grid-template-columns:1fr; } }
@media print { .p5-panel { display:block !important; break-inside:avoid; } .p5-device-card { break-inside:avoid; } .p5-select-element { display:none; } }
'''


def _script() -> str:
    return r'''
<script data-module="mcp-p5-protection-v5">
(() => {
  const panel = document.getElementById('panel-protecciones');
  const tab = document.querySelector('.tab[data-tab="protecciones"]');
  if (!panel || !tab) return;

  document.querySelectorAll('.tab').forEach(btn => btn.addEventListener('click', () => {
    const active = btn === tab;
    panel.classList.toggle('active', active);
    if (active) {
      document.querySelectorAll('.study-panel,.p3-panel,.p4-panel').forEach(other => other.classList.remove('active'));
      document.getElementById('panel-unifilar')?.classList.add('active');
      document.getElementById('panel-datos')?.classList.remove('active');
    }
  }));

  panel.querySelectorAll('[data-p5-select]').forEach(button => button.addEventListener('click', () => {
    const id = button.dataset.p5Select || '';
    const select = document.getElementById('elementSelect');
    if (select && [...select.options].some(option => option.value === id)) {
      select.value = id;
      select.dispatchEvent(new Event('change', {bubbles:true}));
    }
  }));
})();
</script>
'''


def enhance_html(
    html: str,
    snapshot: dict[str, Any],
    protection_snapshot: dict[str, Any],
    datasets: list[dict[str, Any]],
) -> str:
    """Añade la vista V5 P5 de forma idempotente."""
    if MARKER in html:
        return html

    tab_anchor = '<button type="button" class="tab" data-tab="cortocircuito">Cortocircuito</button>'
    if tab_anchor not in html:
        raise ValueError("V5: no se encontró la pestaña Cortocircuito para insertar Protecciones.")
    html = html.replace(
        tab_anchor,
        tab_anchor + '\n      <button type="button" class="tab" data-tab="protecciones">Protecciones / TCC</button>',
        1,
    )

    panel_anchor = '  </div>\n  <aside class="inspector"'
    if panel_anchor not in html:
        raise ValueError("V5: no se encontró el ancla de paneles del workspace.")
    html = html.replace(
        panel_anchor,
        _panel(snapshot, protection_snapshot, datasets) + '\n  </div>\n  <aside class="inspector"',
        1,
    )
    html = html.replace('</style>', _css() + '\n</style>', 1)
    html = html.replace('</body>', MARKER + _script() + '\n</body>', 1)
    return html
