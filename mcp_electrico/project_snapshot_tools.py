"""Tools MCP P7A para snapshot reproducible del proyecto."""

from __future__ import annotations

from . import project_snapshot


def register(mcp) -> None:
    @mcp.tool()
    def construir_snapshot_proyecto_p7a(
        directorio_netlist: str = "temp_export_p7a",
    ) -> dict:
        """Construye el snapshot canónico en memoria y devuelve su SHA-256."""
        return project_snapshot.construir_snapshot(directorio_netlist=directorio_netlist)

    @mcp.tool()
    def exportar_snapshot_proyecto_p7a(
        ruta_salida: str = "mcp_electrico_project.json",
        directorio_netlist: str = "temp_export_p7a",
    ) -> dict:
        """Exporta el snapshot JSON sin sobrescribir archivos previos."""
        return project_snapshot.exportar_snapshot(
            ruta_salida=ruta_salida,
            directorio_netlist=directorio_netlist,
        )

    @mcp.tool()
    def verificar_snapshot_proyecto_p7a(snapshot: dict) -> dict:
        """Verifica schema/hash sin reconstruir el modelo."""
        return project_snapshot.verificar_snapshot(snapshot)
