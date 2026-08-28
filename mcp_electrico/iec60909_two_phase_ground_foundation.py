"""P4-v1.1A — fundamento matemático para falla bifásica a tierra (2F-T).

Este módulo NO lee todavía el modelo pandapower/OpenDSS. Resuelve únicamente
una falla franca 2F-T mediante componentes simétricas a partir de impedancias
Thevenin de secuencia ya conocidas. La integración con el modelo activo y la
promoción al contrato P4 requieren gates posteriores.

Alcance inicial deliberado:
- falla franca b-c-tierra, Zf = 0;
- red simétrica pasiva: Z2 = Z1 explícito;
- fuente de secuencia positiva E1 explícita;
- impedancias Thevenin pasivas con R>=0, X>=0 y |Z|>0;
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


def _passive_sequence_impedance(real: float, imag: float, *, code: str, label: str) -> complex:
    value = _complex_value(real, imag, code=code, label=label)
    if value.real < 0 or value.imag < 0:
        raise ValueError(
            f"{code}: {label} queda fuera del alcance pasivo P4-v1.1A; se requiere R>=0 y X>=0."
        )
    if abs(value) == 0:
        raise ValueError(f"{code}: {label} no puede ser cero.")
    return value


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

    Las corrientes y tensiones de fase se reconstruyen mediante componentes
    simétricas. Para una falla b-c-tierra franca deben cumplirse Ia≈0,
    Vb≈0 y Vc≈0, además de I0+I1+I2≈0 en el nodo de falla.
    """
    try:
        e1 = float(e1_v)
    except (TypeError, ValueError) as exc:
        raise ValueError("P4V11A001: e1_v debe ser numérico y >0.") from exc
    if not isfinite(e1) or e1 <= 0:
        raise ValueError("P4V11A001: e1_v debe ser finito y >0.")

    z1 = _passive_sequence_impedance(r1_ohm, x1_ohm, code="P4V11A002", label="Z1")
    z0 = _passive_sequence_impedance(r0_ohm, x0_ohm, code="P4V11A003", label="Z0")
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

    # Tensiones de secuencia en el punto de falla.
    v1 = complex(e1, 0.0) - z1 * i1
    v2 = -z2 * i2
    v0 = -z0 * i0

    a = complex(-0.5, 3.0**0.5 / 2.0)
    ia = i0 + i1 + i2
    ib = i0 + (a * a) * i1 + a * i2
    ic = i0 + a * i1 + (a * a) * i2
    ig = ia + ib + ic

    va = v0 + v1 + v2
    vb = v0 + (a * a) * v1 + a * v2
    vc = v0 + a * v1 + (a * a) * v2

    current_scale = max(1.0, abs(i0), abs(i1), abs(i2), abs(ib), abs(ic), abs(ig))
    voltage_scale = max(1.0, abs(v0), abs(v1), abs(v2), abs(va), e1)
    current_tol = 1e-9 * current_scale
    voltage_tol = 1e-9 * voltage_scale

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
        "sequence_voltages_v": {
            "v0": _polar(v0),
            "v1": _polar(v1),
            "v2": _polar(v2),
        },
        "phase_currents_a": {
            "ia": _polar(ia),
            "ib": _polar(ib),
            "ic": _polar(ic),
            "ground_sum": _polar(ig),
            "max_faulted_phase_current_a": max(abs(ib), abs(ic)),
        },
        "phase_voltages_v": {
            "va": _polar(va),
            "vb": _polar(vb),
            "vc": _polar(vc),
        },
        "invariants": {
            "ia_should_be_zero": True,
            "ia_residual_a": abs(ia),
            "ia_boundary_ok": abs(ia) <= current_tol,
            "vb_should_be_zero": True,
            "vb_residual_v": abs(vb),
            "vb_boundary_ok": abs(vb) <= voltage_tol,
            "vc_should_be_zero": True,
            "vc_residual_v": abs(vc),
            "vc_boundary_ok": abs(vc) <= voltage_tol,
            "sequence_current_kcl_ok": abs(i0 + i1 + i2) <= current_tol,
            "sequence_fault_voltage_equal_ok": (
                abs(v0 - v1) <= voltage_tol and abs(v1 - v2) <= voltage_tol
            ),
            "ground_current_equals_3i0": abs(ig - 3.0 * i0) <= current_tol,
        },
        "validation_status": {
            "mathematical_foundation": "USABLE_WITH_DECLARED_SCOPE",
            "normative_verification": "PENDING_LICENSED_IEC_REVIEW",
            "external_reference_case": "PENDING",
            "model_integration": "PENDING_P4V11B",
        },
        "result_promotion": {
            "ikss_contractual": False,
            "skss_contractual": False,
            "ip_ith": False,
            "reason": "La matemática foundation es utilizable dentro del alcance declarado; la semántica IEC 60909 de resultados se revisará antes de promover magnitudes contractuales.",
        },
        "professional_emission": False,
    }
