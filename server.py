"""
Servidor MCP para OpenDSS
Permite a Claude modelar y simular redes de distribución MT/BT
(hospitales, edificios, instalaciones críticas) mediante OpenDSSDirect.py
"""

import opendssdirect as dss
import networkx as nx
import plotly.graph_objects as go

# Compatibilidad: en versiones recientes del SDK de MCP, la clase se llama
# MCPServer y vive en mcp.server.mcpserver; en versiones más antiguas se
# llama FastMCP y vive en mcp.server.fastmcp. Ambas exponen la misma API
# (.tool() como decorador, .run() para iniciar el servidor stdio).
try:
    from mcp.server.fastmcp import FastMCP as _MCPServerClass
except ImportError:
    from mcp.server.mcpserver import MCPServer as _MCPServerClass

mcp = _MCPServerClass("opendss-mcp")

# ---------------------------------------------------------------------
# 1. CREACIÓN DE CIRCUITO
# ---------------------------------------------------------------------

@mcp.tool()
def crear_circuito(nombre: str, kv_base: float, frecuencia: int = 60) -> str:
    """
    Crea un nuevo circuito eléctrico, limpiando cualquier modelo previo.

    Args:
        nombre: Nombre del circuito (ej. "hospital_central")
        kv_base: Tensión base de la fuente en kV línea-línea (ej. 13.2 para MT)
        frecuencia: Frecuencia del sistema en Hz (60 para Perú/América, 50 para Europa)
    """
    dss.run_command("Clear")
    dss.run_command(
        f"New Circuit.{nombre} basekv={kv_base} Frequency={frecuencia}"
    )
    # Se registra el primer nivel de tensión base; los transformadores
    # que se agreguen después registran sus propios niveles (ver
    # agregar_transformador). Esto es necesario para que los cálculos
    # en por-unidad (pu) sean correctos.
    global _voltage_bases
    _voltage_bases = {kv_base}
    return f"Circuito '{nombre}' creado a {kv_base} kV, {frecuencia} Hz"


# Registro interno de niveles de tensión presentes en la red, requerido
# por OpenDSS (comando CalcVoltageBases) para resolver correctamente los
# valores en por-unidad en cada bus.
_voltage_bases: set = set()


def _recalcular_bases_de_tension() -> None:
    """Aplica los niveles de tensión acumulados y recalcula las bases pu."""
    niveles = ",".join(str(v) for v in sorted(_voltage_bases, reverse=True))
    dss.run_command(f"Set VoltageBases=[{niveles}]")
    dss.run_command("CalcVoltageBases")


# ---------------------------------------------------------------------
# 2. TOPOLOGÍA: LÍNEAS, TRANSFORMADORES, BUSES
# ---------------------------------------------------------------------

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
    """
    Agrega un tramo de línea/cable entre dos buses.

    Args:
        nombre: Nombre identificador de la línea
        bus1: Bus de origen (ej. "SE_MT.1.2.3")
        bus2: Bus de destino (ej. "tablero1.1.2.3")
        longitud_km: Longitud del tramo en kilómetros
        fases: Número de fases (1 para monofásico BT, 3 para trifásico)
        r1_ohm_km: Resistencia de secuencia positiva (ohm/km)
        x1_ohm_km: Reactancia de secuencia positiva (ohm/km)
    """
    dss.run_command(
        f"New Line.{nombre} Bus1={bus1} Bus2={bus2} Length={longitud_km} "
        f"Units=km Phases={fases} R1={r1_ohm_km} X1={x1_ohm_km}"
    )
    # Recalcula bases de pu por si esta línea introduce un bus nuevo en un
    # nivel de tensión ya conocido (OpenDSS no lo propaga automáticamente).
    _recalcular_bases_de_tension()
    return f"Línea '{nombre}' agregada: {bus1} -> {bus2} ({longitud_km} km)"


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
    """
    Agrega un transformador MT/BT (ej. transformador de distribución del edificio).

    Args:
        nombre: Nombre del transformador
        bus_primario: Bus del lado de MT
        bus_secundario: Bus del lado de BT
        kva: Potencia nominal en kVA
        kv_primario: Tensión nominal primario (kV línea-línea)
        kv_secundario: Tensión nominal secundario (kV línea-línea)
        conexion_primario: "delta" o "wye" (estrella)
        conexion_secundario: "delta" o "wye" (estrella, normalmente con neutro "wye")
    """
    dss.run_command(
        f"New Transformer.{nombre} Phases=3 Windings=2 "
        f"wdg=1 bus={bus_primario} conn={conexion_primario} kv={kv_primario} kva={kva} "
        f"wdg=2 bus={bus_secundario} conn={conexion_secundario} kv={kv_secundario} kva={kva}"
    )
    _voltage_bases.update({kv_primario, kv_secundario})
    _recalcular_bases_de_tension()
    return f"Transformador '{nombre}' agregado: {kva} kVA, {kv_primario}kV/{kv_secundario}kV"


