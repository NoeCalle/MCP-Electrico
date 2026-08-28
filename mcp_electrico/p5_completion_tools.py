"""Tool MCP para el gate formal P5G."""

from __future__ import annotations

from . import p5_completion


def register(mcp) -> None:
    @mcp.tool()
    def evaluar_cierre_p5() -> dict:
        """Evalúa si P5-v1 está listo con limitaciones para entregar a P7."""
        return p5_completion.evaluar_cierre_p5()
