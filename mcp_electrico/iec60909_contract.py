"""Contrato P4 para cortocircuito IEC 60909.

Este módulo NO calcula cortocircuitos. Fija de forma explícita la edición
normativa objetivo, las capacidades que ofrece hoy el backend candidato y las
magnitudes que todavía requieren implementación/validación.

P4 se inicia en 2026, por lo que la referencia objetivo es IEC 60909-0:2026.
Pandapower 3.5.4 documenta un cálculo basado en DIN/IEC EN 60909, pero la
compatibilidad exacta con la edición IEC 60909-0:2026 no se presume: se mantiene
UNVERIFIED_AGAINST_TARGET_EDITION hasta completar una revisión específica.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pandapower as pp

SCHEMA_VERSION = 1
TARGET_STANDARD = {
    "id": "IEC_60909_0_2026",
    "designation": "IEC 60909-0:2026",
    "edition": "3.0",
    "publication_date": "2026-07-23",
    "title": "Short-circuit currents in three-phase AC systems - Part 0: Calculation of currents",
    "official_url": "https://webstore.iec.ch/en/publication/68454",
    "status": "CURRENT",
    "full_text_bundled": False,
}

BACKEND = {
    "engine": "pandapower",
    "engine_version": pp.__version__,
    "module": "pandapower.shortcircuit",
    "declared_method": "equivalent voltage source according to DIN/IEC EN 60909",
    "target_edition_conformance": "UNVERIFIED_AGAINST_TARGET_EDITION",
    "automatic_dispatch": False,
    "crosscheck": False,
}

FAULT_SCOPE = {
    "three_phase": {
        "pandapower_fault": "3ph",
        "backend_api_supported": True,
        "p4_v1_candidate": True,
        "sequence_requirements": ["positive"],
        "status": "FOUNDATION_READY",
    },
    "two_phase": {
        "pandapower_fault": "2ph",
        "backend_api_supported": True,
        "p4_v1_candidate": True,
        "sequence_requirements": ["positive", "negative"],
        "status": "PENDING_VALIDATION",
    },
    "single_phase_ground": {
        "pandapower_fault": "1ph",
        "backend_api_supported": True,
        "p4_v1_candidate": True,
        "sequence_requirements": ["positive", "negative", "zero"],
        "status": "BLOCKED_BY_ZERO_SEQUENCE_VALIDATION",
    },
    "two_phase_ground": {
        "pandapower_fault": None,
        "backend_api_supported": False,
        "p4_v1_candidate": False,
        "sequence_requirements": ["positive", "negative", "zero"],
        "status": "BACKEND_STRATEGY_PENDING",
        "note": "calc_sc() no expone un token directo 2ph-ground; no se aproxima como 2ph ni 1ph.",
    },
}

RESULT_CONTRACT = {
    "ikss_ka": {
        "iec_symbol": "Ik''",
        "pandapower_field": "ikss_ka",
        "status": "DIRECT_BACKEND_RESULT",
    },
    "skss_mva": {
        "iec_symbol": "Sk''",
        "pandapower_field": "skss_mw",
        "status": "DIRECT_BACKEND_RESULT_WITH_UNIT_LABEL_NORMALIZATION_PENDING",
        "note": "Pandapower denomina el campo skss_mw; P4 debe normalizar/justificar la unidad antes de emisión profesional.",
    },
    "ip_ka": {
        "iec_symbol": "ip",
        "pandapower_field": "ip_ka",
        "status": "DIRECT_BACKEND_RESULT_WHEN_REQUESTED",
    },
    "ith_ka": {
        "iec_symbol": "Ith",
        "pandapower_field": "ith_ka",
        "status": "DIRECT_BACKEND_RESULT_WHEN_REQUESTED",
    },
    "ib_ka": {
        "iec_symbol": "Ib",
        "pandapower_field": None,
        "status": "PENDING_P4_STRATEGY",
    },
    "ik_ka": {
        "iec_symbol": "Ik",
        "pandapower_field": None,
        "status": "PENDING_P4_STRATEGY",
    },
}

SOURCE_MAPPING = {
    "p2_scc_max_mva": "ext_grid.s_sc_max_mva",
    "p2_scc_min_mva": "ext_grid.s_sc_min_mva",
    "p2_x_r_max": "ext_grid.rx_max = 1 / X_R_max",
    "p2_x_r_min": "ext_grid.rx_min = 1 / X_R_min",
    "note": "P2 almacena X/R; pandapower recibe R/X. La inversión debe ser explícita y probada.",
}


def obtener_contrato_p4() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": "P4",
        "target_standard": deepcopy(TARGET_STANDARD),
        "backend": deepcopy(BACKEND),
        "fault_scope": deepcopy(FAULT_SCOPE),
        "result_contract": deepcopy(RESULT_CONTRACT),
        "source_mapping": deepcopy(SOURCE_MAPPING),
        "professional_emission": False,
        "note": (
            "La existencia de calc_sc() no demuestra conformidad con IEC 60909-0:2026. "
            "P4 requiere adaptación de datos, benchmarks independientes, revisión de edición y madurez explícita."
        ),
    }
