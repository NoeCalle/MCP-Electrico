"""Tools MCP P8 para admisión y ejecución controlada del piloto real."""

from __future__ import annotations

from . import real_pilot_intake, real_project_dossier_tools


def register(mcp) -> None:
    @mcp.tool()
    def obtener_contrato_p8b_admision_real() -> dict:
        """Devuelve el contrato fail-closed de ingreso de datos del piloto real."""
        return real_pilot_intake.obtener_contrato_p8b()

    @mcp.tool()
    def evaluar_admision_piloto_real(manifest: dict) -> dict:
        """Revisa presencia/trazabilidad de entradas sin construir ni calcular el modelo."""
        return real_pilot_intake.evaluar_admision(manifest)

    # P8F1 añade la entrada integral sin crear una ruta de cálculo paralela:
    # delega en P8E2 y conserva P8D1/P8D2 como fronteras obligatorias.
    real_project_dossier_tools.register(mcp)
