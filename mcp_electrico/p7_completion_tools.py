"""Tools MCP para el gate final P7D / Engineering Preview 0.9."""

from __future__ import annotations

from . import capability_alignment, p7_completion


def register(mcp) -> None:
    # Alinea la metadata P5 al registrar las tools públicas. No despacha ni
    # ejecuta estudios y conserva professional_emission=false.
    capability_alignment.align_p5_capabilities()

    @mcp.tool()
    def evaluar_cierre_p7() -> dict:
        """Evalúa el gate de MCP Eléctrico 0.9 Engineering Preview."""
        return p7_completion.evaluar_cierre_p7()

    @mcp.tool()
    def obtener_release_engineering_preview() -> dict:
        """Devuelve release, alcance de uso y límites del gate P7D."""
        result = p7_completion.evaluar_cierre_p7()
        return {
            "schema": result["schema"],
            "phase_status": result["phase_status"],
            "product_release": result["product_release"],
            "engineering_preview_ready": result["engineering_preview_ready"],
            "internal_use_ready": result["internal_use_ready"],
            "allowed_use": result["allowed_use"],
            "arc_flash_ieee1584": result["arc_flash_ieee1584"],
            "professional_report": result["professional_report"],
            "professional_emission": result["professional_emission"],
            "next_activity": result["next_activity"],
        }
