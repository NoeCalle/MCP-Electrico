"""Clasificación determinista de evidencia normativa para P3/P3B.

Este módulo responde una pregunta distinta a ``READY_DATA``: no evalúa si el
estudio puede ejecutarse, sino qué calidad de evidencia respalda los factores
que entran a Iz. Mantener ambos ejes separados evita tratar un dataset
secundario como dato faltante y, a la vez, evita confundir completitud técnica
con evidencia normativa primaria.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import ampacity

NOT_CONFIGURED = "NOT_CONFIGURED"
PRIMARY_EVIDENCE_READY = "PRIMARY_EVIDENCE_READY"
SECONDARY_EVIDENCE_ONLY = "SECONDARY_EVIDENCE_ONLY"
MANUAL_EVIDENCE = "MANUAL_EVIDENCE"
BASE_CONDITIONS_CONFIRMED = "BASE_CONDITIONS_CONFIRMED"
MIXED_EVIDENCE = "MIXED_EVIDENCE"
EVIDENCE_INCOMPLETE = "EVIDENCE_INCOMPLETE"


def _profile_status(profile: dict[str, Any]) -> dict[str, Any]:
    element = str(profile.get("element") or "Line.?")
    correction = profile.get("correction") or {}
    mode = str(correction.get("mode") or "")
    evidence = deepcopy(correction.get("factor_evidence") or {})
    factors = correction.get("factors") or []
    base_evidence = deepcopy((profile.get("base") or {}).get("evidence") or {})

    if mode == "BASE_CONDITIONS_CONFIRMED":
        return {
            "element": element,
            "status": BASE_CONDITIONS_CONFIRMED,
            "professional_normative_evidence_ready": False,
            "factor_evidence": evidence,
            "base_evidence": base_evidence,
            "reasons": [
                "Las condiciones base fueron confirmadas explícitamente; no existe todavía un lookup P3B primario que respalde toda la cadena normativa."
            ],
        }

    if mode != "EXPLICIT_FACTORS" or not factors:
        return {
            "element": element,
            "status": EVIDENCE_INCOMPLETE,
            "professional_normative_evidence_ready": False,
            "factor_evidence": evidence,
            "base_evidence": base_evidence,
            "reasons": ["La ficha no contiene un conjunto de factores con evidencia clasificable."],
        }

    manual = int(evidence.get("manual") or 0)
    primary = int(evidence.get("dataset_primary") or 0)
    secondary = int(evidence.get("dataset_secondary") or 0)
    total = len(factors)

    if manual + primary + secondary != total:
        return {
            "element": element,
            "status": EVIDENCE_INCOMPLETE,
            "professional_normative_evidence_ready": False,
            "factor_evidence": evidence,
            "base_evidence": base_evidence,
            "reasons": ["El resumen de evidencia no cubre todos los factores configurados."],
        }

    kinds = sum(bool(value) for value in (manual, primary, secondary))
    if kinds > 1:
        status = MIXED_EVIDENCE
        ready = False
        reasons = [
            f"La ficha mezcla evidencia: manual={manual}, primaria={primary}, secundaria={secondary}."
        ]
    elif secondary:
        status = SECONDARY_EVIDENCE_ONLY
        ready = False
        reasons = [
            "Uno o más factores provienen de datasets P3B secundarios; son válidos solo para desarrollo/benchmark con opt-in explícito."
        ]
    elif manual:
        status = MANUAL_EVIDENCE
        ready = False
        reasons = [
            "Los factores fueron introducidos manualmente con referencia; P3B no ha verificado automáticamente sus valores contra un dataset primario."
        ]
    elif primary == total and bool(evidence.get("automatic_normative_lookup")):
        if bool(base_evidence.get("professional_emission")):
            status = PRIMARY_EVIDENCE_READY
            ready = True
            reasons = [
                "Iz_base y todos los factores provienen de datasets P3B primarios/verificados con binding trazable."
            ]
        else:
            status = EVIDENCE_INCOMPLETE
            ready = False
            reasons = [
                "Los factores son primarios, pero Iz_base todavía no dispone de evidencia normativa primaria."
            ]
    else:
        status = EVIDENCE_INCOMPLETE
        ready = False
        reasons = ["La clasificación de factores no satisface una política de evidencia conocida." ]

    return {
        "element": element,
        "status": status,
        "professional_normative_evidence_ready": ready,
        "factor_evidence": evidence,
        "base_evidence": base_evidence,
        "reasons": reasons,
    }


def evaluar() -> dict[str, Any]:
    """Resume calidad de evidencia P3 sin alterar readiness de datos/backend."""
    state = ampacity.snapshot()
    profiles = state.get("profiles") or []
    if not profiles:
        return {
            "schema_version": 1,
            "study": "ampacity",
            "status": NOT_CONFIGURED,
            "professional_normative_evidence_ready": False,
            "profiles": [],
            "summary": {"total": 0},
            "maturity": state.get("maturity", "UNDER_VALIDATION"),
            "professional_emission": False,
            "note": "No hay perfiles P3 configurados; este eje no sustituye READY_DATA/MISSING_DATA.",
        }

    results = [_profile_status(profile) for profile in profiles]
    statuses = {item["status"] for item in results}
    if len(statuses) == 1:
        overall = next(iter(statuses))
    else:
        overall = MIXED_EVIDENCE
    ready = bool(results) and all(
        item["professional_normative_evidence_ready"] for item in results
    )
    counts: dict[str, int] = {}
    for item in results:
        counts[item["status"]] = counts.get(item["status"], 0) + 1

    return {
        "schema_version": 1,
        "study": "ampacity",
        "status": overall,
        "professional_normative_evidence_ready": ready,
        "profiles": results,
        "summary": {"total": len(results), "by_status": counts},
        "maturity": state.get("maturity", "UNDER_VALIDATION"),
        "professional_emission": False,
        "note": (
            "Este eje clasifica evidencia normativa y no cambia por sí solo READY_DATA, "
            "madurez del módulo ni aptitud de emisión."
        ),
    }
