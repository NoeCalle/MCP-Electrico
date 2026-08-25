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
| P3 — Ampacidad normativa | **EN PROGRESO — INFRAESTRUCTURA P3B + GATE P3 IMPLEMENTADOS; EVIDENCIA PRIMARIA PENDIENTE** | `Ib <= In <= Iz`, routing normativo y factores verificables |
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
- V3 con `Ib`, `In`, `Iz_base`, `∏k`, `Iz`, estado, metadata P3A y calidad de evidencia normativa preparada por Python.

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

**Estado: EN PROGRESO — INFRAESTRUCTURA P3B + GATE P3 IMPLEMENTADOS; EVIDENCIA PRIMARIA PENDIENTE.**

Objetivo: verificar selección térmica del conductor mediante:

```text
Ib <= In <= Iz
Iz = Iz_base * product(k_i)
```

sin convertir un rating de catálogo en `Iz` final por simple etiqueta.

### Foundation P3 — implementada

- `Ib` explícita o corriente de flujo aceptada expresamente como corriente de diseño;
- `In` explícito con referencia;
- `Iz_base` desde asignación P2 trazable;
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
- separación entre `READY_DATA` y calidad de evidencia normativa;
- evidencia visible en V3 preparada por Python;
- gate formal P3 con criterios `P3C01`–`P3C13`;
- registro versionado de evidencia de benchmarks;
- motor genérico `exact_rows_v1` para futuros datasets primarios;
- benchmark reproducible `benchmark_p3b.json` en CI.

Primer dataset cargado:

`PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_SECONDARY_V1`

Es una **reproducción secundaria** utilizada únicamente para desarrollo y benchmark de infraestructura. Requiere opt-in explícito y conserva:

```text
verification_status = PENDING_PRIMARY_VERIFICATION
professional_emission = false
automatic_normative_lookup = false
```

El benchmark P3B fija casos 2→0.80, 3→0.70 y 12→0.45 para verificar lookup exacto y trazabilidad. Un CI verde **no valida la tabla normativa primaria**.

La fuente oficial MINEM/CNE ya está fijada en `ampacity_primary_sources.json` como `PINNED` con:

```text
expected_sha256 = 2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64
```

La copia fue capturada desde la URL oficial registrada mediante GitHub Actions run `32875620716`. Este pin cierra P3C08, pero no verifica todavía la Tabla 5C ni promueve el dataset secundario actual.

Detalle: `docs/P3B_DATASETS_NUMERICOS.md`, `docs/P3B_EVIDENCIA_PRIMARIA.md`, `docs/P3_EXIT_GATE.md` y `docs/P3_BENCHMARK_EVIDENCE.md`.

### Gate formal de salida P3 — implementado

`evaluar_cierre_p3()` separa el estado de la fase del estado del modelo y bloquea el paso formal a P4 mientras exista algún criterio P3-v1 pendiente.

Infraestructura y fuente `P3C01`–`P3C08`: implementadas.

Bloqueantes actuales:

- `P3C09` — al menos una revisión numérica `PRIMARY_VERIFIED`;
- `P3C10` — estrategia validada de `Iz_base`; infraestructura P3C10A/B implementada y primer candidato Tabla 2 P3C10C pendiente de revisión humana;
- `P3C11` — cobertura primaria de 5A/5B/5C/5D/5E;
- `P3C12` — benchmarks normativos independientes contra fuente primaria;
- `P3C13` — madurez de ampacidad al menos `VALIDATED_WITH_LIMITATIONS`.

### Pendiente para cerrar P3

- cargar y revisar el primer subconjunto `PRIMARY_VERIFIED`, preferentemente pequeño y auditable (`P3C09`);
- completar la revisión/promoción del primer candidato de `Iz_base` Tabla 2 y extender la estrategia primaria de Tablas 1/2 (`P3C10`);
- completar subconjuntos primarios de 5A/5B/5C/5D/5E según alcance (`P3C11`);
- incorporar benchmarks independientes primarios por familia (`P3C12`);
- mantener BT/MT y ámbitos normativos separados;
- mantener política explícita de valores no tabulados;
- elevar madurez solo si la evidencia lo permite (`P3C13`).

P3 permanece `UNDER_VALIDATION` y no habilita emisión profesional automática.

**Bloqueo humano actual:** P3C09 (Tabla 5C) y el primer candidato P3C10C (Tabla 2) ya disponen de evidencia reproducible, pero conservan revisión humana pendiente y no son `PRIMARY_VERIFIED`. Mientras esa barrera permanece correctamente cerrada, el siguiente bloque técnico automatizable es P3C11A: preparar evidencia primaria candidata para 5A/5B/5D/5E sin promover valores automáticamente. El eje visual V3 permanece en paralelo y ya distingue el origen de `Iz_base` de la evidencia de factores.

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
