"""Vista V4 para cortocircuito IEC 60909 P4.

Consume exclusivamente estudios versionados ``iec60909_3ph``,
``iec60909_2ph``, ``iec60909_1ph_ground`` e ``iec60909_2ph_ground``. El
navegador no ejecuta pandapower, no deriva corrientes ni impedancias y no
completa escenarios fallidos.
"""

from __future__ import annotations

from html import escape
from typing import Any

MARKER = "<!-- MCP-P4-SHORT-CIRCUIT-V4 -->"
STUDY_KEYS = (
    "iec60909_3ph",
    "iec60909_2ph",
    "iec60909_1ph_ground",
    "iec60909_2ph_ground",
)


def _fmt(value: Any, decimals: int = 3, suffix: str = "") -> str:
    if value is None:
        return "—"
    try:
        text = f"{float(value):.{decimals}f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        text = str(value)
    return f"{text}{suffix}"


def _studies(snapshot: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    registered = snapshot.get("status", {}).get("studies", {})
    result: list[tuple[str, dict[str, Any]]] = []
    for key in STUDY_KEYS:
        item = registered.get(key)
        if item and item.get("valid"):
            result.append((key, item.get("result") or {}))
    return result


def _issues_text(payload: dict[str, Any]) -> str:
    issues = payload.get("issues") or []
    if not issues:
        return "—"
    return " | ".join(
        f"{item.get('code', 'ISSUE')}: {item.get('message', '')}" for item in issues
    )


def _duty(payload: dict[str, Any]) -> dict[str, Any]:
    return (
        (payload.get("input_projection") or {}).get("duty")
        or (payload.get("inputs") or {}).get("duty")
        or payload.get("requested_duty")
        or {}
    )


def _scenario_row(name: str, payload: dict[str, Any]) -> str:
    ok = bool(payload.get("ok"))
    values = payload.get("results") or {}
    duty = _duty(payload)
    css = "p4-ok" if ok else "p4-fail"
    state = "CALCULADO" if ok else "NO CALCULADO"
    return (
        f'<tr class="{css}">'
        f'<td><strong>{escape(name.upper())}</strong></td>'
        f'<td><span class="p4-badge {css}">{state}</span></td>'
        f'<td>{_fmt(values.get("ikss_ka"), 3, " kA")}</td>'
        f'<td>{_fmt(values.get("skss_mva"), 2, " MVA")}</td>'
        f'<td>{_fmt(values.get("ip_ka"), 3, " kA")}</td>'
        f'<td>{_fmt(values.get("ith_ka"), 3, " kA")}</td>'
        f'<td>{_fmt(values.get("rk_ohm"), 4, " Ω")}</td>'
        f'<td>{_fmt(values.get("xk_ohm"), 4, " Ω")}</td>'
        f'<td>{_fmt(values.get("rk0_ohm"), 4, " Ω")}</td>'
        f'<td>{_fmt(values.get("xk0_ohm"), 4, " Ω")}</td>'
        f'<td>{escape(str(duty.get("topology") or "—"))}</td>'
        f'<td>{_fmt(duty.get("tk_s"), 3, " s")}</td>'
        f'<td>{escape(str(duty.get("kappa_method") or "—"))}</td>'
        f'<td class="p4-issues">{escape(_issues_text(payload))}</td>'
        "</tr>"
    )


def _fault_label(key: str, study: dict[str, Any]) -> str:
    explicit = str(study.get("fault_label") or "").strip()
    if explicit:
        return explicit
    raw = str(study.get("fault") or "").strip().lower()
    if key == "iec60909_2ph_ground" or raw in {"2ph_ground", "2ph-ground"}:
        return "2F-T"
    if key == "iec60909_1ph_ground" or raw in {"1ph_ground", "1ph-ground", "1ph_ground_fault"}:
        return "1F-T"
    if key == "iec60909_3ph" or raw == "3ph":
        return "3PH"
    if key == "iec60909_2ph" or raw == "2ph":
        return "2PH"
    return raw.upper() or "—"


def _negative_sequence_note(study: dict[str, Any], fault: str) -> str:
    if fault not in {"2PH", "1F-T", "2F-T"}:
        return ""
    policy = study.get("negative_sequence_policy") or {}
    relation = str(policy.get("z2_relation") or policy.get("relation") or "Z2 = Z1")
    if fault == "2PH":
        fallback_scope = "alcance simétrico pasivo P4C06 v1"
        suffix = "Sk'' 2F no se promociona todavía como magnitud contractual normalizada."
    elif fault == "1F-T":
        fallback_scope = "alcance simétrico pasivo P4C07 v1"
        suffix = "Sk'' 1F-T no se promociona todavía como magnitud contractual normalizada; ip/Ith tampoco se derivan en la vista."
    else:
        fallback_scope = "alcance simétrico pasivo P4-v1.1"
        suffix = "La corriente 2F-T mostrada es operativa; Ik'' contractual, Sk'', ip e Ith permanecen pendientes de validación normativa."
    scope = str(policy.get("scope") or fallback_scope)
    universal = bool(policy.get("universal_assumption"))
    return (
        '<div class="p4-policy"><strong>Secuencia negativa explícita:</strong> '
        f'{escape(relation)} · {escape(scope)} · supuesto universal: '
        f'<strong>{"sí" if universal else "no"}</strong>. {suffix}</div>'
    )


def _zero_sequence_note(study: dict[str, Any], fault: str) -> str:
    if fault not in {"1F-T", "2F-T"}:
        return ""
    scenarios = study.get("scenarios") or {}
    payload = scenarios.get("max") or scenarios.get("min") or {}
    projection = (payload.get("inputs") or {}).get("zero_sequence_projection") or {}
    source = projection.get("source") or {}
    lines = projection.get("lines") or []
    transformers = projection.get("transformers") or []
    policy = study.get("zero_sequence_policy") or {}

    source_text = "Z0 fuente no disponible en el escenario mostrado"
    if source.get("r0_ohm") is not None and source.get("x0_ohm") is not None:
        source_text = (
            f"fuente R0={_fmt(source.get('r0_ohm'), 4, ' Ω')}, "
            f"X0={_fmt(source.get('x0_ohm'), 4, ' Ω')}"
        )
    return (
        '<div class="p4-zero"><strong>Secuencia cero explícita:</strong> '
        f'{escape(source_text)} · líneas Z0/C0 proyectadas: <strong>{len(lines)}</strong> · '
        f'transformadores Z0/neutro proyectados: <strong>{len(transformers)}</strong>. '
        f'{escape(str(policy.get("lines") or "R0/X0/C0 explícitos; C0 no se inventa"))}. '
        "La vista presenta el snapshot Python y no reconstruye Z0 en JavaScript.</div>"
    )


def _operational_note(study: dict[str, Any], fault: str) -> str:
    if fault != "2F-T":
        return ""
    promotion = study.get("result_promotion") or {}
    semantics = str(
        promotion.get("operational_current_semantics")
        or "max_faulted_phase_rms_current"
    )
    pending = ", ".join(str(v) for v in promotion.get("pending_validation_ids") or [])
    return (
        '<div class="p4-operational"><strong>Extensión operacional 2F-T:</strong> '
        f'corriente mostrada = {escape(semantics)}; '
        '<strong>no es todavía Ik\'\' contractual IEC</strong>. '
        f'Validaciones pendientes: {escape(pending or "registradas en VALIDACIONES_PENDIENTES.md")}.</div>'
    )


def _study_block(key: str, study: dict[str, Any]) -> str:
    scenarios = study.get("scenarios") or {}
    maximum = scenarios.get("max") or {}
    minimum = scenarios.get("min") or {}
    max_values = maximum.get("results") or {}
    min_values = minimum.get("results") or {}
    engine = study.get("engine") or {}
    if isinstance(engine, str):
        engine = {"engine": engine}
    target = study.get("target_standard") or {}
    bus = str(study.get("bus") or "—")
    fault = _fault_label(key, study)
    maturity = str(study.get("maturity") or "EXPERIMENTAL_P4")
    conformance = str(
        engine.get("target_edition_conformance")
        or maximum.get("target_edition_conformance")
        or minimum.get("target_edition_conformance")
        or "UNVERIFIED"
    )
    runtime_version = (
        engine.get("engine_version_runtime")
        or engine.get("engine_version")
        or maximum.get("pandapower_version")
        or minimum.get("pandapower_version")
        or "—"
    )
    overall = "COMPLETO" if study.get("ok") else "PARCIAL / BLOQUEADO"
    overall_css = "p4-ok" if study.get("ok") else "p4-fail"
    current_label = "I fase MAX" if fault == "2F-T" else "Ik'' MAX"
    current_label_min = "I fase MIN" if fault == "2F-T" else "Ik'' MIN"

    return f'''<article class="p4-study-block" data-p4-study="{escape(key, quote=True)}" data-p4-fault="{escape(fault, quote=True)}" data-p4-study-bus="{escape(bus, quote=True)}">
<div class="p4-header">
  <div><h3>Falla {escape(fault)} · barra <strong>{escape(bus)}</strong></h3><p>MAX/MIN registrados para la revisión vigente; sin recálculo en el navegador.</p></div>
  <div class="p4-kpis">
    <span>{escape(current_label)} <strong>{_fmt(max_values.get('ikss_ka'), 3, ' kA')}</strong></span>
    <span>{escape(current_label_min)} <strong>{_fmt(min_values.get('ikss_ka'), 3, ' kA')}</strong></span>
    <span>Estado <strong class="{overall_css}">{escape(overall)}</strong></span>
  </div>
</div>
<div class="p4-note"><strong>{escape(maturity)} · SIN EMISIÓN PROFESIONAL.</strong> Motor {escape(str(engine.get('engine') or 'pandapower'))} {escape(str(runtime_version))}; objetivo {escape(str(target.get('designation') or target.get('id') or 'IEC 60909'))}. Conformidad de edición: <strong>{escape(conformance)}</strong>. Esta vista no recalcula magnitudes ni sustituye la revisión P4C10.</div>
{_operational_note(study, fault)}
{_negative_sequence_note(study, fault)}
{_zero_sequence_note(study, fault)}
<div class="table-wrap"><table class="study-table"><thead><tr><th>Escenario</th><th>Estado</th><th>Ik'' / I fase</th><th>Sk''</th><th>ip</th><th>Ith</th><th>Rk</th><th>Xk</th><th>Rk0</th><th>Xk0</th><th>Topología</th><th>tk</th><th>κ</th><th>Issues</th></tr></thead><tbody>{_scenario_row('max', maximum)}{_scenario_row('min', minimum)}</tbody></table></div>
</article>'''


def _panel(snapshot: dict[str, Any]) -> str:
    studies = _studies(snapshot)
    if not studies:
        return '''<section class="panel p4-panel" id="panel-cortocircuito">
<div class="p4-empty"><strong>Cortocircuito IEC 60909 no calculado.</strong><br>
Ejecuta explícitamente un estudio 3F, 2F, 1F-T o la extensión operacional 2F-T MAX/MIN para registrar resultados P4 en esta revisión.</div>
</section>'''

    buses: list[str] = []
    for _key, study in studies:
        bus = str(study.get("bus") or "").strip()
        if bus and bus != "—" and bus not in buses:
            buses.append(bus)
    first_bus = buses[0] if buses else "—"
    joined = ",".join(buses)
    blocks = "\n".join(_study_block(key, study) for key, study in studies)

    return f'''<section class="panel p4-panel" id="panel-cortocircuito" data-p4-fault-bus="{escape(first_bus, quote=True)}" data-p4-fault-buses="{escape(joined, quote=True)}">
<div class="p4-panel-title"><h3>Cortocircuito — IEC 60909</h3><p>Estudios P4 vigentes en la revisión actual.</p></div>
{blocks}
</section>'''


def _css() -> str:
    return r'''
/* MCP P4 short-circuit V4 */
.p4-panel { padding:0; }
.p4-panel.active { display:block; margin-top:12px; border-radius:8px; }
.p4-panel-title { padding:15px 16px 4px; border-bottom:1px solid #e2e8f0; }
.p4-panel-title h3 { margin:0 0 4px; color:var(--blue); font-size:16px; }
.p4-panel-title p { margin:0; color:var(--muted); font-size:11px; }
.p4-study-block { padding-bottom:10px; border-bottom:1px solid #e2e8f0; }
.p4-study-block:last-child { border-bottom:0; }
.p4-header { display:flex; justify-content:space-between; gap:18px; align-items:flex-start; padding:16px 16px 8px; }
.p4-header h3 { margin:0 0 4px; color:var(--blue); font-size:14px; }
.p4-header p { margin:0; color:var(--muted); font-size:12px; }
.p4-kpis { display:flex; flex-wrap:wrap; gap:8px; justify-content:flex-end; }
.p4-kpis span { background:#f8fafc; border:1px solid #e2e8f0; border-radius:7px; padding:7px 9px; font-size:11px; white-space:nowrap; }
.p4-note { margin:0 16px 6px; padding:9px 10px; background:#fff7ed; border-left:3px solid #ea580c; color:#7c2d12; font-size:11px; line-height:1.45; }
.p4-operational { margin:0 16px 8px; padding:8px 10px; background:#fefce8; border-left:3px solid #ca8a04; color:#713f12; font-size:11px; line-height:1.45; }
.p4-policy { margin:0 16px 8px; padding:8px 10px; background:#eff6ff; border-left:3px solid #2563eb; color:#1e3a8a; font-size:11px; line-height:1.45; }
.p4-zero { margin:0 16px 8px; padding:8px 10px; background:#f0fdf4; border-left:3px solid #16a34a; color:#14532d; font-size:11px; line-height:1.45; }
.p4-empty { margin:16px; padding:18px; border:1px dashed #cbd5e1; border-radius:8px; color:var(--muted); line-height:1.55; }
.p4-badge { display:inline-block; border-radius:999px; padding:4px 7px; font-size:9px; font-weight:700; }
.p4-ok { color:#166534; }
.p4-fail { color:#b91c1c; }
.p4-badge.p4-ok { background:#dcfce7; }
.p4-badge.p4-fail { background:#fee2e2; }
.p4-panel tr.p4-fail td:first-child { border-left:3px solid #dc2626; }
.p4-panel tr.p4-ok td:first-child { border-left:3px solid #16a34a; }
.p4-issues { max-width:360px; white-space:normal; overflow-wrap:anywhere; font-size:10px; line-height:1.35; }
#workspace-unifilar .overlay-short-circuit-bus { filter:drop-shadow(0 0 5px #dc2626); }
#workspace-unifilar .overlay-short-circuit-bus text { font-weight:700; }
@media (max-width:760px) { .p4-header { flex-direction:column; } .p4-kpis { justify-content:flex-start; } }
@media print { .p4-panel { display:block !important; break-inside:avoid; } .p4-study-block { break-inside:avoid; } }
'''


def _script() -> str:
    return r'''
<script data-module="mcp-p4-short-circuit-v4">
(() => {
  const panel = document.getElementById('panel-cortocircuito');
  const tab = document.querySelector('.tab[data-tab="cortocircuito"]');
  if (!panel || !tab) return;
  const faultBuses = (panel.dataset.p4FaultBuses || panel.dataset.p4FaultBus || '')
    .split(',').map(value => value.trim()).filter(Boolean);

  function clearOverlay() {
    document.querySelectorAll('#workspace-unifilar .overlay-short-circuit-bus')
      .forEach(node => node.classList.remove('overlay-short-circuit-bus'));
  }

  function nodesFor(id) {
    return [...document.querySelectorAll('#workspace-unifilar [data-element-id]')]
      .filter(node => node.dataset.elementId === id);
  }

  function applyOverlay() {
    clearOverlay();
    faultBuses.forEach(bus => nodesFor(`Bus.${bus}`)
      .forEach(node => node.classList.add('overlay-short-circuit-bus')));
  }

  document.querySelectorAll('.tab').forEach(btn => btn.addEventListener('click', () => {
    const active = btn === tab;
    panel.classList.toggle('active', active);
    if (active) {
      document.querySelectorAll('.study-panel,.p3-panel').forEach(other => other.classList.remove('active'));
      document.getElementById('panel-unifilar')?.classList.add('active');
      document.getElementById('panel-datos')?.classList.remove('active');
      applyOverlay();
      const select = document.getElementById('elementSelect');
      const firstBus = faultBuses[0];
      const id = firstBus ? `Bus.${firstBus}` : '';
      if (select && id && [...select.options].some(option => option.value === id)) {
        select.value = id;
        select.dispatchEvent(new Event('change', {bubbles:true}));
      }
    } else {
      clearOverlay();
    }
  }));
})();
</script>
'''


def enhance_html(html: str, snapshot: dict[str, Any]) -> str:
    """Añade la vista V4 IEC 60909 de forma idempotente."""
    if MARKER in html:
        return html

    tab_anchor = '<button type="button" class="tab" data-tab="ampacidad">Ampacidad</button>'
    if tab_anchor not in html:
        raise ValueError("V4: no se encontró la pestaña Ampacidad para insertar Cortocircuito.")
    html = html.replace(
        tab_anchor,
        tab_anchor + '\n      <button type="button" class="tab" data-tab="cortocircuito">Cortocircuito</button>',
        1,
    )

    panel_anchor = '  </div>\n  <aside class="inspector"'
    if panel_anchor not in html:
        raise ValueError("V4: no se encontró el ancla de paneles del workspace.")
    html = html.replace(panel_anchor, _panel(snapshot) + '\n  </div>\n  <aside class="inspector"', 1)
    html = html.replace('</style>', _css() + '\n</style>', 1)
    html = html.replace('</body>', MARKER + _script() + '\n</body>', 1)
    return html
