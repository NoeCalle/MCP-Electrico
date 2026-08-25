from copy import deepcopy

import pytest

from mcp_electrico import (
    ampacity,
    ampacity_base_binding,
    conductor_library,
    core,
    visual_state,
    workspace_p3_view,
)


PRIMARY_BASE_RESULT = {
    "status": "RESOLVED_EXACT",
    "dataset_id": "TEST_TABLE_2_PRIMARY",
    "profile_id": "PERU_CNE_UTIL_2006_030_004",
    "norm_reference_id": "PERU_CNE_UTILIZACION_2006",
    "table": "Tabla 2",
    "axis": "base_ampacity",
    "query": {"installation_method": "B2", "section_mm2": 70.0},
    "value": 250.0,
    "verification_status": "PRIMARY_VERIFIED",
    "professional_emission": True,
    "automatic_normative_lookup": True,
    "provenance": {"source_type": "primary_official"},
}


def _linea():
    core.crear_circuito("p3c10b", 22.9)
    visual_state.reset()
    conductor_library.reset()
    ampacity.reset()
    core.agregar_linea("f_base", "sourcebus", "b1", 0.1, r1_ohm_km=0.3, x1_ohm_km=0.1)
    return conductor_library.aplicar_conductor(
        "Line.f_base",
        "NEXANS-N2XSY-18-30-CU-70-PH16",
        "air_trefoil_30c",
    )


def _mock_primary(monkeypatch, result=None):
    payload = deepcopy(result or PRIMARY_BASE_RESULT)
    monkeypatch.setattr(
        ampacity_base_binding.ampacity_exact_lookup,
        "resolver_catalogo",
        lambda *_args, **_kwargs: deepcopy(payload),
    )
    return ampacity_base_binding.construir_base_desde_resultado(payload)


def test_iz_base_normativa_entra_al_calculo_y_preserva_catalogo_p2(monkeypatch):
    assignment = _linea()
    assert assignment["ampacidad_aplicada_a"] == pytest.approx(296.0)
    base = _mock_primary(monkeypatch)

    ampacity.definir_condiciones(
        "Line.f_base",
        "PERU_CNE_UTILIZACION_2006",
        220.0,
        factores=[{"id": "k_manual", "axis": "temperature", "value": 0.90, "reference": "caso sintético"}],
        ib_diseno_a=180.0,
        referencia_in="QF1",
        referencia_ib="memoria",
        referencia_condiciones_instalacion="caso sintético P3C10B",
        base_normativa=base,
    )

    result = ampacity.evaluar("Line.f_base")
    assert result["values"]["iz_base_a"] == pytest.approx(250.0)
    assert result["values"]["iz_a"] == pytest.approx(225.0)
    assert result["base_evidence"]["primary"] is True
    assert result["installation"]["iz_base_origin"] == "P3B_BASE_DATASET"
    assert result["sources"]["iz_base_catalog_p2"] is not None
    assert result["automatic_normative_lookup"] is False


def test_base_de_otra_referencia_normativa_se_rechaza(monkeypatch):
    _linea()
    other = deepcopy(PRIMARY_BASE_RESULT)
    other["norm_reference_id"] = "OTRA_NORMA"
    base = _mock_primary(monkeypatch, other)

    with pytest.raises(ValueError, match="P3C10B001"):
        ampacity.definir_condiciones(
            "Line.f_base",
            "PERU_CNE_UTILIZACION_2006",
            220.0,
            factores=[{"id": "k", "value": 1.0, "reference": "sintético"}],
            ib_diseno_a=180.0,
            referencia_in="QF1",
            referencia_ib="memoria",
            referencia_condiciones_instalacion="sintético",
            base_normativa=base,
        )


def test_cambio_del_dataset_base_invalida_evaluacion(monkeypatch):
    _linea()
    base = _mock_primary(monkeypatch)
    ampacity.definir_condiciones(
        "Line.f_base",
        "PERU_CNE_UTILIZACION_2006",
        220.0,
        factores=[{"id": "k", "value": 1.0, "reference": "sintético"}],
        ib_diseno_a=180.0,
        referencia_in="QF1",
        referencia_ib="memoria",
        referencia_condiciones_instalacion="sintético",
        base_normativa=base,
    )

    changed = deepcopy(PRIMARY_BASE_RESULT)
    changed["value"] = 249.0
    monkeypatch.setattr(
        ampacity_base_binding.ampacity_exact_lookup,
        "resolver_catalogo",
        lambda *_args, **_kwargs: deepcopy(changed),
    )
    result = ampacity.evaluar("Line.f_base")
    assert result["status"] == "DATOS_INSUFICIENTES"
    assert result["missing"] == ["iz_base_normativa"]


def test_v3_distingue_catalogo_p2_de_base_normativa():
    assert workspace_p3_view._base_evidence_label({
        "base_evidence": {"origin": "P2_CATALOG", "primary": False}
    })[0] == "CATÁLOGO P2"
    assert workspace_p3_view._base_evidence_label({
        "base_evidence": {"origin": "P3B_BASE_DATASET", "normative_base": True, "primary": True}
    })[0] == "PRIMARIA"
