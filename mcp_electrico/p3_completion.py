"""Gate formal de cierre para la Fase P3 — ampacidad normativa.

P3 no se cierra porque un modelo concreto pueda calcular Ib/In/Iz. Este módulo
separa:

- ``phase``: capacidades/evidencia que debe tener MCP Eléctrico para declarar
  P3 cerrada dentro de un alcance normativo publicado;
- ``model``: preparación técnica y calidad de evidencia del circuito activo.

El gate está diseñado para devolver NOT_READY mientras falten fuente primaria
pinneada, datasets primarios/cobertura normativa, estrategia validada de Iz_base
y benchmarks normativos suficientes. No eleva madurez ni promueve datasets.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from opendssdirect import dss

from . import (
    ampacity_datasets,
    ampacity_evidence,
    ampacity_evidence_readiness,
    engine_selection,
    validation_status,
)

PHASE_READY_WITH_LIMITATIONS = "READY_WITH_LIMITATIONS"
PHASE_NOT_READY = "NOT_READY"
MODEL_NOT_CONFIGURED = "MODEL_NOT_CONFIGURED"
MODEL_TECHNICALLY_READY = "MODEL_TECHNICALLY_READY"
MODEL_NOT_READY = "MODEL_NOT_READY"

_ACCEPTABLE_MATURITY = {"VALIDATED_WITH_LIMITATIONS", "VALIDATED"}

# Alcance candidato P3-v1. No se declara cerrado: esta lista hace explícito qué
# debe estar cubierto antes de considerar VALIDATED_WITH_LIMITATIONS.
P3_V1_SCOPE = {
    "jurisdiction": "PE",
    "norm_reference_id": "PERU_CNE_UTILIZACION_2006",
    "profile_id": "PERU_CNE_UTIL_2006_030_004",
    "rule": "030-004",
    "installation_methods_routed": ["A1", "A2", "B1", "B2", "C", "D", "E", "F", "G"],
    "required_numeric_families": [
        "base_ampacity_strategy_Table_1_2_or_validated_equivalent",
        "Table_5A_temperature",
        "Table_5B_soil_thermal_resistivity_when_applicable",
        "Table_5C_grouping_air",
        "Table_5D_grouping_buried_method_D",
        "Table_5E_arrangement_branches_when_applicable",
    ],
}


def _criterion(
    cid: str,
    name: str,
    done: bool,
    evidence: str,
    blocking_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "id": cid,
        "name": name,
        "status": "DONE" if done else "PENDING",
        "evidence": evidence,
        "blocking_reason": None if done else blocking_reason,
    }


def _primary_sources() -> list[dict[str, Any]]:
    try:
        return ampacity_evidence.listar_fuentes()
    except Exception:
        return []


def _datasets() -> list[dict[str, Any]]:
    try:
        return ampacity_datasets.listar_datasets()
    except Exception:
        return []


def _primary_source_pinned() -> bool:
    for source in _primary_sources():
        digest = str(source.get("expected_sha256") or "").strip().lower()
        if (
            source.get("source_class") == "OFFICIAL_PRIMARY_CANDIDATE"
            and source.get("pin_status") == "PINNED"
            and len(digest) == 64
            and all(ch in "0123456789abcdef" for ch in digest)
        ):
            return True
    return False


def _primary_datasets() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for dataset in _datasets():
        provenance = dataset.get("provenance") or {}
        usage = dataset.get("usage_policy") or {}
        if (
            provenance.get("verification_status") == ampacity_datasets.PRIMARY_VERIFIED
            and provenance.get("source_type") == "primary_official"
            and bool(usage.get("professional_emission"))
        ):
            result.append(dataset)
    return result


def _coverage_flags() -> dict[str, bool]:
    """Cobertura primaria exacta actualmente cargada por familia normativa."""
    tables = {str(item.get("table") or "").strip() for item in _primary_datasets()}
    axes = {str(item.get("axis") or "").strip() for item in _primary_datasets()}
    return {
        "base_ampacity_strategy": any(
            str(item.get("axis") or "") == "base_ampacity"
            and str(item.get("table") or "") in {"Tabla 1", "Tabla 2"}
            for item in _primary_datasets()
        ),
        "table_5a": "Tabla 5A" in tables and "ambient_temperature" in axes,
        "table_5b": "Tabla 5B" in tables and "soil_thermal_resistivity" in axes,
        "table_5c": "Tabla 5C" in tables and "grouping" in axes,
        "table_5d": "Tabla 5D" in tables and "grouping" in axes,
        "table_5e": "Tabla 5E" in tables and "grouping" in axes,
    }


def _capabilities() -> list[dict[str, Any]]:
    maturity = validation_status.get_module_status("ampacity")
    coverage = _coverage_flags()
    has_primary = bool(_primary_datasets())
    pinned = _primary_source_pinned()

    return [
        _criterion(
            "P3C01",
            "ib_in_iz_contract",
            True,
            "ampacity.definir_condiciones/evaluar: Ib <= In <= Iz",
        ),
        _criterion(
            "P3C02",
            "normative_applicability_router",
            True,
            "ampacity_profiles P3A: métodos CNE, tablas/ejes y separación IEC",
        ),
        _criterion(
            "P3C03",
            "versioned_numeric_dataset_infrastructure",
            True,
            "ampacity_datasets: lookup exacto, sin interpolación/extrapolación y ROUTE_MISMATCH",
        ),
        _criterion(
            "P3C04",
            "primary_evidence_gate",
            True,
            "ampacity_evidence + defensa del loader contra falsas promociones",
        ),
        _criterion(
            "P3C05",
            "factor_binding_to_calculation",
            True,
            "ampacity_factor_binding: procedencia P3B conservada y revalidada hasta Iz",
        ),
        _criterion(
            "P3C06",
            "normative_evidence_readiness",
            True,
            "ampacity_evidence_readiness: evidencia separada de READY_DATA",
        ),
        _criterion(
            "P3C07",
            "workspace_v3_evidence_visibility",
            True,
            "workspace_p3_view: Ib/In/Iz + evidencia normativa preparada en Python",
        ),
        _criterion(
            "P3C08",
            "official_primary_source_pinned",
            pinned,
            "ampacity_primary_sources.json",
            "La fuente oficial CNE está descubierta pero aún no existe un SHA-256 primario reproducible fijado.",
        ),
        _criterion(
            "P3C09",
            "primary_verified_numeric_dataset",
            has_primary,
            "ampacity_p3b_numeric_datasets.json",
            "El dataset numérico actualmente cargado es secundario; no existe todavía una revisión PRIMARY_VERIFIED apta para emisión.",
        ),
        _criterion(
            "P3C10",
            "validated_base_ampacity_strategy",
            coverage["base_ampacity_strategy"],
            "Tabla 1/2 CNE o estrategia equivalente formalmente validada",
            "Iz_base proviene hoy de catálogo de fabricante P2; falta validar su uso normativo con factores CNE o cargar la base normativa Tabla 1/2.",
        ),
        _criterion(
            "P3C11",
            "primary_correction_factor_coverage",
            all(coverage[key] for key in ("table_5a", "table_5b", "table_5c", "table_5d", "table_5e")),
            "Cobertura primaria de Tablas 5A/5B/5C/5D/5E dentro del alcance P3-v1",
            "La cobertura numérica primaria de temperatura, suelo y agrupamiento/disposición todavía está incompleta.",
        ),
        _criterion(
            "P3C12",
            "independent_primary_normative_benchmarks",
            False,
            "Benchmark P3B actual valida infraestructura sobre evidencia secundaria",
            "Faltan benchmarks independientes contra valores de fuente primaria para base y factores normativos.",
        ),
        _criterion(
            "P3C13",
            "acceptable_module_maturity",
            maturity.get("status") in _ACCEPTABLE_MATURITY,
            f"validation_status.ampacity={maturity.get('status')}",
            "Ampacidad permanece UNDER_VALIDATION y no puede cerrar P3 todavía.",
        ),
    ]


def evaluar_modelo_actual() -> dict[str, Any]:
    """Evalúa el modelo activo sin confundirlo con el cierre del producto P3."""
    try:
        circuit = str(dss.Circuit.Name() or "")
    except Exception:
        circuit = ""
    if not circuit:
        return {
            "status": MODEL_NOT_CONFIGURED,
            "circuit": None,
            "technical_readiness": None,
            "normative_evidence": ampacity_evidence_readiness.evaluar(),
        }

    try:
        technical = engine_selection.evaluar_preparacion_estudio("ampacidad")
    except Exception as exc:
        technical = {"overall_status": "ERROR", "error": str(exc)}
    evidence = ampacity_evidence_readiness.evaluar()
    technically_ready = technical.get("overall_status") == "READY_TO_EXECUTE"
    return {
        "status": MODEL_TECHNICALLY_READY if technically_ready else MODEL_NOT_READY,
        "circuit": circuit,
        "technical_readiness": technical,
        "normative_evidence": evidence,
        "professional_normative_evidence_ready": bool(
            evidence.get("professional_normative_evidence_ready")
        ),
        "note": (
            "Un modelo puede estar técnicamente READY_TO_EXECUTE y conservar evidencia secundaria/manual. "
            "Eso no cambia el estado del gate de producto P3."
        ),
    }


def evaluar_cierre_p3() -> dict[str, Any]:
    """Devuelve el gate formal P3 y el estado independiente del modelo activo."""
    criteria = _capabilities()
    pending = [deepcopy(item) for item in criteria if item["status"] != "DONE"]
    phase_status = PHASE_READY_WITH_LIMITATIONS if not pending else PHASE_NOT_READY
    return {
        "schema_version": 1,
        "phase": "P3",
        "phase_version": "P3-v1-candidate",
        "phase_status": phase_status,
        "ready_for_next_phase": phase_status == PHASE_READY_WITH_LIMITATIONS,
        "scope": deepcopy(P3_V1_SCOPE),
        "criteria": [deepcopy(item) for item in criteria],
        "pending_criteria": pending,
        "model": evaluar_modelo_actual(),
        "next_phase": "P4_IEC_60909" if phase_status == PHASE_READY_WITH_LIMITATIONS else None,
        "professional_emission": False,
        "note": (
            "El gate P3 separa la infraestructura/cobertura normativa del producto de la preparación de un modelo concreto. "
            "No promueve datasets, no eleva madurez y no permite avanzar a P4 mientras existan criterios pendientes."
        ),
    }