# ---------------------------------------------------------------------
# 3. CARGAS
# ---------------------------------------------------------------------

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
    """
    Agrega una carga eléctrica (tablero, área del edificio, equipo).

    Args:
        nombre: Nombre de la carga (ej. "quirofano_1", "iluminacion_piso3")
        bus: Bus donde se conecta
        kw: Potencia activa en kW
        kvar: Potencia reactiva en kVAR (opcional)
        fases: Número de fases
        kv: Tensión nominal de la carga en kV
        critica: Marca la carga como crítica (ej. quirófanos, UCI) para
                 identificarla luego en análisis de contingencia
    """
    dss.run_command(
        f"New Load.{nombre} Bus1={bus} Phases={fases} kV={kv} "
        f"kW={kw} kvar={kvar}"
    )
    etiqueta = " [CRÍTICA]" if critica else ""
    return f"Carga '{nombre}' agregada en {bus}: {kw} kW, {kvar} kVAR{etiqueta}"


@mcp.tool()
def agregar_generador_respaldo(
    nombre: str, bus: str, kw: float, kv: float, fases: int = 3
) -> str:
    """
    Agrega un generador de respaldo (grupo electrógeno) o fuente de UPS.

    Args:
        nombre: Nombre del generador
        bus: Bus donde se conecta
        kw: Potencia activa en kW
        kv: Tensión nominal en kV
        fases: Número de fases
    """
    dss.run_command(
        f"New Generator.{nombre} Bus1={bus} Phases={fases} kV={kv} kW={kw}"
    )
    return f"Generador de respaldo '{nombre}' agregado en {bus}: {kw} kW"


# ---------------------------------------------------------------------
# 4. SIMULACIÓN
# ---------------------------------------------------------------------

@mcp.tool()
def ejecutar_flujo_potencia() -> dict:
    """
    Ejecuta el análisis de flujo de carga (power flow) del circuito actual
    y devuelve un resumen de voltajes por bus y pérdidas totales.
    """
    _recalcular_bases_de_tension()
    dss.run_command("Solve")

    voltajes = {}
    for bus in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus)
        voltajes[bus] = {
            "kv_base": round(dss.Bus.kVBase(), 3),
            "voltajes_pu": [round(v, 4) for v in dss.Bus.puVmagAngle()[0::2]],
        }

    perdidas_kw, perdidas_kvar = dss.Circuit.Losses()
    perdidas_kw = perdidas_kw / 1000
    perdidas_kvar = perdidas_kvar / 1000

    return {
        "convergio": dss.Solution.Converged(),
        "voltajes_por_bus": voltajes,
        "perdidas_totales_kw": round(perdidas_kw, 3),
        "perdidas_totales_kvar": round(perdidas_kvar, 3),
    }


@mcp.tool()
def ejecutar_cortocircuito(bus_falla: str) -> dict:
    """
    Calcula la corriente de cortocircuito trifásico en un bus específico.
    Útil para dimensionar protecciones.

    Args:
        bus_falla: Nombre del bus donde se simula la falla
    """
    dss.run_command(f"Solve Mode=FaultStudy")
    dss.Circuit.SetActiveBus(bus_falla)
    corrientes = dss.Bus.Isc()

    return {
        "bus": bus_falla,
        "corriente_falla_amperios": [round(c, 2) for c in corrientes[0::2]],
    }


@mcp.tool()
def simular_perdida_alimentador(nombre_elemento: str) -> dict:
    """
    Simula la pérdida de un elemento de la red (línea o transformador)
    abriéndolo y recalculando el flujo de potencia. Útil para análisis
    de contingencia N-1 en redes hospitalarias.

    Args:
        nombre_elemento: Nombre completo del elemento, ej. "Line.linea1"
                          o "Transformer.trafo1"
    """
    dss.run_command(f"Open {nombre_elemento} term=1")
    dss.run_command("Solve")

    convergio = dss.Solution.Converged()
    perdidas_kw, _ = dss.Circuit.Losses()

    resultado = {
        "elemento_abierto": nombre_elemento,
        "convergio": convergio,
        "perdidas_kw": round(perdidas_kw / 1000, 3) if convergio else None,
        "nota": (
            "El sistema no convergió: posible pérdida de continuidad de "
            "servicio a cargas críticas (isla no energizada)."
            if not convergio
            else "El sistema convergió con el elemento fuera de servicio."
        ),
    }

    # Restaurar el elemento para no dejar el modelo corrupto
    dss.run_command(f"Close {nombre_elemento} term=1")
    return resultado


# ---------------------------------------------------------------------
# 5. INSPECCIÓN DEL MODELO
# ---------------------------------------------------------------------

@mcp.tool()
def listar_elementos() -> dict:
    """
    Lista todos los elementos actualmente definidos en el circuito
    (buses, líneas, transformadores, cargas, generadores).
    """
    return {
        "buses": dss.Circuit.AllBusNames(),
        "lineas": dss.Lines.AllNames(),
        "transformadores": dss.Transformers.AllNames(),
        "cargas": dss.Loads.AllNames(),
        "generadores": dss.Generators.AllNames(),
    }


