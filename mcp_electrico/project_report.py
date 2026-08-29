"""P7C — reporte técnico reproducible para MCP Eléctrico Engineering Preview.

El reporte se construye exclusivamente desde un snapshot P7A cuyo SHA-256 haya
sido verificado. No consulta ni recalcula el circuito activo. El HTML es una
representación determinista y apta para impresión del contenido técnico ya
congelado por P7A.

P7C NO habilita emisión profesional, firma digital ni conformidad normativa
integral. El PDF se obtiene mediante impresión del HTML en el navegador.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import html
import json
from pathlib import Path
from typing import Any

from . import project_snapshot

SCHEMA = "MCP_ELECTRICO_P7C_TECHNICAL_REPORT_V1"
REPORT_KIND = "TECHNICAL_ENGINEERING_PREVIEW"
REPORT_HASH_ALGORITHM = "sha256"
PDF_EXPORT_MODE = "BROWSER_PRINT"


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(value: dict[str, Any]) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _safe_output_path(path: str | Path) -> Path:
    requested = Path(path).expanduser().resolve()
    requested.parent.mkdir(parents=True, exist_ok=True)
    if not requested.exists():
        return requested
    suffix = requested.suffix or ".html"
    stem = requested.stem if requested.suffix else requested.name
    index = 2
    while True:
        candidate = requested.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def obtener_contrato_p7c() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "source_schema": project_snapshot.SCHEMA,
        "source_integrity_required": "HASH_MATCH",
        "report_kind": REPORT_KIND,
        "report_hash_algorithm": REPORT_HASH_ALGORITHM,
        "deterministic_from_verified_snapshot": True,
        "electrical_recalculation": False,
        "browser_engineering_calculation": False,
        "pdf_export_mode": PDF_EXPORT_MODE,
        "native_pdf_generation": False,
        "engineering_preview_ready": False,
        "professional_report": False,
        "professional_emission": False,
    }


def _classify_studies(workspace: dict[str, Any], model_revision: Any) -> dict[str, Any]:
    status = workspace.get("status") or {}
    studies = status.get("studies") or {}
    current: dict[str, Any] = {}
    historical: dict[str, Any] = {}
    for name in sorted(studies):
        item = deepcopy(studies[name])
        same_revision = item.get("model_revision") == model_revision
        valid = bool(item.get("valid", same_revision)) and same_revision
        target = current if valid else historical
        target[str(name)] = item
    return {
        "current": current,
        "historical": historical,
        "current_count": len(current),
        "historical_count": len(historical),
        "workspace_results_current": bool(status.get("results_current")),
        "workspace_state": status.get("state"),
        "solved_revision": status.get("solved_revision"),
    }


def _module_summary(validation: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for name in sorted(validation):
        item = validation[name] or {}
        rows.append({
            "module": str(name),
            "status": item.get("status"),
            "basis": item.get("basis"),
            "limitations": deepcopy(item.get("limitations") or []),
        })
    return rows


def construir_reporte(snapshot: dict[str, Any]) -> dict[str, Any]:
    verification = project_snapshot.verificar_snapshot(snapshot)
    if not verification.get("ok"):
        return {
            "ok": False,
            "status": "BLOCKED_SNAPSHOT_INTEGRITY",
            "source_verification": verification,
            "write_performed": False,
            "engineering_preview_ready": False,
            "professional_report": False,
            "professional_emission": False,
        }

    payload = deepcopy(snapshot["payload"])
    project = payload.get("project") or {}
    workspace = payload.get("workspace") or {}
    governance = payload.get("governance") or {}
    engineering_data = payload.get("engineering_data") or {}
    model_revision = project.get("model_revision")
    studies = _classify_studies(workspace, model_revision)
    validation = governance.get("validation_matrix") or {}

    report_data = {
        "schema": SCHEMA,
        "report_kind": REPORT_KIND,
        "source_snapshot": {
            "schema": snapshot.get("schema"),
            "sha256": (snapshot.get("hash") or {}).get("value"),
            "verification": "HASH_MATCH",
        },
        "project": {
            "circuit": project.get("circuit"),
            "model_revision": model_revision,
            "visual_revision": project.get("visual_revision"),
        },
        "studies": studies,
        "engineering_data": engineering_data,
        "governance": {
            "module_maturity": _module_summary(validation),
            "limitations": deepcopy(governance.get("limitations") or {}),
            "runtime_versions": deepcopy(governance.get("runtime_versions") or {}),
            "engine_selection": deepcopy(governance.get("engine_selection") or {}),
            "p5_completion": deepcopy(governance.get("p5_completion") or {}),
            "automatic_dispatch": False,
            "crosscheck": False,
            "professional_emission": False,
        },
        "product_status": {
            "p5": "READY_WITH_LIMITATIONS",
            "p6_arc_flash_ieee1584": "DEFERRED",
            "p7c": "EXPERIMENTAL",
            "engineering_preview_ready": False,
            "professional_report": False,
            "professional_emission": False,
        },
        "rendering_contract": {
            "electrical_recalculation": False,
            "browser_engineering_calculation": False,
            "pdf_export_mode": PDF_EXPORT_MODE,
        },
    }
    report_hash = _digest(report_data)
    report = {
        "ok": True,
        "status": "TECHNICAL_REPORT_READY_FOR_PRINT",
        "schema": SCHEMA,
        "report_hash": {
            "algorithm": REPORT_HASH_ALGORITHM,
            "scope": "canonical_p7c_report_data",
            "value": report_hash,
        },
        "data": report_data,
        "engineering_preview_ready": False,
        "professional_report": False,
        "professional_emission": False,
    }
    report["html"] = renderizar_html(report)
    return report


def _esc(value: Any) -> str:
    if value is None:
        return "—"
    return html.escape(str(value), quote=True)


def _json_pre(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
    return f"<pre>{html.escape(text)}</pre>"


def _study_cards(studies: dict[str, Any], empty_text: str) -> str:
    if not studies:
        return f'<p class="muted">{_esc(empty_text)}</p>'
    cards = []
    for name, item in studies.items():
        result = item.get("result")
        cards.append(
            '<article class="study-card">'
            f'<h3>{_esc(name)}</h3>'
            f'<div class="meta">Revisión de modelo: {_esc(item.get("model_revision"))}</div>'
            f'{_json_pre(result)}'
            '</article>'
        )
    return "".join(cards)


def _maturity_rows(rows: list[dict[str, Any]]) -> str:
    body = []
    for item in rows:
        limitations = item.get("limitations") or []
        limits_html = "<br>".join(_esc(limit) for limit in limitations) or "—"
        body.append(
            "<tr>"
            f'<td><code>{_esc(item.get("module"))}</code></td>'
            f'<td>{_esc(item.get("status"))}</td>'
            f'<td>{_esc(item.get("basis"))}</td>'
            f'<td>{limits_html}</td>'
            "</tr>"
        )
    return "".join(body)


def renderizar_html(report: dict[str, Any]) -> str:
    if not report.get("ok"):
        raise ValueError("P7C001: no se puede renderizar un reporte bloqueado.")
    data = report["data"]
    project = data["project"]
    source = data["source_snapshot"]
    studies = data["studies"]
    governance = data["governance"]
    engineering = data["engineering_data"]
    embedded = html.escape(
        json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    )
    return f'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MCP Eléctrico — Resumen técnico {_esc(project.get("circuit"))}</title>
<style>
:root {{ font-family: Arial, Helvetica, sans-serif; color: #17212b; background: #eef2f5; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; }}
.page {{ max-width: 1180px; margin: 24px auto; background: white; padding: 32px; box-shadow: 0 8px 28px rgba(0,0,0,.08); }}
h1,h2,h3 {{ margin-top: 0; }}
h2 {{ margin-top: 30px; border-bottom: 1px solid #d7dee5; padding-bottom: 8px; }}
.banner {{ border: 2px solid currentColor; padding: 14px 16px; font-weight: 700; margin: 16px 0 24px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap: 12px; }}
.card,.study-card {{ border: 1px solid #d7dee5; border-radius: 8px; padding: 14px; margin: 10px 0; break-inside: avoid; }}
.label {{ font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; color: #5c6873; }}
.value {{ font-weight: 700; overflow-wrap: anywhere; }}
.meta,.muted {{ color: #5c6873; font-size: .9rem; }}
table {{ width: 100%; border-collapse: collapse; font-size: .88rem; }}
th,td {{ border: 1px solid #d7dee5; padding: 8px; vertical-align: top; text-align: left; }}
th {{ background: #f4f6f8; }}
pre {{ white-space: pre-wrap; overflow-wrap: anywhere; background: #f6f8fa; border: 1px solid #e2e7ec; padding: 10px; font-size: .78rem; }}
.toolbar {{ display: flex; justify-content: flex-end; margin-bottom: 18px; }}
button {{ padding: 9px 14px; cursor: pointer; }}
.footer {{ margin-top: 32px; font-size: .82rem; color: #5c6873; border-top: 1px solid #d7dee5; padding-top: 12px; }}
@page {{ size: A4; margin: 12mm; }}
@media print {{
  :root {{ background: white; }}
  .page {{ max-width: none; margin: 0; padding: 0; box-shadow: none; }}
  .no-print {{ display: none !important; }}
  h2 {{ break-after: avoid; }}
}}
</style>
</head>
<body>
<main class="page" data-module="mcp-p7c-technical-report">
<div class="toolbar no-print"><button type="button" onclick="window.print()">Imprimir / Guardar PDF</button></div>
<h1>MCP Eléctrico — Resumen técnico reproducible</h1>
<p class="muted">P7C · Engineering Preview · contenido congelado por snapshot P7A</p>
<div class="banner">NO APTO PARA EMISIÓN PROFESIONAL · professional_emission=false</div>
<section class="grid">
  <div class="card"><div class="label">Proyecto / circuito</div><div class="value">{_esc(project.get("circuit"))}</div></div>
  <div class="card"><div class="label">Revisión de modelo</div><div class="value">{_esc(project.get("model_revision"))}</div></div>
  <div class="card"><div class="label">SHA-256 snapshot P7A</div><div class="value">{_esc(source.get("sha256"))}</div></div>
  <div class="card"><div class="label">SHA-256 reporte P7C</div><div class="value">{_esc((report.get("report_hash") or {}).get("value"))}</div></div>
</section>
<h2>Estado del expediente</h2>
<div class="grid">
  <div class="card"><div class="label">Integridad origen</div><div class="value">HASH_MATCH</div></div>
  <div class="card"><div class="label">Resultados workspace vigentes</div><div class="value">{_esc(studies.get("workspace_results_current"))}</div></div>
  <div class="card"><div class="label">P6 IEEE 1584</div><div class="value">DEFERRED</div></div>
  <div class="card"><div class="label">Exportación PDF</div><div class="value">BROWSER_PRINT</div></div>
</div>
<h2>Estudios vigentes en la revisión congelada</h2>
{_study_cards(studies.get("current") or {{}}, "No hay estudios vigentes registrados en este snapshot.")}
<h2>Resultados históricos / no vigentes</h2>
{_study_cards(studies.get("historical") or {{}}, "No hay resultados históricos en este snapshot.")}
<h2>Datos de ingeniería congelados</h2>
<h3>P2 — Datos profesionales</h3>{_json_pre(engineering.get("professional_p2") or {{}})}
<h3>P2 — Secuencia cero</h3>{_json_pre(engineering.get("zero_sequence_p2") or {{}})}
<h3>P3 — Ampacidad</h3>{_json_pre(engineering.get("ampacity_p3") or {{}})}
<h3>P5 — Protección</h3>{_json_pre(engineering.get("protection_p5") or {{}})}
<h3>P5 — Datasets TCC</h3>{_json_pre(engineering.get("tcc_datasets_p5") or [])}
<h2>Madurez y limitaciones</h2>
<table><thead><tr><th>Módulo</th><th>Estado</th><th>Base</th><th>Limitaciones declaradas</th></tr></thead>
<tbody>{_maturity_rows(governance.get("module_maturity") or [])}</tbody></table>
<h2>Motores, versiones y política de ejecución</h2>
{_json_pre(governance.get("runtime_versions") or {{}})}
<h3>Selección de motores</h3>{_json_pre(governance.get("engine_selection") or {{}})}
<h3>Gate P5</h3>{_json_pre(governance.get("p5_completion") or {{}})}
<div class="banner">automatic_dispatch=false · crosscheck=false · engineering_preview_ready=false · professional_emission=false</div>
<div class="footer">Este HTML no recalcula ingeniería. La acción “Imprimir / Guardar PDF” invoca únicamente la impresión del navegador. El contenido técnico proviene del snapshot P7A identificado por su SHA-256.</div>
<script type="application/json" id="p7c-report-data">{embedded}</script>
</main>
</body>
</html>'''


def exportar_reporte(
    snapshot: dict[str, Any],
    ruta_salida: str = "mcp_electrico_report.html",
) -> dict[str, Any]:
    report = construir_reporte(snapshot)
    if not report.get("ok"):
        return report
    target = _safe_output_path(ruta_salida)
    target.write_text(report["html"], encoding="utf-8")
    return {
        "ok": True,
        "status": report["status"],
        "schema": SCHEMA,
        "path": str(target),
        "source_snapshot_sha256": report["data"]["source_snapshot"]["sha256"],
        "report_hash": deepcopy(report["report_hash"]),
        "pdf_export_mode": PDF_EXPORT_MODE,
        "browser_engineering_calculation": False,
        "engineering_preview_ready": False,
        "professional_report": False,
        "professional_emission": False,
    }


def exportar_reporte_desde_archivo(
    ruta_snapshot: str,
    ruta_salida: str = "mcp_electrico_report.html",
) -> dict[str, Any]:
    try:
        snapshot = json.loads(Path(ruta_snapshot).expanduser().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "status": "INVALID_SNAPSHOT_JSON",
            "error": str(exc),
            "write_performed": False,
            "engineering_preview_ready": False,
            "professional_report": False,
            "professional_emission": False,
        }
    return exportar_reporte(snapshot, ruta_salida=ruta_salida)
