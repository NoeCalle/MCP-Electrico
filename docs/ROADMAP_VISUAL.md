# Roadmap visual transversal — MCP Eléctrico

## Objetivo

Mantener la evolución visual del proyecto alineada con la evolución técnica. El workspace y el unifilar no son decoración: deben permitir comprender el modelo, inspeccionar resultados, identificar condiciones anormales y conservar trazabilidad entre elemento eléctrico, estudio y revisión del modelo.

Este roadmap no reemplaza `docs/ROADMAP_PROFESIONAL.md`. Funciona como eje transversal: cuando una fase P2–P7 introduce un nuevo objeto o estudio, debe evaluarse también su representación visual.

## Estado base ya conseguido

La línea visual actual ya incluye:

- unifilar técnico SVG v2 con diferenciación entre barra física y bus lógico;
- simbología para fuente, barras, transformador, protecciones, ATS, UPS, motores, cargas y grupo electrógeno;
- workspace HTML persistente y autocontenido;
- identificadores estables por elemento;
- selección desde SVG, tablas y selector lateral;
- inspector técnico read-only;
- sincronización de selección entre estudio e inspector;
- pestañas de flujo y caída de tensión;
- overlays visuales sobre el unifilar para flujo/cargabilidad y caída de tensión;
- exportación SVG e impresión/PDF;
- validación de JavaScript en CI mediante `node --check`.

## Principios visuales no negociables

1. El navegador no realiza cálculos eléctricos; presenta resultados estructurados generados por MCP Eléctrico.
2. Un resultado visual debe declarar su `model_revision` y no mostrarse como vigente si el modelo cambió.
3. Los IDs del modelo son canónicos. No se crea un segundo sistema de identidad para tablas, overlays o nuevos motores.
4. El unifilar representa ingeniería, no la topología interna literal del solver.
5. No se inventan equipos, protecciones, ratings, impedancias ni estados para completar un dibujo.
6. Los datos visuales provenientes de catálogo, usuario o cálculo deben conservar su procedencia cuando sea técnicamente relevante.
7. Cuando existan varios motores, cada estudio debe mostrar claramente qué motor produjo el resultado; nunca se mezclan resultados de motores distintos dentro de una misma vista sin una función específica para ello.
8. La madurez del módulo (`EXPERIMENTAL`, `VALIDATED_WITH_LIMITATIONS`, etc.) debe ser visible cuando el usuario consulte un estudio que no sea plenamente validado.
9. Las vistas de ingeniería deben seguir siendo legibles en SVG, HTML y salida impresa.
10. La incorporación de una nueva feature numérica no se considera visualmente terminada hasta decidir si requiere inspector, tabla, overlay, símbolo o salida de reporte.

## V1 — Base visual existente

**Estado: IMPLEMENTADA.**

Incluye el unifilar técnico v2, workspace persistente, inspector, selección sincronizada y las primeras vistas de estudios.

Pendientes de consolidación:

- eliminar deuda técnica restante de bindings/IDs que todavía se resuelva en runtime;
- pruebas visuales/regresiones estructurales más fuertes además del chequeo sintáctico JavaScript;
- mejorar manejo de redes grandes sin sacrificar legibilidad.

## V2 — Acompañamiento visual de P2: datos profesionales

Cuando P2 incorpore transformadores, fuente equivalente y datos profesionales, el workspace deberá mostrar como mínimo:

### Transformadores

- kVA/MVA nominal;
- tensiones nominales;
- grupo vectorial;
- `%Z`;
- X/R cuando exista;
- taps y posición vigente;
- pérdidas si forman parte del modelo;
- fuente/procedencia de datos;
- estado de completitud para el estudio solicitado.

El símbolo del transformador debe poder mostrar la relación de tensión y grupo vectorial sin saturar el unifilar. El detalle completo irá al inspector.

### Fuente / red equivalente

El inspector de la fuente deberá poder mostrar:

- tensión nominal;
- Scc/Icc máxima y mínima cuando existan;
- X/R;
- escenario activo;
- procedencia de los datos.

### Conductores BT/MT

