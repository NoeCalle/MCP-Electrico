"""Tools MCP P8 para admisión, ejecución y cierre de uso real controlado."""

from __future__ import annotations

from . import p8_completion_tools, real_pilot_intake, real_project_dossier_tools


def register(mcp) -> None:
    @mcp.tool()
    def obtener_contrato_p8b_admision_real() -> dict:
        """Devuelve el contrato fail-closed de ingreso de datos del piloto real."""
        return real_pilot_intake.obtener_contrato_p8b()

    @mcp.tool()
    def evaluar_admision_piloto_real(manifest: dict) -> dict:
        """Revisa presencia/trazabilidad de entradas sin construir ni calcular el modelo."""
        return real_pilot_intake.evaluar_admision(manifest)

    # La ejecución integral conserva P8D1/P8D2/P8E como fronteras obligatorias.
    real_project_dossier_tools.register(mcp)
    # P8F5 solo evalúa contratos/readiness y expone el checklist; no calcula ingeniería.
    p8_completion_tools.register(mcp)
