"""Tools MCP P8F5 para cierre del piloto real y checklist de uso controlado."""

from __future__ import annotations

from . import p8_completion


def register(mcp) -> None:
    @mcp.tool()
    def evaluar_cierre_p8f5_uso_real_controlado() -> dict:
        """Evalúa el gate final P8 sin ejecutar ingeniería ni habilitar emisión profesional."""
        return p8_completion.evaluar_cierre_p8()

    @mcp.tool()
    def obtener_checklist_p8f5_datos_proyecto_real() -> dict:
        """Devuelve los datos/procedencias que deben sustituirse antes de una corrida real."""
        return {
            "schema": "MCP_ELECTRICO_P8F5_REAL_PROJECT_INPUT_CHECKLIST_V1",
            "items": p8_completion.required_project_inputs(),
            "example_manifest": "examples/p8_first_use_manifest.json",
            "example_is_project_evidence": False,
            "automatic_defaults": False,
            "professional_emission": False,
        }
