"""P3B — verificación de evidencia primaria para datasets de ampacidad.

Este módulo no promueve datasets automáticamente. Construye evidencia
reproducible (archivo + SHA-256 + referencias de tabla/página + revisión
humana) y evalúa si existe información suficiente para crear por PR una
nueva revisión de dataset marcada PRIMARY_VERIFIED.

Regla de seguridad: una fuente descubierta pero no pinneada nunca es evidencia
primaria suficiente. La huella oficial debe fijarse primero en el registro de
fuentes y la copia local debe coincidir byte a byte con ese SHA-256.
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
PINNED = "PINNED"
FILE_HASHED = "FILE_HASHED"
PRIMARY_EVIDENCE_INCOMPLETE = "PRIMARY_EVIDENCE_INCOMPLETE"
PRIMARY_EVIDENCE_READY_FOR_REVIEW = "PRIMARY_EVIDENCE_READY_FOR_REVIEW"
NOT_ELIGIBLE = "NOT_ELIGIBLE"

_MAX_SOURCE_BYTES = 100 * 1024 * 1024


def _valid_sha256(value: Any) -> bool:
    digest = str(value or "").strip().lower()
    return len(digest) == 64 and all(ch in "0123456789abcdef" for ch in digest)


def _validate_source(source: dict[str, Any]) -> None:
    pin_status = str(source.get("pin_status") or "")
    expected = source.get("expected_sha256")
    if pin_status not in {DISCOVERED_UNPINNED, PINNED}:
        raise ValueError(
            f"P3EV003: pin_status no soportado en fuente {source.get('id')}: {pin_status}"
        )
    if pin_status == DISCOVERED_UNPINNED and expected not in {None, ""}:
        raise ValueError(
            f"P3EV004: fuente {source.get('id')} está UNPINNED pero declara expected_sha256"
        )
    if pin_status == PINNED and not _valid_sha256(expected):
        raise ValueError(
            f"P3EV005: fuente {source.get('id')} está PINNED sin SHA-256 válido"
        )


def _load() -> dict[str, Any]:
    payload = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    if int(payload.get("schema_version") or 0) != 1:
        raise ValueError("P3EV001: schema de fuentes primarias no soportado")
    for source in payload.get("sources", []):
        _validate_source(source)
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
    """Calcula SHA-256 de una copia local y comprueba el pin si existe.

    No descarga de Internet ni altera el registro. Para una fuente UNPINNED el
    hash devuelto es solo un candidato: no puede sostener promoción primaria.
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
    pinned = source.get("pin_status") == PINNED
    pinned_match = actual == expected if pinned and expected else None
    return {
        "status": FILE_HASHED,
        "source_id": source["id"],
        "norm_reference_id": source["norm_reference_id"],
        "source_class": source["source_class"],
        "path": str(path),
        "size_bytes": size,
        "sha256": actual,
        "expected_sha256": expected,
        "pinned_hash_match": pinned_match,
        "source_pin_status": source.get("pin_status"),
        "eligible_as_primary_file": bool(pinned and pinned_match is True),
        "professional_emission": False,
        "note": (
            "Archivo coincide con la huella primaria pinneada; aún falta verificar tablas/páginas y revisión humana."
            if pinned_match is True
            else "Hash calculado, pero la fuente no está pinneada o la copia no coincide; no constituye evidencia primaria suficiente."
        ),
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
    if not _valid_sha256(digest):
        raise ValueError("P3EV021: SHA-256 inválido")

    expected = str(source.get("expected_sha256") or "").strip().lower()
    tables = sorted({str(item).strip() for item in tables_checked if str(item).strip()})
    pages = sorted({str(item).strip() for item in page_references if str(item).strip()})
    reviewer_name = str(reviewer or "").strip()

    missing: list[str] = []
    if source.get("pin_status") != PINNED or not _valid_sha256(expected):
        missing.append("source_pinned_sha256")
    elif digest != expected or file_evidence.get("pinned_hash_match") is not True:
        missing.append("source_hash_match")
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
        "source_pin_status": source.get("pin_status"),
        "expected_sha256": expected or None,
        "file_sha256": digest,
        "pinned_hash_match": file_evidence.get("pinned_hash_match"),
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
            else "Faltan condiciones de pin/verificación antes de revisar una promoción primaria."
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

    expected = str(source.get("expected_sha256") or "").strip().lower()
    evidence_digest = str(evidence_packet.get("file_sha256") or "").strip().lower()

    if evidence_packet.get("status") != PRIMARY_EVIDENCE_READY_FOR_REVIEW:
        reasons.append("paquete_evidencia_incompleto")
    if source.get("pin_status") != PINNED or not _valid_sha256(expected):
        reasons.append("fuente_sin_hash_primario_fijado")
    elif evidence_digest != expected or evidence_packet.get("pinned_hash_match") is not True:
        reasons.append("hash_fuente_no_coincide")
    if str(dataset.get("norm_reference_id") or "") != str(source.get("norm_reference_id") or ""):
        reasons.append("norm_reference_id_no_coincide")
    table = str(dataset.get("table") or "").strip()
    tables_checked = {str(item).strip() for item in evidence_packet.get("tables_checked", [])}
    if table not in tables_checked:
        reasons.append("tabla_dataset_no_verificada")
    if str(source.get("source_class") or "") != "OFFICIAL_PRIMARY_CANDIDATE":
        reasons.append("fuente_no_oficial_candidata")
    if not _valid_sha256(evidence_digest):
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
            else "Fijar/verificar la fuente primaria y completar/corregir evidencia antes de proponer una revisión primaria."
        ),
        "note": "La elegibilidad no cambia el estado del dataset existente ni habilita emisión.",
    }
