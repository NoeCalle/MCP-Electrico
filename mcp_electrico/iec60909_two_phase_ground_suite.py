"""Suite P4-v1.1B MAX/MIN para falla bifásica a tierra 2F-T."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import (
    iec60909_contract,
    iec60909_two_phase_ground,
)

SCHEMA = "MCP_ELECTRICO_IEC60909_2PH_GROUND_SUITE_V1"


def _issue_from_exception(exc: Exception) -> dict[str, Any]:
    message = str(exc)
    prefix = message.split(":", 1)[0].strip()
    code = prefix if prefix.startswith("P4V11") else "P4V11B100"
    return {"code": code, "message": message, "element": None}


def _safe_run(
    bus: str,
    case: str,
    line_endtemp_degree_c: dict[str, float] | None,
    lv_tol_percent: int,
) -> dict[str, Any]:
    try:
        return iec60909_two_phase_ground.ejecutar_2ph_ground(
            bus,
            case,
            line_endtemp_degree_c=line_endtemp_degree_c,
            lv_tol_percent=lv_tol_percent,
        )
    except (ValueError, KeyError) as exc:
        return {
            "schema": iec60909_two_phase_ground.SCHEMA,
            "ok": False,
            "study": "IEC60909_SHORT_CIRCUIT_OPERATIONAL_EXTENSION",
            "fault": "2PH_GROUND",
            "fault_type": "two_phase_ground",
            "case": case,
            "bus": str(bus),
            "status": "PREPARATION_BLOCKED",
            "issues": [_issue_from_exception(exc)],
            "target_standard": deepcopy(iec60909_contract.TARGET_STANDARD),
            "target_edition_conformance": iec60909_contract.BACKEND[
                "target_edition_conformance"
            ],
            "maturity": "USABLE_WITH_DECLARED_SCOPE",
            "professional_emission": False,
            "results": {
                "ikss_ka": None,
                "ib_ka": None,
                "ic_ka": None,
                "ground_current_ka": None,
                "rk_ohm": None,
                "xk_ohm": None,
                "rk0_ohm": None,
                "xk0_ohm": None,
                "skss_mva": None,
                "ip_ka": None,
                "ith_ka": None,
            },
        }


def ejecutar_2ph_ground_max_min(
    bus: str,
    line_endtemp_degree_c: dict[str, float] | None = None,
    lv_tol_percent: int = 10,
) -> dict[str, Any]:
    maximum = _safe_run(bus, "max", None, int(lv_tol_percent))
    minimum = _safe_run(bus, "min", line_endtemp_degree_c, int(lv_tol_percent))
    representative = maximum if maximum.get("ok") else minimum

    return {
        "schema": SCHEMA,
        "ok": bool(maximum.get("ok") and minimum.get("ok")),
        "study": "iec60909_operational_extension",
        "fault": "2ph_ground",
        "fault_label": "2F-T",
        "bus": str(bus),
        "scenarios": {"max": maximum, "min": minimum},
        "negative_sequence_policy": deepcopy(
            iec60909_two_phase_ground_foundation_policy()
        ),
        "zero_sequence_policy": deepcopy(
            iec60909_contract.FAULT_SCOPE["single_phase_ground"][
                "zero_sequence_policy"
            ]
        ),
        "engine": {
            "engine": "mcp_sequence_solver",
            "sequence_impedance_backend": "pandapower",
            "engine_version_runtime": representative.get("pandapower_version"),
            "target_edition_conformance": representative.get(
                "target_edition_conformance"
            )
            or iec60909_contract.BACKEND.get("target_edition_conformance"),
            "automatic_dispatch": False,
            "crosscheck": False,
        },
        "target_standard": deepcopy(
            representative.get("target_standard")
            or iec60909_contract.TARGET_STANDARD
        ),
        "maturity": "USABLE_WITH_DECLARED_SCOPE",
        "professional_emission": False,
        "result_promotion": {
            "ikss_contractual": False,
            "skss_contractual": False,
            "ip_ith": False,
            "operational_current_semantics": "max_faulted_phase_rms_current",
            "pending_validation_ids": [
                "VP-IEC-01",
                "VP-2FT-01",
                "VP-2FT-02",
                "VP-2FT-03",
            ],
        },
        "limitations": [
            "2F-T franca b-c-tierra; Zf=0.",
            "Z2=Z1 solo para red simétrica pasiva.",
            "La corriente mostrada es operativa; la promoción contractual IEC permanece pendiente.",
            "Sk'', ip e Ith 2F-T permanecen sin promoción.",
            "No existe cálculo 2ph_ground nativo en pandapower; el solver final es MCP.",
        ],
    }


def iec60909_two_phase_ground_foundation_policy() -> dict[str, Any]:
    # Import local para mantener una única fuente de verdad sin circularidad.
    from . import iec60909_two_phase_ground_foundation

    return dict(iec60909_two_phase_ground_foundation.NEGATIVE_SEQUENCE_POLICY)
