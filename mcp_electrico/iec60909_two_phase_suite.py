"""Suite P4C11B MAX/MIN para falla bifásica IEC 60909.

Orquesta dos ejecuciones P4C06 sin recalcular magnitudes fuera del motor 2F y
conserva por separado los payloads MAX/MIN para su consumo por Workspace V4.
"""

from __future__ import annotations

from typing import Any

from . import iec60909_two_phase, validation_status

SCHEMA = "MCP_ELECTRICO_IEC60909_2PH_SUITE_V1"


def ejecutar_2ph_max_min(
    bus: str,
    line_endtemp_degree_c: dict[str, float] | None = None,
    calcular_ip_ith: bool = False,
    topology: str | None = None,
    tk_s: float | None = None,
    kappa_method: str = "C",
) -> dict[str, Any]:
    maximum = iec60909_two_phase.ejecutar_2ph(
        "max",
        bus,
        calcular_ip_ith=calcular_ip_ith,
        topology=topology,
        tk_s=tk_s,
        kappa_method=kappa_method,
    )
    minimum = iec60909_two_phase.ejecutar_2ph(
        "min",
        bus,
        line_endtemp_degree_c=line_endtemp_degree_c,
        calcular_ip_ith=calcular_ip_ith,
        topology=topology,
        tk_s=tk_s,
        kappa_method=kappa_method,
    )

    representative = maximum if maximum.get("ok") else minimum
    engine = representative.get("engine") or maximum.get("engine") or minimum.get("engine") or {}
    target = representative.get("target_standard") or maximum.get("target_standard") or minimum.get("target_standard") or {}
    policy = (
        representative.get("negative_sequence_policy")
        or maximum.get("negative_sequence_policy")
        or minimum.get("negative_sequence_policy")
        or dict(iec60909_two_phase.NEGATIVE_SEQUENCE_POLICY)
    )
    maturity = validation_status.get_module_status("iec60909")

    return {
        "schema": SCHEMA,
        "ok": bool(maximum.get("ok") and minimum.get("ok")),
        "study": "iec60909",
        "fault": "2ph",
        "bus": str(bus),
        "scenarios": {"max": maximum, "min": minimum},
        "negative_sequence_policy": policy,
        "engine": engine,
        "target_standard": target,
        "maturity": maturity["status"],
        "maturity_detail": maturity,
        "professional_emission": False,
        "limitations": [
            "Suite fase-fase sin tierra; 2F-T permanece OUT_OF_SCOPE_P4_V1.",
            "Z2=Z1 solo para la red simétrica pasiva P4C06 v1.",
            "Sk'' contractual 2F permanece sin normalizar.",
            "La revisión IEC 60909-0:2026 es REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION, no conformidad integral.",
        ],
    }