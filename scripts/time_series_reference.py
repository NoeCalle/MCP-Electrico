"""Independent balanced two-bus PQ/Z reference, without importing the adapter."""
from math import sqrt


def reference_package(mode="daily", frequency=60, model=1, step_hours=1, days=1):
    ref = "SYNTHETIC_INDEPENDENT_TWO_BUS_TIME_SERIES_REFERENCE"
    n = round(24/step_hours)
    count = n if mode == "daily" else n*days
    p = [(.2, .8, .4, 1.1, 0, .6)[i % 6] for i in range(count)]
    q = [(.7, .1, .9, .3, 0, .8)[i % 6] for i in range(count)]
    return {
        "schema": "MCP_ELECTRICO_TIME_SERIES_V1", "id": "TS-REF-01", "source_reference": ref,
        "base_model": {"project": {"id": "TS_REF", "name": "Independent PQ/Z test", "source_reference": ref},
            "source": {"bus": "supply", "kv_ll": .48, "frequency_hz": frequency, "pu": 1,
                       "angle_deg": 0, "scc_max_mva": 10, "x_r_max": 10, "source_reference": ref},
            "topology": {"buses": ["supply", "loadbus"], "transformers": [],
                "lines": [{"id": "Line.feeder", "bus1": "supply", "bus2": "loadbus", "phases": 3,
                           "length_km": 1, "r1_ohm_km": .03, "x1_ohm_km": .04, "c1_nf_km": 0,
                           "normamps_a": 500, "source_reference": ref}],
                "loads": [{"id": "Load.test", "bus": "loadbus", "phases": 3, "kv": .48,
                           "kw": 100, "kvar": 50, "connection": "wye", "model": model,
                           "vminpu": .5, "vmaxpu": 1.5, "source_reference": ref}]}},
        "timeline": {"mode": mode, "start_hour": 0, "step_hours": step_hours, "steps": n*days,
                     "repeat_daily_profile": mode == "daily" and days > 1,
                     "energy_integration": "RECTANGULAR_INTERVAL_END", "source_reference": ref},
        "load_profiles": [{"load_id": "Load.test", "p_multipliers": p, "q_multipliers": q, "source_reference": ref}],
        "criteria": {"voltage_min_pu": .9, "voltage_max_pu": 1.1, "maximum_line_loading_pct": 100,
                     "maximum_transformer_loading_pct": 100, "source_reference": "ILLUSTRATIVE_PROJECT_CRITERIA"},
        "options": {"solver_tolerance": 1e-10, "max_iterations": 100,
                    "active_balance_tolerance_kw": 1e-5, "reactive_balance_tolerance_kvar": 1e-5}}


def analytical(p_multiplier, q_multiplier, model):
    source_r = .48**2/10/sqrt(101)
    source_z = complex(source_r, 10*source_r)
    line_z = complex(.03, .04)
    z = source_z+line_z
    e = 480/sqrt(3)
    s = complex(100000*p_multiplier, 50000*q_multiplier)/3
    if model == 2:
        y = s.conjugate()/e**2
        v = e/(1+z*y)
        i = v*y
        actual_load = 3*v*i.conjugate()/1000
    else:
        a = (z*s.conjugate()).real
        b = e**2-2*a
        u = (b+sqrt(b*b-4*abs(z)**2*abs(s)**2))/2
        v = (u+z.conjugate()*s)/e
        i = (s/v).conjugate()
        actual_load = 3*s/1000
    line_s = 3*abs(i)**2*line_z/1000
    source_s = actual_load+line_s  # External source terminal: excludes Thevenin internal losses.
    return {"voltage_pu": abs(v)/e, "current_a": abs(i), "source_kw": source_s.real,
            "source_kvar": source_s.imag, "load_kw": actual_load.real,
            "network_losses_kw": line_s.real, "actual_load_kvar": actual_load.imag}


def native_script(package):
    f = package["base_model"]["source"]["frequency_hz"]
    model = package["base_model"]["topology"]["loads"][0]["model"]
    profile = package["load_profiles"][0]
    p = ",".join(str(v) for v in profile["p_multipliers"])
    q = ",".join(str(v) for v in profile["q_multipliers"])
    step = package["timeline"]["step_hours"]
    mode = package["timeline"]["mode"]
    return f"""Clear
Set DefaultBaseFrequency={f}
New Circuit.native_ts bus1=supply basekv=0.48 frequency={f}
Edit Vsource.source R1=0.002292565642723656 X1=0.02292565642723656 BaseFreq={f} Frequency={f}
New Line.feeder phases=3 bus1=supply bus2=loadbus length=1 units=km R1=0.03 X1=0.04 C1=0 BaseFreq={f}
New LoadShape.declared npts={len(profile['p_multipliers'])} interval={step} mult=[{p}] qmult=[{q}] UseActual=No
New Load.test phases=3 bus1=loadbus kv=0.48 kw=100 kvar=50 conn=wye model={model} Vminpu=0.5 Vmaxpu=1.5 daily=declared yearly=declared Status=Variable BaseFreq={f}
Set VoltageBases=[0.48]
CalcVoltageBases
Set Mode={mode} Number=1 StepSize={step}h Hour=0 Sec=0 Year=0 ControlMode=Off LoadMult=1 %Growth=0 DemandInterval=No Tolerance=1e-10 MaxIterations=100
"""
