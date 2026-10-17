"""Test-only independent induction-machine solution at imposed shaft speed.

Uses two coupled complex winding currents, matrix exponentials and SciPy
quadrature, never the production Modelica builder or the CSV integration code.
"""
import csv
from math import pi, sqrt

import numpy as np
from scipy.integrate import quad
from scipy.linalg import expm


def reference(package):
    m = package["machine"]
    lm = m["magnetizing_inductance_h"]
    ls, lr = lm+m["stator_leakage_inductance_h"], lm+m["rotor_leakage_inductance_h"]
    resistance = m["stator_resistance_ohm"]+package["switch_resistance_ohm"]
    rotation = m["pole_pairs"]*package["shaft_speed_rad_s"]
    inductances = np.array([[ls, lm], [lm, lr]], dtype=complex)
    circuit = np.array([[-resistance, 0], [1j*rotation*lm, -m["rotor_resistance_ohm"]+1j*rotation*lr]])
    a = np.linalg.solve(inductances, circuit)
    b = np.linalg.solve(inductances, np.array([1, 0], dtype=complex))
    omega = 2*pi*package["frequency_hz"]
    voltage = sqrt(2/3)*package["kv_ll"]*1000*np.exp(1j*(package["angle_deg"]*pi/180-pi/2))
    particular = np.linalg.solve(1j*omega*np.eye(2)-a, b*voltage)
    start = package["fault_time_s"]
    fault_state = particular*np.exp(1j*omega*start)-expm(a*start)@particular

    def currents(t):
        if t <= start:
            state = particular*np.exp(1j*omega*t)-expm(a*t)@particular
        else:
            state = expm(a*(t-start))@fault_state
        return np.array([(state[0]*np.exp(-1j*k*2*pi/3)).real for k in range(3)])

    duration = package["end_time_s"]-start
    energy = [quad(lambda t: currents(t)[k]**2, start, start+duration,
                   epsabs=1e-7, epsrel=1e-9, limit=300)[0] for k in range(3)]
    return {"currents": currents, "joule_integral_a2s_by_phase": energy,
            "equivalent_rms_a_by_phase": [sqrt(e/duration) for e in energy]}


def compare_trace(package, path):
    expected = reference(package)
    max_error, max_current, count = 0., 0., 0
    start = package["fault_time_s"]
    with open(path, encoding="utf8") as stream:
        for index, row in enumerate(csv.DictReader(stream)):
            # Independent waveform comparison throughout pre/post fault.
            if index % 37: continue
            t = float(row["time"])
            if abs(t-start) < 1e-8: continue
            actual = np.array([float(row[key]) for key in ("ia", "ib", "ic")])
            target = expected["currents"](t)
            max_error = max(max_error, float(np.max(np.abs(actual-target))))
            max_current = max(max_current, float(np.max(np.abs(target))))
            count += 1
    return {"waveform_relative_error": max_error/max(max_current, 1e-12),
            "waveform_sample_count": count,
            "reference_joule_integral_a2s_by_phase": expected["joule_integral_a2s_by_phase"],
            "reference_equivalent_rms_a_by_phase": expected["equivalent_rms_a_by_phase"]}
