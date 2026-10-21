"""User-invoked, single-route orchestration of existing public MCP executors.

No numerical model, fallback, data completion or maturity promotion lives here.
The read-only selector remains read-only. Native execution gates are preserved.
"""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

from jsonschema import Draft202012Validator

from . import engine_selection


ROUTES = {
    "protection_coordination_range": "evaluar_coordinacion_intervalo_p5e",
    "motor_terminal_fault_emt": "ejecutar_falla_terminal_motor_modelica",
    "power_flow": "ejecutar_flujo_potencia",
    "voltage_drop": "analizar_caida_tension",
    "ampacity": "evaluar_ampacidad",
    "protection_coordination": "evaluar_coordinacion_temporal_p5e",
    "operating_scenarios": "ejecutar_escenarios_operativos",
    "reactive_compensation": "ejecutar_compensacion_reactiva",
    "harmonics": "ejecutar_armonicos",
    "time_series": "ejecutar_series_temporales",
    "relay_operation": "ejecutar_actuacion_reles",
    "motor_dynamics_dol": "ejecutar_dinamica_modelica",
    "motor_dynamics_simultaneous": "ejecutar_dinamica_modelica",
    "motor_dynamics_soft_starter_scr": "ejecutar_dinamica_modelica",
}
FAULT_ROUTES = {
    "three_phase": "ejecutar_cortocircuito_iec60909_3ph",
    "two_phase": "ejecutar_cortocircuito_iec60909_2ph",
    "single_phase_ground": "ejecutar_cortocircuito_iec60909_1ph_ground",
}


def routes() -> dict:
    """Return independent routing metadata without checking or running engines."""
    return {
        "tool": "ejecutar_estudio",
        "invocation": "EXPLICIT_USER_REQUEST",
        "single_executor_per_request": True,
        "fallback": False,
        "crosscheck": False,
        "routes": deepcopy(ROUTES),
        "iec60909_fault_routes": deepcopy(FAULT_ROUTES),
        "modelica_scope": "EXPLICIT_STUDY_PACKAGE_ONLY_NO_UNIFILAR_TRANSLATION",
        "operating_scenarios_model_effect": "REBUILDS_AND_RESTORES_DECLARED_MANIFEST_BASE_NOT_PREVIOUS_ACTIVE_CIRCUIT",
        "protection_coordination_scope": "POINTWISE_TEMPORAL_MARGIN_FROM_DECLARED_CURRENTS_NO_NEW_FAULT_SOLUTION",
        "protection_coordination_range_scope": "CONTINUOUS_DECLARED_LOG_LOG_CURVES_AND_CONSTANT_CURRENT_RATIO_NOT_SELECTIVITY",
    }


async def contract(mcp) -> dict:
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    names = sorted(set(ROUTES.values()) | set(FAULT_ROUTES.values()))
    return {
        "schema": "MCP_ELECTRICO_STUDY_DISPATCH_V1",
        **routes(),
        "parameter_schemas": {
            name: deepcopy(tools[name].inputSchema) for name in names if name in tools
        },
        "unavailable_tools": [name for name in names if name not in tools],
        "note": "Los parámetros son los del ejecutor público. Se conservan sus gates, resultados y límites; invocar no significa completar ni aprobar el estudio.",
    }


