"""Compatibility notice for the retired MCP-owned RMS solver.

The equivalent-circuit equations and RK4 integrator were removed. Historical
reports remain readable; new physics runs use the explicit MSL study contract.
Old inputs are never silently translated or filled with assumed parameters.
"""
BACKEND = "RETIRED_MCP_BALANCED_RMS_RK4_V1"


def contrato():
    return {"backend": BACKEND, "maturity": "RETIRED", "ready_for_execution": False,
            "replacement_backend": "OPENMODELICA_MSL_4_0_0",
            "replacement_contract_tool": "obtener_contrato_dinamica_modelica",
            "replacement_execution_tool": "ejecutar_dinamica_modelica",
            "migration_requires_explicit_new_package": True,
            "physical_solver_owned_by_mcp": False, "professional_emission": False}


def readiness(manifest, package, options):
    return {**contrato(), "status": "RETIRED_CUSTOM_BACKEND", "data_ready": False,
            "issues": [{"code": "MOTOR_BACKEND_RETIRED", "message": "Use the explicit MSL package; old inputs are not converted automatically."}],
            "network_solve_performed": False}


def execute(manifest, package, options):
    return {**readiness(manifest, package, options), "execution_status": "RETIRED_CUSTOM_BACKEND",
            "results": [], "parent_context_mutated": False}
