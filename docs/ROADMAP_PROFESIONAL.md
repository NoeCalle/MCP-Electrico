# Roadmap profesional — MCP Eléctrico

## Objetivo

Evolucionar MCP Eléctrico desde una herramienta funcional basada en OpenDSS hacia una plataforma de ingeniería reproducible y validada, apta para sustentar estudios revisados y emitidos por un profesional responsable.

La firma y responsabilidad profesional siempre corresponden al ingeniero. El objetivo del roadmap es que la herramienta entregue resultados trazables, reproducibles, verificables y con límites de aplicación explícitos.

## Mapa maestro — orden de ejecución

Este documento es la **guía maestra del proyecto**. Una fase no se considera cumplida por tener una primera implementación: debe satisfacer su criterio de salida, mantener CI/pruebas, documentación, QA y representación visual cuando corresponda.

| Fase | Estado actual | Resultado esperado |
| --- | --- | --- |
| P0 — Gobernanza y QA | COMPLETA | madurez explícita, QA y gate de emisión |
| P1 — Flujo y caída de tensión | COMPLETA CON LIMITACIONES | benchmarks independientes y regresión cuantitativa |
| P1.5 — pandapower | COMPLETA COMO INTEGRACIÓN EXPERIMENTAL | segundo motor disponible sin cross-check |
| P2 — Datos profesionales | **COMPLETA CON LIMITACIONES (P2 v1)** | equipos/fuente/cables trazables sin supuestos silenciosos |
| P3 — Ampacidad normativa | **COMPLETA CON LIMITACIONES (P3 v1)** | `Ib <= In <= Iz`, routing normativo, evidencia primaria y benchmarks independientes |
| P4 — IEC 60909 | **EN DESARROLLO — P4C01–P4C06 DONE** | cortocircuito formal validado; 3F/2F numéricos y visibles en V4 |
| P5 — Protección y TCC | **BLOQUEADA POR P4** | protección del conductor, despeje y coordinación |
| P6 — IEEE 1584 | PENDIENTE | Arc Flash formal y validado |
| P7 — Expediente reproducible | PENDIENTE | paquete reconstruible, fuentes, versiones y hashes |
| P8 — Release profesional 1.0 | PENDIENTE | integración estable de los módulos requeridos |

**Regla de avance:** salvo deuda técnica justificada, el siguiente bloque principal se toma de la primera fase no cerrada. P3-v1 queda cerrado en `READY_WITH_LIMITATIONS`; **P4 es la fase principal activa**. Los ejes transversales V y E evolucionan en paralelo. P3 puede ampliar cobertura normativa de forma incremental sin reabrir su gate v1.

Estado de control actual:

```text
P4C01  DONE     objetivo IEC 60909-0:2026 versionado
P4C02  DONE     backend pandapower determinista
P4C03  DONE     adaptador P2 -> secuencia positiva IEC 60909
P4C04  DONE     3F MAX/MIN + Ik'' + Sk''
P4C05  DONE     ip + Ith con topology/tk/kappa explícitos
P4C06  DONE     2F MAX/MIN + benchmark independiente
P4C07  PENDING  1F-T + cadena Z0 validada
P4C08  PENDING  estrategia 2F-T
P4C09  PENDING  benchmark global del alcance P4-v1
                 ├─ P4C09A DONE  benchmark independiente 3F
                 └─ cobertura 2F independiente incorporada en P4C06
P4C10  PENDING  revisión específica contra IEC 60909-0:2026
P4C11  PENDING  Workspace V4 global
                 ├─ P4C11A DONE  3F MAX/MIN visible
                 └─ P4C11B DONE  2F MAX/MIN visible
P4C12  PENDING  madurez final del módulo

P4 = NOT_READY
P5 = BLOQUEADA
professional_emission = false
```

## Principio rector

OpenDSS se mantiene como motor numérico principal y por defecto para el flujo actualmente validado. El proyecto incorpora motores complementarios cuando existe una ventaja técnica clara para un estudio específico, siempre con alcance, versión, madurez y limitaciones explícitos.

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

Base implementada:

