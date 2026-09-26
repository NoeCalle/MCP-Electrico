from __future__ import annotations

import inspect

from mcp_electrico import (
    core,
    model_placeholders,
    workspace_readiness_view,
    workspace_state,
)


def _base_html() -> str:
    return '''<!doctype html><html><head><style></style></head><body>
<div class="tabs">
  <button type="button" class="tab" data-tab="cortocircuito">Cortocircuito</button>
  <button type="button" class="tab" data-tab="protecciones">Protecciones / TCC</button>
</div>
<div class="workspace-content">
  <section class="panel" id="panel-unifilar"></section>
  <section class="panel" id="panel-protecciones"></section>
  </div>
  <aside class="inspector"></aside>
</body></html>'''


def _snapshot(*, with_placeholder: bool = True) -> dict:
    placeholders = {
        "schema": "MCP_ELECTRICO_MODEL_PLACEHOLDERS_V1",
        "count": 1 if with_placeholder else 0,
        "items": [],
        "has_study_blockers": with_placeholder,
        "solver_materialized_count": 0,
        "automatic_defaults": False,
        "professional_emission": False,
    }
    if with_placeholder:
        placeholders["items"] = [{
            "id": "Transformer.TR_AUX_A",
            "element_type": "TRANSFORMER",
            "status": "MODEL_PLACEHOLDER_TBC",
            "solver_materialized": False,
            "known_data": {"kva": 1500.0, "kv_hv": 4.16, "kv_lv": 0.48},
            "missing_fields": ["uk_percent", "vector_group"],
            "source_reference": "SLD Rev.0",
        }]
    return {
        "status": {
            "state": "MODIFIED",
            "model_revision": 4,
            "solved_revision": 3,
            "results_current": False,
        },
        "model_placeholders": placeholders,
    }


def _qa(*, blocked: bool = True) -> dict:
    return {
        "estudios_requeridos": ["power_flow", "voltage_drop"],
        "module_checks": [
            {"module": "power_flow", "status": "VALIDATED_WITH_LIMITATIONS"},
            {"module": "voltage_drop", "status": "VALIDATED_WITH_LIMITATIONS"},
        ],
        "findings": ([{
            "code": "QA050",
            "severity": "BLOCKER",
            "message": "MODEL_PLACEHOLDER TBC no materializado en el solver; faltan datos: uk_percent, vector_group.",
            "element": "Transformer.TR_AUX_A",
        }] if blocked else []),
        "summary": {
            "blockers": 1 if blocked else 0,
            "errors": 0,
            "warnings": 0,
            "model_data_ok": not blocked,
            "apto_para_emision": False,
        },
    }


def test_readiness_view_renders_model_state_tbc_and_qa_blocker():
    html = workspace_readiness_view.enhance_html(
        _base_html(),
        _snapshot(with_placeholder=True),
        _qa(blocked=True),
    )

    assert workspace_readiness_view.MARKER in html
    assert 'data-tab="preparacion"' in html
    assert 'id="panel-preparacion"' in html
    assert "Preparación de ingeniería" in html
    assert "CONSTRUIDO / MODIFICADO" in html
    assert "Transformer.TR_AUX_A" in html
    assert "uk_percent, vector_group" in html
    assert "SLD Rev.0" in html
    assert "QA050" in html
    assert "BLOCKER" in html
    assert "construido ≠ resuelto ≠ apto para cualquier estudio ≠ emisión profesional" in html
    assert "professional_emission=false" in html


def test_readiness_view_can_show_clean_base_qa_without_claiming_professional_emission():
    html = workspace_readiness_view.enhance_html(
        _base_html(),
        _snapshot(with_placeholder=False),
        _qa(blocked=False),
    )

    assert "Sin MODEL_PLACEHOLDER_TBC" in html
    assert "QA BASE SIN BLOCKERS/ERRORES" in html
    assert "No equivale a readiness universal" in html
    assert "professional_emission=false" in html


def test_readiness_view_is_idempotent():
    snapshot = _snapshot()
    qa = _qa()
    once = workspace_readiness_view.enhance_html(_base_html(), snapshot, qa)
    twice = workspace_readiness_view.enhance_html(once, snapshot, qa)

    assert twice == once
    assert twice.count(workspace_readiness_view.MARKER) == 1
    assert twice.count('data-tab="preparacion"') == 1
    assert twice.count('id="panel-preparacion"') == 1


def test_readiness_javascript_only_toggles_navigation():
    script = workspace_readiness_view._script()
    forbidden = (
        "Math.",
        "opendss",
        "pandapower",
        "fetch(",
        "XMLHttpRequest",
        "Solve",
        "calc_sc",
        "uk_percent",
        "vector_group",
        "model_data_ok",
    )
    for token in forbidden:
        assert token not in script

    assert "data-tab=\"preparacion\"" in script
    assert "classList.toggle" in script


def test_workspace_snapshot_exposes_runtime_placeholders_without_solver_materialization():
    core.crear_circuito("workspace_readiness_snapshot", 4.16, bus_fuente="source_bus")
    model_placeholders.registrar(
        element_id="Transformer.TR_TBC",
        element_type="TRANSFORMER",
        known_data={"kva": 1000.0},
        missing_fields=["uk_percent", "vector_group"],
        source_reference="Design Basis Rev.0",
    )
    snapshot = workspace_state.snapshot()

    assert snapshot["model_placeholders"]["count"] == 1
    item = snapshot["model_placeholders"]["items"][0]
    assert item["id"] == "Transformer.TR_TBC"
    assert item["solver_materialized"] is False
    assert item["missing_fields"] == ["uk_percent", "vector_group"]


def test_readiness_view_module_has_no_electrical_backend_calls():
    source = inspect.getsource(workspace_readiness_view)
    forbidden = (
        "opendssdirect",
        "from pandapower",
        "dss(",
        "calc_sc(",
        "analizar_flujo_operacion",
        "ejecutar_flujo",
    )
    for token in forbidden:
        assert token not in source
