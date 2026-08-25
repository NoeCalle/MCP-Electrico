# Roadmap profesional — MCP Eléctrico

## Objetivo

Evolucionar MCP Eléctrico desde una herramienta funcional basada en OpenDSS hacia una plataforma de ingeniería reproducible y validada, apta para sustentar estudios emitidos por un profesional responsable.

La firma y responsabilidad profesional siempre corresponden al ingeniero. El objetivo del roadmap es que la herramienta entregue resultados trazables, reproducibles, verificables y con límites de aplicación explícitos.

## Mapa maestro — orden de ejecución

Este documento es la **guía maestra del proyecto**. Una fase no se considera cumplida por tener una primera implementación: debe satisfacer su criterio de salida, mantener CI/pruebas, documentación, QA y representación visual cuando corresponda.

| Fase | Estado actual | Resultado esperado |
| --- | --- | --- |
| P0 — Gobernanza y QA | COMPLETA | madurez explícita, QA y gate de emisión |
| P1 — Flujo y caída de tensión | COMPLETA CON LIMITACIONES | benchmarks independientes y regresión cuantitativa |
| P1.5 — pandapower | COMPLETA COMO INTEGRACIÓN EXPERIMENTAL | segundo motor disponible sin cross-check |
| P2 — Datos profesionales | **COMPLETA CON LIMITACIONES (P2 v1)** | equipos/fuente/cables trazables sin supuestos silenciosos |
| P3 — Ampacidad normativa | **EN PROGRESO — P3C01–P3C10 DONE; COBERTURA Y VALIDACIÓN FINAL PENDIENTES** | `Ib <= In <= Iz`, routing normativo y factores verificables |
| P4 — IEC 60909 | PENDIENTE | cortocircuito formal validado |
| P5 — Protección y TCC | PENDIENTE | protección del conductor, despeje y coordinación |
| P6 — IEEE 1584 | PENDIENTE | Arc Flash formal y validado |
| P7 — Expediente reproducible | PENDIENTE | paquete reconstruible, fuentes, versiones y hashes |
| P8 — Release profesional 1.0 | PENDIENTE | integración estable de los módulos requeridos |

**Regla de avance:** salvo deuda técnica justificada, el siguiente bloque principal se toma de la primera fase no cerrada. P3 está en progreso y conserva `UNDER_VALIDATION`; no se avanzará formalmente a P4 hasta completar cobertura normativa, evidencia numérica primaria suficiente, benchmarks normativos primarios y el gate de salida P3 en estado `DONE`. Los ejes transversales V y E evolucionan en paralelo.

## Principio rector

OpenDSS se mantiene como motor numérico principal y por defecto para el flujo actualmente validado. El proyecto puede incorporar motores complementarios cuando exista una ventaja técnica clara para un estudio específico, siempre con alcance, versión, madurez y limitaciones explícitos.

La profesionalización se apoya en cinco pilares:

1. calidad y procedencia de datos;
2. selección determinista del motor;
3. validación independiente y CI;
4. normativa versionada;
5. representación y reporte reproducibles.

## Estados de madurez

Cada módulo declara uno de estos estados:

- `NOT_IMPLEMENTED`;
- `EXPERIMENTAL`;
- `UNDER_VALIDATION`;
- `VALIDATED_WITH_LIMITATIONS`;
- `VALIDATED`.

Un estado `VALIDATED` no elimina la revisión, criterio ni responsabilidad del ingeniero.

## Eje transversal V — workspace y representación visual

La evolución visual es un eje permanente. El unifilar técnico, workspace, inspector, tablas y overlays deben evolucionar junto con P2–P7.

Base ya implementada:

