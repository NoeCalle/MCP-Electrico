"""Execute existing MSL machines/converters; no in-house electrical solver.

First scope: a declared balanced RL supply equivalent at the common motor bus,
one or more existing MSL induction machines, explicit load curves and starters.
It is not an automatic EMT translation of an arbitrary OpenDSS network.
"""
from __future__ import annotations

from copy import deepcopy
import csv
import hashlib
import json
from math import isfinite, pi, sqrt
import os
from pathlib import Path
import platform
import subprocess
from . import module_qualification

SCHEMA = "MCP_ELECTRICO_MSL_MOTOR_STUDY_V1"
BACKEND = "OPENMODELICA_MSL_4_0_0"
CONFIG = Path(__file__).resolve().parents[1] / "local_data" / "modelica-runtime.json"
_configuration = None


def contract():
    return {
        "schema": SCHEMA, "backend": BACKEND,
        "engine": "OpenModelica", "library": "Modelica Standard Library 4.0.0",
        "network_scope": "DECLARED_BALANCED_COMMON_BUS_RL_EQUIVALENT",
        "starting_methods": ["DOL", "SCR"], "prepared_not_enabled_methods": [],
        "scr_scope": "ONE_DELTA_MACHINE_REFERENCE_CONTROLLER",
        "scr_numerical_profile": {"integrator": "dassl", "nonlinear_solver": "newton", "openmodelica_solver_status": "PROTOTYPE_PER_RUNTIME_DOCUMENTATION"},
        "multiple_dynamic_machines": True,
        "physical_solver_owned_by_mcp": False,
        "closed_network_current_voltage_interaction": True,
        "controller": "MSL SoftStartControl, VoltageToAngle, Signal2mPulse",
        "controller_limit": "Reference ramp-hold controller; not a manufacturer controller or guaranteed hard current cap",
        "gate_phase_reference": "UPSTREAM_SINUSOIDAL_SOURCE",
        "switch_regularization": {"Ron_ohm": 1e-6, "Goff_siemens": 1e-5},
        "triac_regularization": {"Ron_ohm": 1e-5, "Goff_siemens": 1e-5, "Vknee_v": 0},
        "qualification": "EXPERIMENTAL_ADAPTER_SYNTHETIC_CASES_ONLY",
        "scoped_qualification": {method:module_qualification.get('modelica_'+method.lower()) for method in ('DOL','SCR')},
        "not_supported": ["automatic_full_unifilar_EMT_translation", "constant_power_background_loads", "VFD", "thermal_evolution", "manufacturer_device_validation", "multiple_machines_with_SCR", "SCR_wye_connection"],
        "professional_emission": False, "automatic_defaults": False,
    }


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _environment(executable):
    env = dict(os.environ, PYTHONUTF8="1")
    runtime = Path(executable).parent.parent
    env["OPENMODELICAHOME"] = str(runtime)
    env["PATH"] = os.pathsep.join([str(runtime / "bin"), str(runtime / "tools/msys/ucrt64/bin"), env.get("PATH", "")])
    return env


def configure(executable, library):
    global _configuration
    compiler, msl = Path(executable).expanduser().resolve(), Path(library).expanduser().resolve()
    if compiler.name.lower() not in {"omc", "omc.exe"} or not compiler.is_file():
        raise ValueError("MSL_RUNTIME: select the installed omc executable")
    required = ["Modelica/package.mo", "Complex.mo", "ModelicaServices/package.mo"]
    if any(not (msl / f).is_file() for f in required):
        raise ValueError("MSL_LIBRARY: Modelica, Complex and ModelicaServices required")
    if 'version="4.0.0"' not in (msl / required[0]).read_text(encoding="utf8"):
        raise ValueError("MSL_VERSION: library 4.0.0 required")
    command = subprocess.run([str(compiler), "--version"], capture_output=True, text=True,
                             stdin=subprocess.DEVNULL, env=_environment(compiler), timeout=60, check=True)
    if "OpenModelica v1.27.1" not in command.stdout:
        raise ValueError("MSL_COMPILER_VERSION: this adapter is pinned to OpenModelica 1.27.1")
    _configuration = {"executable": str(compiler), "library": str(msl), "compiler_version": command.stdout.strip(),
                      "compiler_sha256": _digest(compiler), "library_tree_sha256": _library_digest(msl)}
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(_configuration, indent=2), encoding="utf8")
    return {"status": "RUNTIME_CONFIGURED", **deepcopy(_configuration), "study_executed": False}


def runtime():
    global _configuration
    try:
        if _configuration is None and CONFIG.is_file():
            _configuration = json.loads(CONFIG.read_text(encoding="utf8"))
        if not _configuration or _digest(_configuration["executable"]) != _configuration.get("compiler_sha256") or _library_digest(Path(_configuration["library"])) != _configuration.get("library_tree_sha256"):
            return {"ready": False, "reason": "Configure the installed OpenModelica/MSL runtime; missing or changed files"}
    except (OSError, KeyError, TypeError, ValueError):
        return {"ready": False, "reason": "Runtime configuration or library unavailable"}
    return {"ready": True, **deepcopy(_configuration)}


