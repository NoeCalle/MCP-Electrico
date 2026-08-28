# Roadmap visual transversal — MCP Eléctrico

## Objetivo

Mantener la evolución visual alineada con la evolución técnica. El workspace y el unifilar no son decoración: permiten comprender el modelo, inspeccionar resultados y conservar trazabilidad entre elemento, estudio y revisión.

Este roadmap complementa `docs/ROADMAP_PROFESIONAL.md`.

## Estado base ya conseguido

La línea visual incluye:

- unifilar técnico SVG;
- workspace HTML persistente y autocontenido;
- IDs canónicos por elemento;
- inspector técnico read-only;
- selección sincronizada;
- vistas de flujo y caída de tensión;
- V2 de datos profesionales;
- V3 de ampacidad;
- V4 de cortocircuito IEC 60909;
- V5 de protección/TCC;
- impresión/PDF;
- validación de JavaScript mediante `node --check`.

## Principios visuales no negociables

1. El navegador no realiza cálculos eléctricos; presenta resultados preparados por Python/MCP.
2. Un resultado visual debe estar ligado a su `model_revision` y no mostrarse como vigente si el modelo cambió.
3. Los IDs del modelo son canónicos; no se crea otro sistema de identidad visual.
4. El unifilar representa ingeniería, no la topología interna literal del solver.
5. No se inventan equipos, protecciones, ratings, impedancias, ajustes ni estados para completar un dibujo.
6. La procedencia debe mantenerse cuando sea relevante para interpretar el estudio.
7. Cada estudio identifica claramente su motor y madurez.
8. Las vistas deben seguir siendo legibles en HTML/SVG e impresión.
9. Una feature numérica no está visualmente cerrada hasta decidir si requiere inspector, tabla, overlay, símbolo o reporte.
10. JavaScript queda limitado a interacción, navegación y selección.

## V1 — Base visual existente

**Estado: IMPLEMENTADA.**

Incluye unifilar técnico, workspace persistente, inspector, selección sincronizada, tablas operativas y primeras vistas de estudio.

Pendientes transversales:

- seguir endureciendo regresiones visuales;
- mejorar manejo de redes grandes;
- incorporar screenshots/diffs automatizados cuando el entorno lo permita.

## V2 — Acompañamiento visual de P2: datos profesionales

**Estado: COMPLETA CON LIMITACIONES (V2/P2 v1).**

### Transformadores

El inspector puede mostrar:

- kVA/MVA;
- tensiones nominales;
- grupo vectorial;
- `%Z`;
- X/R;
- taps;
- pérdidas e I0 cuando existen;
- procedencia;
- suficiencia para proyección pandapower y secuencia cero.

### Fuente / red equivalente

Incluye tensión, Scc máxima/mínima, X/R, escenario activo, secuencia cero y procedencia.

### Conductores BT/MT

El inspector distingue una asignación de biblioteca trazable de un texto visual y presenta familia/fabricante, sección, Rdc20, R1/X1, ampacidad de catálogo, instalación y procedencia.

La ampacidad publicada **no es `Iz` normativo P3**.

## V3 — Acompañamiento visual de P3: ampacidad

**Estado: COMPLETA CON LIMITACIONES (V3/P3-v1).**

Hito preservado: **BASE NORMATIVA P3C10** visible y trazable.

La pestaña de ampacidad consume resultados preparados por Python y distingue:

- perfil normativo;
- método de instalación;
- routing normativo;
- `Ib`;
- `In`;
- `Iz_base`;
- origen de `Iz_base`;
- **Tabla / dataset base**;
- `∏k`;
- `Iz`;
- `CUMPLE` / `NO_CUMPLE` / `DATOS_INSUFICIENTES`;
- evidencia `PRIMARIA`, `SECUNDARIA`, `MANUAL`, `BASE`, `MIXTA` o `INCOMPLETA`;
- madurez `VALIDATED_WITH_LIMITATIONS`.

La base primaria para el caso exacto Método C / Cu / XLPE-EPR / 3 conductores cargados / 70 mm² puede mostrar `Iz_base=229 A` desde `PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1`.

La ampacidad de catálogo P2 permanece separada.

**El JavaScript no decide si una evidencia es primaria o secundaria.** Esa clasificación viene preparada por Python.

**El JavaScript de V3 no calcula** `Ib`, `In`, factores, `Iz`, tablas ni routing normativo; solo presenta y navega.

### Vínculo con el gate P3

El gate P3 separa `phase` de `model`. La vista conserva la evidencia exacta y no convierte cobertura limitada en cobertura exhaustiva.

## V4 — Acompañamiento visual de P4: cortocircuito IEC 60909

**Estado: COMPLETA PARA EL ALCANCE P4-v1 — P4C11/P4C12 DONE.**

V4 reutiliza el mismo workspace/unifilar/inspector de V3 y no realiza cálculos IEC 60909 en JavaScript.

