"""Tools MCP P5D para tiempo final de despeje."""

from __future__ import annotations

from . import protection_clearing_time


def register(mcp) -> None:
    @mcp.tool()
    def obtener_contrato_tiempo_despeje_p5d() -> dict:
        return protection_clearing_time.obtener_contrato_p5d()

    @mcp.tool()
    def evaluar_tiempo_despeje_p5d(dispositivo: str, current_a: float) -> dict:
        """Promueve a clearing time solo TOTAL_CLEARING_TIME dentro de dominio."""
        return protection_clearing_time.evaluar_tiempo_despeje(dispositivo, current_a)
