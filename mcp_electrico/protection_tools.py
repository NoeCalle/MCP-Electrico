"""Tools MCP de P5A para datos de protección.

Estas tools registran datos explícitos y readiness. P5B expone la evaluación
numérica de curvas en ``protection_tcc_tools`` para conservar el contrato P5A.
"""

from __future__ import annotations

from . import protection_contract, protection_data


def register(mcp, on_model_change=None) -> None:
    def changed(action: str) -> None:
        if on_model_change is not None:
            on_model_change(action)

    @mcp.tool()
    def obtener_contrato_protecciones_p5a() -> dict:
        """Devuelve alcance, semántica y políticas fail-closed del bloque P5A."""
        return protection_contract.obtener_contrato_p5a()

    @mcp.tool()
    def definir_dispositivo_proteccion_p5a(
        nombre: str,
        tipo: str,
        elemento_protegido: str,
        in_a: float,
        ue_kv: float,
        fabricante: str | None = None,
        serie: str | None = None,
        modelo: str | None = None,
        polos: int | None = None,
        norma_referencia: str | None = None,
        icu_ka: float | None = None,
        ics_ka: float | None = None,
        icw_ka: float | None = None,
        poder_corte_ka: float | None = None,
        categoria_utilizacion: str | None = None,
        fuente_referencia: str | None = None,
        fuente_url: str | None = None,
    ) -> dict:
        result = protection_data.definir_dispositivo(
            nombre=nombre,
            tipo=tipo,
            elemento_protegido=elemento_protegido,
            in_a=in_a,
            ue_kv=ue_kv,
            fabricante=fabricante,
            serie=serie,
            modelo=modelo,
            polos=polos,
            norma_referencia=norma_referencia,
            icu_ka=icu_ka,
            ics_ka=ics_ka,
            icw_ka=icw_ka,
            poder_corte_ka=poder_corte_ka,
            categoria_utilizacion=categoria_utilizacion,
            fuente_referencia=fuente_referencia,
            fuente_url=fuente_url,
        )
        changed(f"definir_dispositivo_proteccion_p5a:{nombre}")
        return result

    @mcp.tool()
    def definir_ajustes_proteccion_p5a(
        dispositivo: str,
        ir_a: float | None = None,
        isd_a: float | None = None,
        ii_a: float | None = None,
        fuente_referencia: str | None = None,
        fuente_url: str | None = None,
    ) -> dict:
        result = protection_data.definir_ajustes(
            dispositivo=dispositivo,
            ir_a=ir_a,
            isd_a=isd_a,
            ii_a=ii_a,
            fuente_referencia=fuente_referencia,
            fuente_url=fuente_url,
        )
        changed(f"definir_ajustes_proteccion_p5a:{dispositivo}")
        return result

    @mcp.tool()
    def vincular_curva_proteccion_p5a(
        dispositivo: str,
        curva_id: str,
        tipo_curva: str,
        fuente_referencia: str,
        fuente_url: str | None = None,
        revision: str | None = None,
    ) -> dict:
        result = protection_data.vincular_curva(
            dispositivo=dispositivo,
            curva_id=curva_id,
            tipo_curva=tipo_curva,
            fuente_referencia=fuente_referencia,
            fuente_url=fuente_url,
            revision=revision,
        )
        changed(f"vincular_curva_proteccion_p5a:{dispositivo}")
        return result

    @mcp.tool()
    def evaluar_preparacion_proteccion_p5a(dispositivo: str) -> dict:
        """Evalúa datos/capacidad de corte y conserva el contrato P5A."""
        return protection_data.evaluar_preparacion(dispositivo)

    @mcp.tool()
    def obtener_estado_protecciones_p5a() -> dict:
        return protection_data.snapshot()
