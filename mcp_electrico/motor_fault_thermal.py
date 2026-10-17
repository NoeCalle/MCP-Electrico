"""Terminal fault of one MSL induction motor at explicitly imposed shaft speed.

OpenModelica owns all machine physics. Python only configures components and
integrates emitted line-current samples. This is NOT an IEC60909 replacement.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from math import isfinite, pi, sqrt
from pathlib import Path

from . import modelica_motor_adapter as runtime_adapter

SCHEMA = "MCP_ELECTRICO_MOTOR_TERMINAL_FAULT_EMT_V1"
FIELDS = {
    "schema", "id", "source_reference", "kv_ll", "frequency_hz", "angle_deg",
    "shaft_speed_rad_s", "fault_time_s", "end_time_s", "switch_resistance_ohm",
    "output_step_s", "maximum_internal_step_s", "solver_tolerance", "timeout_s",
    "machine", "verification_relative_tolerance",
}
MACHINE_FIELDS = {
    "pole_pairs", "stator_resistance_ohm", "rotor_resistance_ohm",
    "stator_leakage_inductance_h", "rotor_leakage_inductance_h",
    "magnetizing_inductance_h", "zero_sequence_inductance_h",
    "rotor_inertia_kg_m2", "temperature_k", "source_reference",
}


CONFIG = Path(__file__).resolve().parents[1] / "local_data" / "modelica-fault-runtime.json"
_configuration = None


def supported_compiler_version(text):
    return text.strip() in {"OpenModelica 1.27.1", "OpenModelica v1.27.1", "OpenModelica v1.27.1 (64-bit)"}


def configure(executable, library):
    """Record the real compiler version, including Linux's release spelling."""
    global _configuration
    compiler, msl = Path(executable).expanduser().resolve(), Path(library).expanduser().resolve()
    if compiler.name.lower() not in {"omc", "omc.exe"} or not compiler.is_file():
        raise ValueError("MOTOR_FAULT_RUNTIME: installed omc executable required")
    required = ("Modelica/package.mo", "Complex.mo", "ModelicaServices/package.mo")
    if any(not (msl/p).is_file() for p in required) or 'version="4.0.0"' not in (msl/required[0]).read_text(encoding="utf8"):
        raise ValueError("MOTOR_FAULT_LIBRARY: unmodified Modelica 4.0.0 with dependencies required")
    result = subprocess.run([str(compiler), "--version"], capture_output=True, text=True,
                            stdin=subprocess.DEVNULL, env=runtime_adapter._environment(compiler),
                            timeout=60, check=True)
    version = result.stdout.strip()
    if not supported_compiler_version(version):
        raise ValueError("MOTOR_FAULT_COMPILER_VERSION: expected release 1.27.1; actual=" + version)
    _configuration = {"executable": str(compiler), "library": str(msl), "compiler_version": version,
                      "compiler_sha256": runtime_adapter._digest(compiler),
                      "library_tree_sha256": runtime_adapter._library_digest(msl)}
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(_configuration, indent=2), encoding="utf8")
    return dict(_configuration)


def runtime():
    global _configuration
    if _configuration is None and not CONFIG.is_file():
        return runtime_adapter.runtime()
    try:
        if _configuration is None:
            _configuration = json.loads(CONFIG.read_text(encoding="utf8"))
        if (not supported_compiler_version(_configuration["compiler_version"])
            or runtime_adapter._digest(_configuration["executable"]) != _configuration["compiler_sha256"]
            or runtime_adapter._library_digest(Path(_configuration["library"])) != _configuration["library_tree_sha256"]):
            return {"ready": False, "reason": "Fault runtime changed; configure again"}
        return {"ready": True, **_configuration}
    except (OSError, KeyError, TypeError, ValueError):
        return {"ready": False, "reason": "Fault runtime unavailable"}