def _library_digest(root):
    files = sorted(p for p in root.rglob("*") if p.is_file())
    if not files or not (root / "Modelica/package.mo").is_file():
        raise ValueError("MSL library incomplete")
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode("utf8"))
        digest.update(b"\0" + bytes.fromhex(_digest(path)))
    return digest.hexdigest()


def validate(package):
    issues = []
    def issue(path, message):
        issues.append({"path": path, "message": message})
    def obj(value, path, fields):
        if not isinstance(value, dict):
            issue(path, "object required"); return {}
        if set(value) != set(fields):
            issue(path, "explicit fields required: " + ", ".join(sorted(fields)))
        return value
    def number(value, path, low=0, inclusive=False):
        if type(value) not in (int, float) or not isfinite(value) or (value < low if inclusive else value <= low):
            issue(path, "finite explicit numeric value outside permitted range"); return None
        return float(value)
    def reference(value, path):
        if not isinstance(value, str) or not value.strip(): issue(path, "source reference required")
    root = obj(package, "study", {"schema", "id", "source_reference", "network", "simulation", "motors"})
    if root.get("schema") != SCHEMA: issue("schema", SCHEMA + " required")
    reference(root.get("id"), "id"); reference(root.get("source_reference"), "source_reference")
    net = obj(root.get("network"), "network", {"basis", "kv_ll", "frequency_hz", "pu", "angle_deg", "r_ohm", "x_ohm", "source_reference"})
    if net.get("basis") != "PER_PHASE_THEVENIN_AT_COMMON_MOTOR_BUS": issue("network.basis", "explicit common-bus equivalent required")
    for key in ("kv_ll", "frequency_hz", "pu"): number(net.get(key), "network." + key)
    for key in ("r_ohm", "x_ohm"): number(net.get(key), "network." + key, inclusive=True)
    angle = net.get("angle_deg")
    if type(angle) not in (int, float) or not isfinite(angle): issue("network.angle_deg", "finite angle required")
    reference(net.get("source_reference"), "network.source_reference")
    sim = obj(root.get("simulation"), "simulation", {"duration_s", "output_step_s", "solver_tolerance", "maximum_internal_step_s", "time_refinement", "timeout_s", "source_reference"})
    for key in ("duration_s", "output_step_s", "solver_tolerance", "maximum_internal_step_s", "timeout_s"):
        number(sim.get(key), "simulation." + key)
    reference(sim.get("source_reference"), "simulation.source_reference")
    if sim.get("time_refinement") != "TOLERANCE_AND_MAX_STEP_REFINEMENT": issue("simulation.time_refinement", "refinement required")
    if type(sim.get("duration_s")) in (int,float) and not 0 < sim["duration_s"] <= 60: issue("simulation.duration_s", "at most 60 s")
    if type(sim.get("timeout_s")) in (int,float) and not 0 < sim["timeout_s"] <= 600: issue("simulation.timeout_s", "at most 600 s")
    f, dt = net.get("frequency_hz"), sim.get("output_step_s")
    if type(f) in (int,float) and f > 0 and type(dt) in (int,float) and dt > 1 / (100*f): issue("simulation.output_step_s", "at least 100 samples per cycle required")
    duration = sim.get("duration_s")
    if type(dt) in (int,float) and isfinite(dt) and dt > 0 and type(duration) in (int,float) and isfinite(duration):
        if duration / dt > 1_200_000: issue("simulation", "output sample budget exceeded")
        if type(f) in (int,float) and isfinite(f) and f > 0 and duration < 2/f: issue("simulation", "at least two complete cycles required")
    tol = sim.get("solver_tolerance")
    if type(tol) in (int,float) and not 1e-12 <= tol <= 1e-4: issue("simulation.solver_tolerance", "supported range 1e-12 to 1e-4")
    internal = sim.get("maximum_internal_step_s")
    if type(internal) in (int,float) and type(dt) in (int,float) and internal > dt: issue("simulation.maximum_internal_step_s", "must not exceed output step")
    motors = root.get("motors")
    if not isinstance(motors, list) or not 1 <= len(motors) <= 8:
        issue("motors", "one to eight machines required"); motors = []
    if type(dt) in (int,float) and isfinite(dt) and dt > 0 and type(duration) in (int,float) and isfinite(duration) and duration/dt*len(motors) > 800_000:
        issue("simulation", "machine-times-output-samples budget exceeded")
    ids = set()
    for index, raw in enumerate(motors):
        path = f"motors[{index}]"
        m = obj(raw, path, {"id", "connection", "electrical", "mechanical", "starting", "criteria", "source_reference"})
        reference(m.get("id"), path + ".id"); reference(m.get("source_reference"), path + ".source_reference")
        identifier = str(m.get("id", "")).casefold()
        if identifier in ids: issue(path + ".id", "duplicate motor")
        ids.add(identifier)
        if m.get("connection") not in ("wye", "delta"): issue(path + ".connection", "wye/delta required")
        e = obj(m.get("electrical"), path + ".electrical", {"pole_pairs", "stator_resistance_ohm", "rotor_resistance_ohm", "stator_leakage_inductance_h", "rotor_leakage_inductance_h", "magnetizing_inductance_h", "zero_sequence_inductance_h", "temperature_k", "loss_model", "source_reference"})
        for key in set(e) - {"source_reference", "loss_model"}: number(e[key], path + ".electrical." + key)
        if type(e.get("pole_pairs")) is not int: issue(path + ".electrical.pole_pairs", "integer required")
        if e.get("loss_model") != "FIXED_RESISTANCES_NO_CORE_STRAY_THERMAL": issue(path + ".electrical.loss_model", "declare supported loss model explicitly")
        reference(e.get("source_reference"), path + ".electrical.source_reference")
        mech = obj(m.get("mechanical"), path + ".mechanical", {"motor_inertia_kg_m2", "load_inertia_kg_m2", "damping_nm_s_rad", "load_curve", "anti_reverse", "source_reference"})
        for key in ("motor_inertia_kg_m2", "load_inertia_kg_m2"): number(mech.get(key), path + ".mechanical." + key)
        number(mech.get("damping_nm_s_rad"), path + ".mechanical.damping_nm_s_rad", inclusive=True)
        if mech.get("anti_reverse") not in ("NONE", "MSL_ONE_WAY_CLUTCH"): issue(path + ".mechanical.anti_reverse", "explicit anti-reverse mechanism required")
        reference(mech.get("source_reference"), path + ".mechanical.source_reference")
        curve = mech.get("load_curve")
        if not isinstance(curve, list) or len(curve) < 2:
            issue(path + ".mechanical.load_curve", "at least two explicit points required"); curve = []
        speeds = []
        for j, point in enumerate(curve):
            p = obj(point, f"{path}.mechanical.load_curve[{j}]", {"speed_rad_s", "torque_nm"})
            speed = number(p.get("speed_rad_s"), path + ".load_curve.speed", low=-float('inf'))
            number(p.get("torque_nm"), path + ".load_curve.torque", low=-float('inf'))
            if speed is not None: speeds.append(speed)
        if speeds and (0 not in speeds or any(b <= a for a,b in zip(speeds,speeds[1:]))): issue(path + ".load_curve", "ordered increasing speeds covering zero required")
        if speeds and speeds[0] >= 0 and mech.get("anti_reverse") == "NONE": issue(path + ".mechanical", "without an anti-reverse mechanism declare the negative-speed load curve too; electrical startup transients can reverse torque")
        if speeds and type(f) in (int,float) and type(e.get("pole_pairs")) is int and e["pole_pairs"] > 0 and speeds[-1] < 2*pi*f/e["pole_pairs"]: issue(path + ".load_curve", "curve must cover synchronous speed; no extrapolation")
        start = obj(m.get("starting"), path + ".starting", {"method", "time_s", "controller"})
        at = number(start.get("time_s"), path + ".starting.time_s", inclusive=True)
        if at is not None and type(sim.get("duration_s")) in (int,float) and at >= sim["duration_s"]: issue(path + ".starting.time_s", "start must precede simulation end")
        if at is not None and type(duration) in (int,float) and type(f) in (int,float) and f > 0 and duration-at < 2/f: issue(path + ".starting.time_s", "two complete post-start cycles required")
        if start.get("method") == "DOL":
            if start.get("controller") is not None: issue(path + ".starting.controller", "DOL requires controller=null")
        elif start.get("method") == "SCR":
            control = obj(start.get("controller"), path + ".starting.controller", {"rated_current_a", "maximum_current_pu", "resume_current_pu", "initial_voltage_pu", "ramp_up_s", "ramp_down_s", "current_filter_tau_s", "bypass_speed_fraction", "bypass_hold_s", "snubber_resistance_ohm", "snubber_capacitance_f", "reference_acknowledgement", "source_reference"})
            for key in set(control) - {"source_reference", "reference_acknowledgement"}: number(control[key], path + ".controller." + key)
            if control.get("reference_acknowledgement") != "MSL_REFERENCE_CONTROLLER_NOT_MANUFACTURER": issue(path + ".controller", "reference controller acknowledgement required")
            reference(control.get("source_reference"), path + ".controller.source_reference")
            if all(type(control.get(k)) in (int,float) for k in ("maximum_current_pu", "resume_current_pu")) and control["resume_current_pu"] >= control["maximum_current_pu"]: issue(path + ".controller", "resume current must be below maximum current")
            for k in ("initial_voltage_pu", "bypass_speed_fraction"):
                if type(control.get(k)) in (int,float) and not 0 < control[k] < 1: issue(path + ".controller." + k, "fraction between zero and one")
        else: issue(path + ".starting.method", "DOL/SCR only")
        criteria_fields = {"target_speed_fraction", "maximum_acceleration_time_s", "minimum_terminal_voltage_pu", "refinement_current_relative_tolerance", "refinement_speed_relative_tolerance", "refinement_time_absolute_tolerance_s", "source_reference"}
        if start.get("method") == "SCR":
            criteria_fields.update({"refinement_voltage_absolute_tolerance_pu", "refinement_torque_relative_tolerance", "refinement_bypass_time_absolute_tolerance_s"})
        criteria = obj(m.get("criteria"), path + ".criteria", criteria_fields)
        for key in set(criteria) - {"source_reference"}: number(criteria[key], path + ".criteria." + key)
        for key in ("target_speed_fraction", "minimum_terminal_voltage_pu"):
            if type(criteria.get(key)) in (int,float) and criteria[key] > 1: issue(path + ".criteria." + key, "fraction cannot exceed one")
        if type(criteria.get("maximum_acceleration_time_s")) in (int,float) and type(duration) in (int,float) and at is not None and criteria["maximum_acceleration_time_s"] > duration-at:
            issue(path + ".criteria.maximum_acceleration_time_s", "deadline must fit the post-start observation window")
        reference(criteria.get("source_reference"), path + ".criteria.source_reference")
    rt = runtime()
    qualification_blockers = []
    scr_motors = [m for m in motors if isinstance(m,dict) and isinstance(m.get("starting"),dict) and m["starting"].get("method") == "SCR"]
    if scr_motors and len(motors) != 1:
        qualification_blockers.append("MULTIMOTOR_SCR_NOT_QUALIFIED")
    if any(m.get("connection") != "delta" for m in scr_motors):
        qualification_blockers.append("SCR_WYE_CONNECTION_NOT_QUALIFIED")
    return {"schema": SCHEMA, "data_ready": not issues, "issues": issues, "runtime": rt,
            "qualification_blockers": qualification_blockers,
            "ready_for_execution": not issues and rt["ready"] and not qualification_blockers, "physical_solver_owned_by_mcp": False,
            "professional_emission": False}


