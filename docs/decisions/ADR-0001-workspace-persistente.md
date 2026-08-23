# ADR-0001 — Workspace HTML persistente

- Estado: **Aceptado para implementación inicial**
- Fecha: 2026-08-23
- Alcance: MCP Eléctrico

## Contexto

MCP Eléctrico se usa conversacionalmente desde ChatGPT. Se quiere añadir una
interfaz visual persistente del circuito sin crear un segundo chatbot, sin
convertir el HTML en un cliente de OpenAI y sin introducir una API de modelos.

El motor eléctrico actual es OpenDSS y conserva el circuito activo en memoria
del proceso. El renderer unifilar SVG ya existe y distingue barras físicas,
buses lógicos, protecciones y metadatos visuales.

## Decisión

### 1. ChatGPT continúa siendo la interfaz conversacional

El `workspace.html` **no contiene un cajetín LLM** y no llama a la API de
OpenAI. Todas las órdenes en lenguaje natural siguen entrando por ChatGPT y se
traducen a tools MCP.

Flujo canónico:

```text
ChatGPT -> tools MCP -> OpenDSS -> snapshot estructurado -> workspace.html
```

No se admite el flujo inverso `HTML -> LLM -> OpenDSS` en esta etapa.

### 2. `core.py` permanece libre de UI

La generación del workspace no se incorpora a `mcp_electrico.core`. La lógica
eléctrica debe seguir siendo ejecutable y testeable sin HTML ni transporte MCP.

Las responsabilidades quedan separadas así:

- `core.py`: modelo y cálculos OpenDSS;
- `visual_state.py`: metadatos de representación que no alteran el cálculo;
- `workspace_state.py`: revisiones, validez y snapshot serializable;
- `workspace.py`: render HTML/SVG;
- `server.py`: orquestación de tools y sincronización automática.

### 3. El snapshot es un contrato versionado

El HTML consume un objeto serializable con `schema_version`. La versión inicial
es `1` y contiene:

- estado y revisiones;
- buses;
- líneas/alimentadores;
- transformadores;
- cargas;
- generadores;
- metadatos visuales;
- estudios registrados.

El frontend no consulta OpenDSS directamente. Esto permite sustituir el HTML
sin acoplarlo al motor eléctrico.

### 4. La validez de resultados depende de la revisión del modelo

Se mantienen al menos:

- `model_revision`;
- `solved_revision`;
- `visual_revision`.

Un estudio es vigente únicamente si su `model_revision` coincide con la
revisión actual. Un cambio eléctrico incrementa `model_revision` y lleva el
estado a `MODIFIED`. Un cambio exclusivamente visual incrementa
`visual_revision` y **no invalida** una solución eléctrica existente.

Esto evita mostrar como actuales resultados que pertenecen a una topología o
parametrización anterior.

### 5. Estado eléctrico y error de interfaz son independientes

Un fallo de render HTML/SVG no cambia un circuito `SOLVED` a `ERROR`. Se
mantienen por separado:

- `electrical_error`;
- `workspace_error`.

La UI es secundaria respecto al resultado eléctrico y nunca debe invalidar una
operación OpenDSS correcta.

### 6. Regeneración automática desde la capa MCP

Las tools que modifican el circuito actualizan la revisión y regeneran el
workspace. Las tools que modifican solo simbología o etiquetas regeneran la
vista sin invalidar resultados. `ejecutar_flujo_potencia` registra la solución
y deja el workspace en `SOLVED` cuando converge.

La regeneración es **best effort**: si falla la vista, la tool eléctrica
conserva su resultado y el fallo queda registrado como `workspace_error`.

### 7. FaultStudy no queda como modo persistente del visor

`ejecutar_cortocircuito` cambia el modo de solución de OpenDSS a `FaultStudy`.
El resultado de cortocircuito se guarda como estudio, pero después se ejecuta
un flujo de potencia normal antes de regenerar el workspace. Así el unifilar
persistente no mezcla tensiones de un estudio de falla con una vista de
operación normal.

### 8. PDF inicial mediante impresión del navegador

La primera versión no incorpora una dependencia PDF. El botón
`Imprimir / PDF` ejecuta `window.print()` y el HTML incluye CSS de impresión.
El usuario puede usar `Guardar como PDF` en Chrome/Edge.

Se mantiene además un SVG vectorial compañero y un botón para descargar el SVG
embebido.

### 9. El HTML es autocontenido y sin dependencias remotas

CSS, JavaScript, snapshot y SVG se embeben localmente. El workspace no usa
CDN, `fetch`, cookies ni almacenamiento de navegador para su funcionamiento
base.

## Consecuencias

### Positivas

- no se requiere API de OpenAI;
- ChatGPT conserva toda la interacción conversacional;
- resultados viejos se identifican de forma explícita;
- el renderer puede evolucionar sin modificar OpenDSS;
- es posible añadir vistas de caída de tensión, flujo y cortocircuito sobre el
  mismo snapshot;
- el HTML puede abrirse directamente en un navegador.

### Costos / limitaciones aceptadas

- OpenDSS y el estado del workspace siguen siendo **en memoria del proceso**;
- abrir un HTML local no implica actualización en vivo del tab del navegador:
  el archivo se regenera automáticamente, pero en esta versión el usuario debe
  pulsar `Recargar archivo` o refrescar el navegador para ver una escritura
  posterior;
- la persistencia de proyectos entre reinicios queda fuera de este PR;
- el conductor mostrado sigue siendo metadato visual mientras no exista la
  futura biblioteca técnica de cables;
- las pestañas de caída de tensión, flujo, cortocircuito y contingencias se
  incorporarán en PRs posteriores sobre este contrato.

## Alternativas descartadas

### Chat embebido en el HTML

Descartado porque requeriría una API/modelo adicional o automatización no
soportada de una sesión de ChatGPT.

### JavaScript modificando OpenDSS directamente

Descartado porque duplicaría la lógica de control, debilitaría trazabilidad y
mezclaría frontend con motor eléctrico.

### Generar un HTML distinto en cada operación

Descartado. Se adopta un único workspace por circuito activo para que la ruta
sea estable y el navegador pueda reutilizarla.

## Próximos ADR posibles

- persistencia de proyectos/snapshots en disco;
- biblioteca de cables y procedencia de parámetros eléctricos;
- criterios configurables para caída de tensión;
- servidor local opcional para actualización en vivo del workspace.
