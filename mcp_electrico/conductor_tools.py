"""Registro de tools MCP para la biblioteca de conductores.

Se mantiene en un módulo separado para que `server.py` siga siendo orquestación
y no contenga la lógica de catálogo/aplicación eléctrica.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from . import conductor_library


def register(mcp: Any, on_model_change: Callable[[str], None]) -> None:
    """Registra las tools de conductores sobre una instancia FastMCP existente."""

    def listar_conductores(nivel: str | None = None, familia: str | None = None) -> list[dict]:
        """Lista productos BT/MT trazables de la biblioteca técnica."""
        return conductor_library.listar_conductores(nivel=nivel, familia=familia)

    def obtener_conductor(codigo: str) -> dict:
        """Devuelve ficha, instalaciones, parámetros y fuente de un conductor."""
        return conductor_library.obtener_conductor(codigo)

    def aplicar_conductor(
        nombre_elemento: str,
        codigo: str,
        instalacion: str,
        actualizar_impedancia: bool = True,
    ) -> dict:
        """Asigna un conductor de catálogo a Line.* e invalida resultados previos.

        R1/X1 se actualizan únicamente cuando el fabricante publica ambos para
        la formación elegida. La ampacidad sí puede aplicarse de forma
        independiente mediante NormAmps y metadatos del workspace.
        """
        result = conductor_library.aplicar_conductor(
            nombre_elemento,
            codigo,
            instalacion,
            actualizar_impedancia=actualizar_impedancia,
        )
        on_model_change(f"aplicar_conductor:{result['elemento']}:{result['codigo']}")
        return result

    def obtener_asignaciones_conductores() -> dict:
        """Devuelve conductores de catálogo asignados al circuito activo."""
        return conductor_library.snapshot_asignaciones()

    mcp.tool()(listar_conductores)
    mcp.tool()(obtener_conductor)
    mcp.tool()(aplicar_conductor)
    mcp.tool()(obtener_asignaciones_conductores)