El inspector del alimentador deberá migrar desde texto libre hacia la ficha estructurada de conductor/cable:

- familia y fabricante;
- material y sección;
- clase de tensión;
- aislamiento;
- pantalla en MT cuando corresponda;
- R/X aplicados al modelo;
- ampacidad disponible;
- condición de instalación asociada;
- fuente del dato.

## V3 — Acompañamiento visual de P3: ampacidad

P3 debe añadir una vista específica de conductor/ampacidad que permita distinguir claramente:

- `Ib` corriente de diseño o resultante;
- `In` protección;
- `Iz` corriente admisible;
- factores de corrección aplicados;
- método de instalación;
- estado `OK` / `NO CUMPLE` / `DATOS INSUFICIENTES`.

El overlay del unifilar podrá resaltar alimentadores fuera de criterio, pero nunca debe convertir un rating de catálogo sin correcciones en `Iz` normativo.

## V4 — Acompañamiento visual de P4: cortocircuito IEC 60909

La vista de cortocircuito deberá contemplar:

- punto de falla seleccionado;
- tipo de falla;
- `Ik''`, `ip`, `Ib`, `Ik` y `Sk''` según el alcance implementado;
- escenario máximo/mínimo;
- contribuciones de fuentes cuando se disponga de ellas;
- motor utilizado y versión;
- estado de validación del módulo.

El unifilar podrá mostrar un marcador de falla y valores resumidos por barra. No debe saturarse mostrando todas las magnitudes simultáneamente.

## V5 — Acompañamiento visual de P5: protección y TCC

Esta fase requiere una ampliación visual importante:

- símbolos/estado de interruptores, relés y fusibles vinculados a objetos reales;
- inspector de protección con In, Icu/Ics/Icw y ajustes Ir/Isd/Ii cuando correspondan;
- panel TCC dedicado;
- curvas de protección y daño térmico/conductor cuando haya información suficiente;
- márgenes de coordinación y tiempos de despeje;
- resultado de verificación `I²t <= k²S²`;
- advertencia visible si faltan curvas comerciales o datos del fabricante.

La TCC será una vista de estudio, no una deformación del unifilar.

## V6 — Acompañamiento visual de P6: Arc Flash

La vista IEEE 1584 deberá mostrar de forma diferenciada:

- barra/equipo evaluado;
- configuración de electrodos;
- gap;
- working distance;
- Iarc e Iarc_min;
- tiempo de despeje vinculado a protección;
- energía incidente;
- arc-flash boundary;
- escenario dominante;
- estado de validación.

El unifilar podrá usar badges o marcadores de riesgo, pero la información necesaria para una etiqueta deberá mantenerse en una vista/artefacto específico.

## V7 — Acompañamiento visual de P7: expediente y reporte

El workspace y los SVG deben poder alimentar un reporte reproducible sin redibujar manualmente resultados.

Objetivos:

- láminas vectoriales aptas para PDF;
- tablas con unidades y procedencia;
- identificación de revisión/model hash;
- estado de validación de cada estudio;
- warnings/limitaciones visibles;
- selección consistente de vistas para anexos;
- estilo de impresión limpio sin controles interactivos.

## Regla para pandapower

P1.5 no crea por ahora una segunda interfaz visual. Los resultados pandapower se registran como estudio independiente y deben identificar explícitamente:

- `engine = pandapower`;
- versión;
- estado `EXPERIMENTAL`;
- alcance/compatibilidad.

No habrá overlay comparativo con OpenDSS ni cross-check visual mientras esa función no exista formalmente.

## Criterio de aceptación visual por PR

Cuando un PR modifica el workspace/unifilar o añade una nueva vista, debe comprobar según aplique:

- generación HTML/SVG exitosa;
- IDs estables y selección funcional;
- resultados ligados a la revisión vigente;
- JavaScript válido;
- ausencia de cálculos eléctricos en navegador;
- representación explícita de datos faltantes, no inferidos;
- salida imprimible razonable;
- regresión de vistas ya existentes.

A futuro se añadirá validación visual automatizada por screenshots/diffs para componentes críticos, además de las comprobaciones estructurales actuales.
