"""Independent published three-wire resistive benchmark for P13G.

This exercises a structural limit, not an induction motor or a device. The
reference uses three-phase waveform segments from a primary university source;
it never calls the one-phase surrogate to construct its waveform or RMS oracle.
"""
from math import cos, isfinite, pi, sin, sqrt

from scipy.integrate import quad
from scipy.optimize import brentq

SCHEMA = 'MCP_ELECTRICO_P13G_REFERENCE_COMPARISON_V1'
SOURCE = {
    'title': 'Three-phase full-wave AC voltage controllers',
    'author': 'Dr. Ayman Yousef',
    'publisher': 'Benha University, Faculty of Engineering, course repository',
    'url': 'https://feng.stafpu.bu.edu.eg/Electrical%20Engineering/4981/crs-15889/Files/Ch4%20%203-phase%20full-Wave%20AC%20voltage%20controllers.pdf',
    'pdf_pages_one_based': [3, 20, 21, 22],
    'date_accessed': '2026-10-02',
    'pdf_sha256': '772950c31f289b38e7af45d808c0f7389899e71c3998bd4b1b5d55446a517996',
    'edition': 'Undated public course PDF; retrieved version identified by evidence SHA-256',
}
FIELDS = {'schema', 'firing_angles_deg', 'fundamental_voltage_targets_pu',
          'numeric_absolute_tolerance_pu', 'comparison_absolute_tolerance_pu',
          'tolerance_kind', 'tolerance_reference'}


def contract():
    return {
        'schema': SCHEMA, 'required_fields': sorted(FIELDS),
        'reference': dict(SOURCE),
        'scope': 'BALANCED_IDEAL_THREE_WIRE_FLOATING_STAR_RESISTIVE_LOAD',
        'source': 'IDEAL_BALANCED_SINUSOIDAL_VOLTAGE',
        'normalization': 'OUTPUT_PHASE_VOLTAGE_AND_LINE_CURRENT_RELATIVE_TO_FULL_CONDUCTION',
        'firing_convention': 'PHASE_VOLTAGE_ZERO_CROSSING_DELAY_WITH_REQUIRED_PAIRED_GATING',
        'comparison_modes': ['SAME_FIRING_ANGLE', 'SAME_FUNDAMENTAL_VOLTAGE_MAGNITUDE'],
        'numerical_oracle': 'PUBLISHED_RMS_CLOSED_FORM_VS_INDEPENDENT_SEGMENT_QUADRATURE',
        'not_evaluated': ['INDUCTIVE_LOAD', 'INDUCTION_MOTOR_TORQUE', 'ACCELERATION_TIME',
                          'REAL_STARTER_CONTROL', 'NETWORK_VOLTAGE_DROP', 'BYPASS', 'THERMAL_LIMITS'],
        'device_validation_promoted': False, 'professional_emission': False,
    }


def _angle(alpha):
    if type(alpha) not in (float, int) or not isfinite(alpha) or not 0 <= alpha <= pi:
        raise ValueError('REFERENCE_ANGLE_OUT_OF_SCOPE')


def segments(alpha):
    """Half-wave phase-a intervals; other half follows odd half-cycle symmetry.

Values are relative to source phase peak. Pair-only intervals use half of
line-line voltage; theta can exceed pi because the floating neutral moves.
"""
    _angle(alpha)
    if alpha >= 5*pi/6: return []
    vab = lambda t: sqrt(3)/2*sin(t+pi/6)
    vac = lambda t: sqrt(3)/2*sin(t-pi/6)
    if alpha <= pi/3:
        candidates = [(alpha, pi/3, sin), (pi/3, pi/3+alpha, vab),
                      (pi/3+alpha, 2*pi/3, sin), (2*pi/3, 2*pi/3+alpha, vac),
                      (2*pi/3+alpha, pi, sin)]
    elif alpha <= pi/2:
        candidates = [(alpha, pi/3+alpha, vab), (pi/3+alpha, 2*pi/3+alpha, vac)]
    else:
        candidates = [(alpha, 5*pi/6, vab), (pi/3+alpha, 7*pi/6, vac)]
    return [(a, b, f) for a, b, f in candidates if b > a]


def waveform(theta, alpha):
    """Periodic phase voltage, for independent KCL checks and plotting."""
    # In modes II/III the positive burst extends past pi. Iterate the shifts
    # around the canonical period instead of cutting a burst at a source zero.
    t = theta % (2*pi)
    for shift in (-2*pi, -pi, 0., pi, 2*pi):
        sign = 1 if round(shift/pi) % 2 == 0 else -1
        for a, b, f in segments(alpha):
            if a <= t-shift < b: return sign*f(t-shift)
    return 0.


def rms_closed_form(alpha):
    """Published ideal three-wire resistive RMS, PDF pages 20-22."""
    _angle(alpha)
    if alpha >= 5*pi/6: return 0.
    if alpha <= pi/3:
        square = 1-3*alpha/(2*pi)+3*sin(2*alpha)/(4*pi)
    elif alpha <= pi/2:
        square = .5+9*sin(2*alpha)/(8*pi)+3*sqrt(3)*cos(2*alpha)/(8*pi)
    else:
        square = 1.25-3*alpha/(2*pi)+3*sin(2*alpha)/(8*pi)+3*sqrt(3)*cos(2*alpha)/(8*pi)
    return sqrt(max(0., square))


def response(alpha):
    """Numerical Fourier/RMS integration of published topology-specific arcs."""
    arcs = segments(alpha)
    def integral(weight):
        results = [quad(lambda t: weight(t, f(t)), a, b, epsabs=1e-12, epsrel=1e-12)
                   for a, b, f in arcs]
        return sum(x[0] for x in results), sum(x[1] for x in results)
    square, error = integral(lambda t, v: v*v)
    b, eb = integral(lambda t, v: v*sin(t))
    a, ea = integral(lambda t, v: v*cos(t))
    b *= 2/pi; a *= 2/pi
    return {'total_rms_pu': sqrt(max(0., 2*square/pi)),
            'fundamental_pu': sqrt(a*a+b*b), 'fundamental_in_phase_pu': b,
            'fundamental_quadrature_pu': a, 'closed_form_rms_pu': rms_closed_form(alpha),
            'quadrature_absolute_error_bound': 2/pi*max(error, eb, ea)}


def compare(package):
    """The comparison against the removed surrogate cannot run again."""
    return {'status': 'RETIRED_SURROGATE_COMPARISON', 'same_angle': [],
            'same_fundamental': [], 'network_solve_performed': False,
            'replacement_contract_tool': 'obtener_contrato_dinamica_modelica',
            'professional_emission': False}
