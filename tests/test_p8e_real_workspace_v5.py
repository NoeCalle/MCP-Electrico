from mcp_electrico import workspace_p5_view, workspace_p8d2_view


def _base_html() -> str:
    return '''<!doctype html><html><head><style></style></head><body>
<div class="tabs"><button type="button" class="tab" data-tab="cortocircuito">Cortocircuito</button></div>
<div class="workspace-content"><section class="panel" id="panel-cortocircuito"></section></div>
<aside class="inspector"><select id="elementSelect"><option value="Line.feeder">Feeder</option></select></aside>
</body></html>'''


def _protection_snapshot() -> dict:
    return {
        "devices": [{
            "id": "Protection.QF01",
            "device_type": "circuit_breaker",
            "protected_element": "Line.feeder",
            "ratings": {
                "in_a": 400.0,
                "ue_kv": 0.48,
                "icu_ka": 36.0,
                "ics_ka": 25.0,
                "icw_ka": 20.0,
            },
            "settings": None,
            "curve": {
                "id": "QF01-MFR-TCC",
                "dataset_id": "QF01-TCC-DATA-REV-A",
                "time_semantics": "TOTAL_CLEARING_TIME",
                "numeric_dataset_loaded": True,
            },
        }]
    }


def _datasets() -> list[dict]:
    return [{
        "dataset_id": "QF01-TCC-DATA-REV-A",
        "curve_id": "QF01-MFR-TCC",
        "shape": "BAND",
        "time_semantics": "TOTAL_CLEARING_TIME",
        "segments": [{
            "id": "full_range",
            "points": [
                {"current_a": 400.0, "time_min_s": 10.0, "time_max_s": 12.0},
                {"current_a": 4000.0, "time_min_s": 0.10, "time_max_s": 0.12},
            ],
        }],
        "source": {"reference": "Manufacturer TCC REV-A", "revision": "REV-A"},
    }]


def _aggregate() -> dict:
    return {
        "schema": "MCP_ELECTRICO_P8D2_PROTECTION_RESULTS_V1",
        "execution_status": "PROTECTION_EXECUTION_COMPLETED",
        "model_revision": 7,
        "device_count": 1,
        "all_clearing_times_ready": True,
        "p4_results_reused": True,
        "p4_recalculation_inside_p5": False,
        "automatic_fault_binding": False,
        "professional_emission": False,
        "devices": [{
            "device_id": "Protection.QF01",
            "device_type": "circuit_breaker",
            "protected_element": "Line.feeder",
            "fault_provenance": {
                "fault_current_ka": 18.4321,
                "fault_bus": "load_bus",
                "fault_type": "3ph",
                "case": "max",
                "current_quantity": "ikss_ka",
                "operating_voltage_kv": 0.48,
                "atomic_schema": "MCP_ELECTRICO_IEC60909_3PH_V1",
                "engine": {"engine": "pandapower"},
                "binding_source_reference": "Protection fault-duty binding REV-A",
                "automatic_target_selection": False,
            },
            "breaking_capacity": {
                "status": "PASS",
                "rating_used": {"type": "Icu", "value_ka": 36.0},
                "other_declared_ratings_not_used_for_pass": {"ics_ka": 25.0, "icw_ka": 20.0},
                "margin_ka": 17.5679,
            },
            "clearing_time": {
                "status": "CLEARING_TIME_READY",
                "clearing_time": {"conservative_time_s": 0.072},
            },
            "thermal_check": {"status": "NOT_REQUESTED", "calculation_performed": False},
            "fault_binding_explicit": True,
            "automatic_fault_binding": False,
            "professional_emission": False,
        }],
    }


def _snapshot(*, valid: bool = True, aggregate_revision: int = 7, item_revision: int = 7) -> dict:
    aggregate = _aggregate()
    aggregate["model_revision"] = aggregate_revision
    return {
        "status": {
            "model_revision": item_revision,
            "studies": {
                "protection_tcc": {
                    "valid": valid,
                    "model_revision": item_revision,
                    "result": aggregate,
                }
            },
        }
    }


def _v5_html(snapshot: dict) -> str:
    html = workspace_p5_view.enhance_html(
        _base_html(), snapshot, _protection_snapshot(), _datasets()
    )
    return workspace_p8d2_view.enhance_html(html, snapshot)


def test_p8e1_renderiza_binding_p4_p5_y_resultado_integrado_vigente():
    html = _v5_html(_snapshot())

    assert workspace_p5_view.MARKER in html
    assert workspace_p8d2_view.MARKER in html
    assert 'data-module="mcp-p8e1-p8d2-v5"' in html
    assert 'data-model-revision="7"' in html
    assert "Resultado integrado P8D2" in html
    assert "Protection.QF01" in html
    assert "Line.feeder" in html
    assert "3ph · MAX @ load_bus" in html
    assert "ikss_ka = 18.4321 kA" in html
    assert "PASS · Icu 36 kA · margen 17.568 kA" in html
    assert "CLEARING_TIME_READY · t cons. 0.072 s" in html
    assert "pandapower · MCP_ELECTRICO_IEC60909_3PH_V1" in html
    assert "Protection fault-duty binding REV-A" in html
    assert "No hay selección automática" in html

    # El card V5 histórico conserva los ratings declarados separados.
    assert "Icu 36 kA" in html
    assert "Ics 25 kA" in html
    assert "Icw 20 kA" in html
    assert 'data-p5-chart-precomputed="true"' in html


def test_p8e1_no_promueve_resultado_p8d2_obsoleto_o_revision_inconsistente():
    stale = _v5_html(_snapshot(valid=False))
    mismatch = _v5_html(_snapshot(aggregate_revision=6, item_revision=7))

    assert workspace_p8d2_view.MARKER not in stale
    assert workspace_p8d2_view.MARKER not in mismatch
    assert "Resultado integrado P8D2" not in stale
    assert "Resultado integrado P8D2" not in mismatch


def test_p8e1_es_idempotente_y_no_duplica_resultado_integrado():
    snapshot = _snapshot()
    once = _v5_html(snapshot)
    twice = workspace_p8d2_view.enhance_html(once, snapshot)

    assert twice == once
    assert twice.count(workspace_p8d2_view.MARKER) == 1
    assert twice.count('data-module="mcp-p8e1-p8d2-v5"') == 1


def test_p8e1_no_agrega_javascript_ni_recalcula_ingenieria():
    source_tokens = (
        "calc_sc(",
        "Math.",
        "log10(",
        "interpolation",
        "extrapolation",
        "automatic_target_selection = True",
    )
    module_source = workspace_p8d2_view.__loader__.get_source(workspace_p8d2_view.__name__)
    assert module_source is not None
    assert "<script" not in module_source
    for token in source_tokens:
        assert token not in module_source
