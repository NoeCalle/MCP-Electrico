"""
Servidor MCP para OpenDSS.

La lógica eléctrica vive en mcp_electrico.core y mcp_electrico.studies. Este
archivo orquesta las herramientas MCP, registra revisiones y mantiene
sincronizado el workspace HTML sin mezclar UI con el motor OpenDSS.
"""

from __future__ import annotations

from pathlib import Path

from mcp_electrico import (
    conductor_tools,
    core,
    studies,
    visual_state,
    workspace,
    workspace_state,
    workspace_studies_view,
)
from mcp_electrico.visualization import generar_diagrama_unifilar as _generar_unifilar

try:
    from mcp.server.fastmcp import FastMCP as _MCPServerClass
except ImportError:
    from mcp.server.mcpserver import MCPServer as _MCPServerClass


mcp = _MCPServerClass("opendss-mcp")


def _enhance_workspace_if_present() -> dict:
    """Añade las vistas de estudios después de regenerar el HTML base."""
    state = workspace.get_state()
    path = Path(state["config"]["ruta_salida"]).expanduser()
    if not path.exists():
        return {"ok": True, "skipped": True, "reason": "workspace aún no generado"}
    return workspace_studies_view.enhance_file(path, workspace_state.snapshot())


def _regenerate_workspace() -> dict:
    result = workspace.safe_regenerate()
    if result.get("ok") and not result.get("skipped"):
        result["study_views"] = _enhance_workspace_if_present()
    return result


def _record_flow(flow: dict, action: str) -> None:
    """Registra solución base + métricas detalladas en la misma revisión."""
    workspace_state.record_solution(flow["powerflow"], "powerflow", action=action)
    workspace_state.record_study("flow", flow, action=f"{action}:detalle")


def _refresh_after_model_change(action: str) -> None:
    workspace_state.mark_model_changed(action)
    _regenerate_workspace()


def _refresh_after_visual_change(action: str) -> None:
    workspace_state.mark_visual_changed(action)
    _regenerate_workspace()


def _refresh_after_solved_change(action: str) -> None:
    """Marca cambio persistente y deja una solución de flujo vigente."""
    workspace_state.mark_model_changed(action)
    flow = studies.analizar_flujo_operacion()
    _record_flow(flow, f"{action}:resolver")
    _regenerate_workspace()


@mcp.tool()
def configurar_workspace(
    ruta_salida: str = "workspace.html",
    titulo: str | None = None,
    auto_regenerar: bool = True,
) -> dict:
    """Configura el visor HTML persistente del circuito activo.

    El workspace es solo una vista del modelo. ChatGPT continúa siendo la
    interfaz conversacional y OpenDSS continúa siendo el motor de cálculo.
    """
    result = workspace.configure(ruta_salida, titulo, auto_regenerar)
    _enhance_workspace_if_present()
    return result


@mcp.tool()
def obtener_estado_workspace() -> dict:
    """Devuelve ruta, revisiones, validez de resultados y estudios registrados."""
    return workspace.get_state()


@mcp.tool()
def regenerar_workspace() -> dict:
    """Regenera manualmente el HTML, SVG y vistas de estudios."""
    result = workspace.regenerate()
    result["study_views"] = _enhance_workspace_if_present()
    return result


@mcp.tool()
def crear_circuito(nombre: str, kv_base: float, frecuencia: int = 60) -> str:
    """Crea un circuito nuevo y reinicia también el workspace persistente."""
    resultado = core.crear_circuito(nombre, kv_base, frecuencia)
    visual_state.reset()
    workspace.new_circuit("crear_circuito")
    _enhance_workspace_if_present()
    return resultado


@mcp.tool()
def agregar_linea(
    nombre: str,
    bus1: str,
    bus2: str,
    longitud_km: float,
    fases: int = 3,
    r1_ohm_km: float = 0.3,
    x1_ohm_km: float = 0.4,
) -> str:
    """Agrega una línea/cable y marca el workspace como MODIFICADO."""
    resultado = core.agregar_linea(
        nombre, bus1, bus2, longitud_km, fases, r1_ohm_km, x1_ohm_km
    )
    _refresh_after_model_change(f"agregar_linea:{nombre}")
    return resultado


@mcp.tool()
def agregar_transformador(
    nombre: str,
    bus_primario: str,
    bus_secundario: str,
    kva: float,
    kv_primario: float,
    kv_secundario: float,
    conexion_primario: str = "delta",
    conexion_secundario: str = "wye",
) -> str:
    """Agrega un transformador trifásico de dos devanados."""
    resultado = core.agregar_transformador(
        nombre,
        bus_primario,
        bus_secundario,
        kva,
        kv_primario,
        kv_secundario,
        conexion_primario,
        conexion_secundario,
    )
    _refresh_after_model_change(f"agregar_transformador:{nombre}")
    return resultado


