"""P3B — datasets numéricos versionados para ampacidad.

La existencia de un valor numérico no implica que pueda sustentar emisión.
Cada dataset declara procedencia, estado de verificación y política de uso.
Los datasets secundarios pueden usarse para desarrollo/benchmark de la
infraestructura únicamente con opt-in explícito.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

_DATA_FILE = Path(__file__).with_name("data") / "ampacity_p3b_numeric_datasets.json"

PRIMARY_VERIFIED = "PRIMARY_VERIFIED"
SECONDARY_TRANSCRIPTION = "SECONDARY_TRANSCRIPTION"
PENDING_PRIMARY_VERIFICATION = "PENDING_PRIMARY_VERIFICATION"

RESOLVED_PRIMARY = "RESOLVED_PRIMARY"
RESOLVED_SECONDARY = "RESOLVED_SECONDARY"
DATASET_NOT_APPROVED = "DATASET_NOT_APPROVED"
DATASET_NOT_FOUND = "DATASET_NOT_FOUND"
VALUE_NOT_TABULATED = "VALUE_NOT_TABULATED"
SCOPE_MISMATCH = "SCOPE_MISMATCH"


def _load() -> dict[str, Any]:
    payload = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    if int(payload.get("schema_version") or 0) != 1:
        raise ValueError("P3B001: schema de datasets numéricos no soportado")
    return payload


def listar_datasets() -> list[dict[str, Any]]:
    return [deepcopy(item) for item in _load().get("datasets", [])]


def obtener_dataset(dataset_id: str) -> dict[str, Any]:
    key = str(dataset_id or "").strip().upper()
    for item in _load().get("datasets", []):
        if str(item.get("id") or "").upper() == key:
            return deepcopy(item)
    raise ValueError(f"P3B002: dataset no registrado: {dataset_id}")


def _scope_check(dataset: dict[str, Any], installation_method: str, arrangement_id: str | None) -> list[str]:
    scope = dataset.get("scope", {})
    issues: list[str] = []
    method = str(installation_method or "").strip().upper()
    methods = {str(item).upper() for item in scope.get("installation_methods", [])}
    if methods and method not in methods:
        issues.append(f"installation_method={method} fuera del alcance del dataset")

    required_arrangement = str(scope.get("arrangement_id") or "").strip()
    actual_arrangement = str(arrangement_id or "").strip()
    if required_arrangement and actual_arrangement != required_arrangement:
        issues.append(
            f"arrangement_id requerido={required_arrangement}; recibido={actual_arrangement or 'NONE'}"
        )
    return issues


def resolver_factor(
    dataset_id: str,
    installation_method: str,
    circuits_grouped: int,
    arrangement_id: str | None = None,
    allow_secondary: bool = False,
) -> dict[str, Any]:
    """Resuelve un valor exacto de dataset sin interpolar ni extrapolar."""
    dataset = obtener_dataset(dataset_id)
    scope_issues = _scope_check(dataset, installation_method, arrangement_id)
    if scope_issues:
        return {
            "status": SCOPE_MISMATCH,
            "dataset_id": dataset["id"],
            "factor": None,
            "scope_issues": scope_issues,
            "professional_emission": False,
        }

    provenance = dataset.get("provenance", {})
    source_type = str(provenance.get("source_type") or "")
    verified = str(provenance.get("verification_status") or "")
    usage = dataset.get("usage_policy", {})
    secondary = source_type == "secondary_reproduction" or verified != PRIMARY_VERIFIED
    if secondary and not allow_secondary:
        return {
            "status": DATASET_NOT_APPROVED,
            "dataset_id": dataset["id"],
            "factor": None,
            "verification_status": verified,
            "requires_explicit_secondary_opt_in": True,
            "professional_emission": False,
            "provenance": deepcopy(provenance),
            "note": "Existe un valor de desarrollo, pero no se devuelve sin opt-in explícito por ser transcripción secundaria.",
        }

    grouped = int(circuits_grouped)
    if grouped < 1:
        raise ValueError("P3B003: circuits_grouped debe ser >= 1")
    values = dataset.get("values", {})
    key = str(grouped)
    if key not in values:
        return {
            "status": VALUE_NOT_TABULATED,
            "dataset_id": dataset["id"],
            "factor": None,
            "requested": {"circuits_grouped": grouped},
            "available_exact_values": sorted(int(item) for item in values),
            "interpolation": False,
            "extrapolation": False,
            "professional_emission": False,
            "note": "P3B no interpola ni extrapola valores no tabulados.",
        }

    factor = float(values[key])
    primary = verified == PRIMARY_VERIFIED and not secondary
    status = RESOLVED_PRIMARY if primary else RESOLVED_SECONDARY
    professional = bool(usage.get("professional_emission")) and primary
    return {
        "status": status,
        "dataset_id": dataset["id"],
        "profile_id": dataset.get("profile_id"),
        "norm_reference_id": dataset.get("norm_reference_id"),
        "axis": dataset.get("axis"),
        "table": dataset.get("table"),
        "factor": factor,
        "query": {
            "installation_method": str(installation_method).upper(),
            "circuits_grouped": grouped,
            "arrangement_id": arrangement_id,
        },
        "provenance": deepcopy(provenance),
        "verification_status": verified,
        "professional_emission": professional,
        "automatic_normative_lookup": professional,
        "note": (
            "Valor resuelto desde fuente primaria verificada."
            if primary
            else "Valor secundario habilitado solo para desarrollo/benchmark; no sustenta emisión profesional."
        ),
    }


def resolver_grouping_for_route(
    route: dict[str, Any],
    circuits_grouped: int,
    arrangement_id: str,
    allow_secondary: bool = False,
) -> dict[str, Any]:
    """Selecciona dataset compatible para el eje grouping de un routing P3A."""
    if str(route.get("profile_id") or "") != "PERU_CNE_UTIL_2006_030_004":
        return {
            "status": DATASET_NOT_FOUND,
            "factor": None,
            "reason": "No existe dataset P3B para el perfil normativo solicitado.",
            "professional_emission": False,
        }
    method = str(route.get("installation_method") or "").upper()
    candidates = [
        item for item in listar_datasets()
        if item.get("profile_id") == route.get("profile_id") and item.get("axis") == "grouping"
    ]
    for dataset in candidates:
        result = resolver_factor(
            dataset["id"],
            installation_method=method,
            circuits_grouped=circuits_grouped,
            arrangement_id=arrangement_id,
            allow_secondary=allow_secondary,
        )
        if result.get("status") != SCOPE_MISMATCH:
            return result
    return {
        "status": DATASET_NOT_FOUND,
        "factor": None,
        "reason": "No se encontró dataset cuyo alcance coincida con método/disposición.",
        "professional_emission": False,
    }
