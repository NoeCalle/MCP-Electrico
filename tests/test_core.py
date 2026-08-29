import opendssdirect as dss
import pytest

from mcp_electrico import core


def _circuito_bt_simple():
    core.crear_circuito("test_bt", 0.4)
    core.agregar_linea(
        "alimentador",
        "sourcebus",
        "tablero",
        longitud_km=0.02,
        r1_ohm_km=0.3,
        x1_ohm_km=0.2,
    )
    core.agregar_carga(
        "critica",
        "tablero",
        kw=20,
        kvar=5,
        kv=0.4,
        critica=True,
    )
    return core.ejecutar_flujo_potencia()


def test_crear_circuito_limpia_metadatos_criticos():
    core.crear_circuito("primero", 0.4)
    core.agregar_carga("uci", "sourcebus", 5, kv=0.4, critica=True)
    assert core.listar_cargas_criticas() == ["uci"]

    core.crear_circuito("segundo", 0.4)
    assert core.listar_cargas_criticas() == []


def test_crear_circuito_permite_barra_fuente_explicita_sin_sourcebus_fantasma():
    core.crear_circuito("source_custom", 22.9, bus_fuente="red_mt")
    core.agregar_linea(
        "entrada",
        "red_mt",
        "se_mt",
        longitud_km=0.01,
        r1_ohm_km=0.1,
        x1_ohm_km=0.1,
    )

    assert dss.Circuit.SetActiveElement("Vsource.source")
    source_bus = dss.CktElement.BusNames()[0].split(".")[0].lower()
    assert source_bus == "red_mt"
    buses = {bus.lower() for bus in dss.Circuit.AllBusNames()}
    assert "red_mt" in buses
    assert "sourcebus" not in buses


def test_crear_circuito_rechaza_barra_fuente_vacia_antes_de_mutar_modelo():
    core.crear_circuito("modelo_previo", 0.4)
    previous = dss.Circuit.Name()

    with pytest.raises(ValueError, match="bus_fuente"):
        core.crear_circuito("modelo_invalido", 22.9, bus_fuente="  ")

    assert dss.Circuit.Name() == previous


def test_contingencia_restaurada_deja_topologia_y_solucion_coherentes():
    flujo = _circuito_bt_simple()
    assert flujo["convergio"] is True

    resultado = core.simular_perdida_alimentador(
        "Line.alimentador", restaurar=True
    )

    assert resultado["estado_modelo"] == "restaurado_y_resuelto"
    assert resultado["estado_final_elemento"] == "cerrado"
    assert resultado["convergio_estado_restaurado"] is True

    assert dss.Circuit.SetActiveElement("Line.alimentador")
    assert not bool(dss.CktElement.IsOpen(1, 0))


def test_contingencia_puede_quedar_activa_para_unifilar():
    _circuito_bt_simple()

    resultado = core.simular_perdida_alimentador(
        "Line.alimentador", restaurar=False
    )

    assert resultado["estado_modelo"] == "contingencia_activa_y_resuelta"
    assert resultado["estado_final_elemento"] == "abierto"
    assert dss.Circuit.SetActiveElement("Line.alimentador")
    assert bool(dss.CktElement.IsOpen(1, 0))

    core.cerrar_elemento("Line.alimentador")
    assert not bool(dss.CktElement.IsOpen(1, 0))


def test_arc_flash_lee_no_asigna_categoria_ppe():
    resultado = core.estimar_arc_flash_lee(
        voltaje_kv=13.2,
        corriente_falla_ka=10,
        tiempo_despeje_s=0.2,
        distancia_trabajo_mm=610,
    )

    assert resultado["energia_incidente_J_cm2"] == pytest.approx(151.972, abs=0.001)
    assert resultado["energia_incidente_cal_cm2"] == pytest.approx(36.322, abs=0.001)
    assert resultado["frontera_arco_mm"] == pytest.approx(3356.3, abs=0.1)
    assert resultado["categoria_ppe"] is None
    assert "No se asigna" in resultado["nota_epp"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"voltaje_kv": 0, "corriente_falla_ka": 10, "tiempo_despeje_s": 0.2},
        {"voltaje_kv": 13.2, "corriente_falla_ka": -1, "tiempo_despeje_s": 0.2},
        {"voltaje_kv": 13.2, "corriente_falla_ka": 10, "tiempo_despeje_s": 0},
    ],
)
def test_arc_flash_rechaza_parametros_no_fisicos(kwargs):
    with pytest.raises(ValueError):
        core.estimar_arc_flash_lee(**kwargs)


def test_exportacion_netlist_devuelve_archivos_y_contenido(tmp_path):
    core.crear_circuito("export_test", 0.4)
    core.agregar_carga("carga", "sourcebus", 10, kv=0.4)

    resultado = core.obtener_netlist(str(tmp_path / "dss"))

    assert resultado["cantidad_archivos"] >= 1
    assert resultado["archivos"]
    assert any(a["contenido"].strip() for a in resultado["archivos"])
    assert all(a["nombre"].lower().endswith(".dss") for a in resultado["archivos"])


def test_cortocircuito_reporta_magnitudes_no_negativas():
    _circuito_bt_simple()
    resultado = core.ejecutar_cortocircuito("sourcebus")

    assert resultado["corriente_falla_amperios"]
    assert all(i >= 0 for i in resultado["corriente_falla_amperios"])
