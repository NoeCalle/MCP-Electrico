"""Registro de tools MCP para gobernanza técnica y QA profesional."""

from __future__ import annotations

from . import model_qa, validation_status


def register(mcp) -> None:
    @mcp.tool()
    def obtener_matriz_validacion() -> dict:
        """Devuelve la madurez técnica declarada de cada módulo."""
        return validation_status.get_validation_matrix()

    @mcp.tool()
    def auditar_modelo(estudios_requeridos: list[str] | None = None) -> dict:
        """Ejecuta QA determinístico y reporta si el modelo puede habilitarse para emisión."""
        return model_qa.auditar_modelo(estudios_requeridos)
