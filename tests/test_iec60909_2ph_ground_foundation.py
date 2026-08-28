import math

import numpy as np
import pytest

from mcp_electrico import iec60909_two_phase_ground_foundation as two_phase_ground


def _phase_domain_reference(*, e1_v: float, z1: complex, z0: complex):
    """Referencia independiente: resuelve directamente Zabc e impone Ia=0,Vb=Vc=0."""
    z2 = z1
    a = complex(-0.5, math.sqrt(3.0) / 2.0)
    transform = np.array(
        [[1.0, 1.0, 1.0], [1.0, a * a, a], [1.0, a, a * a]],
        dtype=complex,
    )
    inverse = np.linalg.inv(transform)
    zabc = transform @ np.diag([z0, z1, z2]) @ inverse
    source = np.array([e1_v, a * a * e1_v, a * e1_v], dtype=complex)

    # Ia=0. Las ecuaciones de las fases b/c son Vb=Vc=0.
    ib, ic = np.linalg.solve(zabc[1:, 1:], source[1:])
    iabc = np.array([0.0 + 0.0j, ib, ic], dtype=complex)
    iseq = inverse @ iabc
    return iabc, iseq


def _complex_from_payload(payload):
    return complex(payload["real"], payload["imag"])


def test_p4v11a_2ft_matches_independent_phase_domain_solution():
    e1_v = 400.0 / math.sqrt(3.0)
    z1 = complex(0.010, 0.040)
    z0 = complex(0.030, 0.090)

    result = two_phase_ground.resolver_2ph_ground_bolted(
        e1_v=e1_v,
        r1_ohm=z1.real,
        x1_ohm=z1.imag,
        r0_ohm=z0.real,
        x0_ohm=z0.imag,
    )
    phase_ref, seq_ref = _phase_domain_reference(e1_v=e1_v, z1=z1, z0=z0)

    assert result["fault_type"] == "two_phase_ground"
    assert result["scope"] == "BOLTED_SYMMETRIC_PASSIVE"
    assert result["negative_sequence_policy"]["relation"] == "Z2 = Z1"
    assert result["negative_sequence_policy"]["universal_assumption"] is False

    phase = result["phase_currents_a"]
    sequence = result["sequence_currents_a"]
    for key, expected in zip(("ia", "ib", "ic"), phase_ref):
        assert _complex_from_payload(phase[key]) == pytest.approx(expected, rel=1e-10, abs=1e-8)
    for key, expected in zip(("i0", "i1", "i2"), seq_ref):
        assert _complex_from_payload(sequence[key]) == pytest.approx(expected, rel=1e-10, abs=1e-8)

    assert phase["ia"]["magnitude"] == pytest.approx(0.0, abs=1e-8)
    assert result["invariants"]["ground_current_equals_3i0"] is True
    assert result["professional_emission"] is False


def test_p4v11a_2ft_preserves_result_scope_fail_closed():
    result = two_phase_ground.resolver_2ph_ground_bolted(
        e1_v=10_000.0 / math.sqrt(3.0),
        r1_ohm=0.1,
        x1_ohm=0.5,
        r0_ohm=0.3,
        x0_ohm=1.0,
    )
    promotion = result["result_promotion"]
    assert promotion["ikss_contractual"] is False
    assert promotion["skss_contractual"] is False
    assert promotion["ip_ith"] is False


def test_p4v11a_2ft_rejects_missing_or_singular_sequence_inputs():
    with pytest.raises(ValueError, match="e1_v"):
        two_phase_ground.resolver_2ph_ground_bolted(
            e1_v=0.0, r1_ohm=0.1, x1_ohm=0.2, r0_ohm=0.2, x0_ohm=0.4
        )
    with pytest.raises(ValueError, match="Z1 no puede ser cero"):
        two_phase_ground.resolver_2ph_ground_bolted(
            e1_v=100.0, r1_ohm=0.0, x1_ohm=0.0, r0_ohm=0.2, x0_ohm=0.4
        )
    with pytest.raises(ValueError, match="Z0 no puede ser cero"):
        two_phase_ground.resolver_2ph_ground_bolted(
            e1_v=100.0, r1_ohm=0.1, x1_ohm=0.2, r0_ohm=0.0, x0_ohm=0.0
        )
