"""
Servidor MCP para OpenDSS
Permite a Claude modelar y simular redes de distribución MT/BT
(hospitales, edificios, instalaciones críticas) mediante OpenDSSDirect.py
"""

import opendssdirect as dss
import networkx as nx

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


# Registro interno de nombres de carga marcados como "críticos" al
# agregarlos. OpenDSS no tiene un atributo nativo para esto, así que lo
# rastreamos aparte para poder resaltarlos en el diagrama unifilar.
_cargas_criticas: set = set()

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
    if critica:
        _cargas_criticas.add(nombre)
    else:
        _cargas_criticas.discard(nombre)
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
    # dss.Bus.Isc() devuelve pares [real, imaginario] intercalados por
    # fase (NO magnitud/ángulo) — hay que calcular la magnitud del
    # fasor explícitamente, o se reporta la parte real como si fuera
    # la corriente total, lo cual subestima o distorsiona el resultado.
    raw = dss.Bus.Isc()
    partes_reales = raw[0::2]
    partes_imaginarias = raw[1::2]
    magnitudes = [
        (re ** 2 + im ** 2) ** 0.5
        for re, im in zip(partes_reales, partes_imaginarias)
    ]

    return {
        "bus": bus_falla,
        "corriente_falla_amperios": [round(m, 2) for m in magnitudes],
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
    Genera un diagrama unifilar (archivo HTML) del circuito actualmente
    cargado, usando convenciones de dibujo de ingeniería eléctrica:
    buses como barras horizontales, transformadores como símbolo de dos
    círculos superpuestos, cargas como triángulos (rojos si son
    críticas), generadores como círculo con "G", e interruptores como
    pequeños rectángulos en cada derivación. El layout se calcula
    automáticamente para la topología actual (no está fijado a un caso
    particular). Pensado para redes radiales/arbóreas; si la red tiene
    anillos, se dibuja un árbol de expansión desde la fuente y se nota
    en el resultado.

    Requiere haber corrido ejecutar_flujo_potencia() antes para que los
    voltajes mostrados sean significativos.

    Args:
        ruta_salida: Ruta del archivo HTML a generar
    """
    buses_info = {}
    for bus in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus)
        kvbase = dss.Bus.kVBase()
        vpu_fases = dss.Bus.puVmagAngle()[0::2]
        vpu = sum(vpu_fases) / len(vpu_fases) if vpu_fases else 0.0
        buses_info[bus] = {"kvbase": kvbase, "vpu": vpu}

    if not buses_info:
        return {"error": "El circuito no tiene buses definidos. Crea un circuito primero."}

    # --- Grafo de conexiones (líneas y transformadores) ---
    G = nx.Graph()
    G.add_nodes_from(buses_info.keys())
    tipo_conexion, nombre_conexion, conexion_abierta = {}, {}, {}
    for name in dss.Lines.AllNames():
        dss.Lines.Name(name)
        b1, b2 = dss.Lines.Bus1().split(".")[0], dss.Lines.Bus2().split(".")[0]
        abierta = dss.CktElement.IsOpen(1, 0)
        G.add_edge(b1, b2)
        tipo_conexion[(b1, b2)] = tipo_conexion[(b2, b1)] = "Línea"
        nombre_conexion[(b1, b2)] = nombre_conexion[(b2, b1)] = name
        conexion_abierta[(b1, b2)] = conexion_abierta[(b2, b1)] = abierta
    for name in dss.Transformers.AllNames():
        dss.Transformers.Name(name)
        bs = dss.CktElement.BusNames()
        b1, b2 = bs[0].split(".")[0], bs[1].split(".")[0]
        abierta = dss.CktElement.IsOpen(1, 0)
        G.add_edge(b1, b2)
        tipo_conexion[(b1, b2)] = tipo_conexion[(b2, b1)] = "Transformador"
        nombre_conexion[(b1, b2)] = nombre_conexion[(b2, b1)] = name
        conexion_abierta[(b1, b2)] = conexion_abierta[(b2, b1)] = abierta

    nodos_fuente = [b for b in G.nodes if "source" in b.lower()]
    raiz = nodos_fuente[0] if nodos_fuente else list(G.nodes)[0]

    # Árbol de expansión desde la raíz. Si la red tiene anillos, esto
    # simplifica el dibujo a un árbol (la conexión "extra" del anillo no
    # se dibuja), aunque el cálculo eléctrico sí consideró el anillo
    # completo. Se reporta en el resultado si esto ocurrió.
    arbol = nx.bfs_tree(G, raiz)
    es_radial_puro = nx.is_tree(G)
    buses_desconectados = [b for b in buses_info if b not in arbol.nodes]

    # --- Cargas y generadores por bus ---
    hojas_por_bus = {}
    for name in dss.Loads.AllNames():
        dss.Loads.Name(name)
        bus = dss.CktElement.BusNames()[0].split(".")[0]
        hojas_por_bus.setdefault(bus, []).append({
            "tipo": "carga", "nombre": name,
            "kw": dss.Loads.kW(), "kvar": dss.Loads.kvar(),
            "critica": name in _cargas_criticas,
        })
    for name in dss.Generators.AllNames():
        dss.Generators.Name(name)
        bus = dss.CktElement.BusNames()[0].split(".")[0]
        hojas_por_bus.setdefault(bus, []).append({
            "tipo": "generador", "nombre": name, "kw": dss.Generators.kW(),
        })

    # --- Layout: recorrido post-orden del árbol asignando posiciones X ---
    LEAF_W, TIER_H = 100, 175
    pos_bus, span_bus, pos_hoja = {}, {}, {}
    cursor = [70]

    def layout(bus, profundidad):
        hijos = list(arbol.successors(bus)) if bus in arbol else []
        hojas = hojas_por_bus.get(bus, [])
        xs = [layout(h, profundidad + 1) for h in hijos]
        for i, hoja in enumerate(hojas):
            x = cursor[0]
            cursor[0] += LEAF_W
            pos_hoja[(bus, i)] = x
            xs.append(x)
        if not xs:
            x = cursor[0]
            cursor[0] += LEAF_W
            xs = [x]
        bus_x = sum(xs) / len(xs)
        pos_bus[bus] = (bus_x, 70 + profundidad * TIER_H)
        span_bus[bus] = (min(xs), max(xs))
        return bus_x

    layout(raiz, 0)

    profundidad_max = max((nx.shortest_path_length(arbol, raiz, b) for b in arbol.nodes), default=0)
    ancho = max(cursor[0] + 60, 760)
    alto = 70 + profundidad_max * TIER_H + 250

    def color_por_voltaje(vpu, kvbase):
        if kvbase == 0:
            return "#e6584f"
        if 0.95 <= vpu <= 1.05:
            return "#4fd1a5"
        if 0.90 <= vpu <= 1.10:
            return "#e8c547"
        return "#e6584f"

    # --- Construcción del SVG ---
    partes = []

    def esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;")

    for bus, (bx, by) in pos_bus.items():
        x0, x1 = span_bus[bus]
        x0, x1 = x0 - 35, x1 + 35
        info = buses_info[bus]
        color = color_por_voltaje(info["vpu"], info["kvbase"])
        vtxt = "SIN TENSIÓN" if info["kvbase"] == 0 else f'{info["vpu"]:.4f} pu'
        partes.append(
            f'<line x1="{x0:.0f}" y1="{by:.0f}" x2="{x1:.0f}" y2="{by:.0f}" '
            f'stroke="{color}" stroke-width="4" stroke-linecap="round"/>'
        )
        partes.append(
            f'<text x="{x0:.0f}" y="{by-14:.0f}" class="lbl-bus">{esc(bus)}</text>'
        )
        partes.append(
            f'<text x="{x0:.0f}" y="{by+18:.0f}" class="lbl-kv" fill="{color}">'
            f'{info["kvbase"]:.3f} kV · {vtxt}</text>'
        )

        # Conexiones hacia hijos (transformador o línea)
        for hijo in (list(arbol.successors(bus)) if bus in arbol else []):
            hx, hy = pos_bus[hijo]
            tipo = tipo_conexion.get((bus, hijo), "Línea")
            nombre = nombre_conexion.get((bus, hijo), "")
            abierta = conexion_abierta.get((bus, hijo), False)
            color_wire = "#e6584f" if abierta else "#5b6b8c"
            partes.append(f'<line x1="{hx:.0f}" y1="{by:.0f}" x2="{hx:.0f}" y2="{by+30:.0f}" stroke="{color_wire}" stroke-width="1.8" fill="none"/>')
            if abierta:
                # Interruptor abierto: gap visible con las dos hojas separadas
                partes.append(f'<line x1="{hx-9:.0f}" y1="{by+30:.0f}" x2="{hx-2:.0f}" y2="{by+34:.0f}" stroke="#e6584f" stroke-width="2"/>')
                partes.append(f'<line x1="{hx+2:.0f}" y1="{by+36:.0f}" x2="{hx+9:.0f}" y2="{by+40:.0f}" stroke="#e6584f" stroke-width="2"/>')
                partes.append(f'<text x="{hx+16:.0f}" y="{by+40:.0f}" class="lbl-elem" fill="#e6584f">ABIERTO</text>')
            else:
                partes.append(
                    f'<rect x="{hx-9:.0f}" y="{by+30:.0f}" width="18" height="10" '
                    f'fill="none" stroke="#c9d3e3" stroke-width="1.5"/>'
                )
            if tipo == "Transformador":
                c1y, c2y = by + 62, by + 94
                col_trafo = "#7a5a44" if abierta else "#c98a55"
                partes.append(f'<circle cx="{hx:.0f}" cy="{c1y:.0f}" r="20" fill="none" stroke="{col_trafo}" stroke-width="1.8"/>')
                partes.append(f'<circle cx="{hx:.0f}" cy="{c2y:.0f}" r="20" fill="none" stroke="{col_trafo}" stroke-width="1.8"/>')
                partes.append(f'<line x1="{hx:.0f}" y1="{c2y+20:.0f}" x2="{hx:.0f}" y2="{hy:.0f}" stroke="{color_wire}" stroke-width="1.8" fill="none"/>')
                partes.append(f'<text x="{hx+28:.0f}" y="{c1y+4:.0f}" class="lbl-elem">{esc(nombre)}</text>')
            else:
                partes.append(f'<line x1="{hx:.0f}" y1="{by+40:.0f}" x2="{hx:.0f}" y2="{hy:.0f}" stroke="{color_wire}" stroke-width="1.8" fill="none"/>')
                partes.append(f'<text x="{hx+16:.0f}" y="{(by+hy)/2:.0f}" class="lbl-elem">{esc(nombre)}</text>')

        # Cargas y generadores colgando de este bus
        for i, hoja in enumerate(hojas_por_bus.get(bus, [])):
            hx = pos_hoja[(bus, i)]
            y0 = by + 30
            if hoja["tipo"] == "carga":
                critica = hoja["critica"]
                col = "#e6584f" if critica else "#c98a55"
                partes.append(f'<line x1="{hx:.0f}" y1="{by:.0f}" x2="{hx:.0f}" y2="{y0:.0f}" stroke="{col}" stroke-width="1.8"/>')
                partes.append(f'<rect x="{hx-8:.0f}" y="{y0:.0f}" width="16" height="8" fill="none" stroke="{col}" stroke-width="1.3"/>')
                partes.append(f'<line x1="{hx:.0f}" y1="{y0+8:.0f}" x2="{hx:.0f}" y2="{y0+35:.0f}" stroke="{col}" stroke-width="1.8"/>')
                partes.append(
                    f'<polygon points="{hx-10:.0f},{y0+35:.0f} {hx+10:.0f},{y0+35:.0f} {hx:.0f},{y0+53:.0f}" '
                    f'fill="none" stroke="{col}" stroke-width="1.8"/>'
                )
                marca = " ⚠" if critica else ""
                partes.append(f'<text x="{hx:.0f}" y="{y0+70:.0f}" text-anchor="middle" class="lbl-elem" fill="{col}">{esc(hoja["nombre"])}</text>')
                partes.append(f'<text x="{hx:.0f}" y="{y0+82:.0f}" text-anchor="middle" class="lbl-elem" fill="{col}">{hoja["kw"]:.0f} kW{marca}</text>')
            else:
                cy = y0 + 30
                partes.append(f'<line x1="{hx:.0f}" y1="{by:.0f}" x2="{hx:.0f}" y2="{y0:.0f}" stroke="#4a9de8" stroke-width="1.8" stroke-dasharray="3,3"/>')
                partes.append(f'<circle cx="{hx:.0f}" cy="{cy:.0f}" r="20" fill="none" stroke="#4a9de8" stroke-width="1.8"/>')
                partes.append(f'<text x="{hx:.0f}" y="{cy+5:.0f}" text-anchor="middle" class="lbl-bus" fill="#4a9de8" font-size="13">G</text>')
                partes.append(f'<text x="{hx:.0f}" y="{cy+38:.0f}" text-anchor="middle" class="lbl-elem" fill="#4a9de8">{esc(hoja["nombre"])}</text>')
                partes.append(f'<text x="{hx:.0f}" y="{cy+50:.0f}" text-anchor="middle" class="lbl-elem" fill="#4a9de8">{hoja["kw"]:.0f} kW</text>')

    # Buses desconectados del árbol (ej. tras abrir un elemento en una
    # contingencia): se dibujan aparte, en rojo, sin conexiones.
    for i, bus in enumerate(buses_desconectados):
        bx, by = ancho - 140, 70 + i * 60
        partes.append(f'<line x1="{bx-35:.0f}" y1="{by:.0f}" x2="{bx+35:.0f}" y2="{by:.0f}" stroke="#e6584f" stroke-width="4" stroke-linecap="round"/>')
        partes.append(f'<text x="{bx-35:.0f}" y="{by-10:.0f}" class="lbl-bus">{esc(bus)}</text>')
        partes.append(f'<text x="{bx-35:.0f}" y="{by+18:.0f}" class="lbl-kv" fill="#e6584f">SIN CONEXIÓN A LA FUENTE</text>')

    convergio = dss.Solution.Converged()
    perdidas_kw, perdidas_kvar = dss.Circuit.Losses()
    perdidas_kw, perdidas_kvar = perdidas_kw / 1000, perdidas_kvar / 1000
    n_cargas = len(dss.Loads.AllNames())
    n_criticas = len(_cargas_criticas)
    n_gens = len(dss.Generators.AllNames())
    n_trafos = len(dss.Transformers.AllNames())

    resumen = (
        f"Convergencia: {'SÍ' if convergio else 'NO'} · Pérdidas: {perdidas_kw:.3f} kW · "
        f"{len(buses_info)} buses · {n_trafos} transformadores · "
        f"{n_cargas} cargas ({n_criticas} críticas) · {n_gens} generadores"
    )
    if not es_radial_puro:
        resumen += " · ⚠ red con anillo(s): se dibuja un árbol de expansión desde la fuente"

    svg_contenido = "\n      ".join(partes)

    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<title>Diagrama unifilar — {esc(dss.Circuit.Name())}</title>
<style>
  :root {{ --bg:#0b1220; --panel:#121b2e; --border:#22314d; --ink:#e7ecf5;
    --ink-dim:#8fa0bd; --copper:#d97a3f; --mono:'JetBrains Mono',Consolas,monospace; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font-family:-apple-system,sans-serif; padding:28px 22px; }}
  .wrap {{ max-width:{ancho+40}px; margin:0 auto; }}
  .eyebrow {{ font-family:var(--mono); font-size:11px; letter-spacing:.12em;
    color:var(--copper); text-transform:uppercase; margin-bottom:6px; }}
  h1 {{ font-size:20px; margin:0 0 16px; font-weight:600; }}
  .panel {{ background:var(--panel); border:1px solid var(--border);
    border-radius:10px; padding:20px; overflow-x:auto; }}
  svg {{ display:block; }}
  text {{ font-family:var(--mono); }}
  .lbl-bus {{ font-size:12px; fill:var(--ink); font-weight:600; }}
  .lbl-kv {{ font-size:10.5px; }}
  .lbl-elem {{ font-size:9.5px; fill:var(--ink-dim); }}
  .wire {{ stroke:#5b6b8c; stroke-width:1.8; fill:none; }}
  .footer {{ margin-top:14px; font-family:var(--mono); font-size:11.5px;
    color:var(--ink-dim); }}
  .legend {{ display:flex; flex-wrap:wrap; gap:16px; margin-top:12px;
    font-family:var(--mono); font-size:10.5px; color:var(--ink-dim); }}
</style></head>
<body><div class="wrap">
  <div class="eyebrow">OpenDSS MCP · diagrama generado dinámicamente</div>
  <h1>{esc(dss.Circuit.Name())}</h1>
  <div class="panel">
    <svg viewBox="0 0 {ancho:.0f} {alto:.0f}" width="{ancho:.0f}" xmlns="http://www.w3.org/2000/svg">
      {svg_contenido}
    </svg>
    <div class="footer">{esc(resumen)}</div>
    <div class="legend">
      <span>— Barra (bus)</span>
      <span>▭ Interruptor</span>
      <span>◎◎ Transformador</span>
      <span>▽ Carga</span>
      <span style="color:#e6584f">▽ Carga crítica</span>
      <span style="color:#4a9de8">◯G Generador/respaldo</span>
    </div>
  </div>
</div></body></html>"""

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(html)

    return {
        "archivo_generado": ruta_salida,
        "buses_dibujados": len(buses_info),
        "buses_desconectados": buses_desconectados,
        "cargas_dibujadas": n_cargas,
        "generadores_dibujados": n_gens,
        "transformadores_dibujados": n_trafos,
        "topologia_radial_pura": es_radial_puro,
    }


@mcp.tool()
def calcular_arc_flash(
    voltaje_kv: float,
    corriente_falla_ka: float,
    tiempo_despeje_s: float,
    distancia_trabajo_mm: float = 455,
) -> dict:
    """
    Estima la energía incidente de arco eléctrico (arc flash) usando el
    método simplificado de Lee (ecuación adoptada por IEEE 1584-2002
    para configuraciones al aire libre, tensiones >15kV, o parámetros
    fuera del rango del modelo empírico completo de IEEE 1584-2018).

    ADVERTENCIA IMPORTANTE: este es un método simplificado para fines
    de aprendizaje y estimación de orden de magnitud. NO reemplaza un
    estudio de arc flash normado (IEEE 1584-2018 completo, hecho en
    ETAP u otro software validado) para determinar EPP real en un
    proyecto. El método de Lee tiende a ser conservador (sobreestima)
    para equipos en gabinete cerrado comparado con el modelo empírico
    completo. Los resultados de esta herramienta NUNCA deben usarse
    para seleccionar equipo de protección personal en una instalación
    real sin validación de un ingeniero eléctrico calificado.

    Args:
        voltaje_kv: Tensión del sistema en kV
        corriente_falla_ka: Corriente de falla franca trifásica en kA
                             (obtenida de ejecutar_cortocircuito)
        tiempo_despeje_s: Tiempo de despeje de la protección en segundos
                          (dato de entrada — este MCP no modela curvas
                          TCC de interruptores/fusibles todavía)
        distancia_trabajo_mm: Distancia de trabajo en mm (típico: 455mm
                               / 18in para tableros BT, mayor para MT)
    """
    IE_J = 2.142e6 * voltaje_kv * corriente_falla_ka * tiempo_despeje_s / (distancia_trabajo_mm ** 2)
    IE_cal = IE_J / 4.184

    # Frontera de arco: distancia donde la energía incidente cae a
    # 5.02 J/cm² (≈1.2 cal/cm², umbral de quemadura de 2do grado curable)
    IE_frontera_J = 5.02
    frontera_mm = (2.142e6 * voltaje_kv * corriente_falla_ka * tiempo_despeje_s / IE_frontera_J) ** 0.5

    # Categorías de PPE aproximadas (NFPA 70E) — umbrales de referencia,
    # verificar contra la edición vigente de la norma para uso real.
    if IE_cal < 1.2:
        categoria = "Sin requerimiento mínimo (por debajo del umbral de 1.2 cal/cm²)"
    elif IE_cal < 4:
        categoria = "Categoría 1 (~4 cal/cm²)"
    elif IE_cal < 8:
        categoria = "Categoría 2 (~8 cal/cm²)"
    elif IE_cal < 25:
        categoria = "Categoría 3 (~25 cal/cm²)"
    elif IE_cal < 40:
        categoria = "Categoría 4 (~40 cal/cm²)"
    else:
        categoria = "Por encima de 40 cal/cm² — requiere controles remotos, no solo EPP"

    return {
        "energia_incidente_cal_cm2": round(IE_cal, 2),
        "energia_incidente_J_cm2": round(IE_J, 2),
        "frontera_arco_mm": round(frontera_mm, 1),
        "frontera_arco_in": round(frontera_mm / 25.4, 1),
        "categoria_ppe_aproximada": categoria,
        "metodo": "Lee simplificado (IEEE 1584-2002) — NO usar para EPP real, solo aprendizaje",
        "parametros_entrada": {
            "voltaje_kv": voltaje_kv,
            "corriente_falla_ka": corriente_falla_ka,
            "tiempo_despeje_s": tiempo_despeje_s,
            "distancia_trabajo_mm": distancia_trabajo_mm,
        },
    }


if __name__ == "__main__":
    mcp.run()
