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
        "negative_sequence_policy": {
            "id": "P4C06_Z2_EQUALS_Z1_SYMMETRIC_PASSIVE_SCOPE",
            "relation": "Z2 = Z1",
            "scope": "red simétrica pasiva P4C06 v1; sin generadores ni motores",
            "explicit": True,
            "universal_assumption": False,
        },
        "status": "FOUNDATION_READY",
    },
    "single_phase_ground": {
        "pandapower_fault": "1ph",
        "backend_api_supported": True,
        "p4_v1_candidate": True,
        "sequence_requirements": ["positive", "negative", "zero"],
        "negative_sequence_policy": {
            "id": "P4C07_Z2_EQUALS_Z1_SYMMETRIC_PASSIVE_SCOPE",
            "relation": "Z2 = Z1",
            "scope": "red simétrica pasiva P4C07 v1; sin generadores ni motores",
            "explicit": True,
            "universal_assumption": False,
        },
        "zero_sequence_policy": {
            "source": "R0/X0 absolutos explícitos P2 por escenario -> r0x0 y x0x preservando Z0",
            "lines": "R0/X0/C0 explícitos P2; C0 no se inventa",
            "transformers": "vk0/vkr0/mag0/si0 + neutro explícitos P2 -> pandapower 3.5.4",
            "min_line_temperature": "endtemp_degree explícita; pandapower corrige R1 y R0",
        },
        "result_scope": {
            "ikss": True,
            "sequence_thevenin_impedances": True,
            "skss_normalized": False,
            "ip_ith": False,
        },
        "status": "FOUNDATION_READY",
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
        "scope": "3ph_normalized_only_in_current_p4",
        "note": (
            "Pandapower denomina el campo skss_mw. P4 3F lo normaliza como magnitud derivada; "
            "P4C06 2F y P4C07 1F-T conservan cualquier campo backend sin promoverlo a Sk'' contractual."
        ),
    },
    "ip_ka": {
        "iec_symbol": "ip",
        "pandapower_field": "ip_ka",
        "status": "DIRECT_BACKEND_RESULT_WHEN_REQUESTED_3PH_2PH",
        "note": "P4C07 no promociona ip para 1F-T porque pandapower 3.5.4 no lo calcula en _calc_sc_1ph.",
    },
    "ith_ka": {
        "iec_symbol": "Ith",
        "pandapower_field": "ith_ka",
        "status": "DIRECT_BACKEND_RESULT_WHEN_REQUESTED_3PH_2PH",
        "note": "P4C07 no promociona Ith para 1F-T porque pandapower 3.5.4 no lo calcula en _calc_sc_1ph.",
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
    "p2_zero_sequence": {
        "r0x0": "R0 / X0",
        "x0x": "X0 / X1_backend",
        "note": "X1_backend usa el mismo factor de tensión c y Scc que pandapower para el escenario activo, preservando R0/X0 absolutos P2.",
    },
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
