"""P13E — Workspace estático para estudios de motores y arranque.

El navegador no calcula ingeniería. Python entrega resultados P13D ya resueltos
y este módulo únicamente los presenta y conserva el payload para trazabilidad.
"""

from __future__ import annotations

from copy import deepcopy
from html import escape
import json
from pathlib import Path
from typing import Any

SCHEMA = "MCP_ELECTRICO_P13E_MOTOR_WORKSPACE_V1"


def _json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return escape(str(value))


def _state_badge(state: str) -> str:
    state = str(state or "")
    css = {
        "OFF": "off",
        "RUNNING": "running",
        "STARTING_PROFILE_POINT": "starting",
    }.get(state, "unknown")
    return f'<span class="badge {css}">{escape(state)}</span>'


def _sequence_sections(execution: dict[str, Any]) -> str:
    sections: list[str] = []
    for sequence in execution.get("results") or []:
        step_rows: list[str] = []
        for step in sequence.get("steps") or []:
            states = {
                str(item.get("motor_id") or ""): item
                for item in step.get("applied_states") or []
            }
            voltages = {
                str(item.get("motor_id") or ""): item
                for item in step.get("motor_terminal_voltages") or []
            }
            motors = sorted(set(states) | set(voltages))
            motor_cells: list[str] = []
            for motor_id in motors:
                state = states.get(motor_id) or {}
                voltage = voltages.get(motor_id) or {}
                details = [
                    _state_badge(state.get("state")),
                    f'<span class="mono">Vmin={_fmt(voltage.get("minimum_voltage_pu"), 4)} pu</span>',
                ]
                if state.get("point_id"):
                    details.append(
                        f'<span class="muted">{escape(str(state.get("profile_id")))} / '
                        f'{escape(str(state.get("point_id")))}</span>'
                    )
                motor_cells.append(
                    '<div class="motor-state">'
                    f'<strong>{escape(motor_id)}</strong>'
                    + "".join(details)
                    + "</div>"
                )

            criteria = step.get("criterion_evaluations") or []
            criterion_html = ""
            if criteria:
                items = []
                for item in criteria:
                    passed = bool(item.get("passed"))
                    items.append(
                        '<li>'
                        f'{escape(str(item.get("motor_id")))}: '
                        f'{_fmt(item.get("minimum_voltage_pu"), 4)} pu '
                        f'≥ {_fmt(item.get("criterion_minimum_voltage_pu"), 4)} pu '
                        f'<strong class="{"pass" if passed else "fail"}">'
                        f'{"PASS" if passed else "FAIL"}</strong>'
                        '</li>'
                    )
                criterion_html = "<ul>" + "".join(items) + "</ul>"
            else:
                criterion_html = '<span class="muted">Sin criterio de arranque aplicable en este paso.</span>'

            step_rows.append(
                '<article class="step">'
                '<header>'
                f'<div><strong>{escape(str(step.get("step_id")))}</strong>'
                f'<span class="muted"> · t={_fmt(step.get("elapsed_time_s"), 3)} s</span></div>'
                f'<span class="result {escape(str(step.get("status") or "").lower())}">'
                f'{escape(str(step.get("status") or ""))}</span>'
                '</header>'
                '<div class="motor-grid">' + "".join(motor_cells) + "</div>"
                f'<div class="criteria"><strong>Criterio(s) de arranque</strong>{criterion_html}</div>'
                '</article>'
            )

        worst = sequence.get("worst_starting_criterion")
        if worst:
            worst_html = (
                '<div class="callout">'
                '<strong>Peor margen de criterio:</strong> '
                f'{escape(str(worst.get("motor_id")))} · '
                f'{escape(str(worst.get("point_id")))} · '
                f'margen {_fmt(worst.get("margin_pu"), 4)} pu'
                '</div>'
            )
        else:
            worst_html = '<div class="callout muted">No hubo criterio de arranque aplicable.</div>'

        sections.append(
            '<section class="sequence">'
            '<div class="sequence-title">'
            f'<h2>{escape(str(sequence.get("sequence_id")))}</h2>'
            f'<span class="result {escape(str(sequence.get("status") or "").lower())}">'
            f'{escape(str(sequence.get("status") or ""))}</span>'
            '</div>'
            f'<p class="muted">{escape(str(sequence.get("sequence_reference") or ""))}</p>'
            + worst_html
            + "".join(step_rows)
            + "</section>"
        )
    return "".join(sections)


