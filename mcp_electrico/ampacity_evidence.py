"""P3B — verificación de evidencia primaria para datasets de ampacidad.

Este módulo no promueve datasets automáticamente. Construye evidencia
reproducible (archivo + SHA-256 + referencias de tabla/página + revisión
humana) y evalúa si existe información suficiente para crear por PR una
nueva revisión de dataset marcada PRIMARY_VERIFIED.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from . import ampacity_datasets

_DATA_FILE = Path(__file__).with_name("data") / "ampacity_primary_sources.json"

DISCOVERED_UNPINNED = "DISCOVERED_UNPINNED"
FILE_HASHED = "FILE_HASHED"
PRIMARY_EVIDENCE_INCOMPLETE = "PRIMARY_EVIDENCE_INCOMPLETE"
PRIMARY_EVIDENCE_READY_FOR_REVIEW = "PRIMARY_EVIDENCE_READY_FOR_REVIEW"
NOT_ELIGIBLE = "NOT_ELIGIBLE"

_MAX_SOURCE_BYTES = 100 * 1024 * 1024


def _load() -> dict[str, Any]:
    payload = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    if int(payload.get("schema_version") or 0) != 1:
        raise ValueError("P3EV001: schema de fuentes primarias no soportado")
    return payload


def listar_fuentes() -> list[dict[str, Any]]:
    return [deepcopy(item) for item in _load().get("sources", [])]


def obtener_fuente(source_id: str) -> dict[str, Any]:
    key = str(source_id or "").strip().upper()
    for item in listar_fuentes():
        if str(item.get("id") or "").upper() == key:
            return item
    raise ValueError(f"P3EV002: fuente primaria no registrada: {source_id}")


def verificar_archivo(source_id: str, ruta_archivo: str) -> dict[str, Any]:
    """Calcula SHA-256 de una copia local y valida que parezca PDF.

    No descarga de Internet ni altera el registro. El hash devuelto es evidencia
    candidata que debe fijarse luego por revisión/PR si corresponde.
    """
    source = obtener_fuente(source_id)
    path = Path(str(ruta_archivo or "")).expanduser()
    if not path.exists() or not path.is_file():
        raise ValueError(f"P3EV010: archivo no encontrado: {path}")
    size = path.stat().st_size
    if size <= 0:
        raise ValueError("P3EV011: archivo fuente vacío")
    if size > _MAX_SOURCE_BYTES:
        raise ValueError("P3EV012: archivo fuente excede 100 MB")

    digest = sha256()
    prefix = b""
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            if not prefix:
                prefix = chunk[:8]
            digest.update(chunk)
    if not prefix.startswith(b"%PDF-"):
        raise ValueError("P3EV013: el archivo no tiene cabecera PDF válida")

    actual = digest.hexdigest()
    expected = str(source.get("expected_sha256") or "").strip().lower() or None
    pinned_match = expected is not None and actual == expected
    return {
        "status": FILE_HASHED,
        "source_id": source["id"],
        "norm_reference_id": source["norm_reference_id"],
        "source_class": source["source_class"],
        "path": str(path),
        "size_bytes": size,
        "sha256": actual,
        "expected_sha256": expected,
        "pinned_hash_match": pinned_match if expected else None,
        "source_pin_status": source.get("pin_status"),
        "professional_emission": False,
        "note": "Hash calculado. Esto no verifica todavía contenido de tablas ni promueve datasets.",
    }


def construir_paquete_evidencia(
    source_id: str,
    file_evidence: dict[str, Any],
    tables_checked: list[str],
    page_references: list[str],
    reviewer: str,
    manual_comparison_confirmed: bool,
    notes: str | None = None,
) -> dict[str, Any]:
    """Construye evidencia para revisión de promoción de un dataset."""
    source = obtener_fuente(source_id)
    if str(file_evidence.get("source_id") or "") != source["id"]:
        raise ValueError("P3EV020: evidencia de archivo corresponde a otra fuente")
    digest = str(file_evidence.get("sha256") or "").lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError("P3EV021: SHA-256 inválido")
    tables = sorted({str(item).strip() for item in tables_checked if str(item).strip()})
    pages = sorted({str(item).strip() for item in page_references if str(item).strip()})
    reviewer_name = str(reviewer or "").strip()

    missing: list[str] = []
    if not tables:
        missing.append("tables_checked")
    if not pages:
        missing.append("page_references")
    if not reviewer_name:
        missing.append("reviewer")
    if not manual_comparison_confirmed:
        missing.append("manual_comparison_confirmed")

    status = PRIMARY_EVIDENCE_READY_FOR_REVIEW if not missing else PRIMARY_EVIDENCE_INCOMPLETE
    return {
        "status": status,
        "source_id": source["id"],
        "norm_reference_id": source["norm_reference_id"],
        "source_class": source["source_class"],
        "file_sha256": digest,
        "file_size_bytes": file_evidence.get("size_bytes"),
        "tables_checked": tables,
        "page_references": pages,
        "reviewer": reviewer_name or None,
        "manual_comparison_confirmed": bool(manual_comparison_confirmed),
        "notes": str(notes or "").strip() or None,
        "missing": missing,
        "professional_emission": False,
        "automatic_promotion": False,
        "note": (
            "Evidencia suficiente para revisión por PR; el dataset aún no es PRIMARY_VERIFIED."
            if not missing
            else "Faltan campos de evidencia antes de revisar una promoción primaria."
        ),
    }


def evaluar_promocion_dataset(dataset_id: str, evidence_packet: dict[str, Any]) -> dict[str, Any]:
    """Evalúa si puede proponerse una revisión primaria del dataset.

    Incluso con evidencia completa, el resultado nunca modifica el dataset. La
    promoción real exige una nueva revisión versionada en Git y CI.
    """
    dataset = ampacity_datasets.obtener_dataset(dataset_id)
    source_id = str(evidence_packet.get("source_id") or "")
    source = obtener_fuente(source_id)
    reasons: list[str] = []

    if evidence_packet.get("status") != PRIMARY_EVIDENCE_READY_FOR_REVIEW:
        reasons.append("paquete_evidencia_incompleto")
    if str(dataset.get("norm_reference_id") or "") != str(source.get("norm_reference_id") or ""):
        reasons.append("norm_reference_id_no_coincide")
    table = str(dataset.get("table") or "").strip()
    tables_checked = {str(item).strip() for item in evidence_packet.get("tables_checked", [])}
    if table not in tables_checked:
        reasons.append("tabla_dataset_no_verificada")
    if str(source.get("source_class") or "") != "OFFICIAL_PRIMARY_CANDIDATE":
        reasons.append("fuente_no_oficial_candidata")
    digest = str(evidence_packet.get("file_sha256") or "")
    if len(digest) != 64:
        reasons.append("sha256_invalido")

    eligible = not reasons
    return {
        "status": "ELIGIBLE_FOR_PRIMARY_DATASET_PR" if eligible else NOT_ELIGIBLE,
        "dataset_id": dataset["id"],
        "source_id": source["id"],
        "eligible": eligible,
        "reasons": reasons,
        "proposed_verification_status": "PRIMARY_VERIFIED" if eligible else None,
        "automatic_promotion": False,
        "professional_emission": False,
        "required_next_action": (
            "Crear una nueva revisión del dataset con source_sha256, páginas/tablas verificadas y someterla a PR+CI."
            if eligible
            else "Completar/corregir evidencia antes de proponer una revisión primaria."
        ),
        "note": "La elegibilidad no cambia el estado del dataset existente ni habilita emisión.",
    }