async def execute(mcp, estudio: str, parametros: dict[str, Any] | None = None,
                  norma: str | None = None, tipo_falla: str | None = None) -> dict:
    # Do not let the legacy selector's standard override redirect an unrelated study.
    study = engine_selection._normalize_study(estudio)
    requested_standard = str(norma or "").replace(" ", "").lower()
    fault_studies = {"iec60909", "short_circuit_exploratory"}
    envelope = {
        "schema": "MCP_ELECTRICO_STUDY_DISPATCH_V1",
        "study_requested": estudio, "study": study,
        "selected_engine": None, "execution_tool": None,
        "executor_invoked": False, "fallback": False, "crosscheck": False,
    }

    def blocked(status, message, **details):
        return {**envelope, "status": status, "message": message, **details}

    if norma is not None:
        if study not in fault_studies or "60909" not in requested_standard:
            return blocked("BLOCKED_STANDARD", "La norma de enrutamiento solo admite IEC 60909 en un pedido de cortocircuito.")
        study = "iec60909"
        envelope["study"] = study
    capability = engine_selection.CAPABILITY_MATRIX.get(study)
    if capability is None:
        return blocked("UNKNOWN_STUDY", "Estudio no registrado; no se infiere otra tarea.")
    envelope["selected_engine"] = capability["preferred"]
    if study == "iec60909":
        tool_name = FAULT_ROUTES.get(tipo_falla)
        if tool_name is None:
            return blocked("BLOCKED_FAULT_TYPE", "Declare three_phase, two_phase o single_phase_ground; no se supone una falla.")
    else:
        if tipo_falla is not None:
            return blocked("BLOCKED_FAULT_TYPE", "tipo_falla solo corresponde a IEC 60909.")
        tool_name = ROUTES.get(study)
    if tool_name is None:
        return blocked("BLOCKED_DISPATCH_ROUTE", "Esta tarea conserva sus herramientas específicas; no tiene una ruta común habilitada.")
    envelope["execution_tool"] = tool_name
    params = {} if parametros is None else deepcopy(parametros)
    if not isinstance(params, dict):
        return blocked("BLOCKED_PARAMETERS", "parametros debe ser un objeto.")
    try:
        json.dumps(params, allow_nan=False)
    except (ValueError, TypeError):
        return blocked("BLOCKED_PARAMETERS", "Los parámetros deben ser JSON con números finitos.")
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    if tool_name not in tools:
        return blocked("BLOCKED_EXECUTOR_UNAVAILABLE", "El ejecutor no está registrado en este servidor.")
    schema = tools[tool_name].inputSchema
    unknown = sorted(set(params) - set(schema.get("properties", {})))
    errors = list(Draft202012Validator(schema).iter_errors(params))
    if unknown or errors:
        return blocked("BLOCKED_PARAMETERS", "Parámetros incompletos o incompatibles con el ejecutor.",
                       unknown_parameters=unknown,
                       issues=[{"path": list(error.absolute_path), "message": error.message} for error in errors])
    if capability.get("requires_active_model") and not engine_selection._has_active_model():
        return blocked("BLOCKED_ACTIVE_MODEL", "No existe un circuito activo.")
    if study.startswith("motor_dynamics_"):
        # Prevent a correctly formed package for a different study being executed.
        motors = params["paquete_estudio"].get("motors")
        if not isinstance(motors, list) or not motors or any(
            not isinstance(motor, dict) or not isinstance(motor.get("starting"), dict)
            for motor in motors
        ):
            return blocked("BLOCKED_MOTOR_STUDY", "Declare las máquinas y su método de arranque en el paquete Modelica.")
        methods = [motor["starting"].get("method") for motor in motors]
        expected = "SCR" if study == "motor_dynamics_soft_starter_scr" else "DOL"
        if any(method != expected for method in methods) or (study == "motor_dynamics_simultaneous" and len(motors) < 2):
            return blocked("BLOCKED_MOTOR_STUDY", "El paquete no corresponde al estudio solicitado; simultánea usa al menos dos DOL. Para SCR multimotor seleccione dinamica_scr.")
    try:
        # Public SDK API: invokes the SAME decorated executor, including its
        # validation and workspace/report hooks. Never call a second executor.
        response = await mcp.call_tool(tool_name, params)
    except Exception as exc:
        return {**envelope, "executor_invoked": True, "status": "EXECUTOR_ERROR",
                "error": f"{type(exc).__name__}: {exc}"}
    # SDK supports structured tuples and legacy dict annotations serialized as
    # one JSON TextContent. Both are used by this server's public executors.
    result = response[1] if isinstance(response, tuple) and len(response) == 2 else None
    if isinstance(response, dict):
        result = response
    elif isinstance(response, list) and len(response) == 1 and getattr(response[0], "type", None) == "text":
        try:
            result = json.loads(response[0].text)
        except (ValueError, TypeError):
            result = None
    if not isinstance(result, dict):
        return {**envelope, "executor_invoked": True, "status": "EXECUTOR_RESPONSE_UNAVAILABLE",
                "message": "El ejecutor no devolvió un resultado estructurado; no se reintenta automáticamente."}
    return {**envelope, "executor_invoked": True, "status": "EXECUTOR_RETURNED", "result": result}


def register(mcp) -> None:
    @mcp.tool()
    async def obtener_contrato_ejecucion_estudios() -> dict:
        """Rutas y esquemas de parámetros para ejecutar un estudio con su motor asignado."""
        return await contract(mcp)

    @mcp.tool()
    async def ejecutar_estudio(estudio: str, parametros: dict | None = None,
                              norma: str | None = None, tipo_falla: str | None = None) -> dict:
        """Selecciona UNA ruta y llama al ejecutor público con sus gates existentes.

        Consultar obtener_contrato_ejecucion_estudios para parámetros. IEC exige
        tipo_falla explícito; Modelica exige paquete equivalente RL propio.
        Revisar result para bloqueos/convergencia; EXECUTOR_RETURNED no significa
        estudio válido ni aprobación de diseño. No hay fallback ni cross-check.
        """
        return await execute(mcp, estudio, parametros, norma, tipo_falla)
