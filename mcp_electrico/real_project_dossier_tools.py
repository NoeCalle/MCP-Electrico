"""P8F1–P8F4 — entrada MCP, integridad, repetición y primer uso P8."""

from __future__ import annotations

from . import dossier_integrity, real_pilot_intake, real_project_dossier

SCHEMA = "MCP_ELECTRICO_P8F1_REAL_PILOT_MCP_ENTRYPOINT_V1"
INTEGRITY_CONTRACT_SCHEMA = "MCP_ELECTRICO_P8F2_DOSSIER_INTEGRITY_CONTRACT_V1"
REPEATABILITY_CONTRACT_SCHEMA = "MCP_ELECTRICO_P8F3_REPEATABILITY_CONTRACT_V1"
FIRST_USE_CONTRACT_SCHEMA = "MCP_ELECTRICO_P8F4_FIRST_USE_OPERATIONAL_CONTRACT_V1"


def obtener_contrato_p8f1() -> dict:
    """Describe la frontera pública del piloto real sin ejecutar ingeniería."""
    return {
        "schema": SCHEMA,
        "entrypoint": "generar_dossier_piloto_real",
        "orchestrator_schema": real_project_dossier.SCHEMA,
        "success_status": real_project_dossier.STATUS_READY,
        "blocked_status": real_project_dossier.STATUS_BLOCKED_EXECUTION,
        "artifact_failure_status": real_project_dossier.STATUS_FAILED_ARTIFACT,
        "integrity_required_before_success": True,
        "integrity_schema": dossier_integrity.SCHEMA,
        "integrity_verifier": "verificar_integridad_dossier_real",
        "collision_safe_output": True,
        "execution_chain": [
            "P8B/P8C readiness inside P8D1",
            "P8D1 P1/P3/P4 controlled execution",
            "P8D2 explicit P4->P5 fault binding",
            "P8E1 Workspace V5",
            "P8E2 P7A/P7B/P7C dossier",
            "P8F2 exact artifact-set SHA-256 verification",
            "P8F3 collision-safe independent delivery",
        ],
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "automatic_fault_binding": False,
        "crosscheck": False,
        "professional_emission": False,
    }


def obtener_contrato_p8f2() -> dict:
    """Devuelve el contrato portable de integridad del dossier."""
    return {
        "schema": INTEGRITY_CONTRACT_SCHEMA,
        "integrity_schema": dossier_integrity.SCHEMA,
        "index_name": dossier_integrity.INDEX_NAME,
        "success_status": dossier_integrity.STATUS_VERIFIED,
        "failure_status": dossier_integrity.STATUS_MISMATCH,
        "hash_algorithm": "sha256",
        "portable_relative_paths": True,
        "exact_file_set_required": True,
        "self_hash_included": False,
        "required_top_level": list(dossier_integrity.REQUIRED_TOP_LEVEL),
        "required_directories": list(dossier_integrity.REQUIRED_DIRECTORIES),
        "professional_emission": False,
    }


def obtener_contrato_p8f3() -> dict:
    """Describe cómo se preservan entregas al repetir el mismo flujo."""
    return {
        "schema": REPEATABILITY_CONTRACT_SCHEMA,
        "entrypoint": "generar_dossier_piloto_real",
        "output_collision_policy": "SUFFIX_INCREMENT",
        "first_collision_suffix": "_2",
        "silent_overwrite": False,
        "blocked_execution_creates_delivery_directory": False,
        "prior_delivery_mutation_allowed": False,
        "each_success_requires_independent_integrity_verification": True,
        "same_manifest_same_manifest_sha256": True,
        "same_manifest_requires_same_p7a_sha256": False,
        "current_workspace_belongs_to_latest_attempt": True,
        "blocked_latest_attempt_may_clear_current_studies_fail_closed": True,
        "new_calculation_types_added": False,
        "professional_emission": False,
    }


