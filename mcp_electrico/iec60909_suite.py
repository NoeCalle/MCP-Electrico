"""Orquestación versionada P4 para resultados 3F MAX/MIN.

Este módulo no implementa ecuaciones adicionales. Ejecuta dos veces el motor
atómico ``iec60909.ejecutar_3ph`` con escenarios explícitos y conserva ambos
payloads completos para trazabilidad, workspace y futuros consumidores.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import iec60909, iec60909_contract

SCHEMA = "MCP_ELECTRICO_IEC60909_3PH_SUITE_V1"


def ejecutar_3ph_max_min(
    bus: str,
    line_endtemp_degree_c: dict[str, float] | None = None,
    calcular_ip_ith: bool = False,
    topology: str | None = None,
    tk_s: float | None = None,
    kappa_method: str = "C",
) -> dict[str, Any]:
    """Ejecuta 3F MAX y MIN sin introducir defaults técnicos ocultos.

    ``line_endtemp_degree_c`` se aplica al escenario MIN y sigue siendo
    obligatorio cuando existen líneas. Los parámetros de duty se transmiten
    idénticos a ambos escenarios cuando ``calcular_ip_ith=True``.
    """
    common = {
        "calcular_ip_ith": calcular_ip_ith,
        "topology": topology,
        "tk_s": tk_s,
        "kappa_method": kappa_method,
    }
    maximum = iec60909.ejecutar_3ph("max", bus, **common)
    minimum = iec60909.ejecutar_3ph(
        "min",
        bus,
        line_endtemp_degree_c=line_endtemp_degree_c,
        **common,
    )
    scenarios = {"max": maximum, "min": minimum}
    ok = all(bool(item.get("ok")) for item in scenarios.values())

    canonical_bus = next(
        (str(item.get("bus")) for item in scenarios.values() if item.get("ok")),
        str(bus),
    )
    runtime_engine = next(
        (deepcopy(item.get("engine")) for item in scenarios.values() if item.get("engine")),
        deepcopy(iec60909_contract.BACKEND),
    )
    target = next(
        (
            deepcopy(item.get("target_standard"))
            for item in scenarios.values()
            if item.get("target_standard")
        ),
        deepcopy(iec60909_contract.TARGET_STANDARD),
    )

    return {
        "schema": SCHEMA,
        "ok": ok,
        "study": "iec60909",
        "fault": "3ph",
        "bus": canonical_bus,
        "scenarios": scenarios,
        "requested_duty": {
            "requested": bool(calcular_ip_ith),
            "topology": str(topology).strip().lower() if topology is not None else None,
            "tk_s": tk_s,
            "kappa_method": str(kappa_method).strip().upper() if calcular_ip_ith else None,
        },
        "engine": runtime_engine,
        "target_standard": target,
        "maturity": "EXPERIMENTAL_P4",
        "professional_emission": False,
        "limitations": [
            "P4C11A visualiza únicamente el alcance 3F MAX/MIN implementado.",
            "La conformidad específica con IEC 60909-0:2026 permanece pendiente en P4C10.",
            "Un escenario fallido se conserva con sus issues; la suite no rellena valores faltantes.",
        ],
    }
