"""Balanced RMS electromechanical dynamics; algebraic T circuit + isolated DSS.

Mechanical dynamics are integrated by fixed-step RK4. Electrical flux
transients are excluded explicitly; this is not EMT or IndMach012 execution.
"""
from __future__ import annotations

from bisect import bisect_right
from copy import deepcopy
from importlib.metadata import version
import cmath
from math import isfinite, pi, sqrt
import platform

from . import motor_dynamics_intake as intake, motor_starting_intake, motor_starting_static as static

BACKEND = "MCP_BALANCED_RMS_RK4_V1"
MODEL = "BALANCED_RMS_QUASI_STEADY_ELECTROMECHANICAL"
OPTIONS = {
    "backend", "electrical_model", "refinement", "rated_speed_fraction",
    "starting_current_relative_tolerance", "starting_pf_absolute_tolerance",
    "rated_output_relative_tolerance", "voltage_unbalance_relative_tolerance",
    "energy_relative_tolerance", "refinement_relative_tolerance",
    "acceleration_time_absolute_tolerance_s", "source_reference",
}
PINNED = {"opendssdirect.py": "0.9.4", "dss-python": "0.15.7", "dss-python-backend": "0.14.5"}


def contrato() -> dict:
    return {
        "schema": "MCP_ELECTRICO_P13F_RMS_EXECUTION_CONTRACT_V1",
        "backend": BACKEND, "electrical_model": MODEL,
        "maturity": "VALIDATED_WITH_LIMITATIONS", "scope": intake.SCOPE,
        "options_required": sorted(OPTIONS), "runtime_required": PINNED.copy(),
        "integrator": "FIXED_STEP_RK4", "refinement": [1, 2, 4],
        "maximum_total_steps": intake.MAXIMUM_STEPS, "simultaneous_dynamic_motors": 1,
        "electrical_flux_transients": False, "waveforms": False,
        "magnetic_energy_state": False, "thermal_evolution": False,
        "initialization": "INSTANTANEOUS_BALANCED_RMS_ENERGIZATION_AT_ZERO_SPEED",
        "professional_emission": False, "automatic_defaults": False, "automatic_dispatch": False,
    }


def electrical(model: dict, motor: dict, speed: float, voltage_ll_v: float) -> dict:
    e = model["electrical"]
    frequency = float(e["frequency_hz"])
    synchronous = 2 * pi * frequency / e["pole_pairs"]
    slip = 1 - speed / synchronous
    if not isfinite(speed) or not 0 < slip <= 1:
        raise ValueError("P13F_SPEED_DOMAIN: motor must remain below synchronous speed and nonnegative")
    w = 2 * pi * frequency
    zs = complex(e["stator_resistance_ohm"], w * e["stator_leakage_inductance_h"])
    zr = complex(e["rotor_resistance_ohm"] / slip, w * e["rotor_leakage_inductance_h"])
    zm = complex(0, w * e["magnetizing_inductance_h"])
    impedance = zs + zm * zr / (zm + zr)
    phase_voltage = voltage_ll_v / sqrt(3) if motor["connection"] == "wye" else voltage_ll_v
    stator_current = phase_voltage / impedance
    rotor_current = (phase_voltage - stator_current * zs) / zr
    power = 3 * phase_voltage * stator_current.conjugate()
    gap = 3 * abs(rotor_current)**2 * e["rotor_resistance_ohm"] / slip
    torque = gap / synchronous
    stator_loss = 3 * abs(stator_current)**2 * e["stator_resistance_ohm"]
    rotor_loss = 3 * abs(rotor_current)**2 * e["rotor_resistance_ohm"]
    line_current = abs(stator_current) * (sqrt(3) if motor["connection"] == "delta" else 1)
    values = {
        "speed_rad_s": speed, "slip": slip, "torque_nm": torque,
        "current_a": line_current, "input_power_w": power.real, "reactive_power_var": power.imag,
        "power_factor": power.real / abs(power), "stator_loss_w": stator_loss,
        "rotor_loss_w": rotor_loss, "converted_power_w": torque * speed,
        "electrical_balance_residual_w": power.real - stator_loss - rotor_loss - torque * speed,
    }
    if not all(isfinite(v) for v in values.values()):
        raise ValueError("P13F_NONFINITE_ELECTRICAL_RESULT")
    return values


