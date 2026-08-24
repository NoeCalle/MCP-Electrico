# ADR-0002 — Inspector interactivo read-only y selección por ID estable

- **Estado:** Aceptado
- **Fecha:** 2026-08-23
- **Contexto:** Workspace HTML de MCP Eléctrico
- **Depende de:** ADR-0001 — Workspace persistente

## Contexto

El workspace persistente ya muestra el unifilar y un snapshot estructurado del
circuito, pero el usuario todavía debe interpretar manualmente qué fila del
modelo corresponde a un símbolo del dibujo. El siguiente paso es permitir
inspección directa de barras, alimentadores, transformadores, cargas y
generadores sin crear una segunda interfaz de edición paralela a ChatGPT/MCP.

## Decisión 1 — El inspector será de solo lectura

El HTML podrá:

- seleccionar elementos;
- resaltar el elemento seleccionado;
- mostrar propiedades y resultados vigentes;
- exponer el identificador inequívoco para usarlo en la conversación.

El HTML **no podrá**:

- modificar OpenDSS;
- escribir parámetros eléctricos;
- abrir/cerrar equipos;
- ejecutar herramientas MCP;
- llamar a un LLM.

Las modificaciones continúan exclusivamente por:

`ChatGPT → herramienta MCP → OpenDSS → snapshot → workspace.html`.

### Motivo

Permitir edición local en JavaScript crearía dos fuentes de verdad: el estado
en memoria de OpenDSS y un estado mutable en el navegador. Mantener la UI
read-only evita divergencias y conserva la trazabilidad del ADR-0001.

## Decisión 2 — IDs estables como identidad primaria

Cada elemento inspeccionable usa un ID derivado del tipo y del nombre OpenDSS:

- `Bus.tgbt`
- `Line.f_motor`
- `Transformer.tr_01`
- `Load.motor_bomba`
- `Generator.ge_01`

El rótulo visible (`F-01`, `TR-01`, `M-01 · BOMBA`) es presentación y puede
cambiar sin alterar la identidad del elemento.

### Consecuencia

La conversación puede usar el rótulo humano, pero el inspector siempre muestra
también la referencia MCP inequívoca.

## Decisión 3 — Catálogo interactivo embebido

El HTML incluye un `workspace-catalog` derivado del snapshot. Ese catálogo
contiene únicamente:

- ID;
- tipo;
- nombre interno;
- rótulo de ingeniería.

No duplica propiedades eléctricas. Las propiedades siguen leyéndose desde
`workspace-snapshot`.

## Decisión 4 — Tres formas equivalentes de seleccionar

La selección puede originarse desde:

1. el unifilar;
2. una fila de la pestaña Datos;
3. el selector del inspector.

Las tres rutas terminan en `selectElement(id)` y muestran la misma ficha.

Esto evita que la interacción dependa exclusivamente del SVG. Si un símbolo no
puede vincularse visualmente de forma inequívoca, el selector sigue siendo una
ruta determinista.

## Decisión 5 — Enlace SVG por etiqueta, identidad por ID

El renderer SVG v2 todavía no imprime `data-element-id` directamente en todos
los grupos. Para no mezclar en este PR el renderer con la UI, el workspace:

1. construye el catálogo de IDs desde el snapshot;
2. localiza etiquetas visibles del SVG;
3. anota en memoria del navegador el texto y el símbolo asociado con
   `data-element-id`;
4. usa ese ID para la selección.

La etiqueta es, por tanto, un mecanismo de **enlace visual**, no la identidad
del modelo.

### Limitación aceptada

Cuando un alimentador no tiene un rótulo de ingeniería explícito, el renderer
puede asignar un `F-xx` automáticamente que no existe como metadato en el
snapshot. En ese caso la selección sigue disponible por el selector y la tabla.

Una fase posterior puede mover `data-element-id` al renderer para eliminar
esta limitación, pero no es necesario para validar el inspector.

## Decisión 6 — Resultados solo si son vigentes

Para buses, el inspector muestra tensiones de `powerflow` únicamente cuando el
estudio tiene `valid=true`.

No se muestran resultados antiguos como si correspondieran a la revisión
actual.

## Decisión 7 — Sin dependencias remotas

La interacción usa JavaScript y CSS embebidos. No se añaden frameworks,
CDN, fetch remoto ni librerías de UI.

Esto mantiene `workspace.html` portable y abrible como archivo local.

## Accesibilidad

Los textos y símbolos enlazados reciben:

- `role="button"`;
- `tabindex="0"`;
- activación por Enter o espacio.

El selector HTML nativo siempre permanece disponible como alternativa.

## Consecuencias

### Positivas

- inspección técnica sin API adicional;
- una sola fuente de verdad;
- selección consistente entre SVG, tabla y panel;
- IDs reutilizables en futuras vistas de caída de tensión y cortocircuito;
- base para resaltar resultados sin reescribir la arquitectura.

### Negativas / pendientes

- el binding visual depende aún de etiquetas visibles;
- no hay edición desde el HTML;
- no hay live reload;
- el inspector todavía no calcula métricas nuevas;
- los alimentadores sin etiqueta explícita pueden requerir selección por lista.

## Criterio de salida de esta fase

La fase se considera completa cuando:

- el HTML genera un catálogo con IDs estables;
- F-01, transformador, carga y buses pueden inspeccionarse;
- las filas de Datos reutilizan los mismos IDs;
- el panel muestra propiedades reales del snapshot;
- los tests garantizan ausencia de dependencias remotas;
- la CI genera el workspace interactivo sin romper regresiones eléctricas.
