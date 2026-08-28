"""Suite P4C11C MAX/MIN para falla monofásica a tierra IEC 60909.

Orquesta dos ejecuciones P4C07 y conserva por separado los payloads MAX/MIN
para Workspace V4. Los errores de preparación Z0 se convierten en payloads
fail-closed; la vista nunca rellena escenarios faltantes ni recalcula valores.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import iec60909_contract, iec60909_single_phase_ground

SCHEMA = "MCP_ELECTRICO_IEC60909_1PH_GROUND_SUITE_V1"


def _issue_from_exception(exc: Exception) -> dict[str, Any]:
    message = str(exc)
    prefix = message.split(":", 1)[0].strip()
    code = prefix if prefix.startswith("P4C07") else "P4C11C001"
    return {"code": code, "message": message, "element": None}


def _safe_run(
    bus: str,
    case: str,
    line_endtemp_degree_c: dict[str, float] | None,
    lv_tol_percent: int,
) -> dict[str, Any]:
    try:
        return iec60909_single_phase_ground.ejecutar_1ph_ground(
            bus,
            case,
            line_endtemp_degree_c=line_endtemp_degree_c,
            lv_tol_percent=lv_tol_percent,
        )
    except (ValueError, KeyError) as exc:
        return {
            "schema": iec60909_single_phase_ground.SCHEMA,
            "ok": False,
            "study": "IEC60909_SHORT_CIRCUIT",
            "fault": "1PH_GROUND",
            "fault_type": "single_phase_ground",
            "case": case,
            "bus": str(bus),
            "status": "PREPARATION_BLOCKED",
            "issues": [_issue_from_exception(exc)],
            "target_standard": deepcopy(iec60909_contract.TARGET_STANDARD),
            "target_edition_conformance": iec60909_contract.BACKEND["target_edition_conformance"],
            "maturity": "EXPERIMENTAL_P4",
            "professional_emission": False,
            "negative_sequence_policy": deepcopy(
                iec60909_single_phase_ground.NEGATIVE_SEQUENCE_POLICY
            ),
            "results": {
                "ikss_ka": None,
                "rk_ohm": None,
                "xk_ohm": None,
                "rk0_ohm": None,
                "xk0_ohm": None,
                "skss_mva": None,
                "ip_ka": None,
                "ith_ka": None,
            },
        }


def _normalized_engine(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "engine": "pandapower",
        "engine_version_runtime": payload.get("pandapower_version")
        or iec60909_contract.BACKEND.get("engine_version"),
        "engine_version": iec60909_contract.BACKEND.get("engine_version"),
        "target_edition_conformance": payload.get("target_edition_conformance")
        or iec60909_contract.BACKEND.get("target_edition_conformance"),
        "automatic_dispatch": False,
        "crosscheck": False,
    }


def ejecutar_1ph_ground_max_min(
    bus: str,
    line_endtemp_degree_c: dict[str, float] | None = None,
    lv_tol_percent: int = 10,
) -> dict[str, Any]:
    maximum = _safe_run(bus, "max", None, int(lv_tol_percent))
    minimum = _safe_run(bus, "min", line_endtemp_degree_c, int(lv_tol_percent))

    representative = maximum if maximum.get("ok") else minimum
    policy = (
        representative.get("negative_sequence_policy")
        or maximum.get("negative_sequence_policy")
        or minimum.get("negative_sequence_policy")
        or deepcopy(iec60909_single_phase_ground.NEGATIVE_SEQUENCE_POLICY)
    )
    target = (
        representative.get("target_standard")
        or maximum.get("target_standard")
        or minimum.get("target_standard")
        or deepcopy(iec60909_contract.TARGET_STANDARD)
    )

    return {
        "schema": SCHEMA,
        "ok": bool(maximum.get("ok") and minimum.get("ok")),
        "study": "iec60909",
        "fault": "1ph_ground",
        "fault_label": "1F-T",
        "bus": str(bus),
        "scenarios": {"max": maximum, "min": minimum},
        "negative_sequence_policy": deepcopy(policy),
        "zero_sequence_policy": deepcopy(
            iec60909_contract.FAULT_SCOPE["single_phase_ground"]["zero_sequence_policy"]
        ),
        "engine": _normalized_engine(representative),
        "target_standard": deepcopy(target),
        "maturity": "EXPERIMENTAL_P4",
        "professional_emission": False,
        "limitations": [
            "Suite monofásica a tierra 1F-T; requiere Z0 explícita y proyectable.",
            "Z2=Z1 solo para la red simétrica pasiva P4C07 v1.",
            "Sk'' contractual 1F-T permanece sin normalizar.",
            "ip/Ith no se promocionan en 1F-T porque pandapower 3.5.4 no los calcula en _calc_sc_1ph.",
            "La conformidad específica con IEC 60909-0:2026 permanece sin verificar.",
        ],
    }
