from __future__ import annotations

from math import sqrt

import pytest

from mcp_electrico import core


def _build_two_level_network() -> None:
    core.crear_circuito("voltage_base_resolution", 22.9)
    core.agregar_linea(
        "mv",
        "sourcebus",
        "se_mt",
        0.05,
        fases=3,
        r1_ohm_km=0.30,
        x1_ohm_km=0.12,
    )
    core.agregar_transformador(
        "tr",
        "se_mt",
        "tgbt",
        1000.0,
        22.9,
        0.48,
        "delta",
        "wye",
    )
    core.agregar_linea(
        "lv",
        "tgbt",
        "db_main",
        0.02,
        fases=3,
        r1_ohm_km=0.10,
        x1_ohm_km=0.08,
    )
    core.agregar_carga("load", "db_main", 100.0, 30.0, fases=3, kv=0.48)


def test_opendss_bus_voltage_bases_follow_explicit_transformer_levels():
    _build_two_level_network()
    flow = core.ejecutar_flujo_potencia()

    assert flow["convergio"] is True
    buses = flow["voltajes_por_bus"]
    assert buses["sourcebus"]["kv_base"] == pytest.approx(22.9 / sqrt(3), abs=0.001)
    assert buses["se_mt"]["kv_base"] == pytest.approx(22.9 / sqrt(3), abs=0.001)
    assert buses["tgbt"]["kv_base"] == pytest.approx(0.48 / sqrt(3), abs=0.001)
    assert buses["db_main"]["kv_base"] == pytest.approx(0.48 / sqrt(3), abs=0.001)

    for bus in ("tgbt", "db_main"):
        assert buses[bus]["voltajes_pu"]
        assert min(buses[bus]["voltajes_pu"]) > 0.80
        assert max(buses[bus]["voltajes_pu"]) < 1.20


def test_load_voltage_does_not_overwrite_existing_network_level():
    _build_two_level_network()
    # Una carga incompatible no debe redefinir silenciosamente el nivel que ya
    # quedó fijado por transformador + propagación de línea.
    core.agregar_carga("bad_declared_load", "db_main", 1.0, 0.0, fases=3, kv=0.40)
    flow = core.ejecutar_flujo_potencia()

    assert flow["voltajes_por_bus"]["db_main"]["kv_base"] == pytest.approx(
        0.48 / sqrt(3), abs=0.001
    )
