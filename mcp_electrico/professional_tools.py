"""Registro de tools MCP para gobernanza técnica y datos profesionales P2–P5."""

from __future__ import annotations

from . import (
    ampacity_tools,
    engine_selection,
    iec60909_tools,
    model_qa,
    p2_completion,
    professional_data,
    protection_check_tools,
    protection_clearing_tools,
    protection_coordination_tools,
    protection_tcc_tools,
    protection_tools,
    runtime_safety,
    validation_status,
    zero_sequence,
)


def register(mcp, on_model_change=None) -> None:
    # Endurece las rutas públicas existentes: reinicio completo de estado en
    # Circuit nuevo y preflight Z0 para FaultStudy.
    runtime_safety.install()

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
    def obtener_capacidades_motores() -> dict:
        """Devuelve la matriz determinista OpenDSS/pandapower/MCP sin ejecutar estudios."""
        return engine_selection.obtener_capacidades_motores()

    @mcp.tool()
    def evaluar_preparacion_estudio(
        estudio: str,
        norma: str | None = None,
        tipo_falla: str | None = None,
        permitir_experimental: bool = False,
    ) -> dict:
        """Separa completitud de datos, aptitud del backend y disponibilidad del módulo."""
        return engine_selection.evaluar_preparacion_estudio(
            estudio=estudio,
            norma=norma,
            tipo_falla=tipo_falla,
            permitir_experimental=permitir_experimental,
        )

    @mcp.tool()
    def evaluar_cierre_p2() -> dict:
        """Evalúa el contrato de producto P2 v1 y la coherencia del modelo activo."""
        return p2_completion.evaluar_cierre_p2()

    @mcp.tool()
    def seleccionar_motor_estudio(
        estudio: str,
        norma: str | None = None,
        permitir_experimental: bool = False,
        tipo_falla: str | None = None,
    ) -> dict:
        """Indica backend, requisitos y aptitud actual; no despacha el cálculo automáticamente."""
        return engine_selection.seleccionar_motor_estudio(
            estudio=estudio,
            norma=norma,
            permitir_experimental=permitir_experimental,
            tipo_falla=tipo_falla,
        )

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
    def definir_secuencia_cero_fuente(
        r0_max_ohm: float,
        x0_max_ohm: float,
        r0_min_ohm: float | None = None,
        x0_min_ohm: float | None = None,
        fuente_referencia: str | None = None,
        fuente_url: str | None = None,
    ) -> dict:
        """Define R0/X0 explícitos de la red aguas arriba por escenario; no deriva Z0 desde Scc3."""
        result = zero_sequence.definir_fuente(
            r0_max_ohm=r0_max_ohm,
            x0_max_ohm=x0_max_ohm,
            r0_min_ohm=r0_min_ohm,
            x0_min_ohm=x0_min_ohm,
            fuente_referencia=fuente_referencia,
            fuente_url=fuente_url,
        )
        changed("definir_secuencia_cero_fuente")
        return result

    @mcp.tool()
    def definir_secuencia_cero_linea(
        nombre_elemento: str,
        r0_ohm_km: float,
        x0_ohm_km: float,
        c0_nf_km: float | None = None,
        fuente_referencia: str | None = None,
        fuente_url: str | None = None,
    ) -> dict:
        """Aplica R0/X0 y opcional C0 explícitos a una Line trifásica."""
        result = zero_sequence.definir_linea(
            nombre_elemento=nombre_elemento,
            r0_ohm_km=r0_ohm_km,
            x0_ohm_km=x0_ohm_km,
            c0_nf_km=c0_nf_km,
            fuente_referencia=fuente_referencia,
            fuente_url=fuente_url,
        )
        changed(f"definir_secuencia_cero_linea:{nombre_elemento}")
        return result

    @mcp.tool()
    def definir_secuencia_cero_transformador(
        nombre_elemento: str,
        uk0_percent: float,
        ur0_percent: float,
        magnetizing_z0_ratio_percent: float,
        magnetizing_r_over_x: float,
        leakage_share_hv: float,
        neutral_side: str | None = None,
        neutral_mode: str | None = None,
        rn_ohm: float | None = None,
        xn_ohm: float | None = None,
        fuente_referencia: str | None = None,
        fuente_url: str | None = None,
    ) -> dict:
        """Registra datos Z0 de transformador sin asumir Z0=Z1 ni proyectarlos silenciosamente a OpenDSS."""
        result = zero_sequence.definir_transformador(
            nombre_elemento=nombre_elemento,
            uk0_percent=uk0_percent,
            ur0_percent=ur0_percent,
            magnetizing_z0_ratio_percent=magnetizing_z0_ratio_percent,
            magnetizing_r_over_x=magnetizing_r_over_x,
            leakage_share_hv=leakage_share_hv,
            neutral_side=neutral_side,
            neutral_mode=neutral_mode,
            rn_ohm=rn_ohm,
            xn_ohm=xn_ohm,
            fuente_referencia=fuente_referencia,
            fuente_url=fuente_url,
        )
        changed(f"definir_secuencia_cero_transformador:{nombre_elemento}")
        return result

    @mcp.tool()
    def seleccionar_escenario_red(escenario: str) -> dict:
        """Activa el escenario máximo o mínimo y reaplica Z0 solo si existe para ese escenario."""
        result = professional_data.seleccionar_escenario_red(escenario)
        zero_sequence.reapply_active_source()
        changed(f"seleccionar_escenario_red:{escenario}")
        return result

    @mcp.tool()
    def obtener_secuencia_cero() -> dict:
        """Devuelve la ficha P2 de secuencia cero de fuente, líneas y transformadores."""
        return zero_sequence.snapshot()

    @mcp.tool()
    def obtener_datos_profesionales() -> dict:
        """Devuelve datos P2 positivos y homopolares con procedencia y derivaciones."""
        result = professional_data.snapshot()
        result["zero_sequence"] = zero_sequence.snapshot()
        return result

    # P3, P4 y P5 conservan registros separados. Cada mutación P5 que cambie
    # el modelo de protección invalida estudios posteriores vía on_model_change.
    ampacity_tools.register(mcp)
    iec60909_tools.register(mcp)
    protection_tools.register(mcp, on_model_change=changed)
    protection_tcc_tools.register(mcp, on_model_change=changed)
    protection_check_tools.register(mcp)
    protection_clearing_tools.register(mcp)
    protection_coordination_tools.register(mcp)
