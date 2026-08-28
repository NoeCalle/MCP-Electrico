"""Tools MCP P5C para capacidad de corte y soportabilidad térmica."""

from __future__ import annotations

from . import protection_checks


def register(mcp) -> None:
    @mcp.tool()
    def obtener_referencias_proteccion_p5c() -> dict:
        """Devuelve referencias objetivo y alcance explícito de P5C."""
        return protection_checks.obtener_referencias_p5c()

    @mcp.tool()
    def evaluar_capacidad_corte_p5c(
        dispositivo: str,
        corriente_falla_ka: float,
        tension_operacion_kv: float,
        fuente_corriente: str,
        tipo_falla: str | None = None,
        escenario: str | None = None,
    ) -> dict:
        """Compara la falla con Icu o poder de corte sin sustituir ratings."""
        return protection_checks.evaluar_capacidad_corte(
            dispositivo=dispositivo,
            corriente_falla_ka=corriente_falla_ka,
            tension_operacion_kv=tension_operacion_kv,
            fuente_corriente=fuente_corriente,
            tipo_falla=tipo_falla,
            escenario=escenario,
        )

    @mcp.tool()
    def evaluar_soportabilidad_termica_conductor_p5c(
        elemento: str,
        corriente_falla_ka: float,
        tiempo_despeje_s: float,
        seccion_mm2: float,
        k_a_sqrt_s_per_mm2: float,
        fuente_k: str,
        fuente_tiempo: str,
        fuente_seccion: str | None = None,
    ) -> dict:
        """Evalúa I²t <= k²S² con k, sección y tiempo explícitos/trazables."""
        return protection_checks.evaluar_soportabilidad_termica_conductor(
            elemento=elemento,
            corriente_falla_ka=corriente_falla_ka,
            tiempo_despeje_s=tiempo_despeje_s,
            seccion_mm2=seccion_mm2,
            k_a_sqrt_s_per_mm2=k_a_sqrt_s_per_mm2,
            fuente_k=fuente_k,
            fuente_tiempo=fuente_tiempo,
            fuente_seccion=fuente_seccion,
        )
