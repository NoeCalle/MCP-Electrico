"""
Servidor MCP para OpenDSS.

La lógica eléctrica vive en mcp_electrico.core para poder probarla sin
arrancar el transporte MCP. Este archivo expone wrappers estables como tools.
"""

from __future__ import annotations

from mcp_electrico import core, visual_state
from mcp_electrico.visualization import generar_diagrama_unifilar as _generar_unifilar

try:
    from mcp.server.fastmcp import FastMCP as _MCPServerClass
except ImportError:
    from mcp.server.mcpserver import MCPServer as _MCPServerClass


mcp = _MCPServerClass("opendss-mcp")


@mcp.tool()
def crear_circuito(nombre: str, kv_base: float, frecuencia: int = 60) -> str:
    """Crea un circuito nuevo y limpia cualquier modelo/estado auxiliar previo."""
    resultado = core.crear_circuito(nombre, kv_base, frecuencia)
    visual_state.reset()
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
    """Agrega una línea o cable representado mediante parámetros de secuencia positiva."""
    return core.agregar_linea(
        nombre, bus1, bus2, longitud_km, fases, r1_ohm_km, x1_ohm_km
    )


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
    return core.agregar_transformador(
        nombre,
        bus_primario,
        bus_secundario,
        kva,
        kv_primario,
        kv_secundario,
        conexion_primario,
        conexion_secundario,
    )


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
    """Agrega una carga y permite escoger su símbolo en el unifilar.

    ``tipo_visual`` admite ``tablero`` (default), ``motor`` o ``carga``.
    La elección es únicamente gráfica y no cambia el modelo OpenDSS.
    """
    resultado = core.agregar_carga(nombre, bus, kw, kvar, fases, kv, critica)
    visual_state.set_load_type(nombre, tipo_visual)
    return resultado


@mcp.tool()
def configurar_tipo_carga_unifilar(nombre_carga: str, tipo_visual: str) -> dict:
    """Cambia el símbolo de una carga existente: tablero, motor o carga genérica."""
    return visual_state.set_load_type(nombre_carga, tipo_visual)


@mcp.tool()
def configurar_etiqueta_carga_unifilar(nombre_carga: str, etiqueta: str) -> dict:
    """Define un rótulo de ingeniería para una carga sin renombrarla en OpenDSS."""
    return visual_state.set_load_label(nombre_carga, etiqueta)


@mcp.tool()
def configurar_bus_unifilar(
    nombre_bus: str,
    rol: str = "auto",
    etiqueta: str = "",
) -> dict:
    """Configura si un bus se dibuja como barra física o conexión lógica.

    ``rol`` admite ``auto``, ``barra`` o ``conexion``.
    """
    return visual_state.configure_bus(nombre_bus, rol, etiqueta)


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
    """Configura la representación gráfica de un alimentador.

    ``dispositivos`` admite ``ats`` y ``ups``.
    ``proteccion`` admite ``breaker``, ``mccb``, ``acb``, ``fuse`` o
    ``isolator``. Los datos de conductor/protección son metadatos visuales y
    NO alteran el cálculo eléctrico de OpenDSS.
    """
    return visual_state.configure_feeder(
        nombre_elemento,
        etiqueta=etiqueta,
        dispositivos=dispositivos,
        fuente_alterna=fuente_alterna,
        proteccion=proteccion,
        conductor=conductor,
        corriente_nominal_a=corriente_nominal_a,
        capacidad_ruptura_ka=capacidad_ruptura_ka,
    )


@mcp.tool()
def obtener_configuracion_unifilar() -> dict:
    """Devuelve los metadatos de representación visual del circuito activo."""
    return visual_state.snapshot()


@mcp.tool()
def agregar_generador_respaldo(
    nombre: str, bus: str, kw: float, kv: float, fases: int = 3
) -> str:
    """Agrega un grupo electrógeno/modelo Generator de OpenDSS.

    No representa una UPS basada en inversor; ese modelo queda fuera del
    alcance actual para evitar atribuirle un comportamiento de falla incorrecto.
    """
    return core.agregar_generador_respaldo(nombre, bus, kw, kv, fases)


@mcp.tool()
def ejecutar_flujo_potencia() -> dict:
    """Resuelve el flujo de potencia y devuelve voltajes pu y pérdidas."""
    return core.ejecutar_flujo_potencia()


@mcp.tool()
def ejecutar_cortocircuito(bus_falla: str) -> dict:
    """Calcula magnitudes de Isc por fase en modo FaultStudy."""
    return core.ejecutar_cortocircuito(bus_falla)


@mcp.tool()
def abrir_elemento(nombre_elemento: str) -> dict:
    """Abre una línea/transformador y deja el circuito resuelto en ese estado."""
    return core.abrir_elemento(nombre_elemento)


@mcp.tool()
def cerrar_elemento(nombre_elemento: str) -> dict:
    """Cierra una línea/transformador y vuelve a resolver el circuito."""
    return core.cerrar_elemento(nombre_elemento)


@mcp.tool()
def simular_perdida_alimentador(
    nombre_elemento: str, restaurar: bool = True
) -> dict:
    """Simula una contingencia N-1."""
    return core.simular_perdida_alimentador(nombre_elemento, restaurar)


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
    """Genera un unifilar técnico SVG/HTML del estado actualmente resuelto.

    Por defecto usa modo de ingeniería, sin leyenda ni branding. Para depurar
    el modelo puede usarse ``modo="diagnostico"``. ``orientacion`` admite
    ``vertical`` y ``horizontal``.
    """
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


if __name__ == "__main__":
    mcp.run()
