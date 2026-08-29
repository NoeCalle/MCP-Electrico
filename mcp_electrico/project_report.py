"""P7C: reporte técnico reproducible para Engineering Preview.

Consume exclusivamente snapshots P7A verificados. No consulta el circuito
activo, no recalcula ingeniería y no habilita emisión profesional.
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


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
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
    current: dict[str, Any] = {}
    historical: dict[str, Any] = {}
    for name in sorted(status.get("studies") or {}):
        item = deepcopy(status["studies"][name])
        same_revision = item.get("model_revision") == model_revision
        valid = bool(item.get("valid", same_revision)) and same_revision
        (current if valid else historical)[str(name)] = item
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
    return [
        {
            "module": str(name),
            "status": (validation[name] or {}).get("status"),
            "basis": (validation[name] or {}).get("basis"),
            "limitations": deepcopy((validation[name] or {}).get("limitations") or []),
        }
        for name in sorted(validation)
    ]


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
    governance = payload.get("governance") or {}
    model_revision = project.get("model_revision")
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
        "studies": _classify_studies(payload.get("workspace") or {}, model_revision),
        "engineering_data": deepcopy(payload.get("engineering_data") or {}),
        "governance": {
            "module_maturity": _module_summary(governance.get("validation_matrix") or {}),
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
    report = {
        "ok": True,
        "status": "TECHNICAL_REPORT_READY_FOR_PRINT",
        "schema": SCHEMA,
        "report_hash": {
            "algorithm": REPORT_HASH_ALGORITHM,
            "scope": "canonical_p7c_report_data",
            "value": _digest(report_data),
        },
        "data": report_data,
        "engineering_preview_ready": False,
        "professional_report": False,
        "professional_emission": False,
    }
    report["html"] = renderizar_html(report)
    return report


def _esc(value: Any) -> str:
    return "—" if value is None else html.escape(str(value), quote=True)


def _pre(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
    return f"<pre>{html.escape(text)}</pre>"


def _json_for_script(value: Any) -> str:
    return (
        _canonical_json(value)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )


def _studies_html(items: dict[str, Any], empty: str) -> str:
    if not items:
        return f'<p class="muted">{_esc(empty)}</p>'
    return "".join(
        f'<article class="card"><h3>{_esc(name)}</h3>'
        f'<p class="muted">Revisión: {_esc(item.get("model_revision"))}</p>'
        f'{_pre(item.get("result"))}</article>'
        for name, item in items.items()
    )


def _maturity_html(rows: list[dict[str, Any]]) -> str:
    result = []
    for row in rows:
        limitations = "<br>".join(_esc(v) for v in row.get("limitations") or []) or "—"
        result.append(
            "<tr>"
            f'<td><code>{_esc(row.get("module"))}</code></td>'
            f'<td>{_esc(row.get("status"))}</td>'
            f'<td>{_esc(row.get("basis"))}</td>'
            f'<td>{limitations}</td></tr>'
        )
    return "".join(result)


def renderizar_html(report: dict[str, Any]) -> str:
    if not report.get("ok"):
        raise ValueError("P7C001: no se puede renderizar un reporte bloqueado.")
    data = report["data"]
    project = data["project"]
    studies = data["studies"]
    engineering = data["engineering_data"]
    governance = data["governance"]
    source_hash = data["source_snapshot"]["sha256"]
    report_hash = report["report_hash"]["value"]
    embedded = _json_for_script(data)
    return f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MCP Eléctrico — Resumen técnico {_esc(project.get("circuit"))}</title>
<style>
:root{{font-family:Arial,Helvetica,sans-serif;color:#17212b;background:#eef2f5}}*{{box-sizing:border-box}}body{{margin:0}}
.page{{max-width:1180px;margin:24px auto;background:#fff;padding:32px}}h2{{margin-top:30px;border-bottom:1px solid #d7dee5;padding-bottom:8px}}
.banner,.card{{border:1px solid #d7dee5;border-radius:8px;padding:14px;margin:10px 0}}.banner{{border-width:2px;font-weight:700}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}}.muted{{color:#5c6873;font-size:.9rem}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f6f8fa;padding:10px;font-size:.78rem}}table{{width:100%;border-collapse:collapse;font-size:.85rem}}
th,td{{border:1px solid #d7dee5;padding:8px;vertical-align:top;text-align:left}}th{{background:#f4f6f8}}.toolbar{{text-align:right}}
@page{{size:A4;margin:12mm}}@media print{{.page{{margin:0;padding:0;max-width:none}}.no-print{{display:none!important}}}}
</style></head><body><main class="page" data-module="mcp-p7c-technical-report">
<div class="toolbar no-print"><button type="button" onclick="window.print()">Imprimir / Guardar PDF</button></div>
<h1>MCP Eléctrico — Resumen técnico reproducible</h1><p class="muted">P7C · Engineering Preview · snapshot P7A verificado</p>
<div class="banner">NO APTO PARA EMISIÓN PROFESIONAL · professional_emission=false</div>
<section class="grid"><div class="card"><b>Proyecto</b><br>{_esc(project.get("circuit"))}</div><div class="card"><b>Revisión</b><br>{_esc(project.get("model_revision"))}</div>
<div class="card"><b>SHA-256 P7A</b><br>{_esc(source_hash)}</div><div class="card"><b>SHA-256 P7C</b><br>{_esc(report_hash)}</div></section>
<h2>Estado del expediente</h2><p>Integridad: <b>HASH_MATCH</b> · P6 IEEE 1584: <b>DEFERRED</b> · PDF: <b>BROWSER_PRINT</b></p>
<h2>Estudios vigentes</h2>{_studies_html(studies.get("current") or {}, "No hay estudios vigentes registrados.")}
<h2>Resultados históricos / no vigentes</h2>{_studies_html(studies.get("historical") or {}, "No hay resultados históricos registrados.")}
<h2>Datos de ingeniería congelados</h2><h3>P2 — Datos profesionales</h3>{_pre(engineering.get("professional_p2") or {})}
<h3>P2 — Secuencia cero</h3>{_pre(engineering.get("zero_sequence_p2") or {})}<h3>P3 — Ampacidad</h3>{_pre(engineering.get("ampacity_p3") or {})}
<h3>P5 — Protección</h3>{_pre(engineering.get("protection_p5") or {})}<h3>P5 — Datasets TCC</h3>{_pre(engineering.get("tcc_datasets_p5") or [])}
<h2>Madurez y limitaciones</h2><table><thead><tr><th>Módulo</th><th>Estado</th><th>Base</th><th>Limitaciones</th></tr></thead><tbody>{_maturity_html(governance.get("module_maturity") or [])}</tbody></table>
<h2>Motores y política</h2>{_pre(governance.get("runtime_versions") or {})}<h3>Selección</h3>{_pre(governance.get("engine_selection") or {})}<h3>Gate P5</h3>{_pre(governance.get("p5_completion") or {})}
<div class="banner">automatic_dispatch=false · crosscheck=false · engineering_preview_ready=false · professional_emission=false</div>
<p class="muted">Este HTML no recalcula ingeniería. Imprimir / Guardar PDF invoca únicamente la impresión del navegador.</p>
<script type="application/json" id="p7c-report-data">{embedded}</script></main></body></html>'''


def exportar_reporte(snapshot: dict[str, Any], ruta_salida: str = "mcp_electrico_report.html") -> dict[str, Any]:
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


def exportar_reporte_desde_archivo(ruta_snapshot: str, ruta_salida: str = "mcp_electrico_report.html") -> dict[str, Any]:
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
