"""
Servidor MCP para OpenDSS.

La lógica eléctrica vive en mcp_electrico.core para poder probarla sin
arrancar el transporte MCP. Este archivo expone wrappers estables como tools.
"""

from __future__ import annotations

from mcp_electrico import core
from mcp_electrico.visualization import generar_diagrama_unifilar as _generar_unifilar

try:
    from mcp.server.fastmcp import FastMCP as _MCPServerClass
except ImportError:
    from mcp.server.mcpserver import MCPServer as _MCPServerClass


mcp = _MCPServerClass("opendss-mcp")


@mcp.tool()
def crear_circuito(nombre: str, kv_base: float, frecuencia: int = 60) -> str:
    """Crea un circuito nuevo y limpia cualquier modelo/estado auxiliar previo."""
    return core.crear_circuito(nombre, kv_base, frecuencia)


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
) -> str:
    """Agrega una carga y opcionalmente la marca como crítica para contingencias."""
    return core.agregar_carga(nombre, bus, kw, kvar, fases, kv, critica)


@mcp.tool()
def agregar_generador_respaldo(
    nombre: str, bus: str, kw: float, kv: float, fases: int = 3
) -> str:
    """
    Agrega un grupo electrógeno/modelo Generator de OpenDSS.

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
    """
    Simula una contingencia N-1.

    Con restaurar=True (por defecto), devuelve resultados de la contingencia
    pero restaura y resuelve el estado original antes de terminar.
    Con restaurar=False, deja el elemento abierto y la contingencia activa
    para inspeccionarla o generar un diagrama unifilar.
    """
    return core.simular_perdida_alimentador(nombre_elemento, restaurar)


@mcp.tool()
def listar_elementos() -> dict:
    """Lista buses, líneas, transformadores, cargas y generadores."""
    return core.listar_elementos()


@mcp.tool()
def obtener_netlist(directorio: str = "temp_export") -> dict:
    """
    Exporta el circuito y devuelve todos los archivos DSS y su contenido.

    A diferencia de versiones anteriores, esta herramienta sí retorna el
    netlist generado, no solo un mensaje indicando que se guardó.
    """
    return core.obtener_netlist(directorio)


@mcp.tool()
def generar_diagrama_unifilar(ruta_salida: str = "diagrama_red.html") -> dict:
    """
    Genera un unifilar SVG del estado actualmente resuelto.

    Los elementos abiertos se muestran como abiertos y los buses sin camino
    eléctrico hacia la fuente se identifican como desconectados.
    """
    return _generar_unifilar(ruta_salida)


@mcp.tool()
def estimar_arc_flash_lee(
    voltaje_kv: float,
    corriente_falla_ka: float,
    tiempo_despeje_s: float,
    distancia_trabajo_mm: float = 455,
) -> dict:
    """
    Estimación educativa de energía incidente mediante el método de Lee.

    No implementa IEEE 1584-2018 completo y no asigna categorías PPE.
    """
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
    """
    Alias compatible con la API v0.5.

    Ejecuta la misma estimación educativa de Lee y ya no convierte el
    resultado numérico en una categoría PPE.
    """
    return core.calcular_arc_flash(
        voltaje_kv, corriente_falla_ka, tiempo_despeje_s, distancia_trabajo_mm
    )


if __name__ == "__main__":
    mcp.run()
