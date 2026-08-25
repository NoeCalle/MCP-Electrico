from copy import deepcopy
from hashlib import sha256

import pytest

from mcp_electrico import ampacity_evidence


SOURCE = "MINEM_CNE_UTIL_2006_OFFICIAL_PDF"
DATASET = "PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_SECONDARY_V1"
OFFICIAL_SHA256 = "2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64"


def _fake_pdf(tmp_path, suffix=b""):
    data = b"%PDF-1.7\n% MCP test source\n1 0 obj\n<<>>\nendobj\n%%EOF\n" + suffix
    path = tmp_path / "cne.pdf"
    path.write_bytes(data)
    return path, data


def _override_source(monkeypatch, *, pin_status, expected_sha256):
    original = ampacity_evidence.obtener_fuente
    source = original(SOURCE)
    overridden = deepcopy(source)
    overridden["pin_status"] = pin_status
    overridden["expected_sha256"] = expected_sha256

    def fake_obtener(source_id):
        if str(source_id).upper() == SOURCE:
            return deepcopy(overridden)
        return original(source_id)

    monkeypatch.setattr(ampacity_evidence, "obtener_fuente", fake_obtener)
    return overridden


def _pin_source(monkeypatch, expected_sha256):
    return _override_source(
        monkeypatch,
        pin_status="PINNED",
        expected_sha256=expected_sha256,
    )


def _unpin_source(monkeypatch):
    return _override_source(
        monkeypatch,
        pin_status="DISCOVERED_UNPINNED",
        expected_sha256=None,
    )


def test_fuente_oficial_candidata_esta_pinned_con_hash_reproducible():
    source = ampacity_evidence.obtener_fuente(SOURCE)
    assert source["source_class"] == "OFFICIAL_PRIMARY_CANDIDATE"
    assert source["pin_status"] == "PINNED"
    assert source["expected_sha256"] == OFFICIAL_SHA256
    assert source["pin_evidence"]["workflow_run_id"] == 32875620716
    assert source["pin_evidence"]["size_bytes"] == 10829258


def test_verificar_archivo_distinto_del_pin_calcula_sha_sin_promover(tmp_path):
    path, data = _fake_pdf(tmp_path)
    result = ampacity_evidence.verificar_archivo(SOURCE, str(path))
    assert result["status"] == "FILE_HASHED"
    assert result["sha256"] == sha256(data).hexdigest()
    assert result["expected_sha256"] == OFFICIAL_SHA256
    assert result["pinned_hash_match"] is False
    assert result["eligible_as_primary_file"] is False
    assert result["professional_emission"] is False


def test_verificar_archivo_rechaza_no_pdf(tmp_path):
    path = tmp_path / "not_pdf.bin"
    path.write_bytes(b"not a pdf")
    with pytest.raises(ValueError, match="P3EV013"):
        ampacity_evidence.verificar_archivo(SOURCE, str(path))


def test_paquete_con_archivo_distinto_del_pin_no_es_elegible(tmp_path):
    path, _ = _fake_pdf(tmp_path)
    file_evidence = ampacity_evidence.verificar_archivo(SOURCE, str(path))
    packet = ampacity_evidence.construir_paquete_evidencia(
        SOURCE,
        file_evidence,
        tables_checked=[],
        page_references=[],
        reviewer="",
        manual_comparison_confirmed=False,
    )
    assert packet["status"] == "PRIMARY_EVIDENCE_INCOMPLETE"
    assert "source_hash_match" in packet["missing"]
    assert "tables_checked" in packet["missing"]
    result = ampacity_evidence.evaluar_promocion_dataset(DATASET, packet)
    assert result["eligible"] is False
    assert result["status"] == "NOT_ELIGIBLE"
    assert result["professional_emission"] is False


