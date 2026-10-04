"""Historical mechanical oracles and external-backend qualification plan."""
from __future__ import annotations

from math import exp

MODEL_REFERENCE = "https://doc.modelica.org/Modelica%204.0.0/Resources/helpWSM/Modelica/Modelica.Electrical.Machines.BasicMachines.InductionMachines.IM_SquirrelCage.html"
DSS_REFERENCE = "https://dss-extensions.org/dss-format/IndMach012.html"
MECHANICAL_REFERENCE = "https://doc.modelica.org/Modelica%204.0.0/Resources/helpWSM/Modelica/Modelica.Mechanics.Rotational.Components.Inertia.html"


def obtener_plan_validacion() -> dict:
    """Return synthetic analytical references; no numerical integration is run."""
    times = [0.0, 0.5, 1.0, 2.0]
    constant = [{"time_s": t, "speed_rad_s": 6 * t, "angle_rad": 3 * t * t,
                 "kinetic_energy_j": 180 * t * t} for t in times]
    damped = [{"time_s": t, "speed_rad_s": 20 * (1 - exp(-0.2 * t)),
               "angle_rad": 20 * t - 100 * (1 - exp(-0.2 * t))} for t in times]
    return {
        "schema": "MCP_ELECTRICO_P13F1_DYNAMIC_QUALIFICATION_PLAN_V1",
        "selected_backend": "OPENMODELICA_MSL_4_0_0",
        "qualified_scope": None, "experimental_scope": "DECLARED_BALANCED_COMMON_BUS_RL_EQUIVALENT",
        "qualification_evidence": "scripts/verify_modelica_motor_adapter_mcp.py",
        "qualification_limitations": ["EXPERIMENTAL_COMMON_BUS_RL_ONLY", "SCR_SINGLE_DELTA_REFERENCE_CONTROLLER_ONLY", "NO_FULL_UNIFILAR_TRANSLATION"],
        "candidates": [
            {"id": "OPENDSS_INDMACH012", "status": "NOT_QUALIFIED", "source_url": DSS_REFERENCE,
             "pending": ["SI_TO_PU_BASE_MAPPING", "STANDSTILL_INITIALIZATION", "MECHANICAL_LOAD_LAW", "TIME_STEP_CONVERGENCE"]},
            {"id": "MODELICA_SQUIRREL_CAGE", "status": "NOT_QUALIFIED", "source_url": MODEL_REFERENCE,
             "pending": ["RUNTIME_AND_LIBRARY_PINNING", "ISOLATED_NETWORK_COUPLING", "LOSS_MODEL_MAPPING", "INDEPENDENT_BENCHMARKS"]},
        ],
        "mechanical_equation": "J_total * d(omega)/dt = T_e - T_load - B * omega",
        "mechanical_reference_url": MECHANICAL_REFERENCE,
        "analytical_oracles": [
            {"id": "P13F_B01_CONSTANT_NET_TORQUE", "source_reference": "CONTROLLED_REFERENCE_DATA - independent Newton rotational balance",
             "inputs": {"total_inertia_kg_m2": 10, "electromagnetic_torque_nm": 80, "load_torque_nm": 20,
                        "viscous_damping_nm_s_per_rad": 0, "initial_speed_rad_s": 0, "initial_angle_rad": 0},
             "speed_formula": "omega(t) = 6*t", "expected": constant,
             "absolute_tolerances": {"speed_rad_s": 1e-6, "angle_rad": 1e-6, "kinetic_energy_j": 1e-5},
             "backend_verified": False},
            {"id": "P13F_B02_VISCOUS_LOAD", "source_reference": "CONTROLLED_REFERENCE_DATA - independent first-order closed-form solution",
             "inputs": {"total_inertia_kg_m2": 10, "electromagnetic_torque_nm": 50, "load_torque_nm": 10,
                        "viscous_damping_nm_s_per_rad": 2, "initial_speed_rad_s": 0, "initial_angle_rad": 0},
             "speed_formula": "omega(t) = 20*(1-exp(-0.2*t))", "expected": damped,
             "absolute_tolerances": {"speed_rad_s": 1e-6, "angle_rad": 1e-6}, "backend_verified": False},
        ],
        "required_qualification_cases": [
            {"id": "P13F_B03_LOCKED_ROTOR", "gate": "Independent equivalent-circuit current, PF and torque with declared connection and SI bases"},
            {"id": "P13F_B04_ENERGY_BALANCE", "gate": "Balanced quasi-steady RMS input equals kinetic energy change plus copper/damping losses and shaft work; magnetic storage and flux transients are excluded"},
            {"id": "P13F_B05_GRID_REFINEMENT", "gate": "Compare dt, dt/2 and dt/4 for speed, current, torque, voltage and acceleration time under fixture-specific tolerances"},
            {"id": "P13F_B06_STALL_AND_NONCONVERGENCE", "gate": "Unreachable speed and failed integration remain explicit; no extrapolation or success promotion"},
            {"id": "P13F_B07_PARENT_ISOLATION_REPLAY", "gate": "Parent circuit unchanged; replay reproduces trajectories using exact backend/library versions"},
        ],
        "scope_exclusions": ["VFD", "SOFT_STARTER", "STAR_DELTA_SWITCHING", "UNBALANCED_EMT", "THERMAL_EVOLUTION", "SATURATION", "MULTI_MOTOR_DYNAMIC_SEQUENCING"],
        "analytical_reference_values_generated": True, "numerical_integration_performed": False,
        "electrical_calculation_performed": False, "model_mutation_performed": False,
        "ready_for_execution": False, "backend_benchmarks_run": False, "retired_backend_benchmarks_historical_only": True, "professional_emission": False,
    }
