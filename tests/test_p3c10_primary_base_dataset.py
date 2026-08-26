import pytest

from mcp_electrico import (
    ampacity,
    ampacity_base_binding,
    ampacity_exact_lookup,
    conductor_library,
    core,
    p3_completion,
    visual_state,
)


DATASET_ID = "PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1"
QUERY = {
    "installation_method": "C",
    "conductor_material": "Cu",
    "insulation": "XLPE_EPR",
    "temperature_c": 90,
    "loaded_conductors": 3,
    "section_mm2": 70.0,
}


def _lookup():
    return ampacity_exact_lookup.resolver_catalogo(DATASET_ID, QUERY)


def _linea():
    core.crear_circuito("p3c10_primary_base", 22.9)
    visual_state.reset()
    conductor_library.reset()
    ampacity.reset()
    core.agregar_linea(
        "f_base_229",
        "sourcebus",
        "b1",
        0.1,
        r1_ohm_km=0.3,
        x1_ohm_km=0.1,
    )
    conductor_library.aplicar_conductor(
        "Line.f_base_229",
        "NEXANS-N2XSY-18-30-CU-70-PH16",
        "air_trefoil_30c",
    )
    ampacity.definir_aplicabilidad_normativa(
        "Line.f_base_229",
        "PERU_CNE_UTIL_2006_030_004",
        "C",
        ambiente="air",
        temperatura_ambiente_c=30.0,
        circuitos_agrupados=1,
    )


def test_tabla_2_primaria_resuelve_solo_consulta_exacta_revisada():
    result = _lookup()
    assert result["status"] == "RESOLVED_EXACT"
    assert result["axis"] == "base_ampacity"
    assert result["table"] == "Tabla 2"
    assert result["value"] == pytest.approx(229.0)
    assert result["verification_status"] == "PRIMARY_VERIFIED"
    assert result["professional_emission"] is True
    assert result["automatic_normative_lookup"] is True
    assert result["row_metadata"]["table_column"] == 23

    outside = dict(QUERY)
    outside["section_mm2"] = 95.0
    not_tabulated = ampacity_exact_lookup.resolver_catalogo(DATASET_ID, outside)
    assert not_tabulated["status"] == "VALUE_NOT_TABULATED"
    assert not_tabulated["value"] is None
    assert not_tabulated["professional_emission"] is False


def test_229a_entra_como_iz_base_normativa_y_catalogo_p2_se_conserva():
    _linea()
    base = ampacity_base_binding.construir_base_desde_resultado(_lookup())

    profile = ampacity.definir_condiciones(
        "Line.f_base_229",
        "PERU_CNE_UTILIZACION_2006",
        220.0,
        confirmar_condiciones_base=True,
        ib_diseno_a=180.0,
        referencia_in="QF1 220 A",
        referencia_ib="memoria de cargas",
        referencia_condiciones_instalacion="Método C y condiciones base verificadas para caso P3C10",
        base_normativa=base,
    )
    assert profile["base"]["ampacity_a"] == pytest.approx(229.0)
    assert profile["base"]["catalog_ampacity_a"] == pytest.approx(296.0)
    assert profile["base"]["evidence"]["primary"] is True

    result = ampacity.evaluar("Line.f_base_229")
    assert result["status"] == "CUMPLE"
    assert result["values"]["ib_a"] == pytest.approx(180.0)
    assert result["values"]["in_a"] == pytest.approx(220.0)
    assert result["values"]["iz_base_a"] == pytest.approx(229.0)
    assert result["values"]["factor_total"] == pytest.approx(1.0)
    assert result["values"]["iz_a"] == pytest.approx(229.0)
    assert result["base_evidence"]["dataset_id"] == DATASET_ID
    assert result["base_evidence"]["table"] == "Tabla 2"
    assert result["installation"]["iz_base_origin"] == "P3B_BASE_DATASET"
    assert result["installation"]["iz_base_table"] == "Tabla 2"
    assert result["professional_emission"] is False


def test_gate_cierra_p3c10_y_p3c11_sin_abrir_p4():
    gate = p3_completion.evaluar_cierre_p3()
    criteria = {item["id"]: item for item in gate["criteria"]}

    assert criteria["P3C08"]["status"] == "DONE"
    assert criteria["P3C09"]["status"] == "DONE"
    assert criteria["P3C10"]["status"] == "DONE"
    assert criteria["P3C11"]["status"] == "DONE"
    assert criteria["P3C12"]["status"] == "PENDING"
    assert criteria["P3C13"]["status"] == "PENDING"
    assert gate["phase_status"] == "NOT_READY"
    assert gate["ready_for_next_phase"] is False
    assert gate["next_phase"] is None
    assert gate["professional_emission"] is False
