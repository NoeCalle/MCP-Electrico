from pathlib import Path

import pytest

import server
from mcp_electrico import core, studies, visual_state, workspace_state


def _build_case():
    core.crear_circuito("study_test", 0.4)
    visual_state.reset()
    workspace_state.reset_for_circuit("study_test")
    core.agregar_linea(
        "f1",
        "sourcebus",
        "tablero",
        longitud_km=0.08,
        r1_ohm_km=0.45,
        x1_ohm_km=0.18,
    )
    core.agregar_carga("carga", "tablero", kw=35, kvar=12, kv=0.4)
    visual_state.configure_feeder(
        "Line.f1",
        etiqueta="F-01",
        conductor="3x35 mm2 Cu XLPE",
        corriente_nominal_a=100,
        proteccion="mccb",
    )


def test_flujo_detallado_reporta_corriente_y_cargabilidad():
    _build_case()
    result = studies.analizar_flujo_operacion()

    assert result["convergio"] is True
    assert result["alimentadores"]
    feeder = result["alimentadores"][0]
    assert feeder["id"] == "Line.f1"
    assert feeder["corriente_max_a"] is not None
    assert feeder["corriente_max_a"] > 0
    assert feeder["flujo_kw_terminal1"] is not None
    assert feeder["cargabilidad_pct"] is not None
    assert feeder["fuente_corriente_nominal"] == "metadato_explicito_usuario"


def test_caida_tension_separa_resultado_de_criterio():
    _build_case()
    result = studies.analizar_caida_tension(limite_pct=0.01)

    assert result["convergio"] is True
    assert result["criterio"]["limite_pct"] == 0.01
    assert result["criterio"]["normativo_universal"] is False
    assert result["criterio"]["origen"] == "configurable_por_usuario"
    assert result["alimentadores"]
    feeder = result["alimentadores"][0]
    assert feeder["caida_evaluada_pct"] >= 0
    assert feeder["caida_promedio_pct_firmada"] is not None
    assert feeder["estado_criterio"] in {"OK", "EXCEDE"}
    assert result["resumen"]["vpu_min_sistema"] is not None


def test_caida_tension_rechaza_limite_no_positivo():
    _build_case()
    with pytest.raises(ValueError):
        studies.analizar_caida_tension(0)


def test_workspace_integra_flujo_y_caida_tension(tmp_path: Path):
    target = tmp_path / "workspace_estudios.html"
    server.configurar_workspace(str(target), "Workspace estudios", True)
    server.crear_circuito("workspace_studies", 0.4)
    server.agregar_linea(
        "f1",
        "sourcebus",
        "tablero",
        0.08,
        r1_ohm_km=0.45,
        x1_ohm_km=0.18,
    )
    server.agregar_carga("carga", "tablero", 35, 12, kv=0.4)
    server.configurar_alimentador_unifilar(
        "Line.f1",
        etiqueta="F-01",
        conductor="3x35 mm2 Cu XLPE",
        proteccion="mccb",
        corriente_nominal_a=100,
    )

    pf = server.ejecutar_flujo_potencia()
    assert pf["convergio"] is True
    drop = server.analizar_caida_tension(limite_pct=3.0)
    assert drop["criterio"]["limite_pct"] == 3.0

    state = server.obtener_estado_workspace()["workspace"]
    assert state["studies"]["flow"]["valid"] is True
    assert state["studies"]["voltage_drop"]["valid"] is True

    html = target.read_text(encoding="utf-8")
    assert 'data-tab="flujo"' in html
    assert 'data-tab="caida"' in html
    assert 'id="panel-flujo"' in html
    assert 'id="panel-caida"' in html
    assert "Criterio configurable" in html
    assert "F-01" in html