- unifilar SVG técnico;
- workspace persistente;
- IDs estables;
- inspector read-only;
- selección sincronizada;
- vistas de flujo y caída de tensión;
- V2 con fuente, transformadores y conductores trazables;
- V3 con `Ib`, `In`, `Iz_base`, `∏k`, `Iz`, estado, metadata P3A y calidad de evidencia normativa preparada por Python;
- V3 distingue el origen de `Iz_base` y muestra **Tabla / dataset base** cuando la base normativa proviene de P3B.

Regla: el navegador **no recalcula ingeniería**. Consume resultados producidos por Python/MCP y conserva trazabilidad a `model_revision`, elemento, motor y estudio.

Detalle: `docs/ROADMAP_VISUAL.md`.

## Eje transversal E — selección determinista de motor

Objetivo: que la elección de OpenDSS, pandapower o una capa propia MCP **no dependa de improvisación del LLM**.

Reglas vigentes:

1. OpenDSS continúa como motor por defecto para el flujo validado y capacidades de distribución donde sea preferente.
2. pandapower se seleccionará cuando el estudio tenga ventaja técnica clara; IEC 60909 es el candidato principal de P4.
3. ampacidad, protección-conductor y IEEE 1584 pertenecen a la capa de orquestación/postproceso MCP.
4. la matriz E responde motor preferente, alternativas, requisitos, madurez, readiness y aptitud de ejecución/emisión.
5. faltantes de datos o limitaciones del backend se expresan; nunca se sustituyen silenciosamente.
6. `automatic_dispatch=false`.
7. `crosscheck=false` en el alcance actual.
8. la matriz recomienda/selecciona determinísticamente, pero **no despacha automáticamente la ejecución**.

Detalle: `docs/ENGINE_SELECTION.md`.

## Fase P0 — Gobernanza técnica y QA del modelo

**Estado: COMPLETA.**

Objetivo: evitar que el sistema presente como listo para emisión un modelo incompleto.

Entregables consolidados:

- matriz de madurez por módulo;
- `ModelQAService` con `INFO`, `WARNING`, `ERROR`, `BLOCKER`;
- `auditar_modelo()`;
- `apto_para_emision` determinístico;
- reglas QA documentadas y probadas;
- estados de madurez específicos en lugar de un aviso genérico experimental.

## Fase P1 — Benchmarks de flujo de potencia y caída de tensión

**Estado: COMPLETA CON LIMITACIONES (P1 v1).**

Objetivo: validar cuantitativamente la cadena MCP → OpenDSS → postproceso.

Cobertura validada:

- casos radiales trifásicos balanceados de dos barras con carga PQ;
- solución compleja independiente de OpenDSS;
- tolerancias declaradas antes de comparar;
- tensión, corriente, pérdidas y caída de tensión;
- CI con `benchmark_p1.json`.

`power_flow` y `voltage_drop` son `VALIDATED_WITH_LIMITATIONS`, no globalmente `VALIDATED`. Feeder IEEE/EPRI completo, desbalance y regulación siguen fuera del alcance P1 v1.

Detalle: `docs/BENCHMARKS_P1.md`.

## Fase P1.5 — Segundo motor experimental: pandapower

**Estado: COMPLETA COMO INTEGRACIÓN EXPERIMENTAL.**

Objetivo: incorporar pandapower de forma controlada sin cross-check.

Entregables:

- pandapower 3.5.x versionado;
- `pandapower_engine.py`;
- tool explícita `ejecutar_flujo_pandapower()`;
- flujo AC balanceado con líneas/cargas y transformadores P2 cuando existen datos suficientes;
- rechazo determinístico de elementos fuera de alcance;
- benchmark frente a referencia analítica P1, no contra OpenDSS;
- `pandapower_power_flow = EXPERIMENTAL`.

P1.5 no habilita IEC 60909 ni protección.

## Fase P2 — Datos de entrada profesionales

**Estado: COMPLETA CON LIMITACIONES (P2 v1).**

Objetivo: eliminar supuestos silenciosos de equipos principales y dejar una base capaz de alimentar las fases normativas.

Entregables consolidados:

- transformadores: kVA, tensiones, grupo vectorial, `%Z/uk`, X/R, taps, pérdidas y procedencia;
- red equivalente: Scc máxima/mínima, X/R, tensión y escenario activo;
- biblioteca BT/MT trazable;
- producto y condición de instalación estructurados;
- R0/X0 explícitos para fuente y líneas;
- ficha homopolar canónica de transformador;
- readiness `READY_DATA`, `MISSING_DATA`, `ENGINE_NOT_READY`, `MODULE_NOT_READY`;
- checks de coherencia de bases kV, fases, buses, ratings y conexiones;
- workspace V2;
- seguridad de runtime contra estado obsoleto;
- `evaluar_cierre_p2()`.

Limitaciones P2 v1:

- biblioteca de mercado no exhaustiva;
- grupos vectoriales limitados al alcance soportado;
- R0/X0 por geometría física pendiente;
- Z0 profesional de transformador no proyectada todavía a OpenDSS sin estrategia validada;
- ampacidad de catálogo no equivale a `Iz` normativo;
- IEC 60909 pertenece a P4.

Detalle: `docs/P2_EXIT_GATE.md`.

## Fase P3 — Ampacidad normativa y conductor

**Estado: EN PROGRESO — P3C01–P3C10 DONE; P3C11–P3C13 PENDIENTES.**

Objetivo: verificar selección térmica del conductor mediante:

```text
Ib <= In <= Iz
Iz = Iz_base * product(k_i)
```

sin convertir un rating de catálogo en `Iz` final por simple etiqueta.

### Foundation P3 — implementada

- `Ib` explícita o corriente de flujo aceptada expresamente como corriente de diseño;
- `In` explícito con referencia;
- `Iz_base` desde asignación P2 trazable cuando todavía no existe base normativa aplicable;
- `Iz_base` normativa primaria mediante dataset P3B cuando existe coincidencia exacta validada;
- factores explícitos y referenciados;
- prohibición de asumir silenciosamente `product(k_i)=1`;
- invalidación si cambia conductor/instalación/base;
- readiness específico P3;
- V3 read-only;
- referencias CNE e IEC versionadas.

### P3A — router normativo implementado

- perfil `PERU_CNE_UTIL_2006_030_004`;
- A1/A2/B1/B2/C/D → Tabla 2 como base;
- E/F/G → Tabla 1 como base;
- temperatura → 5A;
- resistividad térmica para D en ducto enterrado → 5B;
- agrupamiento A1/A2/B1/B2/C → 5C;
- **agrupamiento D enterrado → Tabla 5D**;
- E/F/G → 5C/5E según disposición;
- 030-004(13) restringida a transición subterránea → visible;
- 030-004(14) siempre manual;
- IEC 60364-5-52:2009+AMD1:2024 permanece `REFERENCE_ONLY`;
- bloqueo de mezcla CNE↔IEC;
- factor manual debe vincularse al `axis` requerido.

Detalle: `docs/P3A_PERFILES_NORMATIVOS.md`.

### P3B — infraestructura numérica y de evidencia implementada

P3B ya dispone de:

- registro versionado de datasets y procedencia;
- lookup exacto sin interpolación, extrapolación ni vecino más cercano;
- coherencia obligatoria con el routing P3A;
- gate de fuente primaria con SHA-256 esperado;
- binding trazable dataset → factor → `Iz`;
- binding trazable dataset `base_ampacity` → `Iz_base` → `Iz`;
- separación entre `READY_DATA` y calidad de evidencia normativa;
- evidencia visible en V3 preparada por Python;
- gate formal P3 con criterios `P3C01`–`P3C13`;
- registro versionado de evidencia de benchmarks;
- motor genérico `exact_rows_v1` para datasets normativos primarios;
- benchmark reproducible `benchmark_p3b.json` en CI.

El dataset histórico de infraestructura permanece:

`PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_SECONDARY_V1`

Es una **reproducción secundaria** utilizada únicamente para desarrollo y benchmark de infraestructura. Requiere opt-in explícito y conserva:

```text
verification_status = PENDING_PRIMARY_VERIFICATION
professional_emission = false
automatic_normative_lookup = false
```

El benchmark P3B histórico fija casos 2→0.80, 3→0.70 y 12→0.45 para verificar lookup exacto y trazabilidad. Un CI verde **no valida por sí solo la tabla normativa primaria**.

La fuente oficial MINEM/CNE está fijada en `ampacity_primary_sources.json` como `PINNED` con:

```text
expected_sha256 = 2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64
```

La copia fue capturada desde la URL oficial registrada mediante GitHub Actions run `32875620716`. Este pin cierra P3C08.

El subconjunto 2→0.80, 3→0.70 y 12→0.45 de Tabla 5C fue comparado visualmente bajo revisión `AI_VISUAL_REVIEW_USER_AUTHORIZED` y promovido mediante PR+CI a:

`PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_PRIMARY_V1`

Esto cerró P3C09 sin mutar el dataset secundario histórico.

P3C10 queda cerrado con la primera revisión primaria exacta de `Iz_base`:

`PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1`

Alcance exacto validado:

```text
Método C
Cu
XLPE/EPR — 90 °C
3 conductores cargados
70 mm2
Tabla 2, Col. 23
Iz_base = 229 A
```

La Tabla 3 confirma el routing hacia Tabla 2 Col. 23. El dataset utiliza `exact_rows_v1`: otra sección, método, material, aislamiento o número de conductores cargados devuelve `VALUE_NOT_TABULATED`. **No se declara Tabla 2 completa ni se extrapola 229 A.**

El cálculo P3 conserva simultáneamente la base normativa y la ampacidad de catálogo P2; una no sustituye silenciosamente a la otra. V3 muestra el origen de `Iz_base` y, cuando existe base normativa, la **Tabla / dataset base**.

Detalle: `docs/P3B_DATASETS_NUMERICOS.md`, `docs/P3B_EVIDENCIA_PRIMARIA.md`, `docs/P3C10_BASE_AMPACITY_STRATEGY.md`, `docs/P3_EXIT_GATE.md` y `docs/P3_BENCHMARK_EVIDENCE.md`.

### Gate formal de salida P3 — implementado

`evaluar_cierre_p3()` separa el estado de la fase del estado del modelo y bloquea el paso formal a P4 mientras exista algún criterio P3-v1 pendiente.

Infraestructura, fuente, primera revisión primaria de factores y estrategia de base normativa `P3C01`–`P3C10`: implementados.

Bloqueantes actuales:

- `P3C11` — cobertura primaria de 5A/5B/5C/5D/5E;
- `P3C12` — benchmarks normativos independientes contra fuente primaria;
- `P3C13` — madurez de ampacidad al menos `VALIDATED_WITH_LIMITATIONS`.

### Pendiente para cerrar P3

- ampliar cobertura primaria de 5A/5B/5C/5D/5E según el alcance formal P3-v1 (`P3C11`);
- extender Tablas 1/2 incrementalmente cuando nuevos casos lo requieran, manteniendo lookup exacto y evidencia primaria; P3C10 no se reabre por falta de cobertura exhaustiva;
- incorporar benchmarks independientes primarios por familia (`P3C12`);
- mantener BT/MT y ámbitos normativos separados;
- mantener política explícita de valores no tabulados;
- elevar madurez solo si la evidencia lo permite (`P3C13`).

P3 permanece `UNDER_VALIDATION` y no habilita emisión profesional automática.