def _n(value):
    return format(float(value), ".17g")


def _quote(path):
    return str(Path(path).as_posix()).replace("\\", "\\\\").replace('"', '\\"')


def build_model(package):
    net, sim = package["network"], package["simulation"]
    f, voltage = net["frequency_hz"], net["kv_ll"]*1000
    angle = net["angle_deg"]*pi/180
    phase = ",".join(_n(angle - 2*pi*k/3) for k in range(3))
    declarations = ["within;", "model MCPMSLMotorStudy",
        f"Modelica.Electrical.Polyphase.Sources.SineVoltage source(m=3,V=fill({_n(sqrt(2)*voltage/sqrt(3)*net['pu'])},3),f=fill({_n(f)},3),phase={{{phase}}});",
        "Modelica.Electrical.Polyphase.Basic.Star sourceStar(m=3);",
        "Modelica.Electrical.Analog.Basic.Ground ground;",
        f"Modelica.Electrical.Polyphase.Basic.Resistor supplyR(m=3,R=fill({_n(net['r_ohm'])},3),T_ref=fill(293.15,3),alpha=fill(0,3));",
        f"Modelica.Electrical.Polyphase.Basic.Inductor supplyL(m=3,L=fill({_n(net['x_ohm']/(2*pi*f))},3));"]
    equations = ["connect(source.plug_n,sourceStar.plug_p);", "connect(sourceStar.pin_n,ground.p);",
                 "connect(source.plug_p,supplyR.plug_p);", "connect(supplyR.plug_n,supplyL.plug_p);"]
    initial = []
    for idx, m in enumerate(package["motors"]):
        prefix = f"m{idx}"
        e, mech, start = m["electrical"], m["mechanical"], m["starting"]
        connection = "D" if m["connection"] == "delta" else "Y"
        table = ";".join(_n(p["speed_rad_s"])+","+_n(p["torque_nm"]) for p in mech["load_curve"])
        declarations += [
            f"Modelica.Electrical.Machines.BasicMachines.InductionMachines.IM_SquirrelCage {prefix}motor(p={e['pole_pairs']},fsNominal={_n(f)},Rs={_n(e['stator_resistance_ohm'])},Rr={_n(e['rotor_resistance_ohm'])},Lssigma={_n(e['stator_leakage_inductance_h'])},Lrsigma={_n(e['rotor_leakage_inductance_h'])},Lm={_n(e['magnetizing_inductance_h'])},Lszero={_n(e['zero_sequence_inductance_h'])},TsRef={_n(e['temperature_k'])},TrRef={_n(e['temperature_k'])},TsOperational={_n(e['temperature_k'])},TrOperational={_n(e['temperature_k'])},alpha20s=0,alpha20r=0,Jr={_n(mech['motor_inertia_kg_m2'])},Js={_n(mech['motor_inertia_kg_m2'])},useSupport=false,useThermalPort=false,frictionParameters(PRef=0),statorCoreParameters(PRef=0,VRef={_n(voltage)}),strayLoadParameters(PRef=0,IRef=1),phiMechanical(start=0,fixed=true),wMechanical(start=0,fixed=true));",
            f'Modelica.Electrical.Machines.Utilities.TerminalBox {prefix}terminal(terminalConnection="{connection}");',
            f"Modelica.Electrical.Polyphase.Sensors.CurrentSensor {prefix}lineSensor(m=3);",
            f"Modelica.Mechanics.Rotational.Components.Inertia {prefix}loadInertia(J={_n(mech['load_inertia_kg_m2'])});",
            f"Modelica.Mechanics.Rotational.Components.Fixed {prefix}fixed;",
            f"Modelica.Mechanics.Rotational.Components.Damper {prefix}damper(d={_n(mech['damping_nm_s_rad'])});",
            f"Modelica.Mechanics.Rotational.Sources.Torque {prefix}loadTorque;",
            f"Modelica.Blocks.Tables.CombiTable1Ds {prefix}loadCurve(table=[{table}],columns={{2}},smoothness=Modelica.Blocks.Types.Smoothness.LinearSegments,extrapolation=Modelica.Blocks.Types.Extrapolation.NoExtrapolation);",
            f"output Real {prefix}speed={prefix}motor.wMechanical;",
            f"output Real {prefix}torque={prefix}motor.tauElectrical;",
            f"output Real {prefix}ia={prefix}lineSensor.i[1];",
            f"output Real {prefix}ib={prefix}lineSensor.i[2];",
            f"output Real {prefix}ic={prefix}lineSensor.i[3];",
            f"output Real {prefix}vab={prefix}terminal.plugSupply.pin[1].v-{prefix}terminal.plugSupply.pin[2].v;",
            f"output Real {prefix}vbc={prefix}terminal.plugSupply.pin[2].v-{prefix}terminal.plugSupply.pin[3].v;",
            f"output Real {prefix}vca={prefix}terminal.plugSupply.pin[3].v-{prefix}terminal.plugSupply.pin[1].v;",
            f"output Real {prefix}busvab=supplyL.plug_n.pin[1].v-supplyL.plug_n.pin[2].v;",
            f"output Real {prefix}busvbc=supplyL.plug_n.pin[2].v-supplyL.plug_n.pin[3].v;",
            f"output Real {prefix}busvca=supplyL.plug_n.pin[3].v-supplyL.plug_n.pin[1].v;"]
        equations += [
            f"connect({prefix}lineSensor.plug_n,{prefix}terminal.plugSupply);",
            f"connect({prefix}terminal.plug_sp,{prefix}motor.plug_sp);",
            f"connect({prefix}terminal.plug_sn,{prefix}motor.plug_sn);",
            f"connect({prefix}motor.flange,{prefix}loadInertia.flange_a);",
            f"connect({prefix}loadInertia.flange_b,{prefix}loadTorque.flange);",
            f"connect({prefix}damper.flange_a,{prefix}motor.flange);",
            f"connect({prefix}damper.flange_b,{prefix}fixed.flange);",
            f"{prefix}loadCurve.u={prefix}speed;",
            f"{prefix}loadTorque.tau=-{prefix}loadCurve.y[1];"]
        initial += [f"{prefix}motor.is={{0,0,0}};", f"{prefix}motor.ir={{0,0}};"]
        if mech["anti_reverse"] == "MSL_ONE_WAY_CLUTCH":
            declarations += [f"Modelica.Mechanics.Rotational.Components.OneWayClutch {prefix}restStop(fn_max=1,f_normalized=0);"]
            equations += [f"connect({prefix}fixed.flange,{prefix}restStop.flange_a);", f"connect({prefix}restStop.flange_b,{prefix}motor.flange);"]
        if start["method"] == "DOL":
            declarations += [f"Modelica.Electrical.Analog.Ideal.IdealClosingSwitch {prefix}switch[3](each Ron=1e-6,each Goff=1e-5);"]
            equations += [f"connect(supplyL.plug_n.pin,{prefix}switch.p);",
                          f"for k in 1:3 loop {prefix}switch[k].control=time>={_n(start['time_s'])}; end for;",
                          f"connect({prefix}switch.n,{prefix}lineSensor.plug_p.pin);"]
            declarations += [f"output Boolean {prefix}bypass=false;", f"output Real {prefix}vRef=1;"]
        else:
            c = start["controller"]
            declarations += [
                f"Modelica.Electrical.PowerConverters.ACAC.PolyphaseTriac {prefix}triac(m=3,useHeatPort=false,triac(each Ron=1e-5,each Goff=1e-5,each Vknee=0));",
                f"Modelica.Electrical.Polyphase.Basic.Resistor {prefix}snubberR(m=3,R=fill({_n(c['snubber_resistance_ohm'])},3),alpha=fill(0,3));",
                f"Modelica.Electrical.Polyphase.Basic.Capacitor {prefix}snubberC(m=3,C=fill({_n(c['snubber_capacitance_f'])},3),v(each start=0,each fixed=true));",
                f"Modelica.Electrical.PowerConverters.ACDC.Control.Signal2mPulse {prefix}pulse(m=3,useConstantFiringAngle=false,useFilter=false,f={_n(f)});",
                f"Modelica.Electrical.Polyphase.Sensors.CurrentQuasiRMSSensor {prefix}currentSensor(m=3);",
                f"Modelica.Blocks.Continuous.FirstOrder {prefix}filter(T={_n(c['current_filter_tau_s'])},initType=Modelica.Blocks.Types.Init.InitialOutput,y_start=0);",
                f"Modelica.Electrical.PowerConverters.ACAC.Control.SoftStartControl {prefix}controller(tRampUp={_n(c['ramp_up_s'])},vStart={_n(c['initial_voltage_pu'])},iMax={_n(c['maximum_current_pu'])},iMin={_n(c['resume_current_pu'])},INominal={_n(c['rated_current_a'])},tRampDown={_n(c['ramp_down_s'])},vRef(start=0,fixed=true));",
                f"Modelica.Electrical.PowerConverters.ACAC.Control.VoltageToAngle {prefix}angle(VNominal=1,voltage2Angle=Modelica.Electrical.PowerConverters.Types.Voltage2AngleType.H01);",
                f"Modelica.Blocks.MathBoolean.OnDelay {prefix}bypassDelay(delayTime={_n(c['bypass_hold_s'])});",
                f"Modelica.Electrical.Analog.Ideal.IdealClosingSwitch {prefix}bypassSwitch[3](each Ron=1e-6,each Goff=1e-5);",
                f"output Boolean {prefix}bypass(start=false,fixed=true);",
                f"output Real {prefix}vRef={prefix}controller.vRef;"]
            equations += [
                f"connect(supplyL.plug_n,{prefix}triac.plug_p);",
                f"connect({prefix}triac.plug_p,{prefix}snubberR.plug_p);",
                f"connect({prefix}snubberR.plug_n,{prefix}snubberC.plug_p);",
                f"connect({prefix}snubberC.plug_n,{prefix}triac.plug_n);",
                f"connect({prefix}triac.plug_n,{prefix}currentSensor.plug_p);",
                f"connect({prefix}currentSensor.plug_n,{prefix}lineSensor.plug_p);",
                f"{prefix}filter.u={prefix}currentSensor.I;",
                f"{prefix}controller.iRMS={prefix}filter.y;",
                f"{prefix}controller.start=time>={_n(start['time_s'])};",
                f"{prefix}angle.vRef={prefix}controller.vRef;",
                f"{prefix}pulse.firingAngle={prefix}angle.firingAngle;",
                f"{prefix}pulse.v=source.v;",
                f"connect({prefix}pulse.fire_p,{prefix}triac.fire1);",
                f"connect({prefix}pulse.fire_n,{prefix}triac.fire2);",
                f"connect({prefix}bypassSwitch.p,{prefix}triac.plug_p.pin);",
                f"connect({prefix}bypassSwitch.n,{prefix}triac.plug_n.pin);",
                f"{prefix}bypassDelay.u=({prefix}vRef>=1-1e-8 and {prefix}speed>={_n(c['bypass_speed_fraction']*2*pi*f/e['pole_pairs'])});",
                f"when {prefix}bypassDelay.y then {prefix}bypass=true; end when;",
                f"for k in 1:3 loop {prefix}bypassSwitch[k].control={prefix}bypass; end for;"]
    return "\n".join(declarations + ["initial equation"] + initial + ["equation"] + equations + ["end MCPMSLMotorStudy;", ""])


