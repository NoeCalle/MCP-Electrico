from copy import deepcopy

import pytest

from mcp_electrico import ampacity_datasets


def _secondary():
    return ampacity_datasets.obtener_dataset(
        "PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_SECONDARY_V1"
    )


def _primary_candidate():
    item = deepcopy(_secondary())
    item["id"] = "TEST_PRIMARY"
    item["provenance"] = {
        "source_type": "primary_official",
        "verification_status": "PRIMARY_VERIFIED",
        "primary_source_id": "MINEM_CNE_UTIL_2006_OFFICIAL_PDF",
        "source_sha256": "a" * 64,
        "page_references": ["Sección 030 / Tabla 5C"],
        "verification_record": {
            "reviewer": "Ingeniero revisor",
            "manual_comparison_confirmed": True,
        },
    }
    item["usage_policy"]["professional_emission"] = True
    return item


def test_dataset_secundario_actual_supera_gate_estructural():
    result = ampacity_datasets.validar_dataset_record(_secondary())
    assert result["valid"] is True
    assert result["verification_status"] == "PENDING_PRIMARY_VERIFICATION"
    assert result["professional_emission"] is False


def test_no_permite_emision_profesional_sin_primary_verified():
    item = _secondary()
    item["usage_policy"]["professional_emission"] = True
    with pytest.raises(ValueError, match="P3B013"):
        ampacity_datasets.validar_dataset_record(item)


def test_primary_verified_requiere_hash_paginas_y_revisor():
    item = _primary_candidate()
    item["provenance"].pop("source_sha256")
    with pytest.raises(ValueError, match="P3B008"):
        ampacity_datasets.validar_dataset_record(item)

    item = _primary_candidate()
    item["provenance"]["page_references"] = []
    with pytest.raises(ValueError, match="P3B009"):
        ampacity_datasets.validar_dataset_record(item)

    item = _primary_candidate()
    item["provenance"]["verification_record"]["reviewer"] = ""
    with pytest.raises(ValueError, match="P3B010"):
        ampacity_datasets.validar_dataset_record(item)

    item = _primary_candidate()
    item["provenance"]["verification_record"]["manual_comparison_confirmed"] = False
    with pytest.raises(ValueError, match="P3B011"):
        ampacity_datasets.validar_dataset_record(item)


def test_primary_verified_completo_supera_solo_gate_de_evidencia():
    result = ampacity_datasets.validar_dataset_record(_primary_candidate())
    assert result == {
        "valid": True,
        "dataset_id": "TEST_PRIMARY",
        "verification_status": "PRIMARY_VERIFIED",
        "professional_emission": True,
    }
