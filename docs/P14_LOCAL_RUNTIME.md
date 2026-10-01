# P14B — Runtime MCP local

Estado: IMPLEMENTADO Y VERIFICADO LOCALMENTE — 2026-09-30.

La instalación Windows incluye entorno Python aislado, acceso stdio y servidor
Streamable HTTP en `http://127.0.0.1:8765/mcp`. P14A conserva la construcción
Rev.0 sin Solve ni escritura del Workspace. P14B añade transporte y prueba real
del protocolo. P12E/P12F y el acceso MCP a P13 se integran en esta entrega.

## Instalar y comprobar

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe scripts/verify_local_mcp.py
```

Python 3.12 es la versión comprobada en esta PC. La instalación requiere acceso
a los paquetes durante la preparación. Después los cálculos y expedientes
locales utilizan los motores instalados.

## Iniciar y detener

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_local.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/stop_local.ps1
```

El proceso se inicia oculto. Los logs y el PID se conservan en `local_data/`.
La detención valida el ejecutable del servidor y detiene también el intérprete
hijo del lanzador Windows. El puerto se puede elegir con `-Port`.

Para clientes stdio, configure el Python absoluto de `.venv\Scripts\python.exe`
y el `server.py` absoluto como argumento. Cada proceso stdio tiene su propio
modelo activo. Para HTTP use la URL local y un cliente compatible con Streamable
HTTP. El proceso HTTP acepta una sesión activa porque las herramientas clásicas
comparten un Workspace. Una segunda sesión recibe HTTP 503. El cliente debe
cerrar normalmente la sesión; una desconexión abrupta puede requerir reiniciar
el servidor. No hay caducidad silenciosa del modelo activo.

El servidor limita el enlace a loopback y conserva la comprobación Host/Origin
del SDK MCP. Un servicio de chat ejecutado en la nube no alcanza esta URL: se
necesita un cliente que ejecute en esta PC. El alojamiento remoto queda diferido
por la decisión de instalar localmente.

## Verificación de extremo a extremo

```powershell
.venv\Scripts\python.exe scripts/verify_local_mcp.py --url http://127.0.0.1:8765/mcp
.venv\Scripts\python.exe -m pytest -q -p no:faulthandler tests/test_local_mcp_transport.py
```

La prueba descubre las herramientas públicas, construye Rev.0, resuelve flujo,
genera el expediente de referencia P8/P10 con protecciones, genera el expediente
de transferencia P12 y el expediente de motores P13, comprueba replay, hashes
SHA-256 y preservación del Workspace padre. Conserva `verification.json` y los
expedientes HTML/JSON/SVG. Se prueban ambos transportes, exclusión de otra sesión,
liberación de la sesión y rechazo de Host/Origin externos.

La ampliación P13F1 verifica también las tres herramientas de preparación
dinámica, la admisión del fixture físico y un plan de backend todavía sin
calificar. Guarda `dynamic_preparation.json` conservando el Workspace padre.

## Alcance de cierre

Engineering Preview operativa local; `professional_emission=false`. P12 queda
cerrada como foundation de escenarios estáticos explícitos. P13A–P13E quedan
cerradas con acceso MCP público. P13F1 prepara entradas y validación para
dinámica electromecánica; su backend y ejecución siguen pendientes. IEEE 1584
continúa diferido. El cierre no añade datos normativos ni defaults implícitos.