@mcp.tool()
def agregar_carga(
    nombre: str,
    bus: str,
    kw: float,
    kvar: float = 0,
    fases: int = 3,
    kv: float = 0.22,
    critica: bool = False,
    tipo_visual: str = "tablero",
) -> str:
    """Agrega una carga y permite escoger su símbolo en el unifilar."""
    resultado = core.agregar_carga(nombre, bus, kw, kvar, fases, kv, critica)
    visual_state.set_load_type(nombre, tipo_visual)
    _refresh_after_model_change(f"agregar_carga:{nombre}")
    return resultado


@mcp.tool()
def configurar_tipo_carga_unifilar(nombre_carga: str, tipo_visual: str) -> dict:
    """Cambia el símbolo de una carga sin invalidar la solución eléctrica."""
    resultado = visual_state.set_load_type(nombre_carga, tipo_visual)
    _refresh_after_visual_change(f"tipo_visual_carga:{nombre_carga}")
    return resultado


@mcp.tool()
def configurar_etiqueta_carga_unifilar(nombre_carga: str, etiqueta: str) -> dict:
    """Define un rótulo de ingeniería sin renombrar el elemento OpenDSS."""
    resultado = visual_state.set_load_label(nombre_carga, etiqueta)
    _refresh_after_visual_change(f"etiqueta_carga:{nombre_carga}")
    return resultado


@mcp.tool()
def configurar_bus_unifilar(
    nombre_bus: str,
    rol: str = "auto",
    etiqueta: str = "",
) -> dict:
    """Configura si un bus se dibuja como barra física o conexión lógica."""
    resultado = visual_state.configure_bus(nombre_bus, rol, etiqueta)
    _refresh_after_visual_change(f"configurar_bus:{nombre_bus}")
    return resultado


@mcp.tool()
def configurar_alimentador_unifilar(
    nombre_elemento: str,
    etiqueta: str = "",
    dispositivos: list[str] | None = None,
    fuente_alterna: str | None = None,
    proteccion: str = "breaker",
    conductor: str = "",
    corriente_nominal_a: float | None = None,
    capacidad_ruptura_ka: float | None = None,
) -> dict:
    """Configura metadatos visuales de un alimentador sin tocar OpenDSS."""
    resultado = visual_state.configure_feeder(
        nombre_elemento,
        etiqueta=etiqueta,
        dispositivos=dispositivos,
        fuente_alterna=fuente_alterna,
        proteccion=proteccion,
        conductor=conductor,
        corriente_nominal_a=corriente_nominal_a,
        capacidad_ruptura_ka=capacidad_ruptura_ka,
    )
    _refresh_after_visual_change(f"configurar_alimentador:{nombre_elemento}")
    return resultado


@mcp.tool()
def obtener_configuracion_unifilar() -> dict:
    """Devuelve los metadatos de representación visual del circuito activo."""
    return visual_state.snapshot()


@mcp.tool()
def agregar_generador_respaldo(
    nombre: str, bus: str, kw: float, kv: float, fases: int = 3
) -> str:
    """Agrega un grupo electrógeno/modelo Generator de OpenDSS."""
    resultado = core.agregar_generador_respaldo(nombre, bus, kw, kv, fases)
    _refresh_after_model_change(f"agregar_generador:{nombre}")
    return resultado


@mcp.tool()
def ejecutar_flujo_potencia() -> dict:
    """Resuelve flujo y actualiza también la vista detallada del workspace."""
    flow = studies.analizar_flujo_operacion()
    _record_flow(flow, "ejecutar_flujo_potencia")
    _regenerate_workspace()
    # Compatibilidad: esta tool conserva el payload histórico de powerflow.
    return flow["powerflow"]


@mcp.tool()
def analizar_flujo_operacion() -> dict:
    """Devuelve flujo detallado por alimentador y actualiza el workspace."""
    flow = studies.analizar_flujo_operacion()
    _record_flow(flow, "analizar_flujo_operacion")
    _regenerate_workspace()
    return flow


@mcp.tool()
def analizar_caida_tension(limite_pct: float = 3.0) -> dict:
    """Analiza ΔV por alimentador con un límite configurable por el usuario.

    El valor por defecto de 3 % NO se presenta como requisito normativo
    universal. OpenDSS resuelve las tensiones y el MCP deriva la comparación
    bus1→bus2 sobre la revisión vigente.
    """
    result = studies.analizar_caida_tension(limite_pct)
    flow = result["flow"]
    _record_flow(flow, "analizar_caida_tension:resolver")
    voltage_result = {k: v for k, v in result.items() if k != "flow"}
    workspace_state.record_study(
        "voltage_drop", voltage_result, action="analizar_caida_tension"
    )
    _regenerate_workspace()
    return voltage_result