def construir_html(
    manifest: dict[str, Any],
    profile_package: dict[str, Any],
    sequence_package: dict[str, Any],
    execution: dict[str, Any],
) -> str:
    project = manifest.get("project") or {}
    summary = {
        "project_id": project.get("id"),
        "project_name": project.get("name"),
        "execution_status": execution.get("execution_status"),
        "sequence_count": execution.get("sequence_count"),
        "industry_scope": "CROSS_INDUSTRY",
        "professional_emission": False,
    }
    embedded = {
        "schema": SCHEMA,
        "manifest": deepcopy(manifest),
        "profile_package": deepcopy(profile_package),
        "sequence_package": deepcopy(sequence_package),
        "execution": deepcopy(execution),
        "browser_engineering_calculation": False,
        "professional_emission": False,
    }

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>P13E · Motores y arranque · {escape(str(project.get("id") or ""))}</title>
<style>
:root {{ font-family: Inter, system-ui, sans-serif; color-scheme: light; }}
body {{ margin:0; background:#f4f6f8; color:#17202a; }}
main {{ max-width:1180px; margin:0 auto; padding:28px 18px 64px; }}
.hero,.sequence,.step {{ background:white; border:1px solid #dfe5eb; border-radius:14px; }}
.hero {{ padding:24px; margin-bottom:18px; }}
.hero h1 {{ margin:0 0 8px; font-size:26px; }}
.summary {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:10px; margin-top:18px; }}
.metric {{ background:#f8fafc; border-radius:10px; padding:12px; }}
.metric span {{ display:block; color:#607080; font-size:12px; text-transform:uppercase; }}
.metric strong {{ display:block; margin-top:4px; }}
.sequence {{ padding:20px; margin:18px 0; }}
.sequence-title,.step header {{ display:flex; align-items:center; justify-content:space-between; gap:12px; }}
.sequence-title h2 {{ margin:0; font-size:21px; }}
.step {{ padding:14px; margin:12px 0; background:#fbfcfd; }}
.motor-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:10px; margin:12px 0; }}
.motor-state {{ border:1px solid #e5eaf0; border-radius:10px; padding:10px; display:flex; flex-direction:column; gap:6px; }}
.badge,.result {{ display:inline-block; width:max-content; border-radius:999px; padding:4px 9px; font-size:11px; font-weight:700; }}
.off {{ background:#eceff1; }} .running {{ background:#e8f5e9; }} .starting {{ background:#fff3e0; }}
.result.pass {{ background:#e8f5e9; }} .result.fail {{ background:#ffebee; }} .result.observed {{ background:#e3f2fd; }}
.result.partial,.result.error {{ background:#fff3e0; }}
.pass {{ color:#176b2c; }} .fail {{ color:#a21d2a; }}
.muted {{ color:#667786; font-size:13px; }} .mono {{ font-family:ui-monospace,SFMono-Regular,Consolas,monospace; font-size:12px; }}
.criteria {{ padding-top:10px; border-top:1px solid #e6ebf0; }}
.criteria ul {{ margin:8px 0 0 18px; padding:0; }}
.callout {{ margin:12px 0; padding:10px 12px; background:#f7f9fb; border-left:4px solid #8293a3; }}
.footer {{ margin-top:24px; font-size:12px; color:#6d7b87; }}
@media print {{ body {{ background:white; }} main {{ max-width:none; padding:0; }} .hero,.sequence,.step {{ break-inside:avoid; }} }}
</style>
</head>
<body>
<main>
<section class="hero">
<h1>MCP Eléctrico · Motores y arranque P13E</h1>
<p>{escape(str(project.get("name") or ""))}</p>
<div class="summary">
<div class="metric"><span>Proyecto</span><strong>{escape(str(summary["project_id"] or ""))}</strong></div>
<div class="metric"><span>Estado ejecución</span><strong>{escape(str(summary["execution_status"] or ""))}</strong></div>
<div class="metric"><span>Secuencias</span><strong>{escape(str(summary["sequence_count"] or 0))}</strong></div>
<div class="metric"><span>Alcance</span><strong>CROSS_INDUSTRY</strong></div>
</div>
</section>
{_sequence_sections(execution)}
<div class="footer">
Este Workspace es read-only. El navegador no recalcula flujo, arranque, perfiles ni secuencias.
professional_emission=false.
</div>
<script id="p13e-data" type="application/json">{escape(_json(embedded))}</script>
</main>
</body>
</html>"""


def escribir_workspace(
    path: str | Path,
    manifest: dict[str, Any],
    profile_package: dict[str, Any],
    sequence_package: dict[str, Any],
    execution: dict[str, Any],
) -> dict[str, Any]:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    html = construir_html(manifest, profile_package, sequence_package, execution)
    target.write_text(html, encoding="utf-8")
    return {
        "schema": SCHEMA,
        "path": str(target),
        "bytes": target.stat().st_size,
        "browser_engineering_calculation": False,
        "professional_emission": False,
    }