def load_torque(mechanical: dict, speed: float) -> float:
    curve = mechanical["load_curve"]
    xs = [p["speed_rad_s"] for p in curve]
    if speed < xs[0] or speed > xs[-1]:
        raise ValueError("P13F_LOAD_CURVE_EXTRAPOLATION_BLOCKED")
    j = min(bisect_right(xs, speed), len(xs)-1)
    if j == 0: return float(curve[0]["torque_nm"])
    a, b = curve[j-1], curve[j]
    fraction = (speed-a["speed_rad_s"])/(b["speed_rad_s"]-a["speed_rad_s"])
    return a["torque_nm"] + fraction*(b["torque_nm"]-a["torque_nm"])


def rk4(rhs, state: list[float], time: float, step: float) -> list[float]:
    k1 = rhs(time, state)
    k2 = rhs(time+step/2, [y+step*k/2 for y,k in zip(state,k1)])
    k3 = rhs(time+step/2, [y+step*k/2 for y,k in zip(state,k2)])
    k4 = rhs(time+step, [y+step*k for y,k in zip(state,k3)])
    out = [y+step*(a+2*b+2*c+d)/6 for y,a,b,c,d in zip(state,k1,k2,k3,k4)]
    if not all(isfinite(v) for v in out): raise ValueError("P13F_NONFINITE_INTEGRATION")
    return out


