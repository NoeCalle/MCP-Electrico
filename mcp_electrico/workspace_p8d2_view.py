"""Vista read-only P8E1 para el resultado integrado P8D2 dentro de Workspace V5.

No calcula ingeniería ni modifica el modelo. Consume exclusivamente el estudio
vigente ``protection_tcc`` registrado por P8D2 y lo inserta en el panel V5 ya
existente de protecciones/TCC.
"""

from __future__ import annotations

from html import escape
from math import isfinite
from typing import Any

MARKER = "<!-- MCP-P8E1-P8D2-RESULTS-V5 -->"
STUDY_KEY = "protection_tcc"
EXPECTED_SCHEMA = "MCP_ELECTRICO_P8D2_PROTECTION_RESULTS_V1"


def _fmt(value: Any, decimals: int = 3, suffix: str = "") -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not isfinite(number):
        return "—"
    text = f"{number:.{decimals}f}".rstrip("0").rstrip(".")
    return f"{text}{suffix}"


def _valid_aggregate(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    item = (snapshot.get("status") or {}).get("studies", {}).get(STUDY_KEY)
    if not item or item.get("valid") is not True:
        return None
    result = item.get("result") or {}
    if result.get("schema") != EXPECTED_SCHEMA:
        return None
    if result.get("model_revision") != item.get("model_revision"):
        return None
    return result


def _engine_label(value: Any) -> str:
    if isinstance(value, dict):
        return str(
            value.get("engine")
            or value.get("name")
            or value.get("backend")
            or value.get("id")
            or "pandapower"
        )
    text = str(value or "").strip()
    return text or "pandapower"


def _breaking_text(result: dict[str, Any]) -> str:
    status = str(result.get("status") or "—")
    rating = result.get("rating_used") or {}
    rating_type = str(rating.get("type") or "rating")
    rating_value = _fmt(rating.get("value_ka"), 3, " kA")
    margin = _fmt(result.get("margin_ka"), 3, " kA")
    return f"{status} · {rating_type} {rating_value} · margen {margin}"


def _clearing_text(result: dict[str, Any]) -> str:
    status = str(result.get("status") or "—")
    clearing = result.get("clearing_time") or {}
    if status == "CLEARING_TIME_READY":
        return f"{status} · t cons. {_fmt(clearing.get('conservative_time_s'), 4, ' s')}"
    return status


def _thermal_text(result: dict[str, Any]) -> str:
    status = str(result.get("status") or "—")
    values = result.get("results") or {}
    ratio = values.get("utilization_ratio")
    if ratio is None:
        return status
    return f"{status} · utilización {_fmt(ratio, 3)}"


def _device_row(device: dict[str, Any]) -> str:
    fault = device.get("fault_provenance") or {}
    breaking = device.get("breaking_capacity") or {}
    clearing = device.get("clearing_time") or {}
    thermal = device.get("thermal_check") or {}

    fault_label = (
        f"{fault.get('fault_type') or '—'} · {str(fault.get('case') or '—').upper()}"
        f" @ {fault.get('fault_bus') or '—'}"
    )
    current_label = (
        f"{fault.get('current_quantity') or '—'} = "
        f"{_fmt(fault.get('fault_current_ka'), 4, ' kA')}"
    )
    p4_label = (
        f"{_engine_label(fault.get('engine'))} · {fault.get('atomic_schema') or '—'} · "
        f"{fault.get('binding_source_reference') or '—'}"
    )

    return (
        "<tr>"
        f"<td><strong>{escape(str(device.get('device_id') or '—'))}</strong><br>"
        f"<span>{escape(str(device.get('device_type') or '—'))}</span></td>"
        f"<td>{escape(str(device.get('protected_element') or '—'))}</td>"
        f"<td>{escape(fault_label)}<br><span>{escape(current_label)}</span></td>"
        f"<td>{escape(_breaking_text(breaking))}</td>"
        f"<td>{escape(_clearing_text(clearing))}</td>"
        f"<td>{escape(_thermal_text(thermal))}</td>"
        f"<td>{escape(p4_label)}</td>"
        "</tr>"
    )


def _section(aggregate: dict[str, Any]) -> str:
    devices = aggregate.get("devices") or []
    rows = "".join(_device_row(item) for item in devices if isinstance(item, dict))
    if not rows:
        rows = '<tr><td colspan="7">P8D2 no contiene dispositivos renderizables.</td></tr>'

    status = escape(str(aggregate.get("execution_status") or "—"))
    revision = escape(str(aggregate.get("model_revision") or "—"))
    return f'''{MARKER}
<div class="p8d2-results-section" data-module="mcp-p8e1-p8d2-v5" data-model-revision="{revision}">
  <div class="p8d2-results-head">
    <div><h3>Resultado integrado P8D2</h3><p>Binding explícito P4 → P5 · revisión {revision}</p></div>
    <span class="p8d2-status">{status}</span>
  </div>
  <div class="p8d2-policy"><strong>Trazabilidad:</strong> cada fila consume el Ik'' ya calculado en P4. No hay selección automática de barra/caso ni recálculo de cortocircuito en P5.</div>
  <div class="table-wrap"><table class="study-table p8d2-results"><thead><tr>
    <th>Dispositivo</th><th>Elemento</th><th>Falla ligada</th><th>Capacidad de corte</th><th>Clearing time</th><th>Térmico</th><th>Procedencia P4</th>
  </tr></thead><tbody>{rows}</tbody></table></div>
</div>'''


def _css() -> str:
    return r'''
/* MCP P8E1 integrated P8D2 results */
.p8d2-results-section{margin:14px 16px;padding:12px;border:1px solid #cbd5e1;border-radius:8px;background:#fff}
.p8d2-results-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:8px}
.p8d2-results-head h3{margin:0 0 3px;color:var(--blue);font-size:15px}
.p8d2-results-head p{margin:0;color:var(--muted);font-size:10px}
.p8d2-status{border:1px solid #94a3b8;border-radius:999px;padding:4px 7px;font-size:9px;font-weight:700;white-space:nowrap}
.p8d2-policy{padding:8px 9px;margin-bottom:9px;background:#f8fafc;border-left:3px solid #2563eb;font-size:10px;color:#334155;line-height:1.4}
.p8d2-results td span{color:var(--muted);font-size:9px}
'''


def enhance_html(html: str, snapshot: dict[str, Any]) -> str:
    """Inserta el resultado P8D2 vigente en el panel V5 existente."""
    if MARKER in html:
        return html
    aggregate = _valid_aggregate(snapshot)
    if aggregate is None:
        return html
    if 'id="panel-protecciones"' not in html:
        return html

    anchor = '<div class="p5-results-section"><h3>Resultados P5 vigentes</h3>'
    if anchor not in html:
        return html

    enhanced = html.replace(anchor, _section(aggregate) + "\n" + anchor, 1)
    if "</style>" in enhanced:
        enhanced = enhanced.replace("</style>", _css() + "\n</style>", 1)
    return enhanced
