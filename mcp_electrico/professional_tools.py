"""Registro de tools MCP para gobernanza técnica y datos profesionales P2."""

from __future__ import annotations

from . import model_qa, professional_data, validation_status


def register(mcp, on_model_change=None) -> None:
    def changed(action: str) -> None:
        if on_model_change is not None:
            on_model_change(action)

    @mcp.tool()
    def obtener_matriz_validacion() -> dict:
        """Devuelve la madurez técnica declarada de cada módulo."""
        return validation_status.get_validation_matrix()

    @mcp.tool()
    def auditar_modelo(estudios_requeridos: list[str] | None = None) -> dict:
        """Ejecuta QA determinístico y reporta si el modelo puede habilitarse para emisión."""
        return model_qa.auditar_modelo(estudios_requeridos)

    @mcp.tool()
    def agregar_transformador_profesional(
        nombre: str,
        bus_hv: str,
        bus_lv: str,
        kva: float,
        kv_hv: float,
        kv_lv: float,
        uk_percent: float,
        grupo_vectorial: str,
        x_r: float | None = None,
        load_loss_kw: float | None = None,
        no_load_loss_kw: float | None = None,
        i0_percent: float | None = None,
        tap_side: str | None = None,
        tap_neutral: int = 0,
        tap_min: int = 0,
        tap_max: int = 0,
        tap_step_percent: float | None = None,
        tap_pos: int = 0,
        fabricante: str | None = None,
        modelo: str | None = None,
        fuente_referencia: str | None = None,
        fuente_url: str | None = None,
    ) -> dict:
        """Crea un transformador P2 sin completar %Z, X/R, pérdidas o taps con defaults silenciosos."""
        result = professional_data.agregar_transformador_profesional(
            nombre=nombre,
            bus_hv=bus_hv,
            bus_lv=bus_lv,
            kva=kva,
            kv_hv=kv_hv,
            kv_lv=kv_lv,
            uk_percent=uk_percent,
            grupo_vectorial=grupo_vectorial,
            x_r=x_r,
            load_loss_kw=load_loss_kw,
            no_load_loss_kw=no_load_loss_kw,
            i0_percent=i0_percent,
            tap_side=tap_side,
            tap_neutral=tap_neutral,
            tap_min=tap_min,
            tap_max=tap_max,
            tap_step_percent=tap_step_percent,
            tap_pos=tap_pos,
            fabricante=fabricante,
            modelo=modelo,
            fuente_referencia=fuente_referencia,
            fuente_url=fuente_url,
        )
        changed(f"agregar_transformador_profesional:{nombre}")
        return result

    @mcp.tool()
    def definir_red_equivalente(
        kv_ll: float,
        scc_max_mva: float,
        x_r_max: float,
        scc_min_mva: float | None = None,
        x_r_min: float | None = None,
        escenario_activo: str = "max",
        fuente_referencia: str | None = None,
        fuente_url: str | None = None,
    ) -> dict:
        """Define Scc3/XR máxima y opcional mínima; no infiere secuencia cero."""
        result = professional_data.definir_red_equivalente(
            kv_ll=kv_ll,
            scc_max_mva=scc_max_mva,
            x_r_max=x_r_max,
            scc_min_mva=scc_min_mva,
            x_r_min=x_r_min,
            escenario_activo=escenario_activo,
            fuente_referencia=fuente_referencia,
            fuente_url=fuente_url,
        )
        changed("definir_red_equivalente")
        return result

    @mcp.tool()
    def seleccionar_escenario_red(escenario: str) -> dict:
        """Activa el escenario máximo o mínimo ya definido en la fuente P2."""
        result = professional_data.seleccionar_escenario_red(escenario)
        changed(f"seleccionar_escenario_red:{escenario}")
        return result

    @mcp.tool()
    def obtener_datos_profesionales() -> dict:
        """Devuelve transformadores y red equivalente P2 con procedencia y derivaciones."""
        return professional_data.snapshot()
