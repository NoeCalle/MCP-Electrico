# Changelog

Registro de la evolución del servidor MCP para OpenDSS. Cada entrada indica
qué herramientas se agregaron, qué caso de estudio las motivó, y cualquier
corrección relevante.

## [0.1.0] - Versión inicial

### Herramientas incluidas

- `crear_circuito` — inicializa un circuito con tensión y frecuencia base
- `agregar_linea` — agrega tramos de línea/cable entre buses
- `agregar_transformador` — agrega transformadores MT/BT
- `agregar_carga` — agrega cargas, con flag `critica` para diferenciar
  cargas sensibles (quirófanos, UCI) de cargas generales
- `agregar_generador_respaldo` — modela grupos electrógenos o fuentes UPS
- `ejecutar_flujo_potencia` — power flow: voltajes por bus (pu) y pérdidas
- `ejecutar_cortocircuito` — corriente de falla trifásica en un bus
- `simular_perdida_alimentador` — análisis de contingencia N-1
- `listar_elementos` — inventario del modelo actual

### Correcciones aplicadas durante el desarrollo

- **Bases de tensión (pu) incorrectas**: OpenDSS requiere `Set
  VoltageBases=[...]` + `CalcVoltageBases` cada vez que se introduce un
  nuevo nivel de tensión o un nuevo bus, o los valores en por-unidad
  quedan mal calculados (se reportan como voltios absolutos, no pu). Se
  agregó recálculo automático en `agregar_transformador`, `agregar_linea`,
  y como salvaguarda en `ejecutar_flujo_potencia`.
- **Compatibilidad del SDK de MCP**: el import de `FastMCP` cambia según
  la versión del paquete `mcp` instalado (`mcp.server.fastmcp.FastMCP` en
  versiones antiguas, `mcp.server.mcpserver.MCPServer` en versiones
  recientes). Se agregó un bloque `try/except` para soportar ambas.

### Caso de estudio de referencia

- `examples/hospital_basico.py` — modela un hospital con acometida MT
  (13.2 kV), transformador de 500 kVA, tablero de quirófanos (carga
  crítica), tablero de iluminación general, y grupo electrógeno de
  respaldo. Valida flujo de potencia normal y contingencia N-1 sobre el
  alimentador a quirófanos.

### Pendiente (no incluido aún)

Ver README.md, sección de limitaciones, para el detalle de qué elementos
y modos de análisis de OpenDSS todavía no están expuestos como
herramientas MCP (LoadShape, PVSystem, Storage, Capacitor, RegControl,
modos Daily/Yearly/Harmonic, SAIDI/SAIFI formal, reconfiguración de red,
visualización de topología).
