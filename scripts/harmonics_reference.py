"""Independent single-phase RL/C benchmark, without importing the MCP adapter.

Balanced non-triplen magnitudes: constant R, reactance proportional to order,
load series/parallel damping from nominal P/Q, and ideal bank admittance.
This is a reference calculation, not an application solver or fallback.
"""
from math import sqrt


def reference_package(frequency=60, connection="wye", enabled=True, series_rl_percent=100):
    ref = "SYNTHETIC_TWO_BUS_RLC_REFERENCE_NOT_CLIENT_OR_MANUFACTURER_DATA"
    return {
        "schema": "MCP_ELECTRICO_HARMONICS_V1", "id": "HARM-RLC-01", "source_reference": ref,
        "base_model": {
            "project": {"id": "HARM_RLC", "name": "Independent RL-C test", "source_reference": ref},
            "source": {"bus": "supply", "kv_ll": .48, "frequency_hz": frequency, "pu": 1,
                       "angle_deg": 0, "scc_max_mva": 10, "x_r_max": 10, "source_reference": ref},
            "topology": {"buses": ["supply", "loadbus"], "transformers": [],
                "lines": [{"id": "Line.feeder", "bus1": "supply", "bus2": "loadbus", "phases": 3,
                           "length_km": 1, "r1_ohm_km": .03, "x1_ohm_km": .04, "c1_nf_km": 0,
                           "normamps_a": 500, "source_reference": ref}],
                "loads": [{"id": "Load.test", "bus": "loadbus", "phases": 3, "kv": .48,
                           "kw": 100, "kvar": 50, "connection": connection, "model": 2,
                           "vminpu": .5, "vmaxpu": 1.5, "source_reference": ref}]}},
        "banks": [{"id": "bank", "bus": "loadbus", "kv_ll": .48, "kvar": 100,
                   "connection": connection, "enabled": enabled, "source_reference": ref}],
        "load_harmonics": [{"load_id": "Load.test", "series_rl_percent": series_rl_percent,
            "spectrum": [{"order": 5, "percent": 20, "angle_deg": 0},
                         {"order": 7, "percent": 10, "angle_deg": 25}], "source_reference": ref}],
        "orders": [5, 7, 11],
        "scan": {"buses": ["loadbus"], "orders": [2+i*.1 for i in range(181)],
                 "sequence": "positive", "source_reference": ref},
        "criteria": {"maximum_voltage_thd_percent": 5, "source_reference": "EXAMPLE_CRITERION_ONLY"},
        "options": {"frequency_model": "CONSTANT_R_LINEAR_X_NO_SKIN_EFFECT", "neglect_load_y": False,
                    "solver_tolerance": 1e-10, "max_iterations": 100, "kcl_tolerance_a": 1e-5}}


def analytical(package, order):
    # Literal benchmark constants, intentionally independent of adapter parsing.
    r_source = .48**2/10/sqrt(101)
    z_source = complex(r_source, order*10*r_source)
    z_supply = z_source + complex(.03, order*.04)
    z_load_nominal = 480**2/complex(100000, -50000)
    share = package["load_harmonics"][0]["series_rl_percent"]/100
    y_load = share/complex(z_load_nominal.real, order*z_load_nominal.imag)
    y_load += (1-share)*complex(100000/480**2, -50000/480**2/order)
    y_cap = complex(0, order*100000/480**2) if package["banks"][0]["enabled"] else 0j
    driving_z = 1/(1/z_supply + y_load + y_cap)
    if order == 1:
        voltage = (480/sqrt(3))/(1+z_supply*(y_load+y_cap))
        return {"voltage_v": abs(voltage), "load_current_a": abs(voltage/z_load_nominal),
                "z_ohm": abs(driving_z)}
    i_fund = analytical(package, 1)["load_current_a"]
    percent = next((p["percent"] for p in package["load_harmonics"][0]["spectrum"] if p["order"] == order), 0)
    v_h = i_fund*percent/100*abs(driving_z)
    return {"voltage_v": v_h, "line_current_a": v_h/abs(z_supply), "z_ohm": abs(driving_z),
            "r_ohm": driving_z.real, "x_ohm": driving_z.imag}


def native_script(package):
    """Build the same benchmark directly from independently specified DSS literals."""
    f = package["base_model"]["source"]["frequency_hz"]
    conn = package["base_model"]["topology"]["loads"][0]["connection"]
    series = package["load_harmonics"][0]["series_rl_percent"]
    state = int(package["banks"][0]["enabled"])
    return f"""Clear
Set DefaultBaseFrequency={f}
New Circuit.native_harmonic basekv=0.48 bus1=supply frequency={f}
New Spectrum.voltage_clean NumHarm=1 Harmonic=[1] %Mag=[100] Angle=[0]
New Spectrum.load_known NumHarm=3 Harmonic=[1,5,7] %Mag=[100,20,10] Angle=[0,0,25]
Edit Vsource.source phases=3 basekv=0.48 bus1=supply pu=1 angle=0 R1=0.002292565642723656 X1=0.02292565642723656 BaseFreq={f} Frequency={f} Spectrum=voltage_clean
New Line.feeder phases=3 bus1=supply bus2=loadbus length=1 units=km R1=0.03 X1=0.04 C1=0 Rg=0 Xg=0 BaseFreq={f}
New Load.test phases=3 bus1=loadbus kv=0.48 kw=100 kvar=50 conn={conn} model=2 Vminpu=0.5 Vmaxpu=1.5 %SeriesRL={series} puXHarm=0 XRHarm=6 Spectrum=load_known BaseFreq={f}
New Capacitor.bank phases=3 bus1=loadbus bus2=loadbus.0.0.0 kv=0.48 kvar=100 conn={conn} NumSteps=1 R=[0] XL=[0] States=[{state}] BaseFreq={f}
Set VoltageBases=[0.48]
CalcVoltageBases
Set Mode=Snapshot Frequency={f} ControlMode=Off Tolerance=1e-10 MaxIterations=100 NeglectLoadY=No
Solve
"""
