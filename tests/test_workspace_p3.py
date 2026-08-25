from mcp_electrico import workspace_p3_view


def _snapshot():
    return {
        "status": {
            "studies": {
                "ampacity": {
                    "valid": True,
                    "result": {
                        "study": "ampacity",
                        "status": "NO_CUMPLE",
                        "criterion": "Ib <= In <= Iz",
                        "alimentadores": [
                            {
                                "element": "Line.f1",
                                "status": "NO_CUMPLE",
                                "values": {
                                    "ib_a": 180.0,
                                    "in_a": 220.0,
                                    "iz_base_a": 296.0,
                                    "factor_total": 0.728,
                                    "iz_a": 215.488,
                                },
                            }
                        ],
                        "summary": {
                            "total": 1,
                            "cumple": 0,
                            "no_cumple": 1,
                            "datos_insuficientes": 0,
                        },
                        "maturity": "UNDER_VALIDATION",
                        "automatic_normative_lookup": False,
                    },
                }
            }
        }
    }


def _base_html():
    return '''<!doctype html><html><head><style></style></head><body>
<div class="tabs"><button type="button" class="tab" data-tab="caida">Caída V</button></div>
<div class="workspace-content"><section class="panel" id="panel-caida"></section>
  </div>
  <aside class="inspector"><select id="elementSelect"><option value="Line.f1">F1</option></select></aside>
</body></html>'''


def test_v3_renderiza_resultados_calculados_y_madurez():
    html = workspace_p3_view.enhance_html(_base_html(), _snapshot())
    assert 'data-tab="ampacidad"' in html
    assert 'id="panel-ampacidad"' in html
    assert "UNDER_VALIDATION" in html
    assert "Ib ≤ In ≤ Iz" in html
    assert "180 A" in html
    assert "220 A" in html
    assert "215.49 A" in html
    assert "NO_CUMPLE" in html
    assert workspace_p3_view.MARKER in html


def test_v3_es_idempotente():
    once = workspace_p3_view.enhance_html(_base_html(), _snapshot())
    twice = workspace_p3_view.enhance_html(once, _snapshot())
    assert twice == once
    assert twice.count(workspace_p3_view.MARKER) == 1
    tab_html = '<button type="button" class="tab" data-tab="ampacidad">Ampacidad</button>'
    assert twice.count(tab_html) == 1


def test_javascript_v3_no_recalcula_ampacidad():
    script = workspace_p3_view._script()
    assert "Math." not in script
    assert "factor_total" not in script
    assert "iz_a" not in script
    assert "ib_a" not in script
    assert "in_a" not in script
