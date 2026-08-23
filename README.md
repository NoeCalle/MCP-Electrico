# MCP Eléctrico — OpenDSS

Servidor MCP para modelar, simular e inspeccionar redes eléctricas MT/BT con
[OpenDSS](https://www.epri.com/pages/sa/opendss) mediante
`OpenDSSDirect.py`.

El objetivo del proyecto es ofrecer a un cliente MCP herramientas eléctricas
de alto nivel —crear circuitos, agregar elementos, resolver flujo de potencia,
cortocircuito, contingencias y generar diagramas unifilares— sin darle acceso
directo e irrestricto al intérprete de OpenDSS.

> **Estado:** proyecto educativo / experimental. No sustituye un estudio
> eléctrico profesional ni software validado para diseño, coordinación de
> protecciones o seguridad de arco eléctrico.

## 1. Instalación

Requisitos: Python 3.10 o superior.

```bash
git clone https://github.com/NoeCalle/MCP-Electrico.git
cd MCP-Electrico

python -m venv venv
```

Windows:

```powershell
venv\Scripts\activate
pip install -r requirements.txt
```

Linux/macOS:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

Verificación rápida:

```bash
python -c "import opendssdirect; import mcp; import networkx; print('OK')"
```

## 2. Probar sin un cliente MCP

Los ejemplos importan directamente las funciones de `server.py`:

```bash
python examples/hospital_basico.py
python examples/visualizar_hospital.py
python examples/campus_hospitalario.py
python examples/arc_flash_campus.py
python examples/unifilar_tecnico.py
```

El último ejemplo genera `unifilar_tecnico.svg` y `unifilar_tecnico.html`
con fuente, interruptores, transformador, barras, alimentadores, motor,
tableros, ATS, UPS, grupo electrógeno y tierra.

Para ejecutar la suite de regresión:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

También existe un workflow de GitHub Actions que ejecuta `pytest`, genera el
unifilar técnico de referencia y lo conserva como artefacto en cada PR.

## 3. Conectar a un cliente MCP

Ejemplo para Claude Desktop en Windows:

```json
{
  "mcpServers": {
    "opendss": {
      "command": "C:\\ruta\\MCP-Electrico\\venv\\Scripts\\python.exe",
      "args": ["C:\\ruta\\MCP-Electrico\\server.py"]
    }
  }
}
```

En macOS/Linux, usa el ejecutable Python del `venv` y la ruta absoluta a
`server.py`.

## 4. Herramientas disponibles

| Herramienta | Función |
|---|---|
| `crear_circuito` | Inicia un circuito y limpia el estado auxiliar previo |
| `agregar_linea` | Agrega línea/cable con R1/X1 |
| `agregar_transformador` | Agrega transformador trifásico de dos devanados |
| `agregar_carga` | Agrega carga, criticidad y tipo visual opcional |
| `configurar_tipo_carga_unifilar` | Elige símbolo de tablero, motor o carga genérica |
| `configurar_alimentador_unifilar` | Añade etiqueta y anotaciones ATS/UPS a un alimentador |
| `obtener_configuracion_unifilar` | Devuelve los metadatos visuales del circuito activo |
| `agregar_generador_respaldo` | Agrega un grupo electrógeno mediante `Generator` de OpenDSS |
| `ejecutar_flujo_potencia` | Resuelve voltajes por bus y pérdidas |
| `ejecutar_cortocircuito` | Ejecuta `FaultStudy` y devuelve magnitudes de Isc |
| `abrir_elemento` | Abre un elemento y deja el modelo resuelto en ese estado |
| `cerrar_elemento` | Cierra un elemento y vuelve a resolver |
| `simular_perdida_alimentador` | Ejecuta una contingencia N-1 con restauración opcional |
| `listar_elementos` | Lista buses y elementos principales |
| `obtener_netlist` | Exporta y devuelve los archivos DSS con su contenido |
| `generar_diagrama_unifilar` | Genera un unifilar técnico SVG/HTML del estado resuelto |
| `estimar_arc_flash_lee` | Estimación educativa de energía incidente por Lee |
| `calcular_arc_flash` | Alias compatible con versiones anteriores |

### 4.1 Unifilar técnico SVG

La visualización ya no usa la estética de un grafo genérico. El renderer sigue
reglas explícitas de diagrama unifilar:

1. flujo principal de energía de arriba hacia abajo;
2. barras representadas como líneas horizontales gruesas;
3. una línea por alimentador y derivaciones ortogonales;
4. interruptor en cabecera de cada alimentador;
5. simbología consistente para fuente, transformador, tablero, motor, ATS,
   UPS, generador y tierra;
6. alimentadores principales `F-01`, `F-02`, etc. y circuitos secundarios
   `C-01`, `C-02`, etc.;
7. transformadores con potencia, relación de tensión y conexión Δ/Y cuando la
   información está disponible en OpenDSS;
8. buses con tensión nominal y valor en pu;
9. elementos abiertos y barras desenergizadas diferenciados visualmente.

Ejemplo:

```python
agregar_carga(
    "motor_bomba",
    "mcc_01",
    kw=75,
    kvar=30,
    kv=0.48,
    tipo_visual="motor",
)

configurar_alimentador_unifilar(
    "Line.f_critico",
    dispositivos=["ats", "ups"],
    fuente_alterna="Generator.ge_01",
)

ejecutar_flujo_potencia()
generar_diagrama_unifilar("hospital.html", titulo="Hospital — Diagrama unifilar")
```

Si la ruta termina en `.html`, se genera además un `.svg` vectorial compañero.
La especificación visual completa está en `docs/UNIFILAR_TECNICO.md`.

**ATS y UPS son, por ahora, anotaciones de representación.** Sirven para que el
unifilar documente la arquitectura prevista sin afirmar que OpenDSS ya modela
su electrónica interna, transferencia, autonomía o contribución de falla. Esas
anotaciones no cambian impedancias ni resultados eléctricos.

## 5. Contingencias N-1: estado coherente

`simular_perdida_alimentador()` distingue dos formas de trabajo.

### Resultado temporal y restauración automática

```python
resultado = simular_perdida_alimentador(
    "Line.alimentador_quirofanos",
    restaurar=True,
)
```

El elemento se abre, OpenDSS resuelve la contingencia, se capturan los
resultados y luego se restaura **el estado original** del elemento. Después de
restaurarlo, OpenDSS ejecuta `Solve` otra vez.

Así se evita el estado inconsistente de versiones anteriores, donde la
topología podía quedar cerrada mientras los resultados eléctricos todavía
correspondían al elemento abierto.

### Mantener la contingencia activa

```python
resultado = simular_perdida_alimentador(
    "Line.alimentador_quirofanos",
    restaurar=False,
)

generar_diagrama_unifilar("contingencia.html")
```

En este caso el elemento permanece abierto y el circuito permanece resuelto
en contingencia. El unifilar puede mostrar el interruptor abierto y marcar los
buses que ya no tienen camino eléctrico hacia la fuente.

Para volver a operación normal:

```python
cerrar_elemento("Line.alimentador_quirofanos")
```

## 6. Cargas críticas

Las cargas marcadas con `critica=True` se conservan como metadato del modelo.

Durante una contingencia se devuelve, para cada carga crítica:

- bus de conexión;
- voltajes en pu;
- indicador de si conserva tensión;
- lista de cargas críticas sin tensión.

El umbral interno usado para distinguir una barra esencialmente
desenergizada de una barra con tensión **no es un criterio de cumplimiento de
calidad de servicio**.

Al crear un circuito nuevo, este registro se limpia junto con OpenDSS para no
arrastrar metadatos de un modelo anterior.

## 7. Exportación DSS

`obtener_netlist()` ya no devuelve solamente un mensaje de “exportado”.

```python
resultado = obtener_netlist("mi_exportacion")
```

Devuelve:

- directorio de exportación;
- nombre del `Master.dss` cuando exista;
- número de archivos;
- nombre, ruta y contenido de cada archivo `.dss`.

Esto permite que el cliente MCP inspeccione o persista el modelo realmente
generado por OpenDSS.

## 8. Arc Flash: alcance y seguridad

`estimar_arc_flash_lee()` implementa únicamente la ecuación simplificada de
Lee para fines de aprendizaje y estimación de orden de magnitud.

La herramienta devuelve:

- energía incidente en J/cm²;
- energía incidente en cal/cm²;
- frontera de arco estimada.

**No implementa el modelo empírico completo de IEEE 1584-2018.**

Además, el servidor **no convierte la energía incidente calculada en una
“categoría PPE”**. La selección de EPP requiere aplicar el método y la edición
vigentes de la norma de seguridad correspondiente; no debe inferirse
automáticamente de esta herramienta.

`calcular_arc_flash()` se mantiene como alias para no romper clientes que ya
usaban la API v0.5, pero ahora devuelve la misma salida segura de
`estimar_arc_flash_lee()`.

## 9. Cortocircuito

`dss.Bus.Isc()` entrega componentes reales e imaginarias intercaladas. El
servidor calcula explícitamente la magnitud de cada fasor:

```text
|I| = sqrt(Re(I)^2 + Im(I)^2)
```

Esto evita reportar como corriente de falla únicamente la parte real del
fasor.

## 10. Generadores y UPS

`agregar_generador_respaldo()` representa un **grupo electrógeno** mediante el
objeto `Generator` de OpenDSS.

Una UPS basada en electrónica de potencia no se presenta como equivalente a
un generador síncrono. Su contribución a falla, controles y límites del
inversor requieren un modelo específico y quedan pendientes para una versión
posterior.

## 11. Arquitectura

La lógica está separada por responsabilidad:

```text
MCP-Electrico/
├── server.py
├── mcp_electrico/
│   ├── __init__.py
│   ├── core.py
│   ├── visualization.py
│   ├── visual_state.py
│   └── visual_symbols.py
├── docs/
│   └── UNIFILAR_TECNICO.md
├── examples/
│   └── unifilar_tecnico.py
├── tests/
├── requirements.txt
└── requirements-dev.txt
```

- `server.py`: transporte MCP y contratos públicos de las herramientas.
- `mcp_electrico/core.py`: lógica eléctrica y estado del modelo.
- `mcp_electrico/visualization.py`: topología, layout y render SVG.
- `mcp_electrico/visual_symbols.py`: biblioteca vectorial de símbolos.
- `mcp_electrico/visual_state.py`: metadatos de representación que no alteran
  el cálculo eléctrico.
- `tests/`: regresiones numéricas, de estado y de representación.

Esta separación permite probar el motor eléctrico sin arrancar MCP y evolucionar
la simbología sin mezclarla con la lógica de cálculo.

## 12. Limitaciones actuales

La versión actual todavía simplifica varios aspectos:

- varios elementos usan parámetros de secuencia positiva R1/X1;
- no hay modelado detallado de R0/X0 o matrices de impedancia;
- no hay curvas TCC ni coordinación de protecciones;
- ATS/UPS pueden documentarse visualmente, pero todavía no tienen modelo
  eléctrico detallado propio;
- no hay `LoadShape`, PV, Storage, capacitores, armónicos ni simulación anual;
- el unifilar prioriza redes radiales; en redes malladas usa un árbol de
  expansión para el dibujo;
- el SVG es un unifilar técnico, no un plano CAD contractual ni una biblioteca
  normativa completa de símbolos IEC/ANSI;
- Arc Flash es solo una estimación educativa por Lee.

El siguiente salto de madurez debe centrarse en **casos de validación con
resultados de referencia**, antes de ampliar agresivamente el número de
herramientas.
