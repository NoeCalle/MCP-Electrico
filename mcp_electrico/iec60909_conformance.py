"""Revisión P4C10 contra IEC 60909-0:2026 Ed. 3.0.

La revisión es deliberadamente de alcance limitado. No distribuye el texto
completo de la norma ni convierte una declaración genérica del backend en una
certificación de conformidad. Registra evidencia pública versionada y separa:

- revisión completada con limitaciones;
- verificación integral contra la edición objetivo (no reclamada aquí).
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pandapower as pp

REVIEW_STATUS = "REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION"
FULL_VERIFICATION_STATUS = "VERIFIED_AGAINST_TARGET_EDITION"

EVIDENCE = {
    "iec_official_metadata": {
        "kind": "PRIMARY_METADATA",
        "url": "https://webstore.iec.ch/en/publication/68454",
        "supports": [
            "designation=IEC 60909-0:2026",
            "edition=3.0",
            "publication_date=2026-07-23",
            "scope=LV/HV three-phase AC systems at 50/60 Hz",
        ],
    },
    "iec_2026_public_catalog_extract": {
        "kind": "PUBLIC_FINAL_EDITION_EXTRACT",
        "url": "https://standards.iteh.ai/catalog/standards/iec/111c61a1-d4a4-4eb4-9655-ba4785738720/iec-60909-0-2026",
        "supports": [
            "main aim=max/min bolted short-circuit currents",
            "equivalent voltage source method retained",
            "Clause 6 equipment modelling reorganized/updated",
            "initial-current clauses include 3F, 2F, 2F-T and 1F-T",
        ],
        "copyright_note": "Solo se registran metadatos, estructura y conclusiones de revisión; no se incorpora el texto completo.",
    },
    "iec_2025_cdv_public_preview": {
        "kind": "PUBLIC_DRAFT_PREVIEW_CORROBORATION",
        "url": "https://cdn.standards.iteh.ai/sist-preview/76673/bfef3bb38a53445d97268adf5568bded/oSIST-prEN-IEC-60909-2025.pdf",
        "supports": [
            "ED3 project=73/220/CDV",
            "Clause 6 restructuring visible in public contents",
            "2F-T is an explicit fault category, not equivalent to 2F or 1F-T",
        ],
        "limitation": "CDV es evidencia histórica/corroborativa; la decisión final se ancla a la edición publicada 2026.",
    },
    "pandapower_calc_sc_v354": {
        "kind": "PINNED_BACKEND_SOURCE",
        "url": "https://github.com/e2nIEE/pandapower/blob/v3.5.4/pandapower/shortcircuit/calc_sc.py",
        "blob_sha": "e9f53a79d3ebe9eaacbd9989afadabaa7ed927df",
        "supports": [
            "method=equivalent voltage source according to DIN/IEC EN 60909",
            "cases=max|min",
            "fault tokens=3ph|2ph|1ph",
            "2F-T direct token absent",
        ],
    },
    "pandapower_branch_model_v354": {
        "kind": "PINNED_BACKEND_DOCUMENTATION",
        "url": "https://github.com/e2nIEE/pandapower/blob/v3.5.4/doc/shortcircuit/branch_elements.rst",
        "blob_sha": "73868de22e31f73d40749c30b14ab26f8e1b49bc",
        "supports": [
            "line end-temperature correction for minimum short-circuit",
            "network-transformer impedance correction factor implemented",
            "three-winding transformer correction documented",
        ],
    },
}

REVIEW = {
    "id": "P4C10_IEC60909_0_2026_ED3_PUBLIC_EVIDENCE_V1",
    "target_standard": "IEC_60909_0_2026",
    "target_edition": "3.0",
    "backend": "pandapower",
    "backend_version": pp.__version__,
    "status": REVIEW_STATUS,
    "full_conformance_claim": False,
    "full_text_bundled": False,
    "p4_v1_scope_only": True,
    "in_scope_faults": ["three_phase", "two_phase", "single_phase_ground"],
    "out_of_scope_faults": ["two_phase_ground"],
    "in_scope_network_model": [
        "network feeder/ext_grid equivalent",
        "passive lines/cables",
        "two-winding transformers with P2 data",
        "zero-sequence transformer/neutral data where 1F-T applies",
    ],
    "excluded_equipment_or_methods": [
        "synchronous generators and motors",
        "asynchronous generators and motors",
        "power station units and power plants",
        "power-electronic converter current-source contributions",
        "converter-fed motors",
        "FACTS and HVDC",
        "near-generator dedicated scope",
        "2F-T numerical execution",
        "symmetrical breaking current Ib",
        "steady-state short-circuit current Ik",
        "1F-T ip/Ith promotion",
    ],
    "edition_change_assessment": {
        "published_change_summary": [
            "restructuring/complementing of clauses with particular restructuring/updating of Clause 6",
            "restructuring of subscripts",
        ],
        "impact_on_p4_v1": "LIMITED_SCOPE_REVIEW_REQUIRED",
        "reason": (
            "P4-v1 usa feeder equivalente, líneas/cables y transformadores, por lo que Clause 6 es material. "
            "La evidencia pública confirma método, estructura y categorías de falla, pero no permite demostrar "
            "una comparación exhaustiva ecuación-por-ecuación de toda la edición 3.0."
        ),
    },
    "clause_findings": {
        "scope_and_method": {
            "status": "MATCHED_PUBLIC_FINAL",
            "finding": "El objetivo MAX/MIN de fallas francas y la fuente de tensión equivalente son compatibles con la arquitectura P4-v1.",
        },
        "equipment_modelling_clause_6": {
            "status": "REVIEWED_WITH_LIMITATIONS",
            "finding": "Pandapower modela líneas y transformadores con correcciones IEC declaradas; no se reclama equivalencia exhaustiva con todos los cambios 2026 de Clause 6.",
        },
        "initial_fault_types": {
            "status": "MATCHED_WITH_SCOPE_EXCLUSION",
            "finding": "3F/2F/1F-T tienen ruta P4; 2F-T existe en IEC 2026 pero queda fuera de P4-v1 por ausencia de token directo en pandapower 3.5.4.",
        },
        "peak_and_thermal": {
            "status": "PARTIAL_P4_SCOPE",
            "finding": "P4 promociona ip/Ith solo donde la ruta backend vigente está validada (3F/2F); no rellena 1F-T por fórmula paralela.",
        },
        "breaking_and_steady_state": {
            "status": "OUTSIDE_P4_V1_RESULT_SCOPE",
            "finding": "Ib e Ik permanecen explícitamente pendientes/no promocionados; P4-v1 no se presenta como implementación íntegra de todas las magnitudes de IEC 60909-0.",
        },
    },
    "decision": "P4C10_REVIEW_COMPLETE_WITH_LIMITATIONS",
    "professional_emission": False,
    "upgrade_to_full_verification_requires": [
        "comparación controlada contra el texto completo licenciado de IEC 60909-0:2026",
        "trazabilidad ecuación/tabla por ecuación/tabla para todos los elementos reclamados",
        "benchmarks de referencia de edición 2026 cuando estén disponibles/apliquen",
        "revisión explícita de cualquier ampliación de alcance de equipos o tipos de falla",
    ],
}


def evaluar_revision() -> dict[str, Any]:
    """Devuelve el artefacto P4C10 y un gate determinista de completitud."""
    review = deepcopy(REVIEW)
    evidence = deepcopy(EVIDENCE)
    required_evidence = {
        "iec_official_metadata",
        "iec_2026_public_catalog_extract",
        "pandapower_calc_sc_v354",
        "pandapower_branch_model_v354",
    }
    complete = bool(
        review.get("target_standard") == "IEC_60909_0_2026"
        and review.get("target_edition") == "3.0"
        and review.get("backend") == "pandapower"
        and review.get("backend_version") == "3.5.4"
        and review.get("status") == REVIEW_STATUS
        and review.get("decision") == "P4C10_REVIEW_COMPLETE_WITH_LIMITATIONS"
        and review.get("full_conformance_claim") is False
        and review.get("full_text_bundled") is False
        and review.get("professional_emission") is False
        and set(review.get("in_scope_faults") or []) == {"three_phase", "two_phase", "single_phase_ground"}
        and review.get("out_of_scope_faults") == ["two_phase_ground"]
        and required_evidence.issubset(evidence)
        and review.get("edition_change_assessment", {}).get("impact_on_p4_v1") == "LIMITED_SCOPE_REVIEW_REQUIRED"
        and review.get("upgrade_to_full_verification_requires")
    )
    return {
        "schema_version": 1,
        "criterion": "P4C10",
        "complete": complete,
        "review": review,
        "evidence": evidence,
        "note": (
            "P4C10 completo significa revisión de la edición objetivo con limitaciones explícitas; "
            "no significa certificación ni conformidad integral de todo IEC 60909-0:2026."
        ),
    }
