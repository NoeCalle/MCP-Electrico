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

## [0.2.0] - Visualización de topología

### Herramientas agregadas

- `generar_diagrama_unifilar` — construye un grafo con NetworkX a partir
  de la topología activa en OpenDSS (buses, líneas, transformadores) y lo
  renderiza como HTML interactivo con Plotly. Layout jerárquico por
  profundidad BFS desde el bus fuente (apropiado para redes radiales).
  Cada bus se colorea según su voltaje en pu: verde (0.95–1.05),
  amarillo (0.90–1.10), rojo (fuera de rango o sin tensión / aislado).

### Motivación

OpenDSS tiene comandos de graficado nativos (`Plot Circuit`, `Plot
Profile`) pero dependen de ventanas gráficas del motor que no funcionan
de forma confiable en un flujo headless controlado vía
OpenDSSDirect.py/MCP. Generar el HTML nosotros mismos da control total
sobre el estilo y garantiza que funcione igual sin importar el entorno.

### Caso de estudio de referencia

- `examples/visualizar_hospital.py` — genera `diagrama_normal.html` y
  `diagrama_contingencia.html` a partir del mismo modelo de
  `hospital_basico.py`, mostrando visualmente cómo el bus de quirófanos
  queda sin tensión (rojo) al perderse su alimentador.

### Nueva dependencia

- `networkx`, `plotly` — agregadas a `requirements.txt`

## [0.3.0] - Diagrama enriquecido y caso multi-tablero

### Cambios en `generar_diagrama_unifilar`

- Las cargas y generadores ahora se dibujan como nodos propios (antes
  solo se veían los buses y las líneas/transformadores entre ellos).
  Cargas: cuadrados (rojos si están marcadas como críticas). Generadores:
  diamantes azules.
- Nuevo registro interno `_cargas_criticas` en `agregar_carga`: OpenDSS
  no tiene un atributo nativo para "carga crítica", así que se rastrea
  aparte para poder resaltarla visualmente.
- El HTML generado ahora incluye un panel lateral con el resumen del
  circuito (convergencia, pérdidas activas/reactivas, conteo de buses,
  transformadores, cargas, cargas críticas y generadores) y una leyenda
  de colores/símbolos — antes era solo el grafo, sin contexto.
- `simular_perdida_alimentador` se probó también sobre un transformador
  completo (no solo líneas) — funciona igual, sin cambios de código
  necesarios.

### Caso de estudio nuevo

- `examples/campus_hospitalario.py` — red más realista con una sola
  acometida MT alimentando tres transformadores independientes
  (quirófanos, hospitalización, administración), cada uno con varias
  cargas propias, y un generador de respaldo dedicado al tablero más
  crítico. Incluye contingencia N-1 sobre un transformador.

## [0.4.0] - Diagrama con símbolos de ingeniería eléctrica

### Cambio de tecnología: Plotly → SVG generado a mano

`generar_diagrama_unifilar` se reescribió completamente. Antes usaba
Plotly (nodos tipo grafo de red social: círculos y líneas genéricas).
Ahora genera SVG con convenciones reales de diagrama unifilar:

- **Buses**: barras horizontales gruesas (no círculos), coloreadas por
  voltaje pu, con el ancho de la barra ajustado automáticamente al
  número de elementos conectados.
- **Transformadores**: símbolo estándar de dos círculos superpuestos.
- **Interruptores**: rectángulo pequeño en cada derivación. Si el
  elemento está abierto (`dss.CktElement.IsOpen`), se dibuja con un gap
  visible y la etiqueta "ABIERTO" en rojo — así una contingencia N-1 se
  ve directamente en el diagrama, en el punto exacto donde se abrió el
  circuito, en vez de solo mover el bus afectado a un panel aparte.
- **Cargas**: triángulo colgando del bus (rojo + ⚠ si es crítica).
- **Generadores**: círculo con "G", conexión punteada (respaldo).

### Layout genérico (no hardcodeado a un caso)

El posicionamiento se calcula con un recorrido post-orden del árbol de
buses (vía `networkx.bfs_tree` desde el bus fuente): cada bus reserva
tanto espacio horizontal como necesiten sus hijos (transformadores aguas
abajo) y sus cargas/generadores propios. Funciona para cualquier
topología radial, sin importar cuántos niveles o ramas tenga.

**Limitación conocida**: si la red tiene anillos (mallada), el layout
dibuja un árbol de expansión desde la fuente — el resultado incluye
`topologia_radial_pura: false` como aviso cuando esto ocurre. El cálculo
eléctrico (flujo de potencia, cortocircuito) sí considera la red
completa; solo el *dibujo* se simplifica a un árbol.

### Cambios en el contrato de retorno

`generar_diagrama_unifilar` ahora devuelve `transformadores_dibujados` y
`topologia_radial_pura` en vez de `conexiones_dibujadas`. Se actualizó
`examples/visualizar_hospital.py` para reflejar esto.

### Dependencia removida

- `plotly` — ya no se usa (el SVG se genera directamente con Python, sin
  librería externa de gráficos). `networkx` se mantiene para el cálculo
  del árbol de expansión.


