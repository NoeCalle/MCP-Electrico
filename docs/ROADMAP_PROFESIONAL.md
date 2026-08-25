# Roadmap profesional — MCP Eléctrico

## Objetivo

Evolucionar MCP Eléctrico desde una herramienta funcional basada en OpenDSS hacia una plataforma de ingeniería reproducible y validada, apta para sustentar estudios emitidos por un profesional responsable.

La firma y responsabilidad profesional siempre corresponden al ingeniero. El objetivo de este roadmap es que la herramienta entregue resultados trazables, reproducibles, verificables y con límites de aplicación explícitos.

## Mapa maestro — orden de ejecución

Este documento es la **guía maestra del proyecto**. Las fases no se consideran cumplidas por tener una primera implementación: cada una debe satisfacer su criterio de salida y mantener pruebas/CI, documentación, QA y representación visual cuando corresponda.

| Fase | Estado actual | Resultado esperado |
| --- | --- | --- |
| P0 — Gobernanza y QA | COMPLETA | madurez explícita, QA y gate de emisión |
| P1 — Flujo y caída de tensión | COMPLETA CON LIMITACIONES | benchmarks independientes y regresión cuantitativa |
| P1.5 — pandapower | COMPLETA COMO INTEGRACIÓN EXPERIMENTAL | segundo motor disponible sin cross-check |
| P2 — Datos profesionales | **COMPLETA CON LIMITACIONES (P2 v1)** | equipos/fuente/cables trazables sin supuestos silenciosos |
| P3 — Ampacidad normativa | **EN PROGRESO — P3A ROUTER NORMATIVO UNDER_VALIDATION** | `Ib <= In <= Iz` y factores de corrección trazables |
| P4 — IEC 60909 | PENDIENTE | cortocircuito formal validado |
| P5 — Protección y TCC | PENDIENTE | protección del conductor, despeje y coordinación |
| P6 — IEEE 1584 | PENDIENTE | Arc Flash formal y validado |
| P7 — Expediente reproducible | PENDIENTE | paquete reconstruible, fuentes, versiones y hashes |
| P8 — Release profesional 1.0 | PENDIENTE | integración estable de los módulos requeridos |

**Regla de avance:** salvo deuda técnica justificada, el siguiente bloque principal se toma de la primera fase no cerrada. P3 está ahora **en progreso** y conserva `UNDER_VALIDATION`; no se avanzará formalmente a P4 hasta completar su cobertura normativa, benchmarks y gate de salida. Los ejes transversales V y E continúan evolucionando en paralelo porque sirven a todas las fases.

### P2 — evidencia de cierre v1

P2 se declara **COMPLETA CON LIMITACIONES**, no “completa universalmente”. El cierre corresponde al alcance P2 v1 y está protegido por `evaluar_cierre_p2()` y tests de salida.

Integrado y exigido por el gate:

- transformador P2 de dos devanados/trifásico con kVA, tensiones, grupo vectorial, `uk/%Z`, separación R/X, taps, pérdidas cuando se suministran y procedencia;
- red equivalente positiva-secuencia con Scc3/XR máxima y mínima, escenario activo y procedencia;
- biblioteca BT/MT trazable y asignación estructurada de **producto + condición de instalación**, separada del simple rótulo visual;
- secuencia cero explícita para fuente y líneas y ficha homopolar canónica de transformador, sin derivar Z0 desde Z1/Scc3;
- readiness por estudio con `READY_DATA`, `MISSING_DATA`, `ENGINE_NOT_READY` y `MODULE_NOT_READY`;
- checks sistemáticos de coherencia de tensión de fuente, fases, buses, ratings/conexiones de transformador y consistencia de la asignación de conductor;
- workspace V2 con fuente, transformador y cable/instalación trazables;
- seguridad de runtime contra datos P2, asignaciones o Z0 obsoletas;
- gate de salida que separa **capacidad del producto** de **coherencia del modelo activo**.

Limitaciones que permanecen deliberadamente fuera del cierre P2 v1:

- la biblioteca no pretende cubrir todo el mercado BT/MT;
- solo se admiten los grupos vectoriales expresamente soportados por P2 v1;
- R0/X0 desde geometría física es una ampliación futura; no se inventa cuando falta;
- la ficha Z0 del transformador no se proyecta profesionalmente a OpenDSS hasta validar una estrategia adecuada de conexión/neutro/núcleo;
- la ampacidad de catálogo todavía no es `Iz` normativo: eso comienza en P3;
- IEC 60909 sigue perteneciendo a P4.

Detalle y criterio reproducible: `docs/P2_EXIT_GATE.md`.

## Principio rector

OpenDSS se mantiene como motor numérico principal y por defecto. El proyecto puede incorporar motores complementarios cuando exista una ventaja técnica clara para un estudio específico, siempre con alcance, versión, madurez y limitaciones explícitos. El trabajo pendiente no consiste en reemplazar OpenDSS, sino en profesionalizar la capa alrededor de los motores: calidad de datos, bibliotecas, normativa, benchmarks, trazabilidad, control de versiones y reportabilidad.

## Estados de madurez