def _run(command, folder, env, timeout):
    process = subprocess.run(command, cwd=folder, env=env, capture_output=True, text=True,
                             stdin=subprocess.DEVNULL, encoding="utf8", errors="replace", timeout=timeout)
    return {"command": command, "returncode": process.returncode, "stdout": process.stdout, "stderr": process.stderr}


def _summaries(csv_path, package):
    # Cycle RMS/mean and threshold interpolation are result processing, not physics.
    import numpy as np
    with Path(csv_path).open(encoding="utf8") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
    if not rows or len(rows) > 2_600_000: raise ValueError("MODELICA_TRACE_SIZE")
    times = np.array([float(row["time"]) for row in rows])
    if not np.isfinite(times).all() or np.any(np.diff(times)<0): raise ValueError("MODELICA_TRACE_TIME")
    if times[0] > 1e-9 or abs(times[-1]-package['simulation']['duration_s']) > 1e-8:
        raise ValueError("MODELICA_TRACE_INCOMPLETE_OBSERVATION")
    # Event duplicates keep the final state at that instant.
    event_times = times
    keep = np.r_[times[1:] != times[:-1], True]
    times = times[keep]
    results = []
    f, voltage = package["network"]["frequency_hz"], package["network"]["kv_ll"]*1000
    for index, m in enumerate(package["motors"]):
        prefix = f"m{index}"
        def values(name, with_events=False):
            result = np.array([float(row[prefix+name]) for row in rows])
            if not np.isfinite(result).all(): raise ValueError("MODELICA_TRACE_NONFINITE")
            return result if with_events else result[keep]
        speed, torque = values("speed"), values("torque")
        currents = [values(n, True) for n in ("ia", "ib", "ic")]
        voltages = [values(n, True) for n in ("vab", "vbc", "vca")]
        bus_voltages = [values(n, True) for n in ("busvab", "busvbc", "busvca")]
        vref = values("vRef")
        trajectory = []
        start = m["starting"]["time_s"]
        cycles = int((times[-1]-start)*f + 1e-8)
        boundaries = start + np.arange(cycles+1)/f
        def cycle_integrals(arr, squared=False):
            # Read both left/right event states. Zero-width discontinuities have
            # zero area; do not smear SCR switching over an arbitrary RMS grid.
            delta=np.diff(event_times)
            area=delta*((arr[:-1]**2+arr[:-1]*arr[1:]+arr[1:]**2)/3 if squared else (arr[:-1]+arr[1:])/2)
            cumulative=np.r_[0,np.cumsum(area)]
            k=np.clip(np.searchsorted(event_times,boundaries,side='right')-1,0,len(arr)-2)
            dx=boundaries-event_times[k]
            slope=np.divide(arr[k+1]-arr[k],delta[k],out=np.zeros_like(dx),where=delta[k]>0)
            local=(arr[k]**2*dx+arr[k]*slope*dx**2+slope**2*dx**3/3) if squared else (arr[k]*dx+slope*dx**2/2)
            primitive=cumulative[k]+local
            primitive[boundaries>=event_times[-1]]=cumulative[-1]
            return np.diff(primitive)*f
        rms_currents=[np.sqrt(np.maximum(cycle_integrals(arr,True),0)) for arr in currents]
        rms_voltages=[np.sqrt(np.maximum(cycle_integrals(arr,True),0)) for arr in voltages]
        rms_buses=[np.sqrt(np.maximum(cycle_integrals(arr,True),0)) for arr in bus_voltages]
        mean_torque=cycle_integrals(values('torque',True))
        for cycle in range(cycles):
            left, right = start+cycle/f, start+(cycle+1)/f
            rms_i = [float(arr[cycle]) for arr in rms_currents]
            rms_v = [float(arr[cycle]) for arr in rms_voltages]
            rms_bus = [float(arr[cycle]) for arr in rms_buses]
            trajectory.append({"time_s": right, "speed_rad_s": float(np.interp(right,times,speed)),
                               "current_a": max(rms_i), "phase_currents_rms_a": rms_i,
                               "torque_nm": float(mean_torque[cycle]),
                               "voltage_pu": min(rms_v)/voltage, "line_voltages_rms_v": rms_v,
                               "bus_voltage_pu": min(rms_bus)/voltage, "controller_voltage_reference_pu": float(np.interp(right,times,vref))})
        target = m["criteria"]["target_speed_fraction"]*2*pi*f/m["electrical"]["pole_pairs"]
        crossing = None
        found = np.flatnonzero((times >= start) & (speed >= target))
        if len(found):
            k = int(found[0])
            crossing = float(times[k] if k == 0 else times[k-1]+(target-speed[k-1])*(times[k]-times[k-1])/(speed[k]-speed[k-1]))-start
        bypass = values("bypass")
        bypass_times = times[bypass > 0.5]
        minimum = min((r["voltage_pu"] for r in trajectory), default=None)
        criteria = m["criteria"]
        results.append({"motor_id": m["id"], "starting_method": m["starting"]["method"],
                        "acceleration_time_s": crossing, "minimum_voltage_pu": minimum,
                        "maximum_cycle_rms_current_a": max((r["current_a"] for r in trajectory), default=None),
                        "minimum_bus_voltage_pu": min((r["bus_voltage_pu"] for r in trajectory), default=None),
                        "maximum_current_pu": max((r["current_a"] for r in trajectory), default=0)/m['starting']['controller']['rated_current_a'] if m['starting']['method']=='SCR' else None,
                        "bypass_time_s": float(bypass_times[0]) if len(bypass_times) else None,
                        "criterion": {"passed": crossing is not None and crossing <= criteria["maximum_acceleration_time_s"] and minimum is not None and minimum >= criteria["minimum_terminal_voltage_pu"], "source_reference": criteria["source_reference"]},
                        "trajectory": trajectory})
    return results


