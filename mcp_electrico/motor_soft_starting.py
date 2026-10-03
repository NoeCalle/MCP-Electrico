"""P13G: controlled soft starting with a balanced per-phase RL surrogate.

This is an analytical periodic SCR/RL equivalent coupled to a fundamental-only
network and a fundamental induction-motor model. It is NOT a switched three-wire
motor model, EMT, manufacturer calibration, or a harmonic network study.
The nonfundamental RL power is accounted for separately, never called motor heat.
"""
from __future__ import annotations

from copy import deepcopy
import cmath
from math import acos, cos, exp, isfinite, pi, sin, sqrt
import platform

from . import motor_dynamics as dynamic, motor_starting_static as static

SCHEMA = "MCP_ELECTRICO_P13G_SOFT_STARTER_V1"
BACKEND = "MCP_SCR_RL_SURROGATE_RMS_RK4_V1"
MODEL = "BALANCED_PER_PHASE_PERIODIC_SCR_RL_SURROGATE"
ACKNOWLEDGEMENT = "RL_SURROGATE_NOT_DEVICE_VALIDATED"
CONTROL_FIELDS = {
    "schema", "motor_id", "electrical_model", "scope_acknowledgement", "connection",
    "control_mode", "initial_voltage_fraction", "ramp_time_s", "current_limit_a",
    "bypass_speed_fraction", "bypass_hold_s", "source_reference", "criterion_evidence",
}
EVIDENCE_FIELDS = {"kind", "document", "edition", "clause", "applicability", "source_reference", "voltage_quantity"}


def contract():
    return {
        "schema": "MCP_ELECTRICO_P13G_SOFT_STARTER_CONTRACT_V1", "starter_schema": SCHEMA,
        "backend": BACKEND, "electrical_model": MODEL,
        "maturity": "ANALYTICAL_SURROGATE_NOT_DEVICE_VALIDATED",
        "scope_acknowledgement": ACKNOWLEDGEMENT, "required_fields": sorted(CONTROL_FIELDS),
        "criterion_evidence_fields": sorted(EVIDENCE_FIELDS),
        "scope": "ONE_BALANCED_MOTOR_WITH_POSITIVE_SEQUENCE_RL_EQUIVALENT",
        "reference_manifest": "DOL_FULL_VOLTAGE_LOCKED_ROTOR_PHYSICAL_CALIBRATION_ONLY",
        "control": "FUNDAMENTAL_VOLTAGE_RAMP_WITH_TRUE_RMS_CURRENT_LIMIT_PRIORITY",
        "connection": "INLINE_POSITIVE_SEQUENCE_EQUIVALENT_NOT_SWITCHED_THREE_WIRE_TOPOLOGY",
        "current_limit_basis": "PERIODIC_RL_SURROGATE_TRUE_RMS_LINE_CURRENT_A",
        "motor_torque_basis": "FUNDAMENTAL_VOLTAGE_ONLY",
        "voltage_criterion_basis": "MOTOR_FUNDAMENTAL_RMS",
        "bypass": "LATCH_AFTER_FULL_VOLTAGE_AND_SPEED_FOR_DECLARED_HOLD_TIME",
        "refinement": [1, 2, 4], "maximum_total_steps": 20000,
        "limits": ["NO_THREE_WIRE_SWITCHING_INTERACTION", "NO_DEVICE_CALIBRATION",
                   "NO_NETWORK_HARMONICS", "NO_HARMONIC_MOTOR_TORQUE", "NO_THERMAL_EVOLUTION",
                   "NO_GATE_PULSE_OR_FLUX_TRANSIENTS", "NO_SIMULTANEOUS_DYNAMIC_MOTORS"],
        "extra_power_basis": "RL_SURROGATE_NONFUNDAMENTAL_POWER_NOT_ACTUAL_MOTOR_HEATING",
        "automatic_physical_defaults": False, "universal_normative_threshold": False,
        "professional_emission": False,
        "references": [
            "https://backend.orbit.dtu.dk/ws/portalfiles/portal/7703047/ris_r_1400_ed2.pdf",
            "https://support.industry.siemens.com/cs/attachments/38752095/Manual_softstarter_3RW30_3RW40_en-US.pdf",
        ],
    }


