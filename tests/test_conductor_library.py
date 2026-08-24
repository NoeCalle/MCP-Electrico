import pytest
from opendssdirect import dss

from mcp_electrico import conductor_library, core, visual_state


def _linea(nombre="f1", r1=0.3, x1=0.4):
    core.crear_circuito("conductores_test", 22.9)
    visual_state.reset()
    core.agregar_linea(nombre, "sourcebus", "b1", 0.1, r1_ohm_km=r1, x1_ohm_km=x1)


def test_catalogo_inicial_contiene_bt_y_varios_mt_trazables():
    bt = conductor_library.listar_conductores(nivel="BT")
    mt = conductor_library.listar_conductores(nivel="MT")

    assert len(bt) >= 3
    assert len(mt) >= 6
    assert {x["section_mm2"] for x in mt} >= {70, 95, 120, 150, 185, 240}
    for item in bt + mt:
        assert item["source"]["type"] == "manufacturer"
        assert item["source"]["confidence"] == "HIGH"
        assert item["source"]["url"].startswith("https://www.nexans.pe/")


def test_mt_aplica_r1_x1_y_normamps_publicados_por_formacion():
    _linea("f_mt")
    result = conductor_library.aplicar_conductor(
        "Line.f_mt",
        "NEXANS-N2XSY-18-30-CU-70-PH16",
        "air_trefoil_30c",
    )

    dss.Lines.Name("f_mt")
    assert dss.Lines.R1() == pytest.approx(0.3422)
    assert dss.Lines.X1() == pytest.approx(0.1619)
    assert dss.Lines.NormAmps() == pytest.approx(296.0)
    assert result["impedancia_actualizada"] is True
    assert result["r1_aplicado_ohm_km"] == pytest.approx(0.3422)
    assert result["x1_aplicado_ohm_km"] == pytest.approx(0.1619)
    assert result["fuente"]["confidence"] == "HIGH"


def test_bt_no_inventa_x_y_conserva_impedancia_previa():
    _linea("f_bt", r1=0.25, x1=0.12)
    result = conductor_library.aplicar_conductor(
        "Line.f_bt",
        "NEXANS-N2XOH-0.6-1-CU-70",
        "air_flat_30c",
    )

    dss.Lines.Name("f_bt")
    assert dss.Lines.R1() == pytest.approx(0.25)
    assert dss.Lines.X1() == pytest.approx(0.12)
    assert dss.Lines.NormAmps() == pytest.approx(279.0)
    assert result["impedancia_actualizada"] is False
    assert "no publica" in result["motivo_impedancia_no_actualizada"].lower()


def test_aplicar_conductor_preserva_metadatos_visuales_existentes():
    _linea("f_meta")
    visual_state.configure_feeder(
        "Line.f_meta",
        etiqueta="F-MT-01",
        proteccion="mccb",
        capacidad_ruptura_ka=25,
    )
    conductor_library.aplicar_conductor(
        "Line.f_meta",
        "NEXANS-N2XSY-18-30-CU-95-PH16",
        "buried_trefoil_20c",
    )
    visual = visual_state.get_feeder("Line.f_meta")

    assert visual["etiqueta"] == "F-MT-01"
    assert visual["proteccion"] == "mccb"
    assert visual["capacidad_ruptura_ka"] == pytest.approx(25)
    assert visual["corriente_nominal_a"] == pytest.approx(285)
    assert "N2XSY" in visual["conductor"]


def test_instalacion_no_publicada_se_rechaza():
    _linea("f_bad")
    with pytest.raises(ValueError, match="Instalación no disponible"):
        conductor_library.aplicar_conductor(
            "Line.f_bad",
            "NEXANS-N2XSY-18-30-CU-120-PH12",
            "bandeja_magica",
        )


def test_asignaciones_se_limpian_al_cambiar_circuito():
    _linea("f_old")
    conductor_library.aplicar_conductor(
        "Line.f_old",
        "NEXANS-N2XSY-18-30-CU-150-PH12",
        "air_flat_30c",
    )
    assert conductor_library.snapshot_asignaciones()["alimentadores"]

    core.crear_circuito("otro_circuito", 0.48)
    assert conductor_library.snapshot_asignaciones()["alimentadores"] == {}