def execute(package, directory):
    ready = validate(package)
    if not ready["ready_for_execution"]:
        return {"status": "BLOCKED_MODELICA_READINESS", "readiness": ready, "results": [], "professional_emission": False}
    output = Path(directory).expanduser().resolve()
    try:
        output.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        return {"status": "BLOCKED_MODELICA_OUTPUT", "message": str(exc), "results": [], "professional_emission": False}
    rt, sim = ready["runtime"], package["simulation"]
    compiler, library = rt["executable"], Path(rt["library"])
    source = output / "MCPMSLMotorStudy.mo"
    source.write_text(build_model(package), encoding="utf8")
    (output / "Inputs.json").write_text(json.dumps(package, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf8")
    loader = "\n".join(f'loadFile("{_quote(library/f)}");' for f in ("ModelicaServices/package.mo", "Complex.mo", "Modelica/package.mo"))
    mos = output / "run.mos"
    mos.write_text(loader + f'\nloadFile("{_quote(source)}");\ngetErrorString();\nbuildModel(MCPMSLMotorStudy,stopTime={_n(sim["duration_s"])},numberOfIntervals={int(round(sim["duration_s"]/sim["output_step_s"]))},tolerance={_n(sim["solver_tolerance"])},outputFormat="csv",fileNamePrefix="MotorStudy",variableFilter="time|m[0-9]+(speed|torque|ia|ib|ic|vab|vbc|vca|busvab|busvbc|busvca|bypass|vRef)");\ngetErrorString();\n', encoding="utf8")
    env = _environment(compiler)
    # Isolate compiler bookkeeping from the user's application settings.
    env["APPDATA"] = str(output)
    env["MODELICAPATH"] = str(library)
    records = []
    try:
        record = _run([compiler, str(mos)], output, env, sim["timeout_s"])
        records.append(record)
        executable = output / ("MotorStudy.exe" if platform.system() == "Windows" else "MotorStudy")
        if record["returncode"] or not executable.is_file(): raise RuntimeError("Modelica compilation failed")
        summary_runs = []
        for refined in (False, True):
            file = output / ("Refined.csv" if refined else "Nominal.csv")
            tol = sim["solver_tolerance"]/(10 if refined else 1)
            step = sim["maximum_internal_step_s"]/(2 if refined else 1)
            command = [str(executable), "-r="+str(file), f"-tolerance={_n(tol)}", f"-maxStepSize={_n(step)}",
                       f"-stepSize={_n(sim['output_step_s']/(2 if refined else 1))}"]
            if any(m['starting']['method']=='SCR' for m in package['motors']):
                # Explicit compiler-runtime configuration, not a substitute physics model.
                command += ['-s=dassl', '-nls=newton']
            record = _run(command, output, env, sim["timeout_s"])
            records.append(record)
            if record["returncode"] or "The simulation finished successfully." not in record["stdout"] or not file.is_file(): raise RuntimeError("Modelica simulation failed")
            summary_runs.append(_summaries(file, package))
        results = summary_runs[1]
        for nominal, refined, m in zip(summary_runs[0], results, package["motors"]):
            a, b = nominal["trajectory"], refined["trajectory"]
            if not a or len(a) != len(b): raise ValueError("MODELICA_REFINEMENT_TRACE_MISMATCH")
            current_error = max(abs(x["current_a"]-y["current_a"]) for x,y in zip(a,b))/max(refined["maximum_cycle_rms_current_a"],1e-12)
            speed_error = max(abs(x["speed_rad_s"]-y["speed_rad_s"]) for x,y in zip(a,b))/(2*pi*package["network"]["frequency_hz"]/m["electrical"]["pole_pairs"])
            n_time, r_time = nominal["acceleration_time_s"], refined["acceleration_time_s"]
            time_error = abs(n_time-r_time) if n_time is not None and r_time is not None else (0 if n_time is r_time else None)
            c = m["criteria"]
            refined["verification"] = {"current_relative_error": current_error, "speed_relative_error": speed_error, "acceleration_time_error_s": time_error,
                                       "passed": current_error <= c["refinement_current_relative_tolerance"] and speed_error <= c["refinement_speed_relative_tolerance"] and time_error is not None and time_error <= c["refinement_time_absolute_tolerance_s"]}
            if m['starting']['method']=='SCR':
                voltage_error = max(abs(x['voltage_pu']-y['voltage_pu']) for x,y in zip(a,b))
                bus_error = max(abs(x['bus_voltage_pu']-y['bus_voltage_pu']) for x,y in zip(a,b))
                torque_error = max(abs(x['torque_nm']-y['torque_nm']) for x,y in zip(a,b))/max(max(abs(x['torque_nm']) for x in b),1e-12)
                n_bypass,r_bypass=nominal['bypass_time_s'],refined['bypass_time_s']
                bypass_error=abs(n_bypass-r_bypass) if n_bypass is not None and r_bypass is not None else (0 if n_bypass is r_bypass else None)
                extra_passed = (max(voltage_error,bus_error) <= c['refinement_voltage_absolute_tolerance_pu'] and torque_error <= c['refinement_torque_relative_tolerance'] and bypass_error is not None and bypass_error <= c['refinement_bypass_time_absolute_tolerance_s'])
                refined['verification'].update({'terminal_voltage_absolute_error_pu':voltage_error,'bus_voltage_absolute_error_pu':bus_error,'torque_relative_error':torque_error,'bypass_time_error_s':bypass_error,'passed':refined['verification']['passed'] and extra_passed})
        passed = all(r["verification"]["passed"] for r in results)
        result = {"status": "MODELICA_MOTOR_STUDIES_COMPLETED" if passed else "MODELICA_REFINEMENT_NOT_PASSED",
                  "backend": BACKEND, "contract": contract(), "results": results,
                  "library_modified_by_adapter": False, "physical_solver_owned_by_mcp": False,
                  "runtime": rt, "output_directory": str(output), "professional_emission": False}
    except (RuntimeError, subprocess.TimeoutExpired, OSError, ValueError, KeyError, TypeError) as exc:
        result = {"status": "MODELICA_EXECUTION_FAILED", "message": str(exc), "results": [], "professional_emission": False}
    (output / "Execution.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf8")
    components = ["Modelica/Electrical/Machines/BasicMachines/InductionMachines/IM_SquirrelCage.mo",
                  "Modelica/Electrical/PowerConverters/ACAC/Control/SoftStartControl.mo",
                  "Modelica/Electrical/PowerConverters/ACAC/PolyphaseTriac.mo"]
    result["library_source_sha256"] = {f: _digest(library/f) for f in components}
    result["files_sha256"] = {p.name: _digest(p) for p in output.iterdir() if p.is_file() and p.suffix in {".json", ".mo", ".mos", ".csv"}}
    (output / "Results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf8")
    return result
