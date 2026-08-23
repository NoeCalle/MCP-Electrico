from pathlib import Path

from mcp_electrico import core, visual_state
from mcp_electrico.visualization import generar_diagrama_unifilar


def _build_visual_case():
    core.crear_circuito("visual_test", 13.2)
    visual_state.reset()
    core.agregar_transformador("tr_01", "sourcebus", "tgbt", 500, 13.2, 0.48)
    core.agregar_linea("f_motor", "tgbt", "mcc_01", 0.02)
    core.agregar_linea("f_critico", "tgbt", "tcrit_01", 0.02)
    core.agregar_carga("motor_bomba", "mcc_01", 55, 20, kv=0.48)
    core.agregar_carga("uci", "tcrit_01", 60, 20, kv=0.48, critica=True)
    core.agregar_generador_respaldo("ge_01", "tcrit_01", 70, 0.48)

    visual_state.set_load_type("motor_bomba", "motor")
    visual_state.set_load_type("uci", "tablero")
    visual_state.set_load_label("motor_bomba", "M-01 · BOMBA")
    visual_state.set_load_label("uci", "TABLERO CRÍTICO")
    visual_state.configure_bus("tgbt", "barra", "TGBT")
    visual_state.configure_feeder(
        "Line.f_motor",
        etiqueta="F-01",
        proteccion="mccb",
        conductor="3×70 mm² Cu",
        corriente_nominal_a=125,
        capacidad_ruptura_ka=25,
    )
    visual_state.configure_feeder(
        "Line.f_critico",
        etiqueta="F-02",
        dispositivos=["ats", "ups"],
        fuente_alterna="Generator.ge_01",
        proteccion="mccb",
        conductor="3×50 mm² Cu",
        corriente_nominal_a=100,
        capacidad_ruptura_ka=25,
    )
    core.ejecutar_flujo_potencia()


def test_unifilar_v2_colapsa_buses_logicos_y_genera_svg(tmp_path: Path):
    _build_visual_case()
    result = generar_diagrama_unifilar(str(tmp_path / "unifilar.html"))
    svg = Path(result["archivo_svg"]).read_text(encoding="utf-8")

    assert Path(result["archivo_html"]).exists()
    assert result["estilo"] == "unifilar_tecnico_svg_v2"
    assert result["barras_fisicas_dibujadas"] == ["tgbt"]
    assert "mcc_01" in result["buses_logicos_no_dibujados_como_barra"]
    assert "tcrit_01" in result["buses_logicos_no_dibujados_como_barra"]

    assert svg.count('data-symbol="busbar"') == 1
    assert "MCC-01" not in svg
    assert "TCRIT-01" not in svg
    assert "C-01" not in svg

    for symbol in [
        "source",
        "breaker",
        "transformer",
        "busbar",
        "motor",
        "panel",
        "ats",
        "ups",
        "generator",
        "ground",
    ]:
        assert f'data-symbol="{symbol}"' in svg

    assert "F-01" in svg
    assert "F-02" in svg
    assert "MCCB 125 A · 25 kA" in svg
    assert "3×70 mm² Cu" in svg
    assert "TABLERO CRÍTICO" in svg
    assert "CARGA CRÍTICA" in svg

    assert "MCP ELÉCTRICO" not in svg
    assert 'data-panel="legend"' not in svg
    assert 'data-panel="rules"' not in svg


def test_transformador_de_cabecera_no_se_duplica(tmp_path: Path):
    _build_visual_case()
    result = generar_diagrama_unifilar(str(tmp_path / "u.svg"))
    svg = Path(result["archivo_svg"]).read_text(encoding="utf-8")
    assert svg.count('data-symbol="transformer"') == 1
    assert "SOURCEBUS" not in svg
    assert "500 kVA" in svg
    assert "13.2/0.48 kV" in svg
    assert "Δ/Y" in svg


def test_bus_puede_forzarse_como_barra_fisica(tmp_path: Path):
    _build_visual_case()
    visual_state.configure_bus("mcc_01", "barra", "MCC-01")
    result = generar_diagrama_unifilar(str(tmp_path / "bar.svg"))
    svg = Path(result["archivo_svg"]).read_text(encoding="utf-8")

    assert "mcc_01" not in result["buses_logicos_no_dibujados_como_barra"]
    assert "mcc_01" in result["barras_fisicas_dibujadas"]
    assert svg.count('data-symbol="busbar"') >= 2
    assert "MCC-01" in svg
    assert "C-01" in svg


def test_modo_diagnostico_y_orientacion_horizontal(tmp_path: Path):
    _build_visual_case()
    result = generar_diagrama_unifilar(
        str(tmp_path / "horizontal.svg"),
        modo="diagnostico",
        orientacion="horizontal",
        mostrar_leyenda=True,
        mostrar_reglas=True,
        mostrar_marca=True,
    )
    svg = Path(result["archivo_svg"]).read_text(encoding="utf-8")

    assert result["orientacion"] == "horizontal"
    assert result["modo"] == "diagnostico"
    assert "pu" in svg
    assert "f_motor" in svg
    assert "MCP ELÉCTRICO" in svg
    assert 'data-panel="legend"' in svg
    assert 'data-panel="rules"' in svg


def test_configuracion_visual_no_modifica_modelo_electrico():
    _build_visual_case()
    elementos_antes = core.listar_elementos()
    visual_state.configure_feeder(
        "Line.f_motor",
        etiqueta="F-X",
        proteccion="fuse",
        conductor="3×35 mm² Cu",
    )
    visual_state.configure_bus("mcc_01", "conexion", "MCC")
    visual_state.set_load_label("motor_bomba", "MOTOR DE PRUEBA")
    elementos_despues = core.listar_elementos()
    assert elementos_antes == elementos_despues


def test_estado_visual_se_limpia_al_cambiar_de_circuito():
    core.crear_circuito("uno", 0.4)
    visual_state.reset()
    core.agregar_carga("m1", "sourcebus", 5, kv=0.4)
    visual_state.set_load_type("m1", "motor")
    visual_state.set_load_label("m1", "M-01")
    visual_state.configure_bus("sourcebus", "barra", "BARRA 1")
    assert visual_state.snapshot()["tipos_carga"]

    core.crear_circuito("dos", 0.4)
    snap = visual_state.snapshot()
    assert snap["tipos_carga"] == {}
    assert snap["etiquetas_carga"] == {}
    assert snap["alimentadores"] == {}
    assert snap["buses"] == {}
