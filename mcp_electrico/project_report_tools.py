"""Tools MCP P7C para reporte técnico reproducible."""

from __future__ import annotations

from . import project_report


def register(mcp) -> None:
    @mcp.tool()
    def obtener_contrato_reporte_p7c() -> dict:
        """Devuelve el contrato fail-closed del reporte técnico P7C."""
        return project_report.obtener_contrato_p7c()

    @mcp.tool()
    def exportar_reporte_tecnico_p7c(
        snapshot: dict,
        ruta_salida: str = "mcp_electrico_report.html",
    ) -> dict:
        """Genera HTML reproducible desde un snapshot P7A con hash válido."""
        return project_report.exportar_reporte(snapshot, ruta_salida=ruta_salida)

    @mcp.tool()
    def exportar_reporte_desde_archivo_p7c(
        ruta_snapshot: str,
        ruta_salida: str = "mcp_electrico_report.html",
    ) -> dict:
        """Carga un snapshot P7A JSON y genera el mismo reporte técnico P7C."""
        return project_report.exportar_reporte_desde_archivo(
            ruta_snapshot,
            ruta_salida=ruta_salida,
        )