Cada módulo deberá declarar uno de estos estados:

- `NOT_IMPLEMENTED`: no existe una implementación utilizable.
- `EXPERIMENTAL`: existe implementación, pero no debe emplearse como base de emisión profesional.
- `UNDER_VALIDATION`: implementación funcional con validación incompleta.
- `VALIDATED_WITH_LIMITATIONS`: validada para un alcance y supuestos expresamente definidos.
- `VALIDATED`: validada contra casos patrón y apta dentro de su alcance documentado.

Un estado `VALIDATED` no elimina la obligación del ingeniero de revisar entradas, hipótesis y resultados.

## Eje transversal V — workspace y representación visual

La evolución visual se mantiene como un eje permanente del proyecto y no como una fase opcional separada. El unifilar técnico, workspace, inspector, tablas y overlays deben evolucionar junto con los datos y estudios de P2–P7.

La base ya implementada incluye unifilar SVG técnico, workspace persistente, IDs estables, inspector read-only, selección sincronizada y overlays de flujo/caída de tensión.

Regla de desarrollo: cuando una fase incorpore un nuevo objeto o estudio deberá decidir expresamente qué representación requiere —inspector, tabla, overlay, símbolo o salida de reporte— y mantener la trazabilidad entre `model_revision`, elemento, motor de cálculo y resultado.

El detalle de entregables visuales por fase se mantiene en `docs/ROADMAP_VISUAL.md`.

## Eje transversal E — selección determinista de motor

Objetivo: que la elección de OpenDSS, pandapower o una capa propia MCP **no dependa de una improvisación del LLM**.

La selección se basa en una matriz versionada de capacidades, requisitos del estudio, madurez del módulo, readiness de datos y compatibilidad del modelo. Este eje no altera el orden P0–P8.

Reglas:

1. OpenDSS continúa siendo el motor por defecto para el flujo actualmente validado y para capacidades de distribución donde sea el backend preferente.
2. pandapower se seleccionará cuando el estudio tenga una ventaja técnica clara y el módulo MCP correspondiente esté habilitado; IEC 60909 es el candidato principal de P4.
3. algunos estudios pertenecen a la capa MCP y no a un solver: ampacidad normativa, reglas `Ib/In/Iz`, protección-conductor y IEEE 1584 son ejemplos de orquestación/postproceso propios.
4. la matriz debe poder responder **motor preferente**, **alternativas**, **requisitos**, **madurez**, **readiness de datos/backend**, **si el estudio puede ejecutarse** y **si puede sustentar emisión**.
5. si faltan datos o el módulo/backend no está listo, la decisión debe expresarlo; nunca se sustituirán silenciosamente datos.
6. P1.5/P2 no introducen cross-check. Comparar resultados OpenDSS↔pandapower queda fuera de alcance hasta una fase futura específica.
7. la matriz E **recomienda/selecciona de forma determinista, pero no despacha automáticamente la ejecución**. Las tools explícitas de cada motor se mantienen.

Documento de detalle: `docs/ENGINE_SELECTION.md`.

## Fase P0 — Gobernanza técnica y QA del modelo

**Estado: COMPLETA.**

Objetivo: evitar que el sistema presente como listo para emisión un modelo incompleto.

Entregables:

1. matriz de estado de validación por módulo;
2. `ModelQAService` con severidades `INFO`, `WARNING`, `ERROR` y `BLOCKER`;
3. tool MCP `auditar_modelo()`;
4. bandera `apto_para_emision` calculada de forma determinística;
5. reglas de QA documentadas y cubiertas por tests;
6. sustitución del aviso genérico “educativo/experimental” por estados de madurez específicos por módulo.

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

La evidencia P1 v1 y las limitaciones se documentan en `docs/BENCHMARKS_P1.md`. CI genera `benchmark_p1.json` como artefacto reproducible.

## Fase P1.5 — Segundo motor experimental: pandapower

**Estado: COMPLETA COMO INTEGRACIÓN EXPERIMENTAL.**

Objetivo: incorporar pandapower de forma controlada como motor complementario sin cross-check entre solvers.

Entregables actuales:

- pandapower 3.5.x versionado;
- `pandapower_engine.py` y tool explícita `ejecutar_flujo_pandapower()`;
- flujo AC balanceado con líneas/cargas y transformadores P2 cuando los datos son suficientes;
- rechazo determinístico de elementos fuera de alcance;
- benchmark frente a la solución independiente P1, no frente a OpenDSS;
- estado `pandapower_power_flow = EXPERIMENTAL`.

Pandapower se considera especialmente relevante para la evolución posterior hacia IEC 60909 y protección industrial, pero esos módulos no quedan habilitados por P1.5.

## Fase P2 — Datos de entrada profesionales

**Estado: COMPLETA CON LIMITACIONES (P2 v1).**

Objetivo: eliminar supuestos silenciosos de equipos principales y dejar una base de datos/QA capaz de alimentar las fases normativas siguientes.

Criterio de salida cumplido dentro del alcance v1:

