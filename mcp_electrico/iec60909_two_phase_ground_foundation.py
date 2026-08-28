"""P4-v1.1A — fundamento matemático para falla bifásica a tierra (2F-T).

Este módulo NO lee todavía el modelo pandapower/OpenDSS. Resuelve únicamente
una falla franca 2F-T mediante componentes simétricas a partir de impedancias
Thevenin de secuencia ya conocidas. La integración con el modelo activo y la
promoción al contrato P4 requieren gates posteriores.

Alcance inicial deliberado:
- falla franca b-c-tierra, Zf = 0;
- red simétrica pasiva: Z2 = Z1 explícito;
- fuente de secuencia positiva E1 explícita;
- no genera Sk'', ip, Ith, Ib ni Ik permanentes;
- professional_emission = false.
"""

from __future__ import annotations

import cmath
from math import isfinite, pi
from typing import Any

SCHEMA = "MCP_ELECTRICO_IEC60909_2PH_GROUND_FOUNDATION_V1"
NEGATIVE_SEQUENCE_POLICY = {
    "id": "P4V11A_Z2_EQUALS_Z1_SYMMETRIC_PASSIVE_SCOPE",
    "relation": "Z2 = Z1",
    "explicit": True,
    "scope": "red simétrica pasiva P4-v1.1A; sin generadores, motores ni modelos asimétricos",
    "universal_assumption": False,
}


def _complex_value(real: float, imag: float, *, code: str, label: str) -> complex:
    try:
        r = float(real)
        x = float(imag)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{code}: {label} debe tener parte real/imaginaria numérica.") from exc
    if not isfinite(r) or not isfinite(x):
        raise ValueError(f"{code}: {label} debe ser finita.")
    return complex(r, x)


def _polar(value: complex) -> dict[str, float]:
    return {
        "real": float(value.real),
        "imag": float(value.imag),
        "magnitude": abs(value),
        "angle_deg": cmath.phase(value) * 180.0 / pi,
    }


def resolver_2ph_ground_bolted(
    *,
    e1_v: float,
    r1_ohm: float,
    x1_ohm: float,
    r0_ohm: float,
    x0_ohm: float,
) -> dict[str, Any]:
    """Resuelve una falla b-c-tierra franca con Z2=Z1 explícito.

    Para Zf=0, las redes de secuencia se conectan como:

        Z1 + (Z2 || Z0)

    con:

        I1 = E1 / (Z1 + Z2*Z0/(Z2+Z0))
        I2 = -I1 * Z0/(Z2+Z0)
        I0 = -I1 * Z2/(Z2+Z0)

    Las corrientes de fase se reconstruyen mediante la transformación de
    componentes simétricas. Ia debe resultar aproximadamente cero para una
    falla b-c-tierra ideal.
    """
    try:
        e1 = float(e1_v)
    except (TypeError, ValueError) as exc:
        raise ValueError("P4V11A001: e1_v debe ser numérico y >0.") from exc
    if not isfinite(e1) or e1 <= 0:
        raise ValueError("P4V11A001: e1_v debe ser finito y >0.")

    z1 = _complex_value(r1_ohm, x1_ohm, code="P4V11A002", label="Z1")
    z0 = _complex_value(r0_ohm, x0_ohm, code="P4V11A003", label="Z0")
    if abs(z1) == 0:
        raise ValueError("P4V11A004: Z1 no puede ser cero.")
    if abs(z0) == 0:
        raise ValueError("P4V11A005: Z0 no puede ser cero en P4-v1.1A.")

    z2 = z1
    denominator_parallel = z2 + z0
    if abs(denominator_parallel) == 0:
        raise ValueError("P4V11A006: Z2+Z0 produce singularidad en la conexión de secuencias.")

    z20_parallel = z2 * z0 / denominator_parallel
    denominator = z1 + z20_parallel
    if abs(denominator) == 0:
        raise ValueError("P4V11A007: impedancia equivalente 2F-T singular.")

    i1 = e1 / denominator
    i2 = -i1 * z0 / denominator_parallel
    i0 = -i1 * z2 / denominator_parallel

    a = complex(-0.5, 3.0**0.5 / 2.0)
    ia = i0 + i1 + i2
    ib = i0 + (a * a) * i1 + a * i2
    ic = i0 + a * i1 + (a * a) * i2
    ig = ia + ib + ic

    return {
        "schema": SCHEMA,
        "study": "IEC60909_SHORT_CIRCUIT_FOUNDATION",
        "fault": "2PH_GROUND",
        "fault_type": "two_phase_ground",
        "faulted_phases": ["b", "c"],
        "fault_impedance_ohm": 0.0,
        "scope": "BOLTED_SYMMETRIC_PASSIVE",
        "negative_sequence_policy": dict(NEGATIVE_SEQUENCE_POLICY),
        "inputs": {
            "e1_v": e1,
            "z1_ohm": _polar(z1),
            "z2_ohm": _polar(z2),
            "z0_ohm": _polar(z0),
        },
        "equivalent": {
            "z2_parallel_z0_ohm": _polar(z20_parallel),
            "z_total_seen_by_positive_sequence_ohm": _polar(denominator),
        },
        "sequence_currents_a": {
            "i0": _polar(i0),
            "i1": _polar(i1),
            "i2": _polar(i2),
        },
        "phase_currents_a": {
            "ia": _polar(ia),
            "ib": _polar(ib),
            "ic": _polar(ic),
            "ground_sum": _polar(ig),
            "max_faulted_phase_current_a": max(abs(ib), abs(ic)),
        },
        "invariants": {
            "ia_should_be_zero": True,
            "ia_residual_a": abs(ia),
            "ground_current_equals_3i0": abs(ig - 3.0 * i0) <= 1e-9 * max(1.0, abs(ig)),
        },
        "result_promotion": {
            "ikss_contractual": False,
            "skss_contractual": False,
            "ip_ith": False,
            "reason": "P4-v1.1A valida primero la matemática; la semántica IEC 60909 de resultados se revisará antes de promover magnitudes contractuales.",
        },
        "professional_emission": False,
    }
