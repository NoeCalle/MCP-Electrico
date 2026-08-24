# Roadmap profesional — MCP Eléctrico

## Objetivo

Evolucionar MCP Eléctrico desde una herramienta funcional basada en OpenDSS hacia una plataforma de ingeniería reproducible y validada, apta para sustentar estudios emitidos por un profesional responsable.

La firma y responsabilidad profesional siempre corresponden al ingeniero. El objetivo de este roadmap es que la herramienta entregue resultados trazables, reproducibles, verificables y con límites de aplicación explícitos.

## Principio rector

OpenDSS se mantiene como motor numérico principal y por defecto. El proyecto puede incorporar motores complementarios cuando exista una ventaja técnica clara para un estudio específico, siempre con alcance, versión, madurez y limitaciones explícitas. El trabajo pendiente no consiste en reemplazar OpenDSS, sino en profesionalizar la capa alrededor de los motores: calidad de datos, bibliotecas, normativa, benchmarks, trazabilidad, control de versiones y reportabilidad.

## Estados de madurez

Cada módulo deberá declarar uno de estos estados:

- `NOT_IMPLEMENTED`: no existe una implementación utilizable.
- `EXPERIMENTAL`: existe implementación, pero no debe emplearse como base de emisión profesional.
- `UNDER_VALIDATION`: implementación funcional con validación incompleta.
- `VALIDATED_WITH_LIMITATIONS`: validada para un alcance y supuestos expresamente definidos.
- `VALIDATED`: validada contra casos patrón y apta dentro de su alcance documentado.

Un estado `VALIDATED` no elimina la obligación del ingeniero de revisar entradas, hipótesis y resultados.

## Fase P0 — Gobernanza técnica y QA del modelo

Objetivo: evitar que el sistema presente como listo para emisión un modelo incompleto.

Entregables:

1. matriz de estado de validación por módulo;
2. `ModelQAService` con severidades `INFO`, `WARNING`, `ERROR` y `BLOCKER`;
3. tool MCP `auditar_modelo()`;
4. bandera `apto_para_emision` calculada de forma determinística;
5. reglas de QA documentadas y cubiertas por tests;
6. sustitución del aviso genérico “educativo/experimental” por estados de madurez específicos por módulo.

Esta fase NO declara todavía ningún estudio como profesionalmente validado.

## Fase P1 — Benchmarks de flujo de potencia y caída de tensión

**Estado: COMPLETADA CON LIMITACIONES (P1 v1).**

La primera cobertura valida casos radiales trifásicos balanceados de dos barras con carga PQ mediante una solución compleja independiente de OpenDSS. Los módulos `power_flow` y `voltage_drop` pasan a `VALIDATED_WITH_LIMITATIONS`. La validación completa con feeders IEEE/EPRI, redes desbalanceadas y equipos de regulación permanece pendiente antes de considerar `VALIDATED`.

Objetivo: validar cuantitativamente la cadena MCP → OpenDSS → postproceso.

Entregables:

- casos analíticos simples con solución independiente;
- IEEE/EPRI feeders de referencia donde sea aplicable;
- tolerancias declaradas antes de ejecutar la comparación;
- reporte automático de error absoluto/relativo;
- benchmarks de pérdidas, tensiones, corrientes y caída de tensión;
- CI que impida regresiones fuera de tolerancia.

Criterio de salida: `power_flow` y `voltage_drop` pueden pasar a `VALIDATED_WITH_LIMITATIONS` o `VALIDATED`, según cobertura conseguida.

La evidencia P1 v1 y las limitaciones se documentan en `docs/BENCHMARKS_P1.md`. CI genera `benchmark_p1.json` como artefacto reproducible.

## Fase P1.5 — Segundo motor experimental: pandapower

Objetivo: incorporar pandapower de forma controlada como motor complementario sin introducir todavía selección automática de motor ni cross-check entre solvers.

Primera entrega:

- dependencia pandapower 3.5.x versionada;
- módulo `pandapower_engine.py`;
- tool explícita `ejecutar_flujo_pandapower()`;
- flujo AC balanceado para redes trifásicas de un solo nivel de tensión con `Line + Load`;
- rechazo determinístico de transformadores, generadores, motores y otras topologías fuera de alcance;
- benchmark frente a la solución independiente P1, no frente a OpenDSS;
- estado `pandapower_power_flow = EXPERIMENTAL`;
- documentación de supuestos y códigos de compatibilidad.

Decisiones deliberadas:

- OpenDSS sigue siendo el motor por defecto;
- no existe router automático en P1.5;
- no existe cross-check OpenDSS/pandapower en P1.5;
- pandapower no sustituye el estado de solución base del workspace;
- la traducción de transformadores se pospone hasta disponer de datos profesionales en P2.