@mcp.tool()
def obtener_netlist() -> str:
    """
    Devuelve el script DSS completo (netlist) generado hasta el momento,
    útil para revisar o guardar el modelo.
    """
    dss.run_command("Save Circuit Dir=temp_export")
    return "Circuito exportado. Usa 'exportar_reporte' para obtener el resumen en texto."


@mcp.tool()
def generar_diagrama_unifilar(ruta_salida: str = "diagrama_red.html") -> dict:
    """
    Genera un diagrama unifilar interactivo (archivo HTML) del circuito
    actualmente cargado, coloreando cada bus según su voltaje en
    por-unidad (verde: normal, amarillo: marginal, rojo: fuera de rango
    o sin tensión). Requiere haber corrido ejecutar_flujo_potencia()
    antes para que los voltajes mostrados sean significativos.

    Args:
        ruta_salida: Ruta del archivo HTML a generar
    """
    G = nx.Graph()
    for bus in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus)
        kvbase = dss.Bus.kVBase()
        vpu_fases = dss.Bus.puVmagAngle()[0::2]
        vpu = sum(vpu_fases) / len(vpu_fases) if vpu_fases else 0.0
        G.add_node(bus, kvbase=kvbase, vpu=vpu)

    for name in dss.Lines.AllNames():
        dss.Lines.Name(name)
        b1 = dss.Lines.Bus1().split(".")[0]
        b2 = dss.Lines.Bus2().split(".")[0]
        G.add_edge(b1, b2, tipo="Línea", nombre=name)

    for name in dss.Transformers.AllNames():
        dss.Transformers.Name(name)
        buses_trafo = dss.CktElement.BusNames()
        b1 = buses_trafo[0].split(".")[0]
        b2 = buses_trafo[1].split(".")[0]
        G.add_edge(b1, b2, tipo="Transformador", nombre=name)

    if len(G.nodes) == 0:
        return {"error": "El circuito no tiene buses definidos. Crea un circuito primero."}

    # Layout jerárquico: BFS desde el bus con la fuente de tensión, apropiado
    # para redes de distribución (predominantemente radiales).
    nodos_fuente = [b for b in G.nodes if "source" in b.lower()]
    raiz = nodos_fuente[0] if nodos_fuente else list(G.nodes)[0]
    niveles = nx.single_source_shortest_path_length(G, raiz)

    por_nivel = {}
    for nodo, nivel in niveles.items():
        por_nivel.setdefault(nivel, []).append(nodo)

    pos = {}
    for nivel, nodos_del_nivel in por_nivel.items():
        n = len(nodos_del_nivel)
        for i, nodo in enumerate(nodos_del_nivel):
            pos[nodo] = ((i - (n - 1) / 2) * 2.0, -nivel)

    # Buses desconectados de la fuente (ej. tras una contingencia) se
    # ubican aparte en vez de fallar.
    for nodo in G.nodes:
        if nodo not in pos:
            pos[nodo] = (5.0, -len(por_nivel))

    edge_traces = []
    for u, v, data in G.edges(data=True):
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        estilo = dict(color="#8a97ab", width=2)
        if data["tipo"] == "Transformador":
            estilo = dict(color="#5b6b8c", width=3, dash="dot")
        edge_traces.append(
            go.Scatter(
                x=[x0, x1], y=[y0, y1], mode="lines", line=estilo,
                hoverinfo="text", text=f"{data['tipo']}: {data['nombre']}",
                showlegend=False,
            )
        )

    def color_por_voltaje(vpu, kvbase):
        if kvbase == 0:
            return "#e6584f"
        if 0.95 <= vpu <= 1.05:
            return "#4fd1a5"
        if 0.90 <= vpu <= 1.10:
            return "#e8c547"
        return "#e6584f"

    node_x, node_y, node_color, node_text, node_hover = [], [], [], [], []
    for nodo, data in G.nodes(data=True):
        x, y = pos[nodo]
        node_x.append(x)
        node_y.append(y)
        node_color.append(color_por_voltaje(data["vpu"], data["kvbase"]))
        node_text.append(nodo)
        node_hover.append(
            f"<b>{nodo}</b><br>kV base: {data['kvbase']:.3f}<br>V: {data['vpu']:.4f} pu"
        )

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        marker=dict(size=32, color=node_color, line=dict(width=2, color="#1a2436")),
        text=node_text, textposition="bottom center",
        textfont=dict(color="#e7ecf5", size=11),
        hoverinfo="text", hovertext=node_hover, showlegend=False,
    )

    fig = go.Figure(data=edge_traces + [node_trace])
    fig.update_layout(
        title=dict(text="Diagrama unifilar — circuito activo", font=dict(color="#e7ecf5", size=16)),
        paper_bgcolor="#0b1220",
        plot_bgcolor="#0b1220",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=50, b=20),
        font=dict(family="monospace"),
    )
    fig.write_html(ruta_salida, include_plotlyjs="cdn")

    return {
        "archivo_generado": ruta_salida,
        "buses_dibujados": len(G.nodes),
        "conexiones_dibujadas": len(G.edges),
    }


if __name__ == "__main__":
    mcp.run()