def readiness(manifest: dict, package: dict, options: dict) -> dict:
    admitted = intake.evaluar_admision_dinamica(manifest, package)
    issues = deepcopy(admitted["issues"])
    def issue(message): issues.append({"code": "P13F_EXECUTION_GATE", "message": message})
    if not isinstance(options, dict): options = {}; issue("Se requieren opciones explícitas.")
    def finite(value):
        try: return type(value) in (int,float) and isfinite(value)
        except OverflowError: return False
    if set(options) != OPTIONS: issue("Faltan opciones o existen campos desconocidos.")
    for key in OPTIONS - {"backend", "electrical_model", "refinement", "source_reference"}:
        value = options.get(key)
        if not finite(value) or value <= 0:
            issue(f"{key}: número positivo y finito requerido.")
        elif key != "acceleration_time_absolute_tolerance_s" and value > 0.1 and key != "rated_speed_fraction":
            issue(f"{key}: la tolerancia debe ser como máximo 0.1.")
    if type(options.get("rated_speed_fraction")) in (int,float) and not 0 < options["rated_speed_fraction"] < 1:
        issue("rated_speed_fraction debe estar entre cero y uno.")
    if options.get("backend") != BACKEND or options.get("electrical_model") != MODEL:
        issue("Backend y aproximación RMS deben seleccionarse explícitamente.")
    if options.get("refinement") != "DT_DT2_DT4_REQUIRED": issue("Se requiere convergencia dt, dt/2 y dt/4.")
    if not isinstance(options.get("source_reference"), str) or not options["source_reference"].strip():
        issue("Procedencia de criterios/tolerancias requerida.")
    runtime = {name: version(name) for name in PINNED}
    if runtime != PINNED: issue("Las versiones del backend no corresponden a la calificación publicada.")
    calibration = []
    if admitted["data_ready"]:
        if len(package["motors"]) != 1: issue("El alcance acoplado inicial admite un motor dinámico por estudio.")
        sim = package["simulation"]
        count = round(sim["duration_s"] / sim["time_step_s"])
        if count*7*len(package["studies"]) > intake.MAXIMUM_STEPS:
            issue("La suma de pasos de refinamiento supera 200000.")
        base = motor_starting_intake.evaluar_admision_motor(manifest)
        preflight, _ = static._preflight_base(manifest["base_model"], base["motors"])
        issues.extend(preflight)
        topology = manifest["base_model"]["topology"]
        if any(float(i.get("phases", 3)) != 3 for kind in ("lines", "loads") for i in topology.get(kind, [])):
            issue("El backend RMS inicial requiere una red trifásica equilibrada.")
        if not issues:
            motors = static._motor_map(base)
            for model in package["motors"]:
                motor = motors[model["motor_id"].lower()]
                try:
                    start = electrical(model, motor, 0, motor["kv_ll"]*1000)
                except (ValueError,OverflowError,ZeroDivisionError):
                    issue("Parámetros eléctricos fuera del dominio numérico del backend.")
                    continue
                sync = 2*pi*model["electrical"]["frequency_hz"]/model["electrical"]["pole_pairs"]
                nominal = electrical(model, motor, sync*options["rated_speed_fraction"], motor["kv_ll"]*1000)
                shaft = nominal["converted_power_w"]-model["mechanical"]["viscous_damping_nm_s_per_rad"]*nominal["speed_rad_s"]**2
                current_error = abs(start["current_a"]/motor["starting_current_a"]-1)
                pf_error = abs(start["power_factor"]-motor["starting_power_factor"])
                output_error = abs(shaft/(motor["rated_output_kw"]*1000)-1)
                calibration.append({"motor_id":motor["id"], "starting_current_relative_error":current_error,
                                    "starting_pf_absolute_error":pf_error, "rated_output_relative_error":output_error})
                if current_error > options["starting_current_relative_tolerance"] or pf_error > options["starting_pf_absolute_tolerance"] or output_error > options["rated_output_relative_tolerance"]:
                    issue("El circuito equivalente discrepa de los datos declarados de arranque/nominales.")
    return {"schema":"MCP_ELECTRICO_P13F_RMS_READINESS_V1", "ready_for_execution":not issues,
            "issues":issues, "calibration":calibration, "runtime":runtime, "contract":contrato(),
            "network_solve_performed":False, "model_mutation_performed":False, "professional_emission":False}