- unifilar SVG técnico;
- workspace persistente;
- IDs estables;
- inspector read-only;
- selección sincronizada;
- vistas de flujo y caída de tensión;
- V2 con fuente, transformadores y conductores trazables;
- V3 con `Ib`, `In`, `Iz_base`, `∏k`, `Iz`, estado, metadata P3A y evidencia normativa preparada por Python;
- V4 experimental con cortocircuito IEC 60909 **3F y 2F MAX/MIN**, barra de falla, magnitudes calculadas, motor/versión/madurez y política Z2 visible en 2F.

Regla: el navegador **no recalcula ingeniería**. Consume resultados producidos por Python/MCP y conserva trazabilidad a `model_revision`, elemento, motor y estudio.

Detalle: `docs/ROADMAP_VISUAL.md`.

## Eje transversal E — selección determinista de motor

Objetivo: que la elección de OpenDSS, pandapower o una capa propia MCP **no dependa de improvisación del LLM**.

Reglas vigentes:

1. OpenDSS continúa como motor por defecto para el flujo validado y capacidades de distribución donde sea preferente.
2. pandapower es el backend preferente experimental para IEC 60909 P4 dentro del alcance declarado.
3. ampacidad, protección-conductor y IEEE 1584 pertenecen a la capa de orquestación/postproceso MCP.
4. la matriz E responde motor preferente, alternativas, requisitos, madurez, readiness y aptitud de ejecución/emisión.
5. faltantes de datos o limitaciones del backend se expresan; nunca se sustituyen silenciosamente.
6. `automatic_dispatch=false`.
7. `crosscheck=false` en el alcance actual.
8. la matriz recomienda/selecciona determinísticamente, pero **no despacha automáticamente la ejecución**.

Para IEC 60909, la matriz E reconoce actualmente:

- 3F: `FOUNDATION_READY`, experimental;
- 2F: `FOUNDATION_READY`, experimental, con política `Z2=Z1` explícita solo para red simétrica pasiva;
- 1F-T: bloqueada hasta cerrar P4C07 y validar la cadena Z0;
- 2F-T: bloqueada hasta definir P4C08; no se aproxima silenciosamente como 2F ni 1F-T.

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

P1.5 por sí sola no habilita IEC 60909 ni protección; P4 añade sus contratos, gates y benchmarks propios.

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

Limitaciones P2 v1 relevantes para P4:

- R0/X0 por geometría física no se inventa;
- la secuencia cero profesional de transformadores requiere proyección validada antes de 1F-T;
- grupo vectorial, neutro y puesta a tierra condicionan caminos de secuencia cero;
- datos P2 suficientes para 3F/2F no implican automáticamente datos suficientes para fallas a tierra.

Detalle: `docs/P2_EXIT_GATE.md` y `docs/SECUENCIA_CERO_P2.md`.

## Fase P3 — Ampacidad normativa y conductor

**Estado: COMPLETA CON LIMITACIONES (P3 v1) — P3C01–P3C13 DONE.**

Objetivo: verificar selección térmica del conductor mediante:

```text
Ib <= In <= Iz
Iz = Iz_base * product(k_i)
```

sin convertir un rating de catálogo en `Iz` final por simple etiqueta.

Entregables consolidados:

- `Ib` explícita o corriente de flujo aceptada expresamente como corriente de diseño;
- `In` explícito con referencia;
- `Iz_base` normativa primaria mediante dataset P3B cuando existe coincidencia exacta validada;
- factores explícitos y referenciados;
- router normativo P3A;
- datasets y lookup exacto P3B sin interpolación/extrapolación;
- evidencia primaria versionada;
- benchmark independiente y gate formal P3;
- V3 read-only con origen de `Iz_base`, tabla/dataset y calidad de evidencia;
- `validation_status.ampacity = VALIDATED_WITH_LIMITATIONS`.

P3-v1 no implica cobertura exhaustiva de toda fila normativa. Los casos fuera de evidencia exacta continúan `VALUE_NOT_TABULATED`, manuales o fail-closed. La cobertura puede ampliarse incrementalmente sin bloquear P4.

