"""Tools MCP P5E para coordinación temporal puntual."""

from __future__ import annotations

from . import protection_coordination


def register(mcp) -> None:
    @mcp.tool()
    def obtener_contrato_coordinacion_p5e() -> dict:
        return protection_coordination.obtener_contrato_p5e()

    @mcp.tool()
    def evaluar_coordinacion_temporal_p5e(
        dispositivo_downstream: str,
        corriente_downstream_a: float,
        dispositivo_upstream: str,
        corriente_upstream_a: float,
        margen_minimo_s: float,
        fuente_relacion: str,
        fuente_corrientes: str,
    ) -> dict:
        """Evalúa margen temporal puntual; no declara selectividad total/backup."""
        return protection_coordination.evaluar_coordinacion_temporal(
            dispositivo_downstream=dispositivo_downstream,
            corriente_downstream_a=corriente_downstream_a,
            dispositivo_upstream=dispositivo_upstream,
            corriente_upstream_a=corriente_upstream_a,
            margen_minimo_s=margen_minimo_s,
            fuente_relacion=fuente_relacion,
            fuente_corrientes=fuente_corrientes,
        )
