"""Tools MCP para construcción Rev.0 sin ejecutar estudios.

Expone de forma explícita el materializador P8C3B ya validado. Esta capa evita
que un agente tenga que reconstruir el flujo interno a partir de tools legacy.
"""

from __future__ import annotations

from . import model_placeholders, real_model_materializer, workspace_state

SCHEMA = "MCP_ELECTRICO_REV0_CONSTRUCTION_ENTRYPOINT_V1"


def obtener_contrato() -> dict:
    return {
        "schema": SCHEMA,
        "purpose": "BUILD_REV0_WITHOUT_SOLVE_OR_WORKSPACE_FILE_WRITE",
        "tools": [
            "obtener_contrato_construccion_rev0",
            "validar_construccion_rev0",
            "construir_modelo_rev0",
            "registrar_placeholder_modelo",
            "obtener_placeholders_modelo",
        ],
        "recommended_sequence": [
            "obtener_contrato_construccion_rev0",
            "validar_construccion_rev0",
            "construir_modelo_rev0",
            "registrar_placeholder_modelo_if_needed",
            "auditar_modelo",
            "evaluate_study_readiness_before_any_calculation",
        ],
        "solve_performed": False,
        "workspace_file_written": False,
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
        "tbc_policy": (
            "Los datos obligatorios ausentes no se inventan. Un elemento TBC puede "
            "registrarse como MODEL_PLACEHOLDER, pero no se crea en OpenDSS y bloquea "
            "la preparación para estudios que dependan de él."
        ),
    }


def register(mcp) -> None:
    @mcp.tool()
    def obtener_contrato_construccion_rev0() -> dict:
        """Devuelve la ruta recomendada para construir Rev.0 sin Solve."""
        return obtener_contrato()

    @mcp.tool()
    def validar_construccion_rev0(manifest: dict) -> dict:
        """Valida intake + preflight del materializador sin mutar OpenDSS."""
        return real_model_materializer.evaluar_preflight_materializacion(manifest)

    @mcp.tool()
    def construir_modelo_rev0(manifest: dict) -> dict:
        """Construye el modelo admitido sin Solve y sin regenerar archivos workspace."""
        result = real_model_materializer.materializar_modelo(manifest)
        return {
            **result,
            "entrypoint": "construir_modelo_rev0",
            "solve_performed": False,
            "workspace_file_written": False,
            "study_readiness_evaluated": False,
            "model_ready_for_study": False,
            "next_gate": "EVALUATE_STUDY_READINESS_EXPLICITLY",
            "placeholders": model_placeholders.snapshot(),
        }

    @mcp.tool()
    def registrar_placeholder_modelo(
        element_id: str,
        element_type: str,
        missing_fields: list[str],
        known_data: dict | None = None,
        source_reference: str | None = None,
        note: str | None = None,
    ) -> dict:
        """Registra un TBC sin crear un elemento eléctrico ficticio en OpenDSS."""
        result = model_placeholders.registrar(
            element_id=element_id,
            element_type=element_type,
            known_data=known_data,
            missing_fields=missing_fields,
            source_reference=source_reference,
            note=note,
        )
        workspace_state.mark_model_changed(f"model_placeholder:{element_id}")
        return {
            **result,
            "solve_performed": False,
            "workspace_file_written": False,
        }

    @mcp.tool()
    def obtener_placeholders_modelo() -> dict:
        """Devuelve TBC explícitos que aún bloquean preparación de estudio."""
        return model_placeholders.snapshot()