def _trajectory(manifest, package, options, study, divisor, *, starter=None):
    base = motor_starting_intake.evaluar_admision_motor(manifest)
    motors = base["motors"]
    motor = static._motor_map(base)[study["motor_id"].lower()]
    model = package["motors"][0]
    mechanical = model["mechanical"]
    inertia = mechanical["motor_inertia_kg_m2"]+mechanical["load_inertia_kg_m2"]
    damping = mechanical["viscous_damping_nm_s_per_rad"]
    _, bases = static._preflight_base(manifest["base_model"], motors)
    engine, _ = static._build_isolated_base(manifest["base_model"], motors, bases)
    if motor["base_model_includes_running_motor"]:
        engine(f"Edit {motor['running_load_element_id']} Enabled=No")
    name = "Load.p13f_dynamic_machine"
    if name.lower() in {n.lower() for n in engine.Circuit.AllElementNames()}:
        raise ValueError("P13F_DYNAMIC_ELEMENT_COLLISION")
    engine(f"New {name} Bus1={motor['bus']} Phases=3 kV={motor['kv_ll']} Conn={motor['connection']} Model=2 Status=Fixed kW=1 kvar=1 Vminpu=0.01 Vmaxpu=2")
    engine("Set ControlMode=Off MaxIterations=100 Tolerance=1e-10")
    controller = None
    if starter is not None:
        from .motor_soft_starting import SoftStarterNetwork
        controller = SoftStarterNetwork(engine, name, model, motor, options, starter)
    a = cmath.exp(2j*pi/3)
    def sample(speed, time=0):
        if speed < 0: raise ValueError("P13F_REVERSE_SPEED_OR_COARSE_GRID")
        if controller is not None:
            result = controller.sample(time, speed)
            result["load_torque_nm"] = load_torque(mechanical, speed)
            return result
        demand = electrical(model, motor, speed, motor["kv_ll"]*1000)
        engine(f"Edit {name} kW={demand['input_power_w']/1000} kvar={demand['reactive_power_var']/1000}")
        engine("Solve")
        if not engine.Solution.Converged(): raise ValueError("P13F_NETWORK_NONCONVERGENCE")
        engine.Circuit.SetActiveBus(motor["bus"])
        nodes, raw = list(engine.Bus.Nodes()), engine.Bus.Voltages()
        voltages = dict(zip(nodes, [complex(raw[j],raw[j+1]) for j in range(0,len(raw),2)]))
        va,vb,vc = [voltages[n] for n in (1,2,3)]
        positive = (va+a*vb+a*a*vc)/3
        negative = (va+a*a*vb+a*vc)/3
        zero = (va+vb+vc)/3
        if abs(positive) == 0 or max(abs(negative),abs(zero))/abs(positive) > options["voltage_unbalance_relative_tolerance"]:
            raise ValueError("P13F_UNBALANCED_OR_DEENERGIZED_NETWORK")
        voltage = sqrt(3)*abs(positive)
        result = electrical(model,motor,speed,voltage)
        result["voltage_pu"] = voltage/(motor["kv_ll"]*1000)
        if not 0.01 <= result["voltage_pu"] <= 2:
            raise ValueError("P13F_VOLTAGE_MODEL_DOMAIN")
        engine.Circuit.SetActiveElement(name)
        currents = engine.CktElement.CurrentsMagAng()[0:6:2]
        powers = engine.CktElement.Powers()[0:6:2]
        native_current = sum(currents)/3
        native_power = sum(powers)*1000
        if abs(native_current-result["current_a"])/max(result["current_a"],1e-9)>1e-6 or abs(native_power-result["input_power_w"])/max(result["input_power_w"],1e-9)>1e-6:
            raise ValueError("P13F_NATIVE_NETWORK_COUPLING_MISMATCH")
        result["native_line_current_a"] = native_current
        result["native_input_power_w"] = native_power
        result["load_torque_nm"] = load_torque(mechanical,speed)
        return result
    def rhs(time,state):
        row = sample(state[0], time)
        net = row["torque_nm"]-row["load_torque_nm"]-damping*state[0]
        acceleration = max(net,0)/inertia if state[0] == 0 else net/inertia
        derivatives = [acceleration,state[0],row["input_power_w"],row["stator_loss_w"],row["rotor_loss_w"],row["load_torque_nm"]*state[0],damping*state[0]**2]
        if controller is not None:
            derivatives += [row["rl_surrogate_extra_power_w"], row["current_a"]**2]
        return derivatives
    step = package["simulation"]["time_step_s"]/divisor
    count = round(package["simulation"]["duration_s"]/step)
    state = [0.0]*(9 if controller is not None else 7)
    rows = []
    max_energy_error = 0
    reached = None
    target = study["target_speed_fraction"]*2*pi*model["electrical"]["frequency_hz"]/model["electrical"]["pole_pairs"]
    for j in range(count+1):
        time = j*step
        row = sample(state[0], time)
        if controller is not None:
            controller.commit_boundary(time, row)
        kinetic = 0.5*inertia*state[0]**2
        residual = state[2]-sum(state[3:8])-kinetic
        relative = abs(residual)/max(abs(state[2]),kinetic,1)
        max_energy_error = max(max_energy_error,relative)
        row.update(time_s=time,angle_rad=state[1],kinetic_energy_j=kinetic,
                   electrical_input_energy_j=state[2],stator_loss_energy_j=state[3],rotor_loss_energy_j=state[4],
                   load_work_j=state[5],damping_loss_energy_j=state[6],energy_residual_j=residual)
        if controller is not None:
            row.update(rl_surrogate_extra_energy_j=state[7], line_current_i2t_a2_s=state[8])
        rows.append(row)
        if reached is None and state[0] >= target: reached = time
        if j < count: state = rk4(rhs,state,time,step)
    result = {"study_id":study["id"],"motor_id":motor["id"],"trajectory":rows,
            "time_step_s":step,"acceleration_time_s":reached,"maximum_energy_relative_error":max_energy_error,
            "minimum_voltage_pu":min(r["voltage_pu"] for r in rows),
            "state":"STALLED_AT_REST" if max(r["speed_rad_s"] for r in rows)==0 else "TARGET_REACHED" if reached is not None else "TARGET_NOT_REACHED"}
    if controller is not None:
        result.update(bypass_time_s=controller.bypass_time, maximum_line_current_a=max(r["current_a"] for r in rows),
                      minimum_supply_voltage_pu=min(r["supply_voltage_pu"] for r in rows),
                      current_limit_verified=all(r["starter_state"] == "BYPASS" or r["current_a"] <= starter["current_limit_a"]*(1+1e-7) for r in rows),
                      voltage_quantity="MOTOR_FUNDAMENTAL_RMS")
    return result


