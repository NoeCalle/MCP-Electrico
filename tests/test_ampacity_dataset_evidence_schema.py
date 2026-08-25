from copy import deepcopy
import json

import pytest

from mcp_electrico import ampacity_datasets


SOURCE_ID = "MINEM_CNE_UTIL_2006_OFFICIAL_PDF"


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
        "primary_source_id": SOURCE_ID,
        "source_sha256": "a" * 64,
        "page_references": ["Sección 030 / Tabla 5C"],
        "verification_record": {
            "reviewer": "Ingeniero revisor",
            "manual_comparison_confirmed": True,
        },
    }
    item["usage_policy"]["professional_emission"] = True
    return item


def _set_source_registry(tmp_path, monkeypatch, expected_sha256="a" * 64, norm_reference_id="PERU_CNE_UTILIZACION_2006"):
    path = tmp_path / "sources.json"
    path.write_text(
        json.dumps({
            "schema_version": 1,
            "sources": [{
                "id": SOURCE_ID,
                "norm_reference_id": norm_reference_id,
                "source_class": "OFFICIAL_PRIMARY_CANDIDATE",
                "pin_status": "PINNED",
                "expected_sha256": expected_sha256,
            }],
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(ampacity_datasets, "_PRIMARY_SOURCES_FILE", path)
    return path


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


def test_primary_verified_no_pasa_con_fuente_real_aun_unpinned():
    with pytest.raises(ValueError, match="P3B018"):
        ampacity_datasets.validar_dataset_record(_primary_candidate())


def test_primary_verified_requiere_match_con_hash_pin(tmp_path, monkeypatch):
    _set_source_registry(tmp_path, monkeypatch, expected_sha256="b" * 64)
    with pytest.raises(ValueError, match="P3B019"):
        ampacity_datasets.validar_dataset_record(_primary_candidate())


def test_primary_verified_requiere_misma_referencia_normativa(tmp_path, monkeypatch):
    _set_source_registry(
        tmp_path,
        monkeypatch,
        expected_sha256="a" * 64,
        norm_reference_id="OTRA_REFERENCIA",
    )
    with pytest.raises(ValueError, match="P3B020"):
        ampacity_datasets.validar_dataset_record(_primary_candidate())


def test_primary_verified_completo_supera_gate_solo_con_fuente_pin_exacta(tmp_path, monkeypatch):
    _set_source_registry(tmp_path, monkeypatch)
    result = ampacity_datasets.validar_dataset_record(_primary_candidate())
    assert result == {
        "valid": True,
        "dataset_id": "TEST_PRIMARY",
        "verification_status": "PRIMARY_VERIFIED",
        "professional_emission": True,
    }