def contract():
    return {"schema": SCHEMA, "engine": "OpenModelica 1.27.1 / MSL 4.0.0",
            "scope": "ONE_WYE_INDUCTION_MOTOR_IMPOSED_SHAFT_SPEED_TERMINAL_3PH_FAULT",
            "event": "DISCONNECT_IDEAL_SUPPLY_AND_SHORT_ALL_TERMINALS_THROUGH_EXPLICIT_RESISTANCE",
            "time_window": "FAULT_INCEPTION_TO_DECLARED_END; NOT_A_COMPUTED_CLEARING_TIME",
            "current": "INSTANTANEOUS_TERMINAL_LINE_CURRENT_PER_PHASE_INCLUDING_DC",
            "thermal": "PER_PHASE_JOULE_INTEGRAL_AND_RMS_OVER_DECLARED_WINDOW",
            "initialization": "ZERO_STATOR_AND_ROTOR_CURRENT; IMPOSED_SPEED_FROM_T_ZERO",
            "losses": "FIXED_COPPER_RESISTANCES; NO_CORE_STRAY_FRICTION_OR_THERMAL_EVOLUTION",
            "excluded": ["arbitrary_network", "free_shaft_deceleration", "delta", "multiple_motors",
                         "generator", "VFD", "relay_operation", "automatic_IEC60909_Ith_promotion"],
            "physical_solver_owned_by_mcp": False, "iec60909_conformance_claim": False,
            "installation_validation_closed": False, "professional_emission": False}


def validate(package):
    issues = []
    def issue(path, message):
        issues.append({"path": path, "message": message})
    def obj(value, path, fields):
        if not isinstance(value, dict):
            issue(path, "object required"); return {}
        if set(value) != fields:
            issue(path, "all and only explicit contract fields required")
        return value
    def numeric(value, path, low=0, inclusive=False):
        if type(value) not in (int, float) or not isfinite(value) or (value < low if inclusive else value <= low):
            issue(path, "finite explicit number outside supported range")
            return False
        return True
    root = obj(package, "study", FIELDS)
    if root.get("schema") != SCHEMA:
        issue("schema", SCHEMA + " required")
    for key in ("id", "source_reference"):
        if not isinstance(root.get(key), str) or not root[key].strip():
            issue(key, "nonempty reference required")
    positive = FIELDS - {"schema", "id", "source_reference", "machine", "angle_deg", "shaft_speed_rad_s"}
    for key in positive:
        numeric(root.get(key), key)
    numeric(root.get("angle_deg"), "angle_deg", -float("inf"))
    numeric(root.get("shaft_speed_rad_s"), "shaft_speed_rad_s", inclusive=True)
    machine = obj(root.get("machine"), "machine", MACHINE_FIELDS)
    for key in MACHINE_FIELDS - {"source_reference"}:
        numeric(machine.get(key), "machine." + key)
    if type(machine.get("pole_pairs")) is not int:
        issue("machine.pole_pairs", "positive integer required")
    if not isinstance(machine.get("source_reference"), str) or not machine["source_reference"].strip():
        issue("machine.source_reference", "machine data provenance required")
    if not issues:
        f, dt, start, end = (root[k] for k in ("frequency_hz", "output_step_s", "fault_time_s", "end_time_s"))
        if f not in (50, 60): issue("frequency_hz", "50 or 60 Hz qualified inputs only")
        if not start < end <= 10: issue("end_time_s", "fault time < end <= 10 s")
        if min(start, end-start) < 2/f: issue("fault_time_s", "two complete pre/post cycles required")
        if dt > 1/(500*f): issue("output_step_s", "at least 500 samples per cycle")
        if end/dt > 500_000: issue("output_step_s", "sample budget exceeded")
        if root["maximum_internal_step_s"] > dt: issue("maximum_internal_step_s", "must not exceed output step")
        if not 1e-12 <= root["solver_tolerance"] <= 1e-6: issue("solver_tolerance", "range 1e-12 to 1e-6")
        if not 0 < root["verification_relative_tolerance"] <= .005: issue("verification_relative_tolerance", "at most 0.5 percent")
        if root["timeout_s"] > 600: issue("timeout_s", "at most 600 s per process")
        if not 1e-8 <= root["switch_resistance_ohm"] <= 1: issue("switch_resistance_ohm", "explicit finite contact/fault resistance between 1e-8 and 1 ohm")
        if root["shaft_speed_rad_s"] > 2*pi*f/machine["pole_pairs"]:
            issue("shaft_speed_rad_s", "motoring range through synchronous speed only")
    rt = runtime()
    return {"data_ready": not issues, "issues": issues, "runtime": rt,
            "ready_for_execution": not issues and rt["ready"], "contract": contract()}