def obtener_contrato_p8f4() -> dict:
    """Devuelve la secuencia pública y el contrato de errores del primer uso real."""
    return {
        "schema": FIRST_USE_CONTRACT_SCHEMA,
        "example_manifest": "examples/p8_first_use_manifest.json",
        "example_is_project_data": False,
        "example_requires_replacement_with_project_sources": True,
        "transport_smoke": "MCP_STDIO_SERVER_PY",
        "recommended_sequence": [
            {
                "step": 1,
                "tool": "evaluar_admision_piloto_real",
                "success_status_field": "intake_status",
                "success_status": real_pilot_intake.STATUS_READY,
            },
            {
                "step": 2,
                "tool": "generar_dossier_piloto_real",
                "success_status_field": "status",
                "success_status": real_project_dossier.STATUS_READY,
            },
            {
                "step": 3,
                "tool": "verificar_integridad_dossier_real",
                "success_status_field": "status",
                "success_status": dossier_integrity.STATUS_VERIFIED,
            },
        ],
        "failure_contract": {
            "admission": {
                "status": real_pilot_intake.STATUS_BLOCKED,
                "inspect": ["issues", "issue_count", "study_input_readiness"],
                "delivery_created": False,
                "action": "REPAIR_MANIFEST_AND_REPEAT_ADMISSION",
            },
            "execution": {
                "status": real_project_dossier.STATUS_BLOCKED_EXECUTION,
                "inspect": ["p8d2_execution.execution_status", "p8d2_execution.issues", "p8d2_execution.next_gate"],
                "delivery_created": False,
                "action": "REPAIR_EXPLICIT_ENGINEERING_INPUT_OR_BINDING",
            },
            "artifact_generation": {
                "status": real_project_dossier.STATUS_FAILED_ARTIFACT,
                "inspect": ["error", "output_directory", "integrity_index_generated"],
                "delivery_is_usable": False,
                "action": "DO_NOT_USE_PARTIAL_DIRECTORY_AS_DELIVERY",
            },
            "integrity": {
                "status": dossier_integrity.STATUS_MISMATCH,
                "inspect": ["issues"],
                "delivery_is_usable": False,
                "action": "RESTORE_OR_REGENERATE_FROM_TRUSTED_INPUT",
            },
        },
        "automatic_repair": False,
        "automatic_retry": False,
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "automatic_fault_binding": False,
        "crosscheck": False,
        "professional_emission": False,
    }


def register(mcp) -> None:
    @mcp.tool()
    def obtener_contrato_p8f1_piloto_real() -> dict:
        """Devuelve el contrato del entrypoint integral del primer proyecto real."""
        return obtener_contrato_p8f1()

    @mcp.tool()
    def obtener_contrato_p8f2_integridad_dossier() -> dict:
        """Devuelve el contrato SHA-256 del dossier Engineering Preview."""
        return obtener_contrato_p8f2()

    @mcp.tool()
    def obtener_contrato_p8f3_repeticion_dossier() -> dict:
        """Devuelve la política de repetición, aislamiento y no sobrescritura."""
        return obtener_contrato_p8f3()

    @mcp.tool()
    def obtener_contrato_p8f4_primer_uso() -> dict:
        """Devuelve la secuencia pública y estados de reparación del primer uso P8."""
        return obtener_contrato_p8f4()

    @mcp.tool()
    def generar_dossier_piloto_real(
        manifest: dict,
        directorio_salida: str = "mcp_electrico_real_dossier",
    ) -> dict:
        """Ejecuta el piloto real y genera una entrega íntegra sin sobrescribir previas.

        La operación falla cerrada si P8D2 no completa o si P8F2 no puede
        verificar el conjunto exacto de artefactos por SHA-256. Si el directorio
        solicitado ya contiene una entrega, P8F3 crea un sufijo incremental en
        vez de modificarla. No selecciona motor, falla, caso, curva ni rating
        automáticamente y no habilita emisión profesional.
        """
        return real_project_dossier.generar_dossier(
            manifest,
            directorio_salida=directorio_salida,
        )

    @mcp.tool()
    def verificar_integridad_dossier_real(
        ruta_indice: str,
    ) -> dict:
        """Revalida un dossier copiado usando su dossier_integrity.json."""
        return dossier_integrity.verificar_indice(ruta_indice)
