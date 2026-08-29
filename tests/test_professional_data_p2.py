import math

import pytest
from opendssdirect import dss

from mcp_electrico import core, model_qa, professional_data, visual_state, workspace, workspace_state


def _new(name: str, kv: float = 22.9):
    core.crear_circuito(name, kv)
    visual_state.reset()
    professional_data.reset()
    workspace_state.reset_for_circuit("test")


def _professional_transformer(name: str = "tr1", complete_pp: bool = True):
    return professional_data.agregar_transformador_profesional(
        nombre=name,
        bus_hv="sourcebus",
        bus_lv="lvbus",
        kva=1000,
        kv_hv=22.9,
        kv_lv=0.48,
        uk_percent=6.0,
        grupo_vectorial="Dyn11",
        x_r=10.0,
        no_load_loss_kw=2.0 if complete_pp else None,
        i0_percent=0.8 if complete_pp else None,
        tap_side="hv",
        tap_neutral=0,
        tap_min=-2,
        tap_max=2,
        tap_step_percent=2.5,
        tap_pos=1,
        fabricante="Fabricante de prueba",
        modelo="TR-1000",
        fuente_referencia="placa/ficha técnica de prueba",
        fuente_url="https://example.invalid/tr-1000",
    )


def test_transformador_p2_conserva_datos_derivacion_tap_y_procedencia():
    _new("p2_trafo_structured")
    result = _professional_transformer()

    assert result["id"] == "Transformer.tr1"
    assert result["vector_group"]["grupo_vectorial"] == "Dyn11"
    assert result["vector_group"]["shift_degree"] == 30.0
    assert result["short_circuit"]["uk_percent"] == 6.0
    assert result["short_circuit"]["method"] == "uk_percent + x_r"
    assert math.isclose(result["short_circuit"]["x_r_effective"], 10.0)
    assert result["tap"]["position"] == 1
    assert result["tap"]["tap_pu"] == pytest.approx(1.025)
    assert result["provenance"]["uk_percent"]["reference"] == "placa/ficha técnica de prueba"

    dss.Transformers.Name("tr1")
    assert dss.Transformers.Xhl() == pytest.approx(result["short_circuit"]["x_percent"], rel=1e-6)


def test_transformador_p2_rechaza_datos_de_impedancia_contradictorios():
    _new("p2_trafo_conflict")
    with pytest.raises(ValueError, match="P2TR013"):
        professional_data.agregar_transformador_profesional(
            "tr_bad", "sourcebus", "lvbad", 1000, 22.9, 0.48,
            uk_percent=6.0, grupo_vectorial="Dyn11", x_r=10.0,
            load_loss_kw=20.0,
        )


def test_transformador_p2_no_inventa_separacion_rx():
    _new("p2_trafo_missing_rx")
    with pytest.raises(ValueError, match="P2TR014"):
        professional_data.agregar_transformador_profesional(
            "tr_missing", "sourcebus", "lvbad", 1000, 22.9, 0.48,
            uk_percent=6.0, grupo_vectorial="Dyn11",
        )


def test_red_equivalente_guarda_max_min_y_no_inventa_secuencia_cero():
    _new("p2_source")
    source = professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=500,
        x_r_max=10,
        scc_min_mva=250,
        x_r_min=7,
        fuente_referencia="concesionaria - estudio CC",
        fuente_url="https://example.invalid/source",
    )

    assert source["active_scenario"] == "max"
    assert source["scenarios"]["max"]["scc3_mva"] == 500
    assert source["scenarios"]["min"]["scc3_mva"] == 250
    assert source["zero_sequence"]["available"] is False
    assert source["zero_sequence"]["status"] == "NOT_AVAILABLE"
    assert source["active_equivalent"]["z1_ohm"] == pytest.approx(22.9**2 / 500)

    minimum = professional_data.seleccionar_escenario_red("min")
    assert minimum["active_scenario"] == "min"
    assert minimum["active_equivalent"]["z1_ohm"] == pytest.approx(22.9**2 / 250)


def test_red_equivalente_vincula_barra_fuente_explicita_del_modelo():
    core.crear_circuito("p2_source_custom", 22.9, bus_fuente="red_concesionaria")
    professional_data.reset()

    source = professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=500,
        x_r_max=10,
        scc_min_mva=250,
        x_r_min=7,
        fuente_referencia="concesionaria - estudio CC",
        bus_fuente="red_concesionaria",
    )

    assert source["bus"] == "red_concesionaria"
    assert source["bus_provenance"]["origin"] == "usuario"
    assert source["bus_provenance"]["reference"] == "concesionaria - estudio CC"
    dss("? Vsource.source.bus1")
    assert str(dss.Text.Result()).split(".")[0].strip().lower() == "red_concesionaria"


def test_red_equivalente_rechaza_barra_fuente_que_no_coincide_con_opendss():
    core.crear_circuito("p2_source_mismatch", 22.9, bus_fuente="red_real")
    professional_data.reset()

    with pytest.raises(ValueError, match="P2SRC007"):
        professional_data.definir_red_equivalente(
            kv_ll=22.9,
            scc_max_mva=500,
            x_r_max=10,
            bus_fuente="barra_equivocada",
        )


def test_workspace_v2_serializa_y_muestra_datos_profesionales(tmp_path):
    _new("p2_workspace")
    _professional_transformer()
    professional_data.definir_red_equivalente(
        22.9, 500, 10, 250, 7,
        fuente_referencia="concesionaria - estudio CC",
    )
    core.agregar_carga("c1", "lvbus", 200, 60, fases=3, kv=0.48)
    workspace_state.mark_model_changed("p2_model")

    snap = workspace_state.snapshot()
    assert snap["schema_version"] == 2
    assert snap["model"]["source"]["scenarios"]["max"]["scc3_mva"] == 500
    assert snap["model"]["transformers"][0]["professional"]["short_circuit"]["uk_percent"] == 6.0

    path = tmp_path / "p2_workspace.html"
    workspace.configure(str(path), "P2 V2", True)
    html = path.read_text(encoding="utf-8")
    assert "Grupo vectorial" in html
    assert "Scc3 máxima" in html
    assert "Secuencia cero" in html
    assert "P2 trazable" in html


def test_qa_eleva_datos_de_falla_a_blocker_sin_cambiar_requisito_de_flujo():
    _new("p2_qa")
    _professional_transformer()
    core.agregar_carga("c1", "lvbus", 100, 30, fases=3, kv=0.48)

    flow = model_qa.auditar_modelo(["power_flow"])
    assert not any(f["code"] in {"QA210", "QA215", "QA300", "QA302"} and f["severity"] == "BLOCKER" for f in flow["findings"])

    fault = model_qa.auditar_modelo(["short_circuit"])
    assert any(f["code"] == "QA215" and f["severity"] == "BLOCKER" for f in fault["findings"])
    assert any(f["code"] == "QA300" and f["severity"] == "BLOCKER" for f in fault["findings"])
