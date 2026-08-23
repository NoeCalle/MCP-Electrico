from pathlib import Path

from mcp_electrico import core, visual_state
from mcp_electrico.visualization import generar_diagrama_unifilar


def _build_visual_case():
    core.crear_circuito("visual_test", 13.2)
    visual_state.reset()
    core.agregar_transformador("tr1", "sourcebus", "tgbt", 500, 13.2, 0.48)
    core.agregar_linea("fm", "tgbt", "mcc", 0.02)
    core.agregar_linea("fc", "tgbt", "crit", 0.02)
    core.agregar_carga("bomba", "mcc", 55, 20, kv=0.48)
    core.agregar_carga("uci", "crit", 60, 20, kv=0.48, critica=True)
    core.agregar_generador_respaldo("ge", "crit", 70, 0.48)
    visual_state.set_load_type("bomba", "motor")
    visual_state.set_load_type("uci", "tablero")
    visual_state.configure_feeder("Line.fm", etiqueta="F-01")
    visual_state.configure_feeder(
        "Line.fc",
        etiqueta="F-02",
        dispositivos=["ats", "ups"],
        fuente_alterna="Generator.ge",
    )
    core.ejecutar_flujo_potencia()


def test_unifilar_usa_simbolos_tecnicos_y_genera_svg(tmp_path: Path):
    _build_visual_case()
    result = generar_diagrama_unifilar(str(tmp_path / "unifilar.html"))

    svg_path = Path(result["archivo_svg"])
    html_path = Path(result["archivo_html"])
    assert svg_path.exists()
    assert html_path.exists()

    svg = svg_path.read_text(encoding="utf-8")
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
    assert "CARGA CRÍTICA" in svg
    assert "REPRESENTACIÓN TÉCNICA" in svg
    assert result["estilo"] == "unifilar_tecnico_svg_v1"


def test_transformador_de_cabecera_no_se_duplica_al_ocultar_sourcebus(tmp_path: Path):
    _build_visual_case()
    result = generar_diagrama_unifilar(
        str(tmp_path / "sin_leyenda.svg"), mostrar_leyenda=False
    )
    svg = Path(result["archivo_svg"]).read_text(encoding="utf-8")

    # El caso tiene un único transformador físico. La barra sourcebus se
    # omite visualmente para producir RED -> CB -> TR -> barra BT, por lo que
    # el transformador no debe reaparecer como una rama aguas abajo.
    assert svg.count('data-symbol="transformer"') == 1
    assert "SOURCEBUS" not in svg


def test_configuracion_visual_no_modifica_modelo_electrico():
    _build_visual_case()
    elementos_antes = core.listar_elementos()
    visual_state.configure_feeder(
        "Line.fc", dispositivos=["ats", "ups"], fuente_alterna="Generator.ge"
    )
    elementos_despues = core.listar_elementos()
    assert elementos_antes == elementos_despues


def test_estado_visual_se_limpia_al_cambiar_de_circuito():
    core.crear_circuito("uno", 0.4)
    visual_state.reset()
    core.agregar_carga("m1", "sourcebus", 5, kv=0.4)
    visual_state.set_load_type("m1", "motor")
    assert visual_state.snapshot()["tipos_carga"]

    core.crear_circuito("dos", 0.4)
    assert visual_state.snapshot()["tipos_carga"] == {}
    assert visual_state.snapshot()["alimentadores"] == {}
