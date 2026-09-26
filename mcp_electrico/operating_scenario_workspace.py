"""P12F — Workspace estático para resultados de escenarios operativos.

El HTML no recalcula ingeniería. Solo representa un resultado P12 ya producido
por Python/OpenDSS y conserva los criterios declarados por el proyecto.
"""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
from typing import Any

SCHEMA = "MCP_ELECTRICO_P12F_SCENARIO_WORKSPACE_V1"
MARKER = "MCP_ELECTRICO_P12F_SCENARIO_WORKSPACE"


def _status_class(value: str) -> str:
    text = str(value or "").upper()
    if text == "PASS":
        return "pass"
    if text == "FAIL":
        return "fail"
    return "neutral"


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return escape(str(value))


def construir_html(
    manifest: dict[str, Any],
    package: dict[str, Any],
    execution: dict[str, Any],
) -> str:
    project = manifest.get("project") or {}
    summary = execution.get("summary") or {}
    scenario_rows: list[str] = []
    detail_sections: list[str] = []

    package_by_id = {
        str(item.get("id") or ""): item
        for item in package.get("scenarios") or []
        if isinstance(item, dict)
    }

    for result in execution.get("scenario_results") or []:
        sid = str(result.get("scenario_id") or "")
        scenario = package_by_id.get(sid) or {}
        status = str(result.get("scenario_status") or result.get("execution_status") or "")
        service = result.get("service") or {}
        scenario_rows.append(
            "<tr>"
            f"<td>{escape(sid)}</td>"
            f"<td>{escape(str(result.get('scenario_name') or scenario.get('name') or ''))}</td>"
            f"<td>{escape(str(result.get('purpose') or scenario.get('purpose') or ''))}</td>"
            f"<td><span class='badge {_status_class(status)}'>{escape(status)}</span></td>"
            f"<td>{'Sí' if service.get('powerflow_converged') else 'No'}</td>"
            f"<td>{'Sí' if result.get('model_restored') else 'No'}</td>"
            "</tr>"
        )

        actions = result.get("action_results") or []
        action_rows = "".join(
            "<tr>"
            f"<td>{escape(str(item.get('action') or ''))}</td>"
            f"<td>{escape(str(item.get('element_id') or ''))}</td>"
            f"<td>{escape(str(item.get('source_reference') or ''))}</td>"
            "</tr>"
            for item in actions
        ) or "<tr><td colspan='3'>Sin acciones registradas.</td></tr>"

        checks = service.get("critical_load_checks") or []
        check_rows = "".join(
            "<tr>"
            f"<td>{escape(str(item.get('load_id') or ''))}</td>"
            f"<td>{escape(str(item.get('bus') or ''))}</td>"
            f"<td>{'Sí' if item.get('load_enabled') else 'No'}</td>"
            f"<td>{_fmt(min(item.get('voltage_pu') or []), 4) if item.get('voltage_pu') else '—'}</td>"
            f"<td>{_fmt(item.get('minimum_voltage_pu'), 4)}</td>"
            f"<td>{_fmt(item.get('maximum_voltage_pu'), 4)}</td>"
            f"<td><span class='badge {'pass' if item.get('service_ok') else 'fail'}'>{'PASS' if item.get('service_ok') else 'FAIL'}</span></td>"
            "</tr>"
            for item in checks
        ) or "<tr><td colspan='7'>Sin cargas críticas declaradas.</td></tr>"

        detail_sections.append(
            f"<section><h2>{escape(sid)} · {escape(status)}</h2>"
            "<h3>Acciones explícitas</h3>"
            "<table><thead><tr><th>Acción</th><th>Elemento</th><th>Referencia</th></tr></thead>"
            f"<tbody>{action_rows}</tbody></table>"
            "<h3>Servicio crítico</h3>"
            "<table><thead><tr><th>Carga</th><th>Barra</th><th>Enabled</th><th>Vmin actual pu</th>"
            "<th>Vmin criterio</th><th>Vmax criterio</th><th>Resultado</th></tr></thead>"
            f"<tbody>{check_rows}</tbody></table></section>"
        )

    embedded = json.dumps(
        {
            "schema": SCHEMA,
            "manifest_project": project,
            "scenario_package": package,
            "execution": execution,
            "browser_engineering_calculation": False,
            "professional_emission": False,
        },
        ensure_ascii=False,
        sort_keys=True,
    ).replace("</", "<\/")

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(str(project.get("name") or "MCP Eléctrico"))} — Escenarios P12</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#f5f6f8;color:#16181d}}
main{{max-width:1180px;margin:0 auto;padding:28px}}
header,section{{background:white;border:1px solid #dfe3e8;border-radius:12px;padding:20px;margin-bottom:18px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}}
.card{{background:#f8f9fb;border-radius:9px;padding:14px}}
.card strong{{display:block;font-size:1.45rem}}
table{{width:100%;border-collapse:collapse;font-size:.92rem}}
th,td{{padding:9px;border-bottom:1px solid #e7e9ed;text-align:left;vertical-align:top}}
.badge{{padding:3px 8px;border-radius:999px;font-weight:700;font-size:.8rem}}
.pass{{background:#e6f4ea;color:#176b35}} .fail{{background:#fce8e6;color:#a12622}} .neutral{{background:#eceff3;color:#4b5563}}
small{{color:#6b7280}}
@media print{{body{{background:white}} main{{max-width:none;padding:0}} header,section{{border:none;break-inside:avoid}}}}
</style>
</head>
<body data-marker="{MARKER}">
<main>
<header>
<h1>Escenarios operativos P12</h1>
<p><strong>{escape(str(project.get("name") or ""))}</strong> · {escape(str(project.get("id") or ""))}</p>
<p><small>Vista estática. El navegador no ejecuta cálculos eléctricos ni decide contingencias, maniobras, shedding o transferencias.</small></p>
<div class="grid">
<div class="card"><span>Total</span><strong>{int(summary.get("total") or 0)}</strong></div>
<div class="card"><span>PASS</span><strong>{int(summary.get("pass") or 0)}</strong></div>
<div class="card"><span>FAIL</span><strong>{int(summary.get("fail") or 0)}</strong></div>
<div class="card"><span>Bloqueados/error</span><strong>{int(summary.get("blocked_or_error") or 0)}</strong></div>
</div>
</header>
<section>
<h2>Comparación de escenarios</h2>
<table><thead><tr><th>ID</th><th>Nombre</th><th>Propósito</th><th>Resultado</th><th>Flujo converge</th><th>Restaurado</th></tr></thead>
<tbody>{"".join(scenario_rows)}</tbody></table>
</section>
{"".join(detail_sections)}
<section><h2>Fronteras</h2>
<p><code>automatic_contingency_selection=false</code> · <code>automatic_switching=false</code> ·
<code>automatic_load_shedding=false</code> · <code>automatic_source_selection=false</code> ·
<code>automatic_transfer=false</code> · <code>professional_emission=false</code></p>
</section>
<script type="application/json" id="mcp-p12-data">{embedded}</script>
</main>
</body>
</html>"""


def escribir_workspace(
    path: str | Path,
    manifest: dict[str, Any],
    package: dict[str, Any],
    execution: dict[str, Any],
) -> dict[str, Any]:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    html = construir_html(manifest, package, execution)
    target.write_text(html, encoding="utf-8")
    return {
        "schema": SCHEMA,
        "ok": True,
        "path": str(target),
        "marker": MARKER,
        "browser_engineering_calculation": False,
        "professional_emission": False,
    }