- transformadores, fuente equivalente y cables tienen representación profesional trazable;
- ausencia de secuencia cero se bloquea cuando el estudio la requiere;
- producto y condición de instalación están estructurados y separados del rating visual;
- los datos críticos conservan procedencia;
- OpenDSS/pandapower reciben solo proyecciones explícitas y compatibles;
- readiness diferencia datos faltantes de limitaciones del backend/módulo;
- QA, runtime y gate P2 detectan incoherencias relevantes;
- workspace V2 presenta los datos profesionales implementados.

Entregables consolidados:

- transformador profesional: kVA, tensiones, grupo vectorial, %Z, X/R, taps, pérdidas y fuente;
- red equivalente aguas arriba: Scc máxima/mínima, X/R y tensión;
- biblioteca trazable de conductores BT/MT y condición de instalación publicada;
- R0/X0 explícitos de fuente/líneas y ficha Z0 canónica de transformador;
- metadatos de origen para cada dato crítico;
- checks de coherencia de base kV, fases, buses, ratings y conexiones;
- `evaluar_preparacion_estudio()` y `evaluar_cierre_p2()`.

P2 no adelanta P3/P4: `Iz` normativo e IEC 60909 permanecen respectivamente pendientes.

## Fase P3 — Ampacidad normativa y conductor

**Estado: EN PROGRESO — P3A ROUTER NORMATIVO UNDER_VALIDATION.**

Objetivo: poder verificar selección térmica del conductor, no solo mostrar un rating de catálogo.

Foundation P3 ya implementada:

- contrato explícito `Ib <= In <= Iz` en la capa MCP;
- `In` declarado con referencia, sin inferirlo del rating visual histórico;
- `Ib` explícita o uso de corriente OpenDSS únicamente mediante aceptación expresa del escenario como corriente de diseño;
- `Iz_base` proveniente de una asignación P2 trazable;
- factores de corrección explícitos con referencia, o confirmación documentada de coincidencia con condiciones base;
- prohibición de asumir silenciosamente un factor total igual a 1;
- invalidación del perfil si cambia conductor, instalación o ampacidad base P2;
- readiness específico P3 y madurez `UNDER_VALIDATION`;
- workspace V3 con valores ya calculados y sin cálculo eléctrico en JavaScript;
- referencias versionadas registradas para IEC 60364-5-52 Ed. 3.1 y CNE–Utilización, sin afirmar que sus tablas estén automatizadas.

P3A añade:

- perfil `PERU_CNE_UTIL_2006_030_004` con routing A1/A2/B1/B2/C/D → Tabla 2 y E/F/G → Tabla 1;
- identificación de ejes de corrección de temperatura, resistividad térmica y agrupamiento dentro del alcance modelado;
- separación estricta entre perfil CNE 2006 e IEC 60364-5-52:2009+AMD1:2024;
- IEC 2024 permanece `REFERENCE_ONLY` hasta disponer de dataset propio de esa edición;
- restricción de 030-004(13) a transición subterránea → visible y 030-004(14) como revisión manual;
- vínculo explícito entre factor manual y `axis` normativo requerido;
- readiness bloqueante si el routing queda incompleto, cambia después de la ficha o conserva revisión manual pendiente;
- casos patrón separados en `mcp_electrico/data/ampacity_p3a_reference_cases.json`.

Pendiente para cerrar P3:

- datasets numéricos de ampacidades/factores con procedencia y alcance legal explícitos;
- resolución por aislamiento, sección, método y configuración;
- benchmarks independientes de valores numéricos y casos límite;
- política explícita para valores no tabulados/interpolaciones cuando corresponda;
- gate formal de salida P3;
- elevar madurez solo cuando la evidencia lo permita.

P3 conserva `automatic_normative_lookup=false` y no habilita emisión profesional automática. Detalle: `docs/P3_AMPACIDAD.md` y `docs/P3A_PERFILES_NORMATIVOS.md`.

## Fase P4 — Cortocircuito IEC 60909

**Estado: PENDIENTE.**

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

**Estado: PENDIENTE.**

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

**Estado: PENDIENTE.**

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

**Estado: PENDIENTE.**

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

## Fase P8 — Release profesional 1.0

**Estado: PENDIENTE.**

Criterios mínimos:

- P0 completa;
- flujo y caída de tensión validados dentro de alcance publicado;
- QA bloqueante operativo;
- P2 cerrada con datos profesionales suficientes para estudios incluidos;
- P3 ampacidad normativa implementada;
- P4 cortocircuito IEC 60909 validado;
- P5 protección-conductor implementada;
- P7 expediente reproducible;
- documentación de límites de aplicación;
- CI con benchmarks y pruebas de regresión;
- matriz de validación publicada por release;
- workspace/unifilar coherentes con los estudios incluidos en 1.0.

Arc Flash puede formar parte de 1.0 o de un módulo posterior, pero no debe presentarse como IEEE 1584 hasta completar P6.

## Regla de emisión

`apto_para_emision=true` significa únicamente que el modelo supera los chequeos automáticos definidos para los estudios solicitados y que los módulos requeridos tienen un estado de validación aceptable.

No significa que el software asuma responsabilidad profesional ni sustituye la revisión, criterio, firma o colegiatura del ingeniero responsable.
