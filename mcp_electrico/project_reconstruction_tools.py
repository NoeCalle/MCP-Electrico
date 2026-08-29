"""Tools MCP P7B para reconstrucción verificable de snapshots P7A."""

from __future__ import annotations

from . import project_reconstruction


def register(mcp) -> None:
    @mcp.tool()
    def obtener_contrato_reconstruccion_p7b() -> dict:
        """Devuelve las reglas fail-closed de reconstrucción P7B."""
        return project_reconstruction.obtener_contrato_p7b()

    @mcp.tool()
    def reconstruir_snapshot_proyecto_p7b(
        snapshot: dict,
        directorio_reconstruccion: str = "reconstructed_p7b",
    ) -> dict:
        """Verifica hash, reconstruye DSS y exige round-trip canónico."""
        return project_reconstruction.reconstruir_snapshot(
            snapshot,
            directorio_reconstruccion=directorio_reconstruccion,
        )

    @mcp.tool()
    def reconstruir_archivo_proyecto_p7b(
        ruta_snapshot: str,
        directorio_reconstruccion: str = "reconstructed_p7b",
    ) -> dict:
        """Carga un JSON P7A desde archivo y aplica el mismo gate P7B."""
        return project_reconstruction.reconstruir_archivo(
            ruta_snapshot,
            directorio_reconstruccion=directorio_reconstruccion,
        )
