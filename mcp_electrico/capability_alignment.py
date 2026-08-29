"""Alineaciones de capacidades públicas con fases ya cerradas.

P7D usa esta capa para corregir metadatos históricos sin introducir despacho
automático ni ampliar claims de ingeniería. La coordinación P5E ya está
implementada, pero sigue siendo experimental y no apta para emisión profesional.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import engine_selection

P5_COORDINATION_CAPABILITY = {
    "preferred": "mcp+pandapower",
    "alternatives": [],
    "module": "protection_coordination",
    "implemented": True,
    "professional_emission_candidate": False,
    "requires_active_model": True,
    "reason": (
        "P5-v1 implementa coordinación temporal puntual en la capa MCP usando "
        "corrientes/tiempos trazables; no declara selectividad total/parcial, "
        "backup ni cascading."
    ),
    "requirements": [
        "P4 IEC 60909 o corriente de falla explícita trazable",
        "dispositivos P5 con dataset TCC explícito",
        "TOTAL_CLEARING_TIME para promoción de clearing time",
        "relación downstream/upstream declarada",
        "corriente evaluada explícita por dispositivo",
    ],
}


def align_p5_capabilities() -> dict[str, Any]:
    """Alinea la entrada P5 sin tocar dispatch/crosscheck ni otras capacidades."""
    engine_selection.CAPABILITY_MATRIX["protection_coordination"] = deepcopy(
        P5_COORDINATION_CAPABILITY
    )
    return deepcopy(engine_selection.CAPABILITY_MATRIX["protection_coordination"])