def build_model(p):
    n = runtime_adapter._n
    m = p["machine"]
    machine_map = {"p": "pole_pairs", "Rs": "stator_resistance_ohm", "Rr": "rotor_resistance_ohm",
                   "Lssigma": "stator_leakage_inductance_h", "Lrsigma": "rotor_leakage_inductance_h",
                   "Lm": "magnetizing_inductance_h", "Lszero": "zero_sequence_inductance_h",
                   "Jr": "rotor_inertia_kg_m2", "Js": "rotor_inertia_kg_m2"}
    settings = ",".join(f"{key}={n(m[value])}" for key, value in machine_map.items())
    settings += "," + ",".join(f"{key}={n(m['temperature_k'])}" for key in ("TsRef", "TrRef", "TsOperational", "TrOperational"))
    angles = ",".join(n(p["angle_deg"]*pi/180 - k*2*pi/3) for k in range(3))
    return f'''within;
model MCPMotorTerminalFault
  Modelica.Electrical.Machines.BasicMachines.InductionMachines.IM_SquirrelCage motor(
    {settings},fsNominal={n(p['frequency_hz'])},alpha20s=0,alpha20r=0,
    useSupport=false,useThermalPort=false,frictionParameters(PRef=0),
    statorCoreParameters(PRef=0,VRef={n(p['kv_ll']*1000)}),strayLoadParameters(PRef=0,IRef=1),
    phiMechanical(start=0,fixed=true));
  Modelica.Electrical.Machines.Utilities.TerminalBox terminal(terminalConnection="Y");
  Modelica.Electrical.Polyphase.Sources.SineVoltage supply(m=3,
    V=fill({n(sqrt(2/3)*p['kv_ll']*1000)},3),f=fill({n(p['frequency_hz'])},3),phase={{{angles}}});
  Modelica.Electrical.Polyphase.Basic.Star supplyStar(m=3);
  Modelica.Electrical.Analog.Basic.Ground ground;
  Modelica.Electrical.Polyphase.Sensors.CurrentSensor sensor(m=3);
  Modelica.Electrical.Analog.Ideal.IdealClosingSwitch feed[3](each Ron={n(p['switch_resistance_ohm'])},each Goff=0);
  Modelica.Electrical.Analog.Ideal.IdealClosingSwitch fault[3](each Ron={n(p['switch_resistance_ohm'])},each Goff=0);
  Modelica.Mechanics.Rotational.Sources.Speed drive(exact=true,useSupport=false,phi(fixed=false));
  Modelica.Blocks.Continuous.Integrator energy[3](each y_start=0,each initType=Modelica.Blocks.Types.Init.InitialState);
  output Real ia=sensor.i[1];
  output Real ib=sensor.i[2];
  output Real ic=sensor.i[3];
  output Real qa=energy[1].y;
  output Real qb=energy[2].y;
  output Real qc=energy[3].y;
  output Real speed=motor.wMechanical;
initial equation
  motor.is=zeros(3);
  motor.ir=zeros(2);
equation
  connect(supply.plug_n,supplyStar.plug_p);
  connect(supplyStar.pin_n,ground.p);
  connect(supply.plug_p.pin,feed.p);
  connect(feed.n,sensor.plug_p.pin);
  connect(sensor.plug_p.pin,fault.p);
  connect(sensor.plug_n,terminal.plugSupply);
  connect(terminal.plug_sp,motor.plug_sp);
  connect(terminal.plug_sn,motor.plug_sn);
  connect(motor.flange,drive.flange);
  drive.w_ref={n(p['shaft_speed_rad_s'])};
  for k in 1:3 loop
    connect(fault[k].n,ground.p);
    feed[k].control=time<{n(p['fault_time_s'])};
    fault[k].control=time>={n(p['fault_time_s'])};
    energy[k].u=if time>={n(p['fault_time_s'])} then sensor.i[k]^2 else 0;
  end for;
end MCPMotorTerminalFault;
'''


