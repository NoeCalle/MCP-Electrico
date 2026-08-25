import json
from pathlib import Path

import pytest

from mcp_electrico import (
    ampacity,
    ampacity_profiles,
    conductor_library,
    core,
    engine_selection,
    visual_state,
)


CASES = (
    Path(__file__).resolve().parents[1]
    / "mcp_electrico"
    / "data"
    / "ampacity_p3a_reference_cases.json"
)


def _linea(nombre="f_p3a"):
    core.crear_circuito("ampacity_p3a_test", 22.9)
    visual_state.reset()
    conductor_library.reset()
    ampacity.reset()
    core.agregar_linea(nombre, "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    return conductor_library.aplicar_conductor(
        f"Line.{nombre}",
        "NEXANS-N2XSY-18-30-CU-70-PH16",
        "air_trefoil_30c",
    )


def _required_axes(result):
    return sorted(
        item["axis"]
        for item in result.get("required_axes", [])
        if item.get("required")
    )


def test_casos_patron_p3a_se_evaluan_desde_dataset_independiente():
    payload = json.loads(CASES.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert len(payload["cases"]) >= 6

    for case in payload["cases"]:
        result = ampacity_profiles.evaluar_aplicabilidad(**case["input"])
        expected = case["expected"]
        assert result["status"] == expected["status"], case["id"]
        assert _required_axes(result) == sorted(expected.get("required_axes", [])), case["id"]
        assert result["unresolved_numeric_factors"] is expected["unresolved_numeric_factors"], case["id"]
        if "base_ampacity_table" in expected:
            assert result["base_ampacity_table"] == expected["base_ampacity_table"], case["id"]
        if "missing_parameters" in expected:
            assert result["missing_parameters"] == expected["missing_parameters"], case["id"]
        if "applicable" in expected:
            assert result["applicable"] is expected["applicable"], case["id"]
        if "segment_policy" in expected:
            assert result["segment_policy"]["policy"] == expected["segment_policy"], case["id"]


def test_perfiles_cne_e_iec_no_se_mezclan():
    cne = ampacity_profiles.obtener_perfil("PERU_CNE_UTIL_2006_030_004")
    iec = ampacity_profiles.obtener_perfil("IEC_60364_5_52_2009_A1_2024")

    assert cne["status"] == "RULE_SCHEMA_READY"
    assert cne["norm_reference_id"] == "PERU_CNE_UTILIZACION_2006"
    assert iec["status"] == "REFERENCE_ONLY"
    assert iec["norm_reference_id"] == "IEC_60364_5_52_2009_A1_2024"
    assert cne["automatic_factor_lookup"] is False
    assert iec["automatic_factor_lookup"] is False

    with pytest.raises(ValueError, match="P3P006"):
        ampacity_profiles.validar_compatibilidad_norma(
            "PERU_CNE_UTIL_2006_030_004",
            "IEC_60364_5_52_2009_A1_2024",
        )


def test_metodo_d_exige_contexto_enterrado_y_resistividad_para_ducto():
    result = ampacity_profiles.evaluar_aplicabilidad(
        profile_id="PERU_CNE_UTIL_2006_030_004",
        installation_method="D",
        ambient_temperature_c=20.0,
    )
    assert result["status"] == "MISSING_INPUTS"
    assert "environment: buried_duct | direct_buried" in result["missing_parameters"]

    duct = ampacity_profiles.evaluar_aplicabilidad(
        profile_id="PERU_CNE_UTIL_2006_030_004",
        installation_method="D",
        environment="buried_duct",
        ambient_temperature_c=20.0,
    )
    assert duct["status"] == "MISSING_INPUTS"
    assert "soil_thermal_resistivity_k_m_per_w" in duct["missing_parameters"]


def test_regla_13_no_se_generaliza_a_cualquier_cambio_de_tramo():
    missing_transition = ampacity_profiles.evaluar_aplicabilidad(
        profile_id="PERU_CNE_UTIL_2006_030_004",
        installation_method="C",
        ambient_temperature_c=30.0,
        segment_count=2,
    )
    assert missing_transition["status"] == "MISSING_INPUTS"
    assert any("segment_transition" in item for item in missing_transition["missing_parameters"])

    other = ampacity_profiles.evaluar_aplicabilidad(
        profile_id="PERU_CNE_UTIL_2006_030_004",
        installation_method="C",
        ambient_temperature_c=30.0,
        segment_count=2,
        segment_transition="other",
    )
    assert other["segment_policy"]["policy"] == "MANUAL_REVIEW_REQUIRED"
    assert any("no se generaliza" in item for item in other["manual_review"])


def test_excepcion_030_004_14_permanece_manual():
    result = ampacity_profiles.evaluar_aplicabilidad(
        profile_id="PERU_CNE_UTIL_2006_030_004",
        installation_method="C",
        ambient_temperature_c=30.0,
        segment_count=2,
        segment_transition="underground_to_exposed",
        request_short_segment_exception=True,
    )
    assert result["segment_policy"]["exception_14_automatic"] is False
    assert result["segment_policy"]["exception_14_requested"] is True
    assert any("030-004(14)" in item for item in result["manual_review"])


def test_router_cne_obliga_factor_por_eje_y_luego_evalua_ib_in_iz():
    _linea()
    route = ampacity.definir_aplicabilidad_normativa(
        "Line.f_p3a",
        "PERU_CNE_UTIL_2006_030_004",
        "C",
        ambiente="air",
        temperatura_ambiente_c=35.0,
        circuitos_agrupados=1,
    )
    assert route["status"] == "REQUIREMENTS_IDENTIFIED"
    assert _required_axes(route) == ["ambient_temperature"]

    with pytest.raises(ValueError, match="P3A032"):
        ampacity.definir_condiciones(
            "Line.f_p3a",
            "PERU_CNE_UTILIZACION_2006",
            250,
            confirmar_condiciones_base=True,
            ib_diseno_a=200,
            referencia_in="QF1 250 A",
            referencia_ib="memoria de cargas",
            referencia_condiciones_instalacion="levantamiento de instalación",
        )

    with pytest.raises(ValueError, match="P3A033"):
        ampacity.definir_condiciones(
            "Line.f_p3a",
            "PERU_CNE_UTILIZACION_2006",
            250,
            factores=[{
                "id": "k_temp",
                "value": 0.96,
                "reference": "factor manual verificado en fuente autorizada del proyecto",
            }],
            ib_diseno_a=200,
            referencia_in="QF1 250 A",
            referencia_ib="memoria de cargas",
            referencia_condiciones_instalacion="levantamiento de instalación",
        )

    ampacity.definir_condiciones(
        "Line.f_p3a",
        "PERU_CNE_UTILIZACION_2006",
        250,
        factores=[{
            "id": "k_temp",
            "axis": "ambient_temperature",
            "value": 0.96,
            "reference": "factor manual verificado en fuente autorizada del proyecto",
            "table_or_clause": "030-004(8) / Tabla 5A",
        }],
        ib_diseno_a=200,
        referencia_in="QF1 250 A",
        referencia_ib="memoria de cargas",
        referencia_condiciones_instalacion="levantamiento de instalación compatible con método C",
    )
    result = ampacity.evaluar("Line.f_p3a")
    assert result["status"] == "CUMPLE"
    assert result["values"]["factor_total"] == pytest.approx(0.96)
    assert result["values"]["iz_a"] == pytest.approx(284.16)
    assert result["normative_applicability"]["profile_id"] == "PERU_CNE_UTIL_2006_030_004"

    ready = engine_selection.evaluar_preparacion_estudio("ampacidad")
    assert ready["data_status"] == "READY_DATA"


def test_cambio_posterior_del_routing_invalida_readiness_si_falta_un_eje():
    _linea()
    ampacity.definir_aplicabilidad_normativa(
        "Line.f_p3a",
        "PERU_CNE_UTIL_2006_030_004",
        "C",
        temperatura_ambiente_c=35.0,
    )
    ampacity.definir_condiciones(
        "Line.f_p3a",
        "PERU_CNE_UTILIZACION_2006",
        250,
        factores=[{
            "id": "k_temp",
            "axis": "ambient_temperature",
            "value": 0.96,
            "reference": "fuente autorizada proyecto",
        }],
        ib_diseno_a=200,
        referencia_in="QF1",
        referencia_ib="memoria",
        referencia_condiciones_instalacion="método C verificado",
    )

    ampacity.definir_aplicabilidad_normativa(
        "Line.f_p3a",
        "PERU_CNE_UTIL_2006_030_004",
        "C",
        temperatura_ambiente_c=35.0,
        circuitos_agrupados=2,
    )

    result = ampacity.evaluar("Line.f_p3a")
    assert result["status"] == "DATOS_INSUFICIENTES"
    assert "P3A033" in result["note"]

    ready = engine_selection.evaluar_preparacion_estudio("ampacidad")
    assert ready["data_status"] == "MISSING_DATA"
    assert any(item["code"] == "P3READY116" for item in ready["missing_data"])


def test_router_cne_no_puede_vincularse_a_ficha_iec():
    _linea()
    ampacity.definir_aplicabilidad_normativa(
        "Line.f_p3a",
        "PERU_CNE_UTIL_2006_030_004",
        "C",
        temperatura_ambiente_c=30.0,
    )

    with pytest.raises(ValueError, match="P3P006"):
        ampacity.definir_condiciones(
            "Line.f_p3a",
            "IEC_60364_5_52_2009_A1_2024",
            250,
            confirmar_condiciones_base=True,
            ib_diseno_a=200,
            referencia_in="QF1",
            referencia_ib="memoria",
            referencia_condiciones_instalacion="inspección",
        )
