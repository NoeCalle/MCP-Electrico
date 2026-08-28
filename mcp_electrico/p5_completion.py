"""Gate formal de cierre P5 para la ruta de Engineering Preview.

P5G cierra la fase funcional de protección dentro de sus alcances declarados.
No promociona los módulos P5 a VALIDATED y no habilita emisión profesional.
El siguiente bloque obligatorio para la preview operativa es P7 reproducible.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import (
    p5_benchmarks,
    protection_checks,
    protection_clearing_time,
    protection_contract,
    protection_coordination,
    protection_curves,
    validation_status,
    workspace_p5_view,
    workspace_v5,
)

PHASE_READY_WITH_LIMITATIONS = "READY_WITH_LIMITATIONS"
PHASE_NOT_READY = "NOT_READY"
NEXT_PHASE = "P7_REPRODUCIBLE_DOSSIER_MINIMUM"
DEFERRED_PHASE = "P6_IEEE1584_ARC_FLASH"

P5_V1_SCOPE = {
    "phase_version": "P5-v1",
    "devices": ["circuit_breaker", "fuse"],
    "tcc_shapes": ["SINGLE", "BAND"],
    "tcc_interpolation": "LOG_LOG_LINEAR",
    "clearing_ready_time_semantics": ["TOTAL_CLEARING_TIME"],
    "coordination_scope": "TEMPORAL_POINT_COORDINATION",
    "selectivity_claim": False,
    "backup_claim": False,
    "cascading_claim": False,
    "workspace": "V5_PROTECTION_TCC",
}

_P5_MODULES = (
    "protection_data",
    "tcc_curve_evaluation",
    "protection_checks",
    "protection_clearing_time",
    "protection_coordination",
)

_ACCEPTABLE_IMPLEMENTED_MATURITY = {
    "EXPERIMENTAL",
    "UNDER_VALIDATION",
    "VALIDATED_WITH_LIMITATIONS",
    "VALIDATED",
}


def _criterion(
    cid: str,
    name: str,
    done: bool,
    evidence: str,
    blocker: str | None = None,
) -> dict[str, Any]:
    return {
        "id": cid,
        "name": name,
        "status": "DONE" if done else "PENDING",
        "evidence": evidence,
        "blocking_reason": None if done else blocker,
    }


def _module_maturity() -> dict[str, dict[str, Any]]:
    return {name: validation_status.get_module_status(name) for name in _P5_MODULES}


def _criteria() -> list[dict[str, Any]]:
    p5a = protection_contract.obtener_contrato_p5a()
    p5c = protection_checks.obtener_referencias_p5c()
    p5d = protection_clearing_time.obtener_contrato_p5d()
    p5e = protection_coordination.obtener_contrato_p5e()
    maturity = _module_maturity()

    scope = p5a.get("scope") or {}
    visual = p5a.get("visual_policy") or {}
    targets = (p5c.get("targets") or {}).values()
    p5c_fail_closed = bool(targets) and all(
        item.get("full_conformance_claim") is False for item in targets
    )
    p5e_claims = p5e.get("claims") or {}
    maturity_ready = all(
        item.get("status") in _ACCEPTABLE_IMPLEMENTED_MATURITY
        for item in maturity.values()
    )
    benchmark_contract_ready = (
        p5_benchmarks.SUITE_ID == "MCP_ELECTRICO_P5G_BENCHMARK_SUITE_V1"
        and tuple(p5_benchmarks.BENCHMARK_IDS)
        == (
            "P5G_B01_TCC_BAND_LOGLOG",
            "P5G_B02_TCC_NO_EXTRAPOLATION",
            "P5G_B03_CLEARING_TIME_BAND",
            "P5G_B04_TEMPORAL_COORDINATION",
            "P5G_B05_BREAKING_CAPACITY",
            "P5G_B06_CONDUCTOR_THERMAL",
        )
    )

    return [
        _criterion(
            "P5G01",
            "canonical_protection_data_contract",
            scope.get("included_device_types") == ["circuit_breaker", "fuse"]
            and scope.get("excluded_device_types") == ["relay"]
            and p5a.get("professional_emission") is False,
            "protection_contract.P5A_SCOPE + protection_data",
            "Falta cerrar el contrato canónico breaker/fuse sin aproximar relés.",
        ),
        _criterion(
            "P5G02",
            "numeric_tcc_fail_closed",
            protection_curves.SCHEMA == "MCP_ELECTRICO_P5B_TCC_DATASET_V1"
            and protection_curves.INTERPOLATION == "LOG_LOG_LINEAR"
            and protection_curves.ALLOWED_SHAPES == {"SINGLE", "BAND"}
            and "TOTAL_CLEARING_TIME" in protection_curves.ALLOWED_TIME_SEMANTICS,
            "protection_curves: segmentos explícitos, LOG_LOG_LINEAR, no extrapolation/cross-gap por contrato y tests",
            "Falta infraestructura TCC numérica versionada y fail-closed.",
        ),
        _criterion(
            "P5G03",
            "breaking_capacity_and_conductor_thermal_checks",
            p5c.get("scope") == "REFERENCE_TARGETS_NOT_FULL_CONFORMANCE"
            and p5c_fail_closed
            and p5c.get("professional_emission") is False,
            "protection_checks P5C: Icu/breaking_capacity + I²t <= k²S² con inputs explícitos",
            "Faltan checks P5C o se está realizando un claim normativo mayor al soportado.",
        ),
        _criterion(
            "P5G04",
            "clearing_time_semantics",
            p5d.get("clearing_ready_time_semantics") == ["TOTAL_CLEARING_TIME"]
            and (p5d.get("band_policy") or {}).get("average_band") is False
            and p5d.get("p4_tk_s_consumed") is False
            and p5d.get("professional_emission") is False,
            "protection_clearing_time P5D: TOTAL_CLEARING_TIME únicamente, bandas preservadas, tk_s P4 no consumido",
            "Falta un contrato fail-closed para promover tiempo TCC a clearing time.",
        ),
        _criterion(
            "P5G05",
            "pointwise_temporal_coordination",
            p5e.get("method") == "TEMPORAL_POINT_COORDINATION"
            and p5e.get("domain_scan") is False
            and p5e.get("topology_inference") is False
            and p5e_claims.get("temporal_point_coordination") is True
            and p5e_claims.get("total_selectivity") is False
            and p5e_claims.get("partial_selectivity") is False
            and p5e_claims.get("energy_selectivity") is False
            and p5e_claims.get("backup") is False
            and p5e_claims.get("cascading") is False
            and p5e.get("professional_emission") is False,
            "protection_coordination P5E: upstream_min - downstream_max, relación/corrientes explícitas",
            "Falta coordinación temporal puntual o existen claims de selectividad/backup no soportados.",
        ),
        _criterion(
            "P5G06",
            "workspace_v5",
            workspace_p5_view.MARKER == "<!-- MCP-P5-PROTECTION-V5 -->"
            and callable(workspace_v5.enhance_file)
            and visual.get("second_visual_app") is False
            and visual.get("javascript_engineering_calculation") is False,
            "workspace_v5 + workspace_p5_view + CI de HTML/JavaScript",
            "Falta representación V5 en el workspace persistente o se introdujo cálculo eléctrico en navegador.",
        ),
        _criterion(
            "P5G07",
            "deterministic_benchmark_suite",
            benchmark_contract_ready,
            f"{p5_benchmarks.SUITE_ID}: {', '.join(p5_benchmarks.BENCHMARK_IDS)}; ejecución obligatoria en CI",
            "Falta la suite reproducible P5G o cobertura de alguno de los checks críticos.",
        ),
        _criterion(
            "P5G08",
            "explicit_module_maturity",
            maturity_ready,
            "; ".join(f"{name}={item.get('status')}" for name, item in maturity.items()),
            "Algún módulo P5 requerido continúa NOT_IMPLEMENTED o tiene un estado inválido.",
        ),
        _criterion(
            "P5G09",
            "non_professional_emission_contract",
            p5a.get("professional_emission") is False
            and p5c.get("professional_emission") is False
            and p5d.get("professional_emission") is False
            and p5e.get("professional_emission") is False,
            "P5A/P5C/P5D/P5E conservan professional_emission=false",
            "P5 no puede cerrar este gate si alguna capa afirma emisión profesional prematura.",
        ),
        _criterion(
            "P5G10",
            "operational_roadmap_handoff",
            NEXT_PHASE == "P7_REPRODUCIBLE_DOSSIER_MINIMUM"
            and DEFERRED_PHASE == "P6_IEEE1584_ARC_FLASH",
            "P6 deferred; P7 reproducibilidad mínima es el siguiente bloque antes de Engineering Preview 0.9",
            "Falta fijar el handoff P5 -> P7 sin reactivar Arc Flash implícitamente.",
        ),
    ]


def evaluar_cierre_p5() -> dict[str, Any]:
    """Evalúa el cierre funcional P5 sin elevar madurez ni emisión profesional."""
    criteria = _criteria()
    pending = [deepcopy(item) for item in criteria if item["status"] != "DONE"]
    phase_status = PHASE_READY_WITH_LIMITATIONS if not pending else PHASE_NOT_READY
    maturity = _module_maturity()
    ready = phase_status == PHASE_READY_WITH_LIMITATIONS

    return {
        "schema": "MCP_ELECTRICO_P5G_COMPLETION_GATE_V1",
        "phase": "P5",
        "phase_version": "P5-v1",
        "phase_status": phase_status,
        "scope": deepcopy(P5_V1_SCOPE),
        "criteria": deepcopy(criteria),
        "pending_criteria": pending,
        "module_maturity": deepcopy(maturity),
        "benchmark_evidence": {
            "suite_id": p5_benchmarks.SUITE_ID,
            "required_benchmark_ids": list(p5_benchmarks.BENCHMARK_IDS),
            "execution_gate": "CI_REQUIRED",
            "automatic_runtime_execution": False,
        },
        "ready_for_next_phase": ready,
        "next_phase": NEXT_PHASE if ready else None,
        "deferred_phase": DEFERRED_PHASE,
        "operational_path_ready": ready,
        "engineering_preview_ready": False,
        "engineering_preview_blockers": ["P7_REPRODUCIBLE_DOSSIER_MINIMUM"] if ready else ["P5_PENDING_CRITERIA", "P7_REPRODUCIBLE_DOSSIER_MINIMUM"],
        "professional_emission": False,
        "note": (
            "READY_WITH_LIMITATIONS significa que P5 puede entregar sus funciones declaradas para la ruta de uso interno. "
            "No convierte los módulos P5 en VALIDATED, no declara selectividad integral y no habilita Engineering Preview "
            "hasta cerrar el expediente/reproducibilidad mínima P7."
        ),
    }