def execute(manifest: dict, package: dict, options: dict) -> dict:
    parent = static._parent_signature()
    ready = readiness(manifest,package,options)
    result = {"schema":"MCP_ELECTRICO_P13F_DYNAMIC_EXECUTION_V1", "execution_status":"BLOCKED_DYNAMIC_READINESS",
              "readiness":ready,"results":[],"contract":contrato(),"runtime":ready["runtime"],
              "python_version":platform.python_version(),"parent_context_mutated":False,
              "dynamic_integration_performed":False,"professional_emission":False}
    if not ready["ready_for_execution"]: return result
    try:
        for study in package["studies"]:
            grids = [_trajectory(manifest,package,options,study,d) for d in (1,2,4)]
            coarse,middle,fine = grids
            errors = {}
            for field in ("speed_rad_s","current_a","torque_nm","voltage_pu"):
                scale = max(max(abs(r[field]) for r in fine["trajectory"]),1e-9)
                errors[field] = max(max(abs(r[field]-fine["trajectory"][j*d][field])/scale for j,r in enumerate(g["trajectory"])) for g,d in ((coarse,4),(middle,2)))
            times = [g["acceleration_time_s"] for g in grids]
            time_match = all(t is None for t in times) or all(t is not None for t in times) and max(times)-min(times) <= options["acceleration_time_absolute_tolerance_s"]
            energy = max(g["maximum_energy_relative_error"] for g in grids)
            verified = max(errors.values()) <= options["refinement_relative_tolerance"] and time_match and energy <= options["energy_relative_tolerance"]
            coarse["verification"] = {"grid_relative_errors":errors,"acceleration_times_s":times,
                                      "maximum_energy_relative_error":energy,"grid_and_energy_verified":verified}
            coarse["criterion"] = {"passed":coarse["minimum_voltage_pu"]>=study["minimum_terminal_voltage_pu"] and times[0] is not None and times[0]<=study["maximum_acceleration_time_s"],"reference":study["criterion_reference"]}
            coarse["ok"] = verified
            result["results"].append(coarse)
        result["execution_status"] = "DYNAMIC_STUDIES_COMPLETED" if all(r["ok"] for r in result["results"]) else "DYNAMIC_VALIDATION_FAILED"
    except Exception as exc:
        result["execution_status"] = "DYNAMIC_INTEGRATION_FAILED"
        result["error"] = str(exc)
    finally:
        result["dynamic_integration_performed"] = True
        if parent != static._parent_signature(): raise RuntimeError("P13F_PARENT_CONTEXT_MUTATED")
    return result
