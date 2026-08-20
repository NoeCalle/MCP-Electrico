# OpenDSS MCP Server

Servidor MCP que permite a Claude modelar y simular redes eléctricas de
distribución MT/BT (hospitales, edificios, instalaciones críticas) usando
[OpenDSS](https://www.epri.com/pages/sa/opendss) a través de la librería
`OpenDSSDirect.py`.

## 1. Instalación

Requisitos: Python 3.10 o superior.

```bash
cd opendss-mcp
python3 -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Verifica que todo importa correctamente:

```bash
python3 -c "import opendssdirect; import mcp; print('OK')"
```

## 2. Probar el servidor de forma aislada (opcional pero recomendado)

Antes de conectarlo a Claude, puedes probar la lógica directamente con el
caso de estudio incluido:

```bash
python3 examples/hospital_basico.py
```

Si ves `"convergio": true` y voltajes en por-unidad cercanos a 1.0, el
servidor está funcionando correctamente. El script modela un hospital con
acometida en MT, transformador de distribución, tablero de quirófanos
(carga crítica) y análisis de contingencia N-1 — ver el código en
`examples/hospital_basico.py` para el detalle completo.

## 3. Conectar a Claude Desktop

Abre (o crea) el archivo de configuración de Claude Desktop:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Agrega esta entrada (ajusta la ruta absoluta a donde guardaste el proyecto):

```json
{
  "mcpServers": {
    "opendss": {
      "command": "/ruta/absoluta/a/opendss-mcp/venv/bin/python3",
      "args": ["/ruta/absoluta/a/opendss-mcp/server.py"]
    }
  }
}
```

En Windows, la ruta al ejecutable de Python del venv normalmente es
`...\opendss-mcp\venv\Scripts\python.exe`.

Reinicia Claude Desktop por completo. Deberías ver el ícono de herramientas
(🔨) con "opendss" listado como servidor conectado.

## 4. Herramientas disponibles

| Herramienta | Qué hace |
|---|---|
| `crear_circuito` | Inicia un circuito nuevo con tensión y frecuencia base |
| `agregar_linea` | Agrega un tramo de línea/cable entre dos buses |
| `agregar_transformador` | Agrega un transformador MT/BT |
| `agregar_carga` | Agrega una carga (tablero, quirófano, etc.), con flag de "crítica" |
| `agregar_generador_respaldo` | Agrega grupo electrógeno o fuente UPS |
| `ejecutar_flujo_potencia` | Corre el power flow: voltajes por bus y pérdidas |
| `ejecutar_cortocircuito` | Calcula corriente de falla trifásica en un bus |
| `simular_perdida_alimentador` | Análisis de contingencia N-1: abre un elemento y recalcula |
| `listar_elementos` | Lista buses, líneas, transformadores, cargas, generadores actuales |
| `generar_diagrama_unifilar` | Genera un HTML interactivo del circuito, coloreado por voltaje |

## 5. Ejemplo de uso conversacional con Claude

Una vez conectado, puedes pedirle a Claude cosas como:

> "Modela un hospital con una acometida de 13.2 kV, un transformador de
> 500 kVA a 0.4 kV, un tablero de quirófanos con 50 kW críticos y un
> tablero de iluminación con 20 kW. Corre el flujo de potencia y dime si
> los voltajes están dentro de rango normal (±5%)."

O para análisis de contingencia:

> "Simula qué pasa si se pierde la línea principal de BT. ¿El hospital
> queda sin servicio en el tablero de quirófanos?"

O para visualizar la red:

> "Genera el diagrama unifilar del circuito actual y ábrelo en el navegador."

## 5.1 Ejemplo de visualización

`examples/visualizar_hospital.py` construye el mismo modelo del hospital y
genera dos diagramas HTML interactivos: uno en condición normal y otro en
contingencia N-1, para comparar visualmente el efecto de perder el
alimentador a quirófanos.

```bash
python3 examples/visualizar_hospital.py
```

Cada bus se colorea según su voltaje en por-unidad (verde: 0.95–1.05 pu,
amarillo: 0.90–1.10 pu, rojo: fuera de rango o sin tensión). Pasa el mouse
sobre un bus o línea para ver el detalle.

## 6. Notas técnicas importantes

- **Bases de tensión (`VoltageBases`)**: OpenDSS requiere que se declaren
  explícitamente los niveles de tensión de la red (`Set VoltageBases=[...]`
  + `CalcVoltageBases`) para calcular correctamente los valores en
  por-unidad. El servidor lo hace automáticamente cada vez que agregas un
  transformador — no necesitas preocuparte por esto en el uso normal.
- **Persistencia**: el modelo vive en memoria mientras el proceso del
  servidor MCP esté corriendo. Si cierras Claude Desktop, se pierde. Para
  guardar un modelo, puedes pedirle a Claude que use `obtener_netlist()` y
  exportar el script `.dss` resultante.
- **Limitación actual**: el servidor asume redes trifásicas balanceadas por
  simplicidad en varios parámetros por defecto (R1/X1). Para modelar
  desbalance fino (común en BT monofásico/bifásico) se pueden extender las
  herramientas con parámetros de secuencia cero (R0/X0) y matrices de
  impedancia — no está incluido en esta versión inicial.

## 7. Historial de cambios

Ver [CHANGELOG.md](CHANGELOG.md) para el detalle de qué herramientas se
agregaron en cada versión, correcciones aplicadas, y qué elementos de
OpenDSS todavía no están cubiertos (LoadShape, PVSystem, Storage,
Capacitor, análisis horario, armónicos, visualización de topología, etc.).
Este proyecto se extiende de forma incremental, un caso de estudio a la vez.
