# MCP Eléctrico — OpenDSS

Servidor MCP para modelar, simular e inspeccionar redes eléctricas MT/BT con
[OpenDSS](https://www.epri.com/pages/sa/opendss) mediante
`OpenDSSDirect.py`.

El objetivo del proyecto es ofrecer a un cliente MCP herramientas eléctricas
de alto nivel —crear circuitos, agregar elementos, resolver flujo de potencia,
analizar caída de tensión, cortocircuito, contingencias y generar diagramas
unifilares— sin darle acceso directo e irrestricto al intérprete de OpenDSS.

Además del diálogo mediante ChatGPT/MCP, el proyecto puede mantener un
**workspace HTML persistente** que actúa como visor técnico del circuito activo.
El HTML no contiene un segundo chatbot ni usa una API de modelos: ChatGPT sigue
siendo la interfaz conversacional, OpenDSS sigue siendo el motor eléctrico y el
workspace es una vista estructurada del estado, propiedades y estudios.

> **Estado:** plataforma en desarrollo con módulos en distintos niveles de madurez.
> Flujo de potencia, caída de tensión, biblioteca de conductores y ampacidad P3-v1
> están `VALIDATED_WITH_LIMITATIONS` dentro de alcances publicados. IEC 60909,
> coordinación/TCC, IEEE 1584 y expediente profesional completo continúan pendientes.
> La herramienta no sustituye la revisión ni responsabilidad del ingeniero.

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
python examples/workspace_hospital.py
```

`unifilar_tecnico.py` genera `unifilar_tecnico.svg` y
`unifilar_tecnico.html`. `workspace_hospital.py` genera un
`workspace_hospital.html` persistente con unifilar, inspector técnico,
propiedades, flujo de potencia, caída de tensión y botones para impresión/PDF y
descarga SVG.

Para ejecutar la suite de regresión:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

GitHub Actions ejecuta `pytest`, genera el unifilar técnico y el workspace de
referencia con estudios y conserva ambos como artefactos en cada PR.

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
| `configurar_workspace` | Configura ruta, título y regeneración automática del visor HTML |
| `obtener_estado_workspace` | Devuelve revisiones, validez de resultados y estudios registrados |
| `regenerar_workspace` | Fuerza la regeneración del HTML, SVG y vistas de estudios |
| `crear_circuito` | Inicia un circuito y limpia el estado auxiliar previo |
| `agregar_linea` | Agrega línea/cable con R1/X1 |
| `agregar_transformador` | Agrega transformador trifásico de dos devanados |
| `agregar_carga` | Agrega carga, criticidad y tipo visual opcional |
| `configurar_tipo_carga_unifilar` | Elige símbolo de tablero, motor o carga genérica |
| `configurar_etiqueta_carga_unifilar` | Define rótulo de ingeniería sin renombrar OpenDSS |
| `configurar_bus_unifilar` | Fuerza bus como barra física, conexión lógica o auto |
| `configurar_alimentador_unifilar` | Añade etiqueta, protección, conductor y anotaciones ATS/UPS |
| `obtener_configuracion_unifilar` | Devuelve los metadatos visuales del circuito activo |
| `agregar_generador_respaldo` | Agrega un grupo electrógeno mediante `Generator` de OpenDSS |
| `ejecutar_flujo_potencia` | Resuelve voltajes/pérdidas y actualiza el estudio detallado `flow` |
| `analizar_flujo_operacion` | Devuelve corriente, kW/kvar y cargabilidad disponible por alimentador |
| `analizar_caida_tension` | Calcula ΔV por `Line` contra un límite configurable por el usuario |
| `ejecutar_cortocircuito` | Ejecuta `FaultStudy` y devuelve magnitudes de Isc |
| `abrir_elemento` | Abre un elemento y deja el modelo resuelto en ese estado |
| `cerrar_elemento` | Cierra un elemento y vuelve a resolver |
| `simular_perdida_alimentador` | Ejecuta una contingencia N-1 con restauración opcional |
| `listar_elementos` | Lista buses y elementos principales |
| `obtener_netlist` | Exporta y devuelve los archivos DSS con su contenido |
| `generar_diagrama_unifilar` | Genera un unifilar técnico SVG/HTML independiente |
| `estimar_arc_flash_lee` | Estimación educativa de energía incidente por Lee |
| `calcular_arc_flash` | Alias compatible con versiones anteriores |

## 5. Workspace HTML persistente

El workspace fija una ruta estable para el circuito activo. Las tools MCP que
cambian el modelo o su representación regeneran ese archivo automáticamente.

Ejemplo conceptual:

```python
configurar_workspace(
    "workspace.html",
    titulo="Hospital — Sistema eléctrico",
    auto_regenerar=True,
)

crear_circuito("hospital", 22.9)
agregar_transformador(...)
agregar_linea(...)
agregar_carga(...)
ejecutar_flujo_potencia()
analizar_caida_tension(limite_pct=3.0)
```

### 5.1 Estado y revisiones

El workspace distingue:

- `EMPTY`: no existe modelo utilizable;
- `MODIFIED`: el modelo cambió después de la última solución;
- `SOLVED`: la revisión actual coincide con la revisión resuelta;
- `ERROR`: existe un error eléctrico/no convergencia relevante.

Se mantienen `model_revision`, `solved_revision` y `visual_revision`. Un cambio
eléctrico invalida automáticamente estudios anteriores; un cambio únicamente
visual no invalida una solución correcta.

Cada estudio conserva la revisión con la que fue calculado y expone una bandera
`valid`. Así un resultado histórico puede permanecer trazable sin presentarse
como vigente.

### 5.2 HTML, inspector y exportación

La interfaz incluye:

- unifilar SVG embebido;
- resumen de buses, alimentadores, cargas y pérdidas;
- inspector técnico **read-only** con IDs estables del modelo;
- selección desde el unifilar, tabla `Datos` o selector lateral;
- snapshot JSON embebido y versionado;
- botón **Imprimir / PDF**, basado en `window.print()` y CSS de impresión;
- botón **Descargar SVG**;
- botón **Recargar archivo**.

El HTML es autocontenido y no usa dependencias remotas. El archivo se reescribe
automáticamente, pero una pestaña local ya abierta debe refrescarse para leer
la nueva versión.

Las decisiones base están en:

- `docs/WORKSPACE.md`;
- `docs/WORKSPACE_INTERACTIVO.md`;
- `docs/decisions/ADR-0001-workspace-persistente.md`;
- `docs/decisions/ADR-0002-workspace-interactivo.md`.

### 5.3 Flujo de potencia dentro del workspace

`ejecutar_flujo_potencia()` conserva su payload histórico, pero además registra
un estudio `flow` detallado. La pestaña **Flujo** puede mostrar por alimentador:

- corriente máxima del terminal 1;
- flujo kW y kvar del terminal 1;
- cargabilidad respecto a `corriente_nominal_a`, cuando ese rating existe;
- pérdidas totales del circuito.

La cargabilidad **no equivale por sí sola a validación normativa de ampacidad**.
Hasta implementar una biblioteca formal de conductores, el rating usado es un
metadato explícito suministrado al alimentador.

### 5.4 Caída de tensión dentro del workspace

`analizar_caida_tension(limite_pct=3.0)` calcula la diferencia de magnitudes pu
entre `bus1` y `bus2` de cada `Line`.

El resultado conserva:

- tensión promedio de origen y destino;
- caída por fase;
- caída promedio firmada;
- máxima caída positiva evaluada;
- estado `OK` / `EXCEDE` respecto al límite suministrado.

El límite es **configurable por el usuario**. El valor 3 % es solo el default de
la herramienta y no se presenta como requisito normativo universal.

La metodología y decisiones completas están en:

- `docs/WORKSPACE_ESTUDIOS.md`;
- `docs/decisions/ADR-0003-estudios-operativos-workspace.md`.

## 6. Unifilar técnico SVG

La visualización evita la estética de un grafo genérico. El renderer interpreta
el modelo eléctrico para mostrar barras físicas solo cuando corresponde y
colapsa buses puramente lógicos por defecto.

Principios principales:

1. flujo principal de energía ordenado;
2. barras físicas claramente jerarquizadas;
3. alimentadores ortogonales y ordenados;
4. protección en cabecera;
5. simbología consistente para fuente, transformador, tablero, motor, ATS,
   UPS, generador y tierra;
6. rótulos de ingeniería independientes del nombre interno OpenDSS;
7. protecciones visuales diferenciables: breaker, MCCB, ACB, fusible y
   seccionador;
8. modo `ingenieria` limpio y modo `diagnostico` con información adicional;
9. orientación vertical u horizontal;
10. elementos abiertos y buses desenergizados diferenciados visualmente.

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
    proteccion="mccb",
    conductor="3x50 mm2 Cu XLPE",
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

## 7. Contingencias N-1: estado coherente

`simular_perdida_alimentador()` distingue dos formas de trabajo.

Con `restaurar=True`, el elemento se abre, OpenDSS resuelve la contingencia,
se capturan los resultados y después se restaura exactamente el estado
original y se vuelve a resolver.

Con `restaurar=False`, el elemento permanece abierto y el circuito queda
resuelto en contingencia para inspección y visualización.

El workspace registra el estudio de contingencia junto con la revisión del
modelo a la que corresponde.

## 8. Cargas críticas

Las cargas marcadas con `critica=True` se conservan como metadato del modelo.
Durante una contingencia se devuelve, para cada carga crítica, su bus, voltajes
en pu, indicador de energización y la lista de cargas críticas sin tensión.

El umbral interno usado para distinguir una barra esencialmente desenergizada
de una barra con tensión **no es un criterio de cumplimiento de calidad de
servicio**.

## 9. Exportación DSS

`obtener_netlist()` exporta el circuito y devuelve directorio, `Master.dss`,
número de archivos y contenido de cada archivo `.dss` generado.

## 10. Arc Flash: alcance y seguridad

`estimar_arc_flash_lee()` implementa únicamente la ecuación simplificada de
Lee para aprendizaje y estimación de orden de magnitud.

**No implementa el modelo empírico completo de IEEE 1584-2018** y no convierte
energía incidente en una categoría PPE. `calcular_arc_flash()` se mantiene como
alias compatible.

## 11. Cortocircuito

`dss.Bus.Isc()` entrega componentes reales e imaginarias intercaladas. El
servidor calcula explícitamente la magnitud de cada fasor:

```text
|I| = sqrt(Re(I)^2 + Im(I)^2)
```

Al integrarlo con el workspace, el `FaultStudy` se conserva como estudio y
después se restaura una solución de flujo de potencia antes de regenerar el
visor. Esto evita mezclar modos de solución en el unifilar persistente.

## 12. Generadores y UPS

`agregar_generador_respaldo()` representa un **grupo electrógeno** mediante el
objeto `Generator` de OpenDSS. Una UPS basada en electrónica de potencia no se
presenta como equivalente a un generador síncrono.

## 13. Arquitectura

```text
MCP-Electrico/
├── server.py
├── mcp_electrico/
│   ├── __init__.py
│   ├── core.py
│   ├── studies.py
│   ├── visualization.py
│   ├── visual_state.py
│   ├── visual_symbols.py
│   ├── workspace_state.py
│   ├── workspace.py
│   └── workspace_studies_view.py
├── docs/
│   ├── UNIFILAR_TECNICO.md
│   ├── WORKSPACE.md
│   ├── WORKSPACE_INTERACTIVO.md
│   ├── WORKSPACE_ESTUDIOS.md
│   └── decisions/
│       ├── ADR-0001-workspace-persistente.md
│       ├── ADR-0002-workspace-interactivo.md
│       └── ADR-0003-estudios-operativos-workspace.md
├── examples/
│   ├── unifilar_tecnico.py
│   └── workspace_hospital.py
├── tests/
├── requirements.txt
└── requirements-dev.txt
```

- `server.py`: tools MCP y orquestación.
- `core.py`: lógica eléctrica y estado OpenDSS.
- `studies.py`: métricas operativas derivadas de soluciones OpenDSS.
- `visualization.py`: interpretación topológica, layout y render SVG.
- `visual_symbols.py`: biblioteca vectorial de símbolos.
- `visual_state.py`: metadatos visuales que no alteran el cálculo.
- `workspace_state.py`: revisiones, validez y contrato snapshot.
- `workspace.py`: HTML persistente e inspector base.
- `workspace_studies_view.py`: pestañas read-only para resultados de estudios.

## 14. Limitaciones actuales

- varios elementos usan parámetros de secuencia positiva R1/X1;
- todavía no existe biblioteca técnica de cables con procedencia de parámetros;
- no hay modelado detallado de R0/X0 o matrices de impedancia;
- no hay curvas TCC ni coordinación de protecciones;
- ATS/UPS pueden documentarse visualmente, pero aún no tienen modelo eléctrico
  detallado propio;
- no hay `LoadShape`, PV, Storage, capacitores, armónicos ni simulación anual;
- el workspace no persiste el proyecto entre reinicios del proceso;
- un HTML local abierto requiere refresco manual para leer una regeneración;
- la caída de tensión inicial se evalúa por cada `Line`, no todavía como caída
  acumulada independiente hasta cada carga;
- la corriente nominal usada para cargabilidad es un dato explícito, no una
  ampacidad calculada según método de instalación;
- vistas específicas de C.C. y contingencias aún no tienen pestañas propias;
- el SVG es un unifilar técnico, no un plano CAD contractual ni una biblioteca
  normativa completa IEC/ANSI;
- Arc Flash es solo una estimación educativa por Lee.

El siguiente salto recomendado es formalizar la **biblioteca/modelo de
conductores**: material, sección, aislamiento, tensión nominal, instalación,
R/X, ampacidad y procedencia del dato. Eso permitirá relacionar el objeto físico
seleccionado por el usuario con el modelo OpenDSS y con verificaciones de diseño
más sólidas.
