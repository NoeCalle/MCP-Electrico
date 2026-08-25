from hashlib import sha256

import pytest

from mcp_electrico import ampacity_evidence


SOURCE = "MINEM_CNE_UTIL_2006_OFFICIAL_PDF"
DATASET = "PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_SECONDARY_V1"


def _fake_pdf(tmp_path):
    data = b"%PDF-1.7\n% MCP test source\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
    path = tmp_path / "cne.pdf"
    path.write_bytes(data)
    return path, data


def test_fuente_oficial_candidata_permanece_unpinned():
    source = ampacity_evidence.obtener_fuente(SOURCE)
    assert source["source_class"] == "OFFICIAL_PRIMARY_CANDIDATE"
    assert source["pin_status"] == "DISCOVERED_UNPINNED"
    assert source["expected_sha256"] is None


def test_verificar_archivo_calcula_sha_sin_promover(tmp_path):
    path, data = _fake_pdf(tmp_path)
    result = ampacity_evidence.verificar_archivo(SOURCE, str(path))
    assert result["status"] == "FILE_HASHED"
    assert result["sha256"] == sha256(data).hexdigest()
    assert result["pinned_hash_match"] is None
    assert result["professional_emission"] is False


def test_verificar_archivo_rechaza_no_pdf(tmp_path):
    path = tmp_path / "not_pdf.bin"
    path.write_bytes(b"not a pdf")
    with pytest.raises(ValueError, match="P3EV013"):
        ampacity_evidence.verificar_archivo(SOURCE, str(path))


def test_paquete_incompleto_no_es_elegible(tmp_path):
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
    result = ampacity_evidence.evaluar_promocion_dataset(DATASET, packet)
    assert result["eligible"] is False
    assert result["status"] == "NOT_ELIGIBLE"
    assert result["professional_emission"] is False


def test_evidencia_completa_solo_habilita_pr_no_promocion_automatica(tmp_path):
    path, _ = _fake_pdf(tmp_path)
    file_evidence = ampacity_evidence.verificar_archivo(SOURCE, str(path))
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

    result = ampacity_evidence.evaluar_promocion_dataset(DATASET, packet)
    assert result["eligible"] is True
    assert result["status"] == "ELIGIBLE_FOR_PRIMARY_DATASET_PR"
    assert result["proposed_verification_status"] == "PRIMARY_VERIFIED"
    assert result["automatic_promotion"] is False
    assert result["professional_emission"] is False


def test_tabla_distinta_no_puede_promover_dataset(tmp_path):
    path, _ = _fake_pdf(tmp_path)
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