@mcp.tool()
def ejecutar_cortocircuito(bus_falla: str) -> dict:
    """Calcula Isc y restaura después una solución de flujo para el workspace.

    FaultStudy cambia el modo de solución de OpenDSS. El resultado de falla se
    conserva como estudio, pero el visor vuelve a una solución de flujo normal
    para no mezclar tensiones de modos distintos en el unifilar persistente.
    """
    resultado = core.ejecutar_cortocircuito(bus_falla)
    workspace_state.record_study("short_circuit", resultado, "ejecutar_cortocircuito")
    flow = studies.analizar_flujo_operacion()
    _record_flow(flow, "restaurar_flujo_tras_cortocircuito")
    _regenerate_workspace()
    return resultado


@mcp.tool()
def abrir_elemento(nombre_elemento: str) -> dict:
    """Abre un elemento, resuelve y sincroniza la revisión persistente."""
    resultado = core.abrir_elemento(nombre_elemento)
    _refresh_after_solved_change(f"abrir_elemento:{nombre_elemento}")
    return resultado


@mcp.tool()
def cerrar_elemento(nombre_elemento: str) -> dict:
    """Cierra un elemento, resuelve y sincroniza la revisión persistente."""
    resultado = core.cerrar_elemento(nombre_elemento)
    _refresh_after_solved_change(f"cerrar_elemento:{nombre_elemento}")
    return resultado


@mcp.tool()
def simular_perdida_alimentador(
    nombre_elemento: str, restaurar: bool = True
) -> dict:
    """Simula una contingencia N-1 y la registra en el workspace."""
    resultado = core.simular_perdida_alimentador(nombre_elemento, restaurar)
    if restaurar:
        workspace_state.record_study(
            "contingency", resultado, f"contingencia:{nombre_elemento}"
        )
        flow = studies.analizar_flujo_operacion()
        _record_flow(flow, "restaurar_tras_contingencia")
        _regenerate_workspace()
    else:
        workspace_state.mark_model_changed(f"contingencia_activa:{nombre_elemento}")
        workspace_state.record_study(
            "contingency", resultado, f"contingencia:{nombre_elemento}"
        )
        flow = studies.analizar_flujo_operacion()
        _record_flow(flow, "resolver_contingencia_activa")
        _regenerate_workspace()
    return resultado


@mcp.tool()
def listar_elementos() -> dict:
    """Lista buses, líneas, transformadores, cargas y generadores."""
    return core.listar_elementos()


@mcp.tool()
def obtener_netlist(directorio: str = "temp_export") -> dict:
    """Exporta el circuito y devuelve todos los archivos DSS y su contenido."""
    return core.obtener_netlist(directorio)


@mcp.tool()
def generar_diagrama_unifilar(
    ruta_salida: str = "diagrama_red.html",
    mostrar_leyenda: bool = False,
    titulo: str | None = None,
    modo: str = "ingenieria",
    orientacion: str = "vertical",
    mostrar_marca: bool = False,
    mostrar_reglas: bool = False,
) -> dict:
    """Genera un unifilar técnico SVG/HTML independiente del workspace."""
    return _generar_unifilar(
        ruta_salida=ruta_salida,
        mostrar_leyenda=mostrar_leyenda,
        titulo=titulo,
        modo=modo,
        orientacion=orientacion,
        mostrar_marca=mostrar_marca,
        mostrar_reglas=mostrar_reglas,
    )


@mcp.tool()
def estimar_arc_flash_lee(
    voltaje_kv: float,
    corriente_falla_ka: float,
    tiempo_despeje_s: float,
    distancia_trabajo_mm: float = 455,
) -> dict:
    """Estimación educativa de energía incidente mediante el método de Lee."""
    return core.estimar_arc_flash_lee(
        voltaje_kv, corriente_falla_ka, tiempo_despeje_s, distancia_trabajo_mm
    )


@mcp.tool()
def calcular_arc_flash(
    voltaje_kv: float,
    corriente_falla_ka: float,
    tiempo_despeje_s: float,
    distancia_trabajo_mm: float = 455,
) -> dict:
    """Alias compatible con la API v0.5."""
    return core.calcular_arc_flash(
        voltaje_kv, corriente_falla_ka, tiempo_despeje_s, distancia_trabajo_mm
    )


conductor_tools.register(mcp, _refresh_after_model_change)


if __name__ == "__main__":
    mcp.run()