def phase_response(alpha: float, phi: float) -> dict:
    """Periodic antiparallel SCR with sustained gate command and a passive RL.

For alpha>phi, i(theta)/(Vpeak/|Z|) = sin(theta-phi)
 - sin(alpha-phi)*exp(-(theta-alpha)/tan(phi)), alpha<=theta<=beta.
For alpha<=phi continuous conduction recovers DOL. Fourier integrals are
analytical. True RMS follows the independent RL real-power identity.
"""
    if not all(isfinite(v) for v in (alpha, phi)) or not 0 <= alpha <= pi or not 0 <= phi < pi/2:
        raise ValueError("P13G_PHASE_DOMAIN")
    if alpha <= phi:
        return {"gain": 1., "in_phase": cos(phi), "quadrature": -sin(phi),
                "true_current_factor": 1., "voltage_rms_factor": 1., "extinction_angle_rad": pi+phi}
    if alpha == pi:
        return {"gain": 0., "in_phase": 0., "quadrature": 0.,
                "true_current_factor": 0., "voltage_rms_factor": 0., "extinction_angle_rad": pi}
    if phi == 0:
        beta = pi
        es = ec = 0.
    else:
        lam = cos(phi)/sin(phi)
        c = sin(alpha-phi)
        lo, hi = pi, pi+phi
        for _ in range(42):
            middle = (lo+hi)/2
            value = sin(middle-phi)-c*exp(-lam*(middle-alpha))
            if value > 0: lo = middle
            else: hi = middle
        beta = (lo+hi)/2
        eb = exp(-lam*(beta-alpha))
        es = c*(eb*(-lam*sin(beta)-cos(beta))+lam*sin(alpha)+cos(alpha))/(1+lam*lam)
        ec = c*(eb*(-lam*cos(beta)+sin(beta))+lam*cos(alpha)-sin(alpha))/(1+lam*lam)
    delta = beta-alpha
    s2 = (sin(2*beta)-sin(2*alpha))/4
    cross = (sin(beta)**2-sin(alpha)**2)/2
    b = 2/pi*(cos(phi)*(delta/2-s2)-sin(phi)*cross-es)
    a = 2/pi*(cos(phi)*cross-sin(phi)*(delta/2+s2)-ec)
    b = max(b, 0.)
    gain = sqrt(a*a+b*b)
    if gain > 1+1e-9: raise ValueError("P13G_NONPASSIVE_GAIN")
    return {"gain": min(gain, 1.), "in_phase": b, "quadrature": a,
            "true_current_factor": sqrt(b/cos(phi)),
            "voltage_rms_factor": sqrt(max(0., (delta-2*s2)/pi)), "extinction_angle_rad": beta}


def alpha_for_gain(gain: float, phi: float) -> float:
    if not 0 <= gain <= 1: raise ValueError("P13G_GAIN_DOMAIN")
    if gain == 1: return 0.
    if gain == 0: return pi
    lo, hi = phi, pi
    for _ in range(30):
        middle = (lo+hi)/2
        if phase_response(middle, phi)["gain"] > gain: lo = middle
        else: hi = middle
    return hi


