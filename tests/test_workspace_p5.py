from mcp_electrico import workspace_p5_view


def _base_html():
    return '''<!doctype html><html><head><style></style></head><body>
<div class="tabs">
  <button type="button" class="tab" data-tab="ampacidad">Ampacidad</button>
  <button type="button" class="tab" data-tab="cortocircuito">Cortocircuito</button>
</div>
<div class="workspace-content">
  <section class="panel" id="panel-unifilar"><svg id="workspace-unifilar"></svg></section>
  <section class="panel p4-panel" id="panel-cortocircuito"></section>
  </div>
  <aside class="inspector"><select id="elementSelect"><option value="Line.f1">F1</option></select></aside>
</body></html>'''


def _protection_snapshot():
    return {
        "devices": [
            {
                "id": "Protection.qf1",
                "device_type": "circuit_breaker",
                "protected_element": "Line.f1",
                "ratings": {
                    "in_a": 250.0,
                    "ue_kv": 0.48,
                    "icu_ka": 36.0,
                    "ics_ka": 27.0,
                    "icw_ka": 20.0,
                },
                "settings": {
                    "basis": "ABSOLUTE_A",
                    "ir_a": 225.0,
                    "isd_a": 1250.0,
                    "ii_a": 2500.0,
                },
                "curve": {
                    "id": "CURVE-QF1-A",
                    "dataset_id": "ds-qf1",
                    "time_semantics": "TOTAL_CLEARING_TIME",
                    "numeric_dataset_loaded": True,
                },
            }
        ]
    }


def _datasets():
    return [
        {
            "dataset_id": "ds-qf1",
            "curve_id": "CURVE-QF1-A",
            "shape": "BAND",
            "time_semantics": "TOTAL_CLEARING_TIME",
            "interpolation": "LOG_LOG_LINEAR",
            "segments": [
                {
                    "id": "inverse",
                    "points": [
                        {"current_a": 100.0, "time_min_s": 8.0, "time_max_s": 12.0},
                        {"current_a": 200.0, "time_min_s": 2.0, "time_max_s": 3.0},
                    ],
                },
                {
                    "id": "instantaneous",
                    "points": [
                        {"current_a": 400.0, "time_min_s": 0.08, "time_max_s": 0.12},
                        {"current_a": 1000.0, "time_min_s": 0.05, "time_max_s": 0.07},
                    ],
                },
            ],
            "source": {
                "type": "TEST_DATA",
                "reference": "P5F visual benchmark",
                "revision": "A",
            },
        }
    ]


def _snapshot():
    return {
        "status": {
            "studies": {
                "protection_breaking_capacity": {
                    "valid": True,
                    "result": {
                        "status": "PASS",
                        "device_id": "Protection.qf1",
                        "margin_ka": 11.5,
                    },
                },
                "protection_clearing_time": {
                    "valid": True,
                    "result": {
                        "status": "CLEARING_TIME_READY",
                        "device_id": "Protection.qf1",
                        "clearing_time": {"conservative_time_s": 0.12},
                    },
                },
                "protection_coordination": {
                    "valid": True,
                    "result": {
                        "status": "PASS",
                        "relationship": {
                            "downstream_device": "Protection.qf1",
                            "upstream_device": "Protection.qf0",
                        },
                        "conservative_margin_s": 0.25,
                    },
                },
                "protection_conductor_thermal": {
                    "valid": False,
                    "result": {"status": "FAIL", "results": {"utilization_ratio": 1.4}},
                },
            }
        }
    }


def test_v5_renderiza_dispositivo_tcc_y_resultados_vigentes():
    html = workspace_p5_view.enhance_html(
        _base_html(), _snapshot(), _protection_snapshot(), _datasets()
    )

    assert 'data-tab="protecciones"' in html
    assert 'id="panel-protecciones"' in html
    assert workspace_p5_view.MARKER in html
    assert "Protection.qf1" in html
    assert "Line.f1" in html
    assert "Icu 36 kA" in html
    assert "Ir 225 A" in html
    assert "CURVE-QF1-A" in html
    assert "ds-qf1" in html
    assert "TOTAL_CLEARING_TIME" in html
    assert "P5F visual benchmark" in html
    assert 'data-p5-chart-precomputed="true"' in html
    assert "Capacidad de corte" in html
    assert "Clearing time" in html
    assert "Coordinación temporal" in html
    assert "11.5 kA" in html
    assert "0.12 s" in html
    assert "0.25 s" in html
    assert "Térmica conductor" not in html  # estudio obsoleto no se presenta como vigente
    assert "EXPERIMENTAL · SIN EMISIÓN PROFESIONAL" in html
    assert "no selectividad total" in html


def test_v5_banda_segmentada_no_une_discontinuidades():
    html = workspace_p5_view.enhance_html(
        _base_html(), _snapshot(), _protection_snapshot(), _datasets()
    )

    # Dos segmentos BAND producen cuatro paths independientes: min/max por segmento.
    assert html.count('class="p5-tcc-line p5-tcc-min"') == 2
    assert html.count('class="p5-tcc-line p5-tcc-max"') == 2
    assert html.count('data-segment="0"') == 2
    assert html.count('data-segment="1"') == 2
    assert "300 A" not in html  # no se fabrica un punto en el hueco 200–400 A


def test_v5_es_idempotente_y_no_duplica_tab_o_panel():
    once = workspace_p5_view.enhance_html(
        _base_html(), _snapshot(), _protection_snapshot(), _datasets()
    )
    twice = workspace_p5_view.enhance_html(
        once, _snapshot(), _protection_snapshot(), _datasets()
    )

    assert twice == once
    assert twice.count(workspace_p5_view.MARKER) == 1
    assert twice.count('data-tab="protecciones"') == 1
    assert twice.count('id="panel-protecciones"') == 1


def test_javascript_v5_solo_navega_y_no_calcula_tcc():
    script = workspace_p5_view._script()

    forbidden = (
        "Math.",
        "log10",
        "LOG_LOG_LINEAR",
        "current_a",
        "time_s",
        "time_min_s",
        "time_max_s",
        "conservative_margin_s",
        "interpolation",
        "extrapolation",
    )
    for token in forbidden:
        assert token not in script

    assert "elementSelect" in script
    assert "data-p5-select" in script