def test_unpinned_sigue_bloqueado_aunque_comparacion_manual_este_completa(tmp_path, monkeypatch):
    _unpin_source(monkeypatch)
    path, _ = _fake_pdf(tmp_path)
    file_evidence = ampacity_evidence.verificar_archivo(SOURCE, str(path))
    packet = ampacity_evidence.construir_paquete_evidencia(
        SOURCE,
        file_evidence,
        tables_checked=["Tabla 5C"],
        page_references=["Sección 030 / Tabla 5C"],
        reviewer="Ingeniero revisor",
        manual_comparison_confirmed=True,
    )
    assert packet["status"] == "PRIMARY_EVIDENCE_INCOMPLETE"
    assert packet["missing"] == ["source_pinned_sha256"]

    result = ampacity_evidence.evaluar_promocion_dataset(DATASET, packet)
    assert result["eligible"] is False
    assert "fuente_sin_hash_primario_fijado" in result["reasons"]
    assert result["proposed_verification_status"] is None


def test_pinned_con_hash_distinto_no_es_elegible(tmp_path, monkeypatch):
    path, data = _fake_pdf(tmp_path)
    wrong_digest = sha256(data + b"otra copia").hexdigest()
    _pin_source(monkeypatch, wrong_digest)

    file_evidence = ampacity_evidence.verificar_archivo(SOURCE, str(path))
    assert file_evidence["pinned_hash_match"] is False
    assert file_evidence["eligible_as_primary_file"] is False

    packet = ampacity_evidence.construir_paquete_evidencia(
        SOURCE,
        file_evidence,
        tables_checked=["Tabla 5C"],
        page_references=["Sección 030 / Tabla 5C"],
        reviewer="Ingeniero revisor",
        manual_comparison_confirmed=True,
    )
    assert packet["status"] == "PRIMARY_EVIDENCE_INCOMPLETE"
    assert "source_hash_match" in packet["missing"]

    result = ampacity_evidence.evaluar_promocion_dataset(DATASET, packet)
    assert result["eligible"] is False
    assert "hash_fuente_no_coincide" in result["reasons"]


def test_pinned_match_solo_habilita_pr_no_promocion_automatica(tmp_path, monkeypatch):
    path, data = _fake_pdf(tmp_path)
    digest = sha256(data).hexdigest()
    _pin_source(monkeypatch, digest)

    file_evidence = ampacity_evidence.verificar_archivo(SOURCE, str(path))
    assert file_evidence["pinned_hash_match"] is True
    assert file_evidence["eligible_as_primary_file"] is True

    packet = ampacity_evidence.construir_paquete_evidencia(
        SOURCE,
        file_evidence,
        tables_checked=["Tabla 5C"],
        page_references=["Sección 030 / Tabla 5C"],
        reviewer="Ingeniero revisor",
        manual_comparison_confirmed=True,
        notes="Comparación manual registrada para prueba de infraestructura.",
    )
    assert packet["status"] == "PRIMARY_EVIDENCE_READY_FOR_REVIEW"
    assert packet["automatic_promotion"] is False
    assert packet["pinned_hash_match"] is True

    result = ampacity_evidence.evaluar_promocion_dataset(DATASET, packet)
    assert result["eligible"] is True
    assert result["status"] == "ELIGIBLE_FOR_PRIMARY_DATASET_PR"
    assert result["proposed_verification_status"] == "PRIMARY_VERIFIED"
    assert result["automatic_promotion"] is False
    assert result["professional_emission"] is False


def test_tabla_distinta_no_puede_promover_dataset(tmp_path, monkeypatch):
    path, data = _fake_pdf(tmp_path)
    _pin_source(monkeypatch, sha256(data).hexdigest())
    file_evidence = ampacity_evidence.verificar_archivo(SOURCE, str(path))
    packet = ampacity_evidence.construir_paquete_evidencia(
        SOURCE,
        file_evidence,
        tables_checked=["Tabla 5D"],
        page_references=["Sección 030 / Tabla 5D"],
        reviewer="Ingeniero revisor",
        manual_comparison_confirmed=True,
    )
    result = ampacity_evidence.evaluar_promocion_dataset(DATASET, packet)
    assert result["eligible"] is False
    assert "tabla_dataset_no_verificada" in result["reasons"]