Detalle: `docs/P3_AMPACIDAD.md`, `docs/P3_EXIT_GATE.md` y documentación P3A/P3B.

## Fase P4 — Cortocircuito IEC 60909

**Estado: EN DESARROLLO — P4C01–P4C06 DONE.**

Objetivo: disponer de un estudio formal conforme a una edición declarada de IEC 60909, con datos profesionales, resultados reproducibles, benchmarks independientes y límites visibles.

### Objetivo normativo y backend

- objetivo: **IEC 60909-0:2026, edición 3.0**;
- backend candidato/preferente: pandapower 3.5.x;
- `automatic_dispatch=false`;
- `crosscheck=false`;
- `target_edition_conformance=UNVERIFIED_AGAINST_TARGET_EDITION` hasta P4C10;
- `professional_emission=false`.

### Alcance numérico actual

**3F — implementada experimentalmente**

- MAX/MIN;
- `Ik''`, `Sk''`, Rk/Xk;
- `ip/Ith` con topología, `tk_s` y κ explícitos;
- benchmark independiente P4C09A.

**2F fase-fase — implementada experimentalmente**

- MAX/MIN;
- `Ik''`, Rk/Xk;
- `ip/Ith` con los mismos gates explícitos;
- política `Z2=Z1` limitada a red simétrica pasiva, visible y no universal;
- benchmark independiente por componentes simétricas;
- `Sk''` 2F todavía no se promociona como magnitud contractual normalizada.

**1F-T — P4C07 PENDING**

No se habilita por la sola existencia de `fault="1ph"` en pandapower. Debe cerrarse la cadena profesional de secuencia cero:

- Z0 de fuente;
- R0/X0 de líneas;
- grupo vectorial y trayectoria Z0 de transformadores;
- neutro y puesta a tierra;
- mapeo exacto a parámetros pandapower;
- benchmark independiente.

**2F-T — P4C08 PENDING**

La API `calc_sc()` no expone un token directo de falla bifásica a tierra en el contrato actual. MCP no la aproximará silenciosamente.

### P4C05 — ip/Ith

Contrato actual:

```text
calcular_ip_ith = true
topology = radial | meshed
tk_s > 0
kappa_method = C
```

No se acepta `topology="auto"` y no se inventa `tk_s`. El tiempo deberá vincularse naturalmente con P5/TCC cuando esa fase exista.

### P4C09 — validación independiente

Cobertura ya incorporada:

- P4C09A: benchmark independiente 3F MAX/MIN;
- P4C06: benchmark independiente 2F MAX/MIN.

P4C09 global permanece pendiente hasta cubrir el alcance P4-v1 que finalmente se declare.

### P4C11 — Workspace V4

Subhitos visuales cerrados:

- **P4C11A DONE:** 3F MAX/MIN, barra de falla, `Ik''`, `Sk''`, `ip`, `Ith`, Rk/Xk, motor, versión, edición y madurez;
- **P4C11B DONE:** 2F MAX/MIN en la misma pestaña, coexistencia con 3F, política Z2 visible, ausencia explícita de `Sk''` contractual 2F y overlay de barras de falla.

JavaScript no recalcula ingeniería. V4 consume snapshots versionados y conserva `professional_emission=false`.

P4C11 global sigue pendiente hasta que la vista cubra el alcance final que cierre P4-v1.

Detalle: `docs/P4_IEC60909.md` y `docs/ROADMAP_VISUAL.md`.

### Siguiente bloque

**P4C07 — 1F-T + secuencia cero validada.**

El orden de trabajo será: auditar modelo Z0 existente → fijar contrato/mapeo pandapower → fail-closed por dato faltante → implementar 1F-T → benchmark independiente → incorporar resultado a V4. No se avanzará por fórmulas improvisadas ni valores por defecto silenciosos.

## Fase P5 — Protección del conductor y coordinación

**Estado: BLOQUEADA POR P4.**

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

El `tk_s` usado hoy por P4 no sustituye esta fase. P5 deberá producir tiempos de despeje trazables a dispositivos/curvas reales.

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
- P4 IEC 60909 validado dentro de alcance declarado;
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