Implementa para 3F, 2F y 1F-T:

- snapshots versionados;
- MAX/MIN;
- `Ik''` y magnitudes disponibles según cada alcance;
- Rk/Xk y Rk0/Xk0 cuando aplican;
- topología, `tk_s` y κ cuando existen;
- motor/versión;
- edición objetivo;
- madurez `VALIDATED_WITH_LIMITATIONS` preparada por Python;
- `professional_emission=false`;
- barras de falla resaltadas;
- fail-closed visual cuando un escenario no puede calcularse.

P4C08 mantiene 2F-T fuera de P4-v1 contractual; cualquier extensión operacional conserva sus warnings y no se presenta como validación integral IEC.

V4 muestra solo estudios vigentes para la revisión actual.

## V5 — Acompañamiento visual de P5: protección y TCC

**Estado: COMPLETA CON LIMITACIONES (V5/P5F).**

V5 es una extensión incremental del mismo workspace:

```text
workspace base -> V3 ampacidad -> V4 cortocircuito -> V5 protección/TCC
```

No crea una aplicación paralela.

### Panel TCC

La pestaña **Protecciones / TCC** incorpora un **panel TCC** dedicado con:

- objetos `Protection.*`;
- vínculo al elemento protegido;
- interruptores y fusibles dentro del alcance P5;
- In/Ue;
- Icu/Ics/Icw o poder de corte según el tipo;
- Ir/Isd/Ii cuando existen;
- identidad de curva y dataset;
- semántica del tiempo;
- procedencia;
- TCC SVG por dispositivo.

### Representación de curvas

Las coordenadas log-log del SVG se preparan en Python a partir de puntos estructurados P5B.

- `SINGLE`: un trazo por segmento;
- `BAND`: min/max como trazos separados;
- segmentos distintos nunca se unen;
- los huecos preservan discontinuidades;
- no se crean puntos intermedios visuales;
- no hay extrapolación;
- no se promedian bandas.

El navegador no digitaliza ni sintetiza curvas comerciales.

### Resultados P5 vigentes

V5 puede resumir estudios vigentes de la revisión actual:

- evaluación TCC;
- capacidad de corte;
- `I²t <= k²S²`;
- clearing time P5D;
- coordinación temporal P5E.

Un estudio invalidado por cambio de `model_revision` no se presenta como vigente.

Un `PASS` P5E significa solo coordinación temporal puntual; **no equivale a selectividad total**, selectividad energética, backup o cascading.

### Regla JavaScript V5

El JavaScript V5 solo:

- cambia de pestaña;
- sincroniza la selección del elemento protegido con el inspector.

No interpola curvas, no calcula tiempos, no calcula márgenes, no ejecuta `I²t`, no decide selectividad y no deriva ratings.

```text
browser_engineering_calculation = false
professional_emission           = false
```

No se representa una curva de daño del conductor hasta disponer de un dataset backend explícito y trazable que la justifique.

## V6 — Acompañamiento visual de P6: Arc Flash

**Estado: DEFERRED CON P6.**

IEEE 1584 queda pausado por decisión de producto para priorizar el uso operativo del MCP. Cuando se retome, V6 deberá consumir resultados backend trazables y mostrar al menos:

- barra/equipo evaluado;
- configuración de electrodos;
- gap;
- working distance;
- Iarc e Iarc_min;
- clearing time proveniente de P5;
- energía incidente;
- arc-flash boundary;
- escenario dominante;
- estado de validación.

No bloquea la Engineering Preview previa.

## V7 — Acompañamiento visual de P7: expediente y reporte

**Estado: NEXT DESPUÉS DE P5G.**

Objetivos del bloque operacional mínimo:

- láminas vectoriales aptas para PDF;
- tablas con unidades y procedencia;
- revisión/model hash;
- estado de validación por estudio;
- warnings/limitaciones;
- selección consistente de anexos;
- estilo de impresión limpio;
- exportación reproducible sin redibujar manualmente.

## Regla para pandapower

P1.5 no crea por ahora una segunda interfaz visual. Los resultados pandapower se registran como estudios independientes e identifican explícitamente motor, versión, madurez y alcance/compatibilidad.

No habrá overlay comparativo con OpenDSS ni cross-check visual mientras esa función no exista formalmente.

## Criterio de aceptación visual por PR

Cuando un PR modifica el workspace/unifilar o añade una vista, debe comprobar según aplique:

- generación HTML/SVG exitosa;
- IDs estables y selección funcional;
- resultados ligados a la revisión vigente;
- JavaScript válido;
- ausencia de cálculos eléctricos en navegador;
- representación explícita de datos faltantes;
- procedencia/evidencia visible;
- salida imprimible razonable;
- regresión de vistas ya existentes.

A futuro se añadirá validación visual automatizada por screenshots/diffs para componentes críticos, además de las comprobaciones estructurales actuales.