def readiness(manifest, package, options, starter):
    ready = dynamic.readiness(manifest, package, options)
    issues = deepcopy(ready["issues"])
    def issue(path, message): issues.append({"code": "P13G_GATE", "path": path, "message": message})
    if not isinstance(starter, dict):
        starter = {}; issue("starter", "Se requiere configuración explícita del arrancador.")
    if set(starter) != CONTROL_FIELDS: issue("starter", "Campos ausentes o desconocidos en el contrato SCR.")
    for key, expected in {"schema": SCHEMA, "electrical_model": MODEL, "scope_acknowledgement": ACKNOWLEDGEMENT,
                          "connection": "INLINE_POSITIVE_SEQUENCE_EQUIVALENT",
                          "control_mode": "FUNDAMENTAL_VOLTAGE_RAMP_CURRENT_LIMIT"}.items():
        if starter.get(key) != expected: issue(key, f"Se requiere {expected}.")
    def numeric(key, minimum, maximum, *, lower_inclusive=False):
        value = starter.get(key)
        try:
            valid = type(value) in (int, float) and isfinite(value) and (value >= minimum if lower_inclusive else value > minimum) and value <= maximum
        except OverflowError: valid = False
        if not valid: issue(key, "Número explícito fuera de rango.")
    numeric("initial_voltage_fraction", .01, 1)
    numeric("ramp_time_s", 0, 86400)
    numeric("current_limit_a", 0, 1e7)
    numeric("bypass_speed_fraction", 0, .999)
    numeric("bypass_hold_s", 0, 86400, lower_inclusive=True)
    if not isinstance(starter.get("source_reference"), str) or not starter["source_reference"].strip():
        issue("source_reference", "Procedencia de ajustes requerida.")
    if ready["ready_for_execution"]:
        if starter.get("motor_id") != package["motors"][0]["motor_id"]:
            issue("motor_id", "El arrancador debe referenciar el único motor dinámico.")
        count = round(package["simulation"]["duration_s"]/package["simulation"]["time_step_s"])
        if count*7*len(package["studies"]) > 20000: issue("simulation", "El presupuesto SCR admite como máximo 20000 pasos sumando refinamientos y estudios.")
    evidence = starter.get("criterion_evidence")
    raw_studies = package.get("studies", []) if isinstance(package, dict) else []
    studies = raw_studies if isinstance(raw_studies, list) else []
    if not isinstance(evidence, dict):
        evidence = {}; issue("criterion_evidence", "Se requiere procedencia por estudio; no existen mínimos normativos predeterminados.")
    if set(evidence) != {s["id"] for s in studies if isinstance(s, dict) and "id" in s}:
        issue("criterion_evidence", "La evidencia debe corresponder exactamente a los estudios.")
    for study in studies:
        if not isinstance(study, dict): continue
        ev = evidence.get(study.get("id"))
        if not isinstance(ev, dict): issue("criterion_evidence", "Falta evidencia estructurada."); continue
        if set(ev) != EVIDENCE_FIELDS: issue("criterion_evidence", "Faltan campos o existen campos desconocidos.")
        for key in EVIDENCE_FIELDS:
            if not isinstance(ev.get(key), str) or not ev[key].strip(): issue(f"criterion_evidence.{key}", "Texto explícito requerido.")
        if not isinstance(ev.get("kind"), str) or ev["kind"] not in {"ILLUSTRATIVE", "PROJECT_REQUIREMENT", "MANUFACTURER_LIMIT", "NORMATIVE_REQUIREMENT"}:
            issue("criterion_evidence.kind", "Clasificación desconocida.")
        if ev.get("voltage_quantity") != "MOTOR_FUNDAMENTAL_RMS":
            issue("criterion_evidence.voltage_quantity", "No comparar el resultado fundamental con límites de tensión RMS total.")
        if ev.get("source_reference") != study.get("criterion_reference"):
            issue("criterion_evidence.source_reference", "Debe coincidir con la referencia del criterio ejecutado.")
    return {"schema": "MCP_ELECTRICO_P13G_SOFT_STARTER_READINESS_V1", "ready_for_execution": not issues,
            "issues": issues, "physical_readiness": ready, "contract": contract(),
            "network_solve_performed": False, "dynamic_integration_performed": False,
            "professional_emission": False}


class SoftStarterNetwork:
    """Controller evaluation has no history writes; only sampled boundaries latch bypass."""
    def __init__(self, engine, name, model, motor, options, starter):
        self.engine, self.name, self.model, self.motor = engine, name, model, motor
        self.options, self.starter = options, starter
        self.bypass_time = None
        self.full_voltage_since = None
        self.nominal = motor["kv_ll"]*1000
        self.sync = 2*pi*model["electrical"]["frequency_hz"]/model["electrical"]["pole_pairs"]

    def _at_alpha(self, speed, full, phi, alpha):
        response = phase_response(alpha, phi)
        grid_p = sqrt(3)*self.nominal*full["current_a"]*response["in_phase"]
        grid_q = -sqrt(3)*self.nominal*full["current_a"]*response["quadrature"]
        self.engine(f"Edit {self.name} kW={grid_p/1000} kvar={grid_q/1000}")
        self.engine("Solve")
        if not self.engine.Solution.Converged(): raise ValueError("P13G_NETWORK_NONCONVERGENCE")
        self.engine.Circuit.SetActiveBus(self.motor["bus"])
        raw = self.engine.Bus.Voltages()
        volts = dict(zip(self.engine.Bus.Nodes(), [complex(raw[j], raw[j+1]) for j in range(0, len(raw), 2)]))
        a = cmath.exp(2j*pi/3)
        va, vb, vc = [volts[n] for n in (1, 2, 3)]
        positive = (va+a*vb+a*a*vc)/3
        negative = (va+a*a*vb+a*vc)/3
        zero = (va+vb+vc)/3
        if abs(positive) == 0 or max(abs(negative), abs(zero))/abs(positive) > self.options["voltage_unbalance_relative_tolerance"]:
            raise ValueError("P13G_UNBALANCED_OR_DEENERGIZED_NETWORK")
        supply_pu = sqrt(3)*abs(positive)/self.nominal
        if not .01 <= supply_pu <= 2: raise ValueError("P13G_SUPPLY_VOLTAGE_DOMAIN")
        gain = response["gain"]
        row = dynamic.electrical(self.model, self.motor, speed, self.nominal*supply_pu*gain)
        motor_p = row["input_power_w"]
        power = grid_p*supply_pu**2
        extra = power-motor_p
        if extra < -1e-7*max(power, 1): raise ValueError("P13G_NONPASSIVE_POWER_BALANCE")
        fundamental_current = full["current_a"]*supply_pu*gain
        true_current = full["current_a"]*supply_pu*response["true_current_factor"]
        self.engine.Circuit.SetActiveElement(self.name)
        native_current = sum(self.engine.CktElement.CurrentsMagAng()[0:6:2])/3
        native_power = sum(self.engine.CktElement.Powers()[0:6:2])*1000
        if abs(native_current-fundamental_current)/max(fundamental_current, 1e-9) > 1e-6 or abs(native_power-power)/max(power, 1e-9) > 1e-6:
            raise ValueError("P13G_NATIVE_COUPLING_MISMATCH")
        row.update(current_a=true_current, fundamental_line_current_a=fundamental_current,
                   motor_fundamental_power_factor=full["power_factor"],
                   supply_displacement_power_factor=response["in_phase"]/max(gain, 1e-12),
                   supply_true_power_factor_rl=response["in_phase"]/max(response["true_current_factor"], 1e-12),
                   motor_fundamental_input_power_w=motor_p, input_power_w=power,
                   supply_reactive_power_var=grid_q*supply_pu**2,
                   rl_surrogate_extra_power_w=max(extra, 0.),
                   native_line_current_a=native_current, native_input_power_w=native_power,
                   voltage_pu=supply_pu*gain, supply_voltage_pu=supply_pu,
                   motor_voltage_rms_pu=supply_pu*response["voltage_rms_factor"],
                   voltage_gain=gain, firing_angle_rad=alpha,
                   surrogate_current_thd=sqrt(max(0., true_current**2-fundamental_current**2))/max(fundamental_current, 1e-12))
        return row

    def sample(self, time, speed):
        full = dynamic.electrical(self.model, self.motor, speed, self.nominal)
        phi = acos(min(max(full["power_factor"], 0.), 1.))
        s = self.starter
        if self.bypass_time is not None:
            row = self._at_alpha(speed, full, phi, 0.)
            row.update(starter_state="BYPASS", requested_voltage_fraction=1., current_limit_active=False)
            return row
        requested = s["initial_voltage_fraction"]+(1-s["initial_voltage_fraction"])*min(max(time/s["ramp_time_s"], 0.), 1.)
        alpha = alpha_for_gain(requested, phi)
        row = self._at_alpha(speed, full, phi, alpha)
        limited = row["current_a"] > s["current_limit_a"]
        if limited:
            lo, hi = alpha, pi
            # Upper endpoint is deenergized and always below the declared cap.
            for _ in range(26):
                middle = (lo+hi)/2
                candidate = self._at_alpha(speed, full, phi, middle)
                if candidate["current_a"] > s["current_limit_a"]: lo = middle
                else: hi = middle
            row = self._at_alpha(speed, full, phi, hi)
        row.update(starter_state="CURRENT_LIMIT" if limited else "FULL_VOLTAGE" if requested == 1 else "VOLTAGE_RAMP",
                   requested_voltage_fraction=requested, current_limit_active=limited)
        return row

    def commit_boundary(self, time, row):
        if self.bypass_time is not None: return
        eligible = row["voltage_gain"] >= 1-1e-8 and not row["current_limit_active"] and row["speed_rad_s"] >= self.starter["bypass_speed_fraction"]*self.sync
        if not eligible:
            self.full_voltage_since = None
            return
        if self.full_voltage_since is None: self.full_voltage_since = time
        if time-self.full_voltage_since >= self.starter["bypass_hold_s"]-1e-12:
            self.bypass_time = time
            row["starter_state"] = "BYPASS"