def summarize_trace(path, package, step):
    rows = []
    with Path(path).open(encoding="utf8") as stream:
        reader = csv.DictReader(stream)
        if not {"time", "ia", "ib", "ic", "qa", "qb", "qc", "speed"} <= set(reader.fieldnames or []):
            raise ValueError("MOTOR_FAULT_TRACE_COLUMNS")
        for raw in reader:
            row = {key: float(raw[key]) for key in ("time", "ia", "ib", "ic", "qa", "qb", "qc", "speed")}
            if not all(isfinite(v) for v in row.values()): raise ValueError("MOTOR_FAULT_NONFINITE_TRACE")
            if rows and row["time"] < rows[-1]["time"]: raise ValueError("MOTOR_FAULT_UNORDERED_TRACE")
            if rows and row["time"] == rows[-1]["time"]: rows[-1] = row
            else: rows.append(row)
    start, end = package["fault_time_s"], package["end_time_s"]
    if len(rows) < 3 or rows[0]["time"] > 1e-10 or abs(rows[-1]["time"]-end) > 1e-8:
        raise ValueError("MOTOR_FAULT_INCOMPLETE_TRACE")
    energy = [0., 0., 0.]
    for a, b in zip(rows, rows[1:]):
        dt = b["time"]-a["time"]
        if dt > step*1.6: raise ValueError("MOTOR_FAULT_TRACE_GAP")
        lo, hi = max(start, a["time"]), min(end, b["time"])
        if hi <= lo: continue
        for index, key in enumerate(("ia", "ib", "ic")):
            x = a[key]+(b[key]-a[key])*(lo-a["time"])/dt
            y = a[key]+(b[key]-a[key])*(hi-a["time"])/dt
            energy[index] += (hi-lo)*(x*x+x*y+y*y)/3
    if not all(isfinite(e) and e >= 0 for e in energy): raise ValueError("MOTOR_FAULT_INVALID_ENERGY")
    q = [rows[-1][key] for key in ("qa", "qb", "qc")]
    errors = [abs(a-b)/max(abs(b), 1e-12) for a,b in zip(energy, q)]
    speed_error = max(abs(r["speed"]-package["shaft_speed_rad_s"]) for r in rows)
    return {"joule_integral_a2s_by_phase": energy,
            "equivalent_rms_a_by_phase": [sqrt(e/(end-start)) for e in energy],
            "maximum_phase_equivalent_rms_a": sqrt(max(energy)/(end-start)),
            "native_msl_integral_a2s_by_phase": q,
            "integral_crosscheck_relative_errors": errors,
            "imposed_speed_maximum_error_rad_s": speed_error,
            "sample_count": len(rows), "trace_complete": True}