**Estado actual:** P3C08–P3C10 están `DONE`. Tabla 5C dispone de una revisión `PRIMARY_VERIFIED` limitada a 2, 3 y 12 circuitos, y Tabla 2 dispone de una revisión `PRIMARY_VERIFIED` limitada al caso Método C / Cu / XLPE-EPR / 3 conductores / 70 mm² = 229 A. Ambas revisiones conservan `AI_VISUAL_REVIEW_USER_AUTHORIZED`, con `human_reviewer=null`; la madurez global P3 continúa `UNDER_VALIDATION`, `professional_emission=false` a nivel de fase y P4 permanece bloqueada. El eje visual V3 sigue en paralelo y distingue origen, tabla/dataset de `Iz_base` y evidencia de factores.

Detalle general: `docs/P3_AMPACIDAD.md`.

## Fase P4 — Cortocircuito IEC 60909

**Estado: PENDIENTE.**

Objetivo: disponer de un estudio formal conforme a una edición declarada de IEC 60909.

Entregables previstos:

- backend IEC 60909 desacoplado del solver de flujo;
- evaluación de pandapower como backend principal antes de reimplementar ecuaciones;
- fallas 3F, 2F, 1F-T y 2F-T según alcance;
- `Ik''`, `ip`, `Ib`, `Ik`, `Sk''` cuando correspondan;
- factores de tensión y contribuciones de fuentes;
- escenarios máximo/mínimo;
- casos oficiales/independientes de validación;
- V4 de cortocircuito.

## Fase P5 — Protección del conductor y coordinación

**Estado: PENDIENTE.**

Objetivo: verificar que el dispositivo realmente protege al conductor y coordina con otros dispositivos.

Entregables previstos:

- biblioteca comercial trazable;
- Icu/Ics/Icw;
- ajustes Ir/Isd/Ii;
- curvas TCC;
- verificación de sobrecarga;
- `I²t <= k²S²`;
- tiempos de despeje;
- selectividad/backup cuando exista información suficiente;
- advertencia bloqueante cuando falten curvas/datos;
- V5 con panel TCC.

## Fase P6 — Arc Flash IEEE 1584

**Estado: PENDIENTE.**

Objetivo: implementar IEEE 1584-2018 como módulo formal de arco eléctrico.

Entregables previstos:

- configuraciones de electrodos;
- gap, enclosure y working distance;
- Iarc e Iarc_min;
- tiempo de despeje vinculado a protección;
- energía incidente;
- arc-flash boundary;
- validación independiente;
- V6 Arc Flash.

Lee permanece separado como método experimental/histórico y no sustituye IEEE 1584.

## Fase P7 — Reporte reproducible y expediente de cálculo

**Estado: PENDIENTE.**

Objetivo: reconstruir exactamente cada estudio emitido.

Paquete previsto:

- `report.pdf`;
- `model.json`;
- export DSS;
- `sources.json`;
- `assumptions.json`;
- matriz de validación;
- QA;
- versiones de MCP/OpenDSS/pandapower/bibliotecas;
- hash SHA-256;
- V7/salida vectorial reportable.

## Fase P8 — Release profesional 1.0

**Estado: PENDIENTE.**

Criterios mínimos:

- P0 completa;
- P1 validada dentro de alcance publicado;
- QA bloqueante operativo;
- P2 cerrada dentro de alcance;
- P3 ampacidad normativa implementada/validada para alcance declarado;
- P4 IEC 60909 validado;
- P5 protección-conductor implementada;
- P7 expediente reproducible;
- documentación de límites;
- CI con benchmarks;
- matriz de validación por release;
- workspace/unifilar coherentes con los estudios incluidos.

Arc Flash puede entrar en 1.0 o en un módulo posterior, pero nunca se presentará como IEEE 1584 antes de cerrar P6.

## Regla de emisión

`apto_para_emision=true` significa únicamente que el modelo supera los chequeos automáticos de los estudios solicitados y que los módulos requeridos tienen un estado de validación aceptable.

No significa que el software asuma responsabilidad profesional ni sustituye la revisión, criterio, firma o colegiatura del ingeniero responsable.