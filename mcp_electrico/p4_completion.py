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
    maturity = validation_status.get_module_status("short_circuit")

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
            bool(capabilities.get("single_phase_ground")),
            "Pendiente: 1F-T + cadena Z0",
            "La falla a tierra requiere secuencia cero validada de fuente/líneas/transformadores.",
        ),
        _criterion(
            "P4C08",
            "two_phase_ground_strategy",
            bool(capabilities.get("two_phase_ground")),
            "Pendiente: estrategia 2F-T; calc_sc no expone token directo",
            "No existe todavía estrategia validada para 2F-T y no se permite aproximarla silenciosamente.",
        ),
        _criterion(
            "P4C09",
            "independent_normative_benchmarks",
            False,
            "Pendiente: benchmark global; P4C09A 3F PASS y benchmark independiente P4C06 2F incorporado",
            "Faltan benchmarks independientes para el alcance P4-v1.",
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
            False,
            "P4C11A DONE: V4 3F MAX/MIN. P4C11B DONE: V4 2F MAX/MIN, política Z2 visible, convivencia 3F+2F y tool MCP 2F versionada.",
            "Workspace V4 ya cubre 3F y 2F, pero P4C11 global debe completar el alcance final de fallas que cierre P4-v1.",
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
        "backend": deepcopy(iec60909_contract.BACKEND),
        "next_phase": "P5_PROTECTION_TCC" if status == PHASE_READY_WITH_LIMITATIONS else None,
        "professional_emission": False,
        "note": "P4 no se cierra por la sola existencia de pandapower.calc_sc; requiere adaptación, validación de edición, benchmarks, V4 y madurez.",
    }
