"""Gate formal de la Fase P4 — IEC 60909.

El gate separa la existencia de un backend de la validación normativa del
producto. Un cálculo experimental pandapower no cierra P4 por sí solo.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import iec60909, iec60909_contract, validation_status

PHASE_NOT_READY = "NOT_READY"
PHASE_READY_WITH_LIMITATIONS = "READY_WITH_LIMITATIONS"


def _criterion(cid: str, name: str, done: bool, evidence: str, blocker: str | None = None) -> dict[str, Any]:
    return {
        "id": cid,
        "name": name,
        "status": "DONE" if done else "PENDING",
        "evidence": evidence,
        "blocking_reason": None if done else blocker,
    }


def _criteria() -> list[dict[str, Any]]:
    contract = iec60909_contract.obtener_contrato_p4()
    target = contract["target_standard"]
    backend = contract["backend"]
    capabilities = iec60909.CAPABILITIES
    fault_scope = contract["fault_scope"]
    p4_scope = contract.get("p4_v1_scope") or {}
    maturity = validation_status.get_module_status("short_circuit")

    two_phase_ground = fault_scope.get("two_phase_ground", {})
    strategy = two_phase_ground.get("strategy") or {}
    p4c08_done = bool(
        p4_scope.get("status") == "CLOSED"
        and two_phase_ground.get("status") == "OUT_OF_SCOPE_P4_V1"
        and two_phase_ground.get("p4_v1_candidate") is False
        and two_phase_ground.get("backend_api_supported") is False
        and strategy.get("decision") == "EXCLUDE_FROM_P4_V1"
        and strategy.get("no_approximation") is True
        and strategy.get("future_reentry_conditions")
    )

    in_scope_names = list(p4_scope.get("included_faults") or [])
    in_scope = [fault_scope.get(name, {}) for name in in_scope_names]
    benchmarks_complete = bool(in_scope) and p4c08_done and all(
        item.get("p4_v1_candidate") is True
        and item.get("status") == "FOUNDATION_READY"
        and (item.get("independent_benchmark") or {}).get("status") == "PASS"
        for item in in_scope
    )
    workspace_complete = bool(in_scope) and p4c08_done and all(
        item.get("p4_v1_candidate") is True
        and item.get("status") == "FOUNDATION_READY"
        and (item.get("workspace_v4") or {}).get("status") == "DONE"
        for item in in_scope
    )

    return [
        _criterion(
            "P4C01",
            "versioned_normative_target",
            target.get("id") == "IEC_60909_0_2026" and target.get("status") == "CURRENT",
            "iec60909_contract.TARGET_STANDARD",
            "Falta fijar una edición normativa objetivo vigente.",
        ),
        _criterion(
            "P4C02",
            "deterministic_backend_contract",
            backend.get("engine") == "pandapower"
            and backend.get("automatic_dispatch") is False
            and backend.get("crosscheck") is False,
            "iec60909_contract.BACKEND + engine_selection",
            "Falta fijar backend y política de ejecución sin despacho/cross-check silencioso.",
        ),
        _criterion(
            "P4C03",
            "p2_to_iec60909_positive_sequence_adapter",
            bool(capabilities.get("positive_sequence_adapter")),
            "iec60909: fuente P2 Scc/X-R -> ext_grid Ssc/R-X + líneas R1/X1 + transformadores P2",
            "La red P2 todavía no se proyecta a un modelo IEC 60909 dedicado y probado.",
        ),
        _criterion(
            "P4C04",
            "three_phase_max_min_ikss_skss",
            bool(capabilities.get("three_phase_max_min")),
            "iec60909.ejecutar_3ph: calc_sc 3ph max/min + Ik''/Sk'' normalizados",
            "Falta implementación 3F max/min reproducible.",
        ),
        _criterion(
            "P4C05",
            "peak_and_thermal_currents",
            bool(capabilities.get("peak_thermal")),
            "iec60909.ejecutar_3ph: ip/Ith con topology radial|meshed, tk_s>0 y kappa_method=C explícitos; tests P4C05 fail-closed y sensibilidad temporal",
            "Falta estrategia validada para ip e Ith.",
        ),
        _criterion(
            "P4C06",
            "two_phase_fault",
            bool(capabilities.get("two_phase")),
            "iec60909_two_phase.ejecutar_2ph + benchmark independiente 2F max/min; Z2=Z1 declarada solo para red simétrica pasiva P4C06 v1",
            "Falta implementar y validar falla fase-fase.",
        ),
        _criterion(
            "P4C07",
            "single_phase_ground_zero_sequence",
            fault_scope.get("single_phase_ground", {}).get("status") == "FOUNDATION_READY",
            (
                "iec60909_single_phase_ground.ejecutar_1ph_ground + benchmark independiente 1F-T MAX/MIN; "
                "Z0 explícita de fuente/líneas/transformadores, C0 explícita por línea y Z2=Z1 limitada "
                "al alcance simétrico pasivo; Sk''/ip/Ith no se promocionan para 1F-T"
            ),
            "La falla a tierra requiere secuencia cero validada de fuente/líneas/transformadores.",
        ),
        _criterion(
            "P4C08",
            "two_phase_ground_strategy",
            p4c08_done,
            (
                "P4C08: 2F-T excluida formalmente de P4-v1; pandapower 3.5.4 calc_sc solo expone 3ph/2ph/1ph. "
                "No se aproxima como 2F/1F-T. Reingreso futuro exige backend directo o solver MCP dedicado + benchmark + revisión normativa."
            ),
            "Falta una decisión versionada y fail-closed sobre 2F-T.",
        ),
        _criterion(
            "P4C09",
            "independent_normative_benchmarks",
            benchmarks_complete,
            (
                "Cobertura independiente completa del alcance P4-v1 declarado: 3F=P4C09A PASS, "
                "2F=P4C06 PASS, 1F-T=P4C07 PASS; 2F-T=P4C08 fuera de alcance y no requerida para este gate."
            ),
            "Falta benchmark independiente de algún tipo de falla incluido en P4-v1.",
        ),
        _criterion(
            "P4C10",
            "target_edition_conformance_review",
            backend.get("target_edition_conformance") == "VERIFIED_AGAINST_TARGET_EDITION",
            f"backend target edition conformance={backend.get('target_edition_conformance')}",
            "Pandapower 3.5.4 aún no ha sido contrastado específicamente contra IEC 60909-0:2026.",
        ),
        _criterion(
            "P4C11",
            "workspace_v4",
            workspace_complete,
            (
                "Workspace V4 cubre todo el alcance P4-v1 declarado: P4C11A 3F DONE, P4C11B 2F DONE, "
                "P4C11C 1F-T DONE. 2F-T está excluida formalmente por P4C08 y no se dibuja ni calcula."
            ),
            "Falta representación V4 de algún tipo de falla incluido en P4-v1.",
        ),
        _criterion(
            "P4C12",
            "acceptable_module_maturity",
            maturity.get("status") in {"VALIDATED_WITH_LIMITATIONS", "VALIDATED"},
            f"validation_status.short_circuit={maturity.get('status')}",
            "short_circuit permanece UNDER_VALIDATION.",
        ),
    ]


def evaluar_cierre_p4() -> dict[str, Any]:
    criteria = _criteria()
    pending = [deepcopy(item) for item in criteria if item["status"] != "DONE"]
    status = PHASE_READY_WITH_LIMITATIONS if not pending else PHASE_NOT_READY
    return {
        "schema_version": 1,
        "phase": "P4",
        "phase_version": "P4-v1-candidate",
        "phase_status": status,
        "ready_for_next_phase": status == PHASE_READY_WITH_LIMITATIONS,
        "criteria": deepcopy(criteria),
        "pending_criteria": pending,
        "target_standard": deepcopy(iec60909_contract.TARGET_STANDARD),
        "p4_v1_scope": deepcopy(iec60909_contract.P4_V1_SCOPE),
        "backend": deepcopy(iec60909_contract.BACKEND),
        "next_phase": "P5_PROTECTION_TCC" if status == PHASE_READY_WITH_LIMITATIONS else None,
        "professional_emission": False,
        "note": "P4 no se cierra por la sola existencia de pandapower.calc_sc; requiere alcance cerrado, adaptación, benchmarks, revisión de edición, V4 y madurez.",
    }
