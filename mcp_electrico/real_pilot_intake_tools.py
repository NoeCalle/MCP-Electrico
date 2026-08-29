"""Tools MCP P8B para admisión de un paquete de datos de proyecto real."""

from __future__ import annotations

from . import real_pilot_intake


def register(mcp) -> None:
    @mcp.tool()
    def obtener_contrato_p8b_admision_real() -> dict:
        """Devuelve el contrato fail-closed de ingreso de datos del piloto real."""
        return real_pilot_intake.obtener_contrato_p8b()

    @mcp.tool()
    def evaluar_admision_piloto_real(manifest: dict) -> dict:
        """Revisa presencia/trazabilidad de entradas sin construir ni calcular el modelo."""
        return real_pilot_intake.evaluar_admision(manifest)
