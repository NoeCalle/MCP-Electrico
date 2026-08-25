from copy import deepcopy

import pytest

from mcp_electrico import ampacity_base_binding


PRIMARY_RESULT = {
    "status": "RESOLVED_EXACT",
    "dataset_id": "TEST_TABLE_2_PRIMARY",
    "profile_id": "PERU_CNE_UTIL_2006_030_004",
    "norm_reference_id": "PERU_CNE_UTILIZACION_2006",
    "table": "Tabla 2",
    "axis": "base_ampacity",
    "query": {
        "installation_method": "B2",
        "conductor_material": "Cu",
        "insulation": "XLPE",
        "section_mm2": 35.0,
    },
    "value": 125.0,
    "verification_status": "PRIMARY_VERIFIED",
    "professional_emission": True,
    "automatic_normative_lookup": True,
    "provenance": {"source_type": "primary_official"},
}


def test_construye_iz_base_normativa_trazable():
    base = ampacity_base_binding.construir_base_desde_resultado(PRIMARY_RESULT)

    assert base["origin"] == "P3B_BASE_DATASET"
    assert base["ampacity_a"] == 125.0
    assert base["axis"] == "base_ampacity"
    assert base["table"] == "Tabla 2"
    assert base["dataset"]["id"] == "TEST_TABLE_2_PRIMARY"
    assert base["dataset"]["professional_emission"] is True


def test_rechaza_factor_o_tabla_que_no_sea_base_p3_v1():
    wrong_axis = deepcopy(PRIMARY_RESULT)
    wrong_axis["axis"] = "grouping"
    with pytest.raises(ValueError, match="P3C10A002"):
        ampacity_base_binding.construir_base_desde_resultado(wrong_axis)

    wrong_table = deepcopy(PRIMARY_RESULT)
    wrong_table["table"] = "Tabla 5C"
    with pytest.raises(ValueError, match="P3C10A003"):
        ampacity_base_binding.construir_base_desde_resultado(wrong_table)


def test_revalida_valor_y_procedencia_con_catalogo_activo(monkeypatch):
    monkeypatch.setattr(
        ampacity_base_binding.ampacity_exact_lookup,
        "resolver_catalogo",
        lambda *_args, **_kwargs: deepcopy(PRIMARY_RESULT),
    )
    item = ampacity_base_binding.construir_base_desde_resultado(PRIMARY_RESULT)
    validated = ampacity_base_binding.validar_base_dataset(item)
    assert validated["ampacity_a"] == 125.0
    assert validated["dataset"]["professional_emission"] is True

    tampered = deepcopy(item)
    tampered["ampacity_a"] = 126.0
    with pytest.raises(ValueError, match="P3C10A009"):
        ampacity_base_binding.validar_base_dataset(tampered)


def test_base_secundaria_requiere_opt_in_explicito(monkeypatch):
    secondary = deepcopy(PRIMARY_RESULT)
    secondary["dataset_id"] = "TEST_TABLE_2_SECONDARY"
    secondary["verification_status"] = "PENDING_PRIMARY_VERIFICATION"
    secondary["professional_emission"] = False
    secondary["automatic_normative_lookup"] = False
    secondary["provenance"] = {"source_type": "secondary_reproduction"}

    monkeypatch.setattr(
        ampacity_base_binding.ampacity_exact_lookup,
        "resolver_catalogo",
        lambda *_args, **_kwargs: deepcopy(secondary),
    )
    item = ampacity_base_binding.construir_base_desde_resultado(secondary)

    with pytest.raises(ValueError, match="P3C10A011"):
        ampacity_base_binding.validar_base_dataset(item)

    validated = ampacity_base_binding.validar_base_dataset(
        item,
        permitir_secundario=True,
    )
    assert validated["dataset"]["professional_emission"] is False


def test_catalogo_p2_no_se_confunde_con_base_normativa():
    summary = ampacity_base_binding.resumen_evidencia_base(None)
    assert summary == {
        "origin": "P2_CATALOG",
        "normative_base": False,
        "primary": False,
        "professional_emission": False,
    }
