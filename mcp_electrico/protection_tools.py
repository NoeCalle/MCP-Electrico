"""Tools MCP P5A/P5B para datos y curvas de protección.

P5B evalúa datasets TCC explícitos. No calcula selectividad todavía, no
sintetiza curvas de fabricante y no convierte automáticamente tiempo de curva
en tiempo real de despeje.
"""

from __future__ import annotations

from . import protection_contract, protection_curves, protection_data


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
    def registrar_dataset_curva_tcc_p5b(
        dataset_id: str,
        curve_id: str,
        shape: str,
        time_semantics: str,
        segments: list[dict],
        source_type: str,
        source_reference: str,
        source_url: str | None = None,
        revision: str | None = None,
        digitization_method: str | None = None,
    ) -> dict:
        """Registra puntos TCC explícitos; no digitaliza ni inventa curvas."""
        return protection_curves.registrar_dataset(
            dataset_id=dataset_id,
            curve_id=curve_id,
            shape=shape,
            time_semantics=time_semantics,
            segments=segments,
            source_type=source_type,
            source_reference=source_reference,
            source_url=source_url,
            revision=revision,
            digitization_method=digitization_method,
        )

    @mcp.tool()
    def listar_datasets_curva_tcc_p5b() -> list[dict]:
        return protection_curves.listar_datasets()

    @mcp.tool()
    def vincular_dataset_curva_tcc_p5b(dispositivo: str, dataset_id: str) -> dict:
        result = protection_curves.vincular_dataset_dispositivo(dispositivo, dataset_id)
        changed(f"vincular_dataset_curva_tcc_p5b:{dispositivo}")
        return result

    @mcp.tool()
    def evaluar_curva_tcc_p5b(dispositivo: str, current_a: float) -> dict:
        """Evalúa la curva del dispositivo dentro de un segmento, sin extrapolar."""
        return protection_curves.evaluar_dispositivo(dispositivo, current_a)

    @mcp.tool()
    def evaluar_dataset_tcc_p5b(dataset_id: str, current_a: float) -> dict:
        return protection_curves.evaluar_dataset(dataset_id, current_a)

    @mcp.tool()
    def evaluar_preparacion_proteccion_p5a(dispositivo: str) -> dict:
        """Evalúa datos, capacidad de corte disponible y readiness TCC P5B."""
        return protection_data.evaluar_preparacion(dispositivo)

    @mcp.tool()
    def obtener_estado_protecciones_p5a() -> dict:
        return protection_data.snapshot()