Pandapower se considera especialmente relevante para la evolución posterior hacia IEC 60909 y protección industrial, pero esos módulos no se habilitan en P1.5.

## Fase P2 — Datos de entrada profesionales

Objetivo: eliminar supuestos silenciosos de equipos principales.

Entregables:

- biblioteca de transformadores: kVA, tensiones, grupo vectorial, %Z, X/R, taps, pérdidas y fuente;
- modelo de red equivalente aguas arriba: Scc/Icc máxima y mínima, X/R y tensión;
- ampliación de biblioteca de conductores BT/MT;
- R0/X0 o geometría cuando el estudio lo requiera;
- metadatos de origen para cada dato crítico;
- chequeos de coherencia de base kV, fases y conexiones.

P2 deberá definir datos suficientes para proyectar de forma trazable transformadores y fuentes tanto a OpenDSS como, cuando corresponda, a pandapower.

## Fase P3 — Ampacidad normativa y conductor

Objetivo: poder verificar selección térmica del conductor, no solo mostrar un rating de catálogo.

Entregables:

- métodos de instalación;
- temperatura ambiente/suelo;
- agrupamiento;
- resistividad térmica del terreno cuando corresponda;
- factores de corrección;
- corriente admisible `Iz` trazable;
- chequeos `Ib <= In <= Iz`;
- distinción entre dato de fabricante y valor derivado por norma.

La norma de referencia deberá versionarse explícitamente en cada release.

## Fase P4 — Cortocircuito IEC 60909

Objetivo: disponer de un estudio formal de cortocircuito conforme a una edición declarada de IEC 60909.

Entregables:

- integración o motor IEC 60909 desacoplado del solver de flujo, con versión y alcance explícitos;
- evaluación de pandapower como backend normativo principal antes de implementar ecuaciones propias innecesariamente;
- fallas 3F, 2F, 1F-T y 2F-T según alcance;
- `Ik''`, `ip`, `Ib`, `Ik`, `Sk''` cuando correspondan;
- factores de tensión y contribuciones de fuentes;
- casos ejemplo oficiales/independientes de validación;
- escenarios de red máxima y mínima.

## Fase P5 — Protección del conductor y coordinación

Objetivo: verificar que el dispositivo realmente protege al conductor.

Entregables:

- biblioteca comercial de dispositivos con fuente;
- Icu/Ics/Icw según equipo;
- ajustes Ir/Isd/Ii y curvas TCC;
- verificación de sobrecarga;
- verificación adiabática `I²t <= k²S²`;
- tiempos de despeje;
- selectividad/backup donde exista información suficiente;
- advertencia explícita cuando falten curvas o datos del fabricante.

## Fase P6 — Arc Flash IEEE 1584

Objetivo: reemplazar el cálculo Lee como herramienta principal de arco eléctrico.

Entregables:

- IEEE 1584-2018;
- configuraciones de electrodos;
- gap, enclosure y working distance;
- Iarc e Iarc_min;
- tiempos de despeje vinculados a protección;
- energía incidente y arc-flash boundary;
- validación con casos independientes;
- Lee permanece únicamente como método histórico/educativo separado.

## Fase P7 — Reporte reproducible y expediente de cálculo

Objetivo: que cada informe pueda reconstruirse exactamente.

Paquete de emisión propuesto:

- `report.pdf`;
- `model.json`;
- export DSS completo;
- `sources.json`;
- `assumptions.json`;
- matriz de validación;
- resultados QA;
- versiones de MCP Eléctrico, OpenDSS y bibliotecas;
- hash SHA-256 del paquete/modelo.

El informe debe mostrar qué módulos están validados y qué limitaciones permanecen.

## Fase P8 — Release profesional 1.0

Criterios mínimos propuestos:

- P0 completa;
- flujo y caída de tensión validados;
- QA bloqueante operativo;
- bibliotecas con trazabilidad;
- cortocircuito IEC 60909 validado;
- protección-conductor implementada;
- expediente reproducible;
- documentación de límites de aplicación;
- CI con benchmarks y pruebas de regresión;
- matriz de validación publicada por release.

Arc Flash puede formar parte de 1.0 o de un módulo posterior, pero no debe presentarse como IEEE 1584 hasta completar P6.

## Regla de emisión

`apto_para_emision=true` significa únicamente que el modelo supera los chequeos automáticos definidos para los estudios solicitados y que los módulos requeridos tienen un estado de validación aceptable.

No significa que el software asuma responsabilidad profesional ni sustituye la revisión, criterio, firma o colegiatura del ingeniero responsable.