def execute(manifest, package, options, starter):
    parent = static._parent_signature()
    ready = readiness(manifest, package, options, starter)
    result = {"schema": "MCP_ELECTRICO_P13G_SOFT_STARTER_EXECUTION_V1", "execution_status": "BLOCKED_SOFT_STARTER_READINESS",
              "readiness": ready, "results": [], "contract": contract(),
              "runtime": ready["physical_readiness"]["runtime"], "python_version": platform.python_version(),
              "dynamic_integration_performed": False, "parent_context_mutated": False,
              "design_acceptance_status": "NOT_DEMONSTRATED", "professional_emission": False}
    if not ready["ready_for_execution"]: return result
    try:
        for study in package["studies"]:
            grids = [dynamic._trajectory(manifest, package, options, study, d, starter=starter) for d in (1, 2, 4)]
            coarse, middle, fine = grids
            errors = {}
            for field in ("speed_rad_s", "current_a", "torque_nm", "voltage_pu", "supply_voltage_pu", "line_current_i2t_a2_s"):
                scale = max(max(abs(r[field]) for r in fine["trajectory"]), 1e-9)
                errors[field] = max(max(abs(r[field]-fine["trajectory"][j*d][field])/scale for j, r in enumerate(g["trajectory"])) for g, d in ((coarse, 4), (middle, 2)))
            def matching_times(key):
                times = [g[key] for g in grids]
                return all(t is None for t in times) or all(t is not None for t in times) and max(times)-min(times) <= options["acceleration_time_absolute_tolerance_s"]
            energy = max(g["maximum_energy_relative_error"] for g in grids)
            verified = max(errors.values()) <= options["refinement_relative_tolerance"] and matching_times("acceleration_time_s") and matching_times("bypass_time_s") and energy <= options["energy_relative_tolerance"] and all(g["current_limit_verified"] for g in grids)
            ev = deepcopy(starter["criterion_evidence"][study["id"]])
            passed = coarse["minimum_voltage_pu"] >= study["minimum_terminal_voltage_pu"] and coarse["acceleration_time_s"] is not None and coarse["acceleration_time_s"] <= study["maximum_acceleration_time_s"]
            coarse.update(ok=verified, verification={"grid_relative_errors": errors, "acceleration_times_s": [g["acceleration_time_s"] for g in grids],
                           "bypass_times_s": [g["bypass_time_s"] for g in grids], "maximum_energy_relative_error": energy, "grid_and_energy_verified": verified},
                          criterion={"passed": passed, "reference": study["criterion_reference"], "evidence": ev,
                                     "normative_compliance_demonstrated": False, "source_authentication": "USER_DECLARED_NOT_AUTHENTICATED",
                                     "interpretation": "ILLUSTRATIVE_THRESHOLD_COMPARISON" if ev["kind"] == "ILLUSTRATIVE" else "DECLARED_CRITERION_COMPARISON"})
            result["results"].append(coarse)
        result["execution_status"] = "SOFT_STARTER_STUDIES_COMPLETED" if all(r["ok"] for r in result["results"]) else "SOFT_STARTER_VALIDATION_FAILED"
    except Exception as exc:
        result.update(execution_status="SOFT_STARTER_INTEGRATION_FAILED", error=str(exc))
    finally:
        result["dynamic_integration_performed"] = True
        if parent != static._parent_signature(): raise RuntimeError("P13G_PARENT_CONTEXT_MUTATED")
    return result
