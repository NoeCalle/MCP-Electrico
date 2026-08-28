"""Tools MCP P5D para tiempo final de despeje."""

from __future__ import annotations

from . import protection_clearing_time


def register(mcp, on_result=None) -> None:
    def recorded(name: str, result: dict, action: str) -> dict:
        if on_result is not None:
            on_result(name, result, action)
        return result

    @mcp.tool()
    def obtener_contrato_tiempo_despeje_p5d() -> dict:
        return protection_clearing_time.obtener_contrato_p5d()

    @mcp.tool()
    def evaluar_tiempo_despeje_p5d(dispositivo: str, current_a: float) -> dict:
        """Promueve a clearing time solo TOTAL_CLEARING_TIME dentro de dominio."""
        result = protection_clearing_time.evaluar_tiempo_despeje(dispositivo, current_a)
        return recorded(
            "protection_clearing_time",
            result,
            f"evaluar_tiempo_despeje_p5d:{dispositivo}",
        )