def execute(package, directory):
    ready = validate(package)
    if not ready["ready_for_execution"]:
        return {"status": "BLOCKED_MOTOR_FAULT_READINESS", "readiness": ready, "results": None}
    output = Path(directory).expanduser().resolve()
    try:
        output.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        return {"status": "BLOCKED_MOTOR_FAULT_OUTPUT", "message": str(exc), "results": None}
    rt = ready["runtime"]
    library = Path(rt["library"])
    source = output/"MCPMotorTerminalFault.mo"
    source.write_text(build_model(package), encoding="utf8")
    inputs = json.dumps(package, sort_keys=True, ensure_ascii=False, allow_nan=False)
    (output/"Inputs.json").write_text(inputs, encoding="utf8")
    loader = "\n".join(f'loadFile("{runtime_adapter._quote(library/f)}");' for f in ("ModelicaServices/package.mo", "Complex.mo", "Modelica/package.mo"))
    mos = output/"run.mos"
    mos.write_text(loader+f'\nloadFile("{runtime_adapter._quote(source)}");\ngetErrorString();\nbuildModel(MCPMotorTerminalFault,stopTime={package["end_time_s"]},numberOfIntervals={round(package["end_time_s"]/package["output_step_s"])},tolerance={package["solver_tolerance"]},outputFormat="csv",fileNamePrefix="MotorFault",variableFilter="time|ia|ib|ic|qa|qb|qc|speed");\ngetErrorString();', encoding="utf8")
    env = runtime_adapter._environment(rt["executable"])
    env.update(APPDATA=str(output), MODELICAPATH=str(library))
    records = []
    try:
        def run(command):
            record = runtime_adapter._run(command, output, env, package["timeout_s"])
            records.append(record)
            if record["returncode"] != 0: raise RuntimeError("OpenModelica execution failed")
            return record
        run([rt["executable"], str(mos)])
        import os
        binary = output/("MotorFault.exe" if os.name == "nt" else "MotorFault")
        if not binary.is_file(): raise RuntimeError("OpenModelica compilation failed")
        summaries = []
        for name, divisor in (("Nominal", 1), ("Refined", 2)):
            trace = output/(name+".csv")
            step = package["output_step_s"]/divisor
            record = run([str(binary), "-s=dassl", "-r="+str(trace),
                          "-stepSize="+str(step), "-maxStepSize="+str(package["maximum_internal_step_s"]/divisor),
                          "-tolerance="+str(package["solver_tolerance"]/(10 if divisor == 2 else 1))])
            if "The simulation finished successfully." not in record["stdout"]:
                raise RuntimeError("Simulation not completed")
            summaries.append(summarize_trace(trace, package, step))
        a, b = [s["joule_integral_a2s_by_phase"] for s in summaries]
        errors = [abs(x-y)/max(abs(y), 1e-12) for x,y in zip(a,b)]
        checks = errors + [e for s in summaries for e in s["integral_crosscheck_relative_errors"]]
        passed = max(checks) <= package["verification_relative_tolerance"] and all(s["imposed_speed_maximum_error_rad_s"] <= 1e-7 for s in summaries)
        result = {"status": "MOTOR_FAULT_EMT_VERIFIED" if passed else "MOTOR_FAULT_EMT_NOT_CONVERGED",
                  "results": summaries[1] if passed else None,
                  "verification": {"passed": passed, "energy_refinement_relative_errors": errors,
                                   "nominal": summaries[0], "refined": summaries[1]},
                  "runtime": rt}
    except (RuntimeError, OSError, ValueError, KeyError, TypeError) as exc:
        tail = ((records[-1].get("stdout", "") + records[-1].get("stderr", ""))[-8192:] if records else "")
        result = {"status": "MOTOR_FAULT_EMT_EXECUTION_FAILED", "message": str(exc),
                  "engine_diagnostic_tail": tail, "results": None}
    (output/"Execution.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf8")
    result.update(contract=contract(), input_sha256=hashlib.sha256(inputs.encode()).hexdigest(),
                  output_directory=str(output), results_are_iec60909_ith=False,
                  computed_clearing_time_s=None, electrical_design_assessed=False)
    result["files_sha256"] = {p.name: runtime_adapter._digest(p) for p in output.iterdir() if p.suffix in (".mo", ".mos", ".csv", ".json") and p.is_file()}
    (output/"Results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf8")
    return result
