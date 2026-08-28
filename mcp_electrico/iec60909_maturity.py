"""Evaluación determinista de madurez P4C12 para IEC 60909.

Este módulo no ejecuta estudios y no depende de ``p4_completion`` ni de
``validation_status``. Evalúa directamente el contrato P4-v1 y la revisión
P4C10 para evitar circularidades y, sobre todo, para no mezclar la madurez del
IEC 60909 con el FaultStudy exploratorio de OpenDSS.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import iec60909_conformance, iec60909_contract

MATURE_STATUS = "VALIDATED_WITH_LIMITATIONS"

LIMITATIONS = [
    "Alcance P4-v1 limitado a fallas 3F, 2F fase-fase y 1F-T; 2F-T permanece OUT_OF_SCOPE_P4_V1.",
    "La política Z2=Z1 se limita a redes simétricas pasivas según los contratos P4C06/P4C07; no es una suposición universal.",
    "Generadores, motores, convertidores, unidades de generación, FACTS/HVDC y alcance near-generator dedicado permanecen fuera de P4-v1.",
    "Sk'' contractual se normaliza en 3F; 2F y 1F-T no la promocionan actualmente.",
    "ip/Ith se promocionan únicamente para 3F/2F con topology, tk_s y kappa_method explícitos; 1F-T no los promociona.",
    "Ib simétrico de corte e Ik permanente no están implementados/promocionados en P4-v1.",
    "El cálculo MIN con líneas exige endtemp_degree explícita; no se inventan temperaturas finales.",
    "La revisión IEC 60909-0:2026 está completada como REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION, no como verificación integral ecuación-por-ecuación.",
    "La aptitud de un modelo concreto depende además de sus datos P2, readiness, QA y revisión del ingeniero responsable.",
    "professional_emission permanece false; cerrar P4 habilita P5 como siguiente fase de desarrollo, no una emisión automática del estudio.",
]

BASIS = (
    "P4-v1 IEC 60909: alcance cerrado P4C08 + benchmarks independientes 3F/2F/1F-T "
    "+ revisión IEC 60909-0:2026 P4C10 + Workspace V4 P4C11 + gates fail-closed de datos y duty"
)


def _check(name: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {
        "id": name,
        "status": "PASS" if passed else "FAIL",
        "evidence": evidence,
    }


def evaluar_madurez() -> dict[str, Any]:
    contract = iec60909_contract.obtener_contrato_p4()
    backend = contract["backend"]
    target = contract["target_standard"]
    scope = contract["p4_v1_scope"]
    faults = contract["fault_scope"]
    results = contract["result_contract"]
    conformance = iec60909_conformance.evaluar_revision()

    included = list(scope.get("included_faults") or [])
    expected_included = ["three_phase", "two_phase", "single_phase_ground"]

    fault_evidence_complete = bool(included) and all(
        faults.get(name, {}).get("status") == "FOUNDATION_READY"
        and faults.get(name, {}).get("p4_v1_candidate") is True
        and faults.get(name, {}).get("independent_benchmark", {}).get("status") == "PASS"
        and faults.get(name, {}).get("workspace_v4", {}).get("status") == "DONE"
        for name in included
    )

    two_phase_ground = faults.get("two_phase_ground", {})
    two_phase_ground_strategy = two_phase_ground.get("strategy") or {}
    exclusion_safe = bool(
        two_phase_ground.get("status") == "OUT_OF_SCOPE_P4_V1"
        and two_phase_ground.get("backend_api_supported") is False
        and two_phase_ground.get("p4_v1_candidate") is False
        and two_phase_ground_strategy.get("decision") == "EXCLUDE_FROM_P4_V1"
        and two_phase_ground_strategy.get("no_approximation") is True
    )

    result_scope_safe = bool(
        results.get("skss_mva", {}).get("scope") == "3ph_normalized_only_in_current_p4"
        and results.get("ib_ka", {}).get("pandapower_field") is None
        and results.get("ik_ka", {}).get("pandapower_field") is None
        and faults.get("single_phase_ground", {}).get("result_scope", {}).get("ip_ith") is False
        and faults.get("single_phase_ground", {}).get("result_scope", {}).get("skss_normalized") is False
    )

    checks = [
        _check(
            "P4M01_TARGET",
            target.get("id") == "IEC_60909_0_2026"
            and target.get("edition") == "3.0"
            and target.get("status") == "CURRENT",
            "iec60909_contract.TARGET_STANDARD",
        ),
        _check(
            "P4M02_ENGINE_POLICY",
            backend.get("engine") == "pandapower"
            and backend.get("engine_version") == "3.5.4"
            and backend.get("automatic_dispatch") is False
            and backend.get("crosscheck") is False,
            "iec60909_contract.BACKEND",
        ),
        _check(
            "P4M03_SCOPE_CLOSED",
            scope.get("status") == "CLOSED"
            and included == expected_included
            and scope.get("excluded_faults") == ["two_phase_ground"],
            "P4C08 / P4_V1_SCOPE",
        ),
        _check(
            "P4M04_FAULT_EVIDENCE",
            fault_evidence_complete,
            "P4C09 benchmarks + P4C11 Workspace V4 por cada falla incluida",
        ),
        _check(
            "P4M05_2FT_FAIL_CLOSED",
            exclusion_safe,
            "P4C08 two_phase_ground strategy",
        ),
        _check(
            "P4M06_EDITION_REVIEW",
            conformance.get("complete") is True
            and backend.get("target_edition_conformance")
            == iec60909_conformance.REVIEW_STATUS
            and backend.get("full_conformance_claim") is False
            and conformance.get("review", {}).get("full_conformance_claim") is False,
            "P4C10 IEC 60909-0:2026 review",
        ),
        _check(
            "P4M07_RESULT_SCOPE_FAIL_CLOSED",
            result_scope_safe,
            "RESULT_CONTRACT + 1F-T result_scope",
        ),
        _check(
            "P4M08_NO_PROFESSIONAL_EMISSION",
            contract.get("professional_emission") is False
            and scope.get("professional_emission") is False,
            "P4 contract emission policy",
        ),
    ]

    passed = all(item["status"] == "PASS" for item in checks)
    status = MATURE_STATUS if passed else "UNDER_VALIDATION"

    return {
        "schema_version": 1,
        "criterion": "P4C12",
        "status": status,
        "ready": passed,
        "basis": BASIS if passed else "P4C12 evidence incomplete",
        "limitations": deepcopy(LIMITATIONS),
        "checks": checks,
        "professional_emission": False,
        "full_conformance_claim": False,
        "note": (
            "VALIDATED_WITH_LIMITATIONS aplica únicamente al módulo IEC 60909 P4-v1 declarado. "
            "No promociona OpenDSS FaultStudy ni amplía automáticamente el alcance técnico."
        ),
    }


def get_validation_status() -> dict[str, Any]:
    result = evaluar_madurez()
    return {
        "status": result["status"],
        "basis": result["basis"],
        "limitations": deepcopy(result["limitations"]),
    }
