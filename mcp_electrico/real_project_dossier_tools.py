"""P8F1 — entrada MCP controlada al piloto real P8.

La tool no implementa un segundo flujo de cálculo: delega íntegramente en
P8E2, que a su vez ejecuta P8D2 y conserva todos sus gates fail-closed.
"""

from __future__ import annotations

from . import real_project_dossier

SCHEMA = "MCP_ELECTRICO_P8F1_REAL_PILOT_MCP_ENTRYPOINT_V1"


def obtener_contrato_p8f1() -> dict:
    """Describe la frontera pública del piloto real sin ejecutar ingeniería."""
    return {
        "schema": SCHEMA,
        "entrypoint": "generar_dossier_piloto_real",
        "orchestrator_schema": real_project_dossier.SCHEMA,
        "success_status": real_project_dossier.STATUS_READY,
        "blocked_status": real_project_dossier.STATUS_BLOCKED_EXECUTION,
        "artifact_failure_status": real_project_dossier.STATUS_FAILED_ARTIFACT,
        "execution_chain": [
            "P8B/P8C readiness inside P8D1",
            "P8D1 P1/P3/P4 controlled execution",
            "P8D2 explicit P4->P5 fault binding",
            "P8E1 Workspace V5",
            "P8E2 P7A/P7B/P7C dossier",
        ],
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
    def generar_dossier_piloto_real(
        manifest: dict,
        directorio_salida: str = "mcp_electrico_real_dossier",
    ) -> dict:
        """Ejecuta el piloto real P1/P3/P4/P5 y genera Workspace + P7A/P7B/P7C.

        La operación falla cerrada si P8D2 no completa. No selecciona motor,
        falla, caso, curva ni rating automáticamente y no habilita emisión
        profesional.
        """
        return real_project_dossier.generar_dossier(
            manifest,
            directorio_salida=directorio_salida,
        )
