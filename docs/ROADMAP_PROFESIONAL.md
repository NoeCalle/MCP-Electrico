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
| P4 — IEC 60909 | **COMPLETA CON LIMITACIONES (P4 v1)** | cortocircuito IEC 60909 validado dentro del alcance declarado |
| P5 — Protección y TCC | **DESBLOQUEADA — FASE PRINCIPAL ACTIVA** | protección del conductor, despeje y coordinación |
| P6 — IEEE 1584 | PENDIENTE | Arc Flash formal y validado |
| P7 — Expediente reproducible | PENDIENTE | paquete reconstruible, fuentes, versiones y hashes |
| P8 — Release profesional 1.0 | PENDIENTE | integración estable de los módulos requeridos |

**Regla de avance:** salvo deuda técnica justificada, el siguiente bloque principal se toma de la primera fase no cerrada. P3-v1 y P4-v1 quedan cerrados en `READY_WITH_LIMITATIONS`; **P5 es la fase principal activa**. Los ejes transversales V y E evolucionan en paralelo.

**Estado actual:**

```text
P3C01–P3C13 DONE
P4C01  DONE     objetivo IEC 60909-0:2026 versionado
P4C02  DONE     backend pandapower determinista
P4C03  DONE     adaptador P2 -> secuencia positiva IEC 60909
P4C04  DONE     3F MAX/MIN + Ik'' + Sk''
P4C05  DONE     ip + Ith con topology/tk/kappa explícitos
P4C06  DONE     2F MAX/MIN + benchmark independiente
P4C07  DONE     1F-T MAX/MIN + Z0 validada + benchmark independiente
P4C08  DONE     2F-T = OUT_OF_SCOPE_P4_V1, sin aproximación
P4C09  DONE     benchmark global del alcance P4-v1
P4C10  DONE     revisión IEC 60909-0:2026 = REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION
P4C11  DONE     Workspace V4 global del alcance P4-v1
                 ├─ P4C11A DONE  3F
                 ├─ P4C11B DONE  2F
                 └─ P4C11C DONE  1F-T
P4C12  DONE     iec60909 = VALIDATED_WITH_LIMITATIONS

P4 = READY_WITH_LIMITATIONS
P5 = DESBLOQUEADA / INICIO
professional_emission = false
automatic_dispatch = false
crosscheck = false
automatic_normative_lookup = false
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

La evolución visual es permanente. El navegador no recalcula ingeniería; consume resultados preparados por Python/MCP y conserva trazabilidad a revisión, elemento, motor y estudio.

Base implementada:

- unifilar SVG técnico;
- workspace persistente;
- IDs estables;
- inspector read-only;
- selección sincronizada;
- vistas de flujo y caída de tensión;
- V2 con fuente, transformadores y conductores trazables;
- V3 con `Ib`, `In`, `Iz_base`, `∏k`, `Iz`, estado y evidencia normativa;
- **V4 completo para P4-v1** con 3F, 2F y 1F-T MAX/MIN, barras de falla, Rk/Xk, Rk0/Xk0 cuando aplica, motor/versión/madurez y políticas de secuencia visibles.

La revisión visual humana autorizada del cierre P3 se conserva como `AI_VISUAL_REVIEW_USER_AUTHORIZED`; no sustituye CI, benchmarks ni los checks estructurales.

P4C08 excluye 2F-T de P4-v1, por lo que V4 no fabrica una visualización de un cálculo inexistente. Si 2F-T reingresa en una versión futura, deberá reabrirse su gate visual.

P4C10 no requiere una segunda interfaz: V4 muestra el estado de edición que ya viene preparado por Python. El cambio a `REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION` no introduce ningún cálculo normativo en JavaScript.

P4C12 tampoco crea una interfaz nueva: las suites 3F/2F/1F-T exponen la madurez `VALIDATED_WITH_LIMITATIONS` preparada en Python y el mismo workspace V4 la presenta de forma read-only. La siguiente ampliación visual importante corresponde a **V5 — protección/TCC**.

Detalle: `docs/ROADMAP_VISUAL.md`.

## Eje transversal E — selección determinista de motor

Reglas vigentes:

1. OpenDSS continúa como motor por defecto para flujo y capacidades de distribución donde sea preferente.
2. pandapower 3.5.4 es el backend preferente para el módulo IEC 60909 P4-v1, cuya madurez es `VALIDATED_WITH_LIMITATIONS`; la integración pandapower de flujo P1.5 sigue separada y experimental.
3. ampacidad, reglas de protección-conductor y IEEE 1584 pertenecen a la capa MCP.
4. la matriz E expone motor, requisitos, madurez y readiness.
5. datos faltantes o limitaciones del backend se expresan; nunca se sustituyen silenciosamente.
6. `automatic_dispatch=false`.
7. `crosscheck=false`.

La matriz recomienda/selecciona determinísticamente, pero **no despacha automáticamente la ejecución**.

Para IEC 60909:

- 3F: `FOUNDATION_READY`;
- 2F: `FOUNDATION_READY`, con `Z2=Z1` explícita y limitada;
- 1F-T: `FOUNDATION_READY`, con Z0/C0/neutro explícitos y `Z2=Z1` limitada;
- 2F-T: `OUT_OF_SCOPE_P4_V1`, reconocida pero `ENGINE_NOT_READY` con código `P4READY804`;
- edición objetivo: `REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION`, con `full_conformance_claim=false`;
- madurez del módulo `iec60909`: `VALIDATED_WITH_LIMITATIONS`;
- `short_circuit` permanece `UNDER_VALIDATION` y describe únicamente OpenDSS FaultStudy exploratorio.

Detalle: `docs/ENGINE_SELECTION.md`, `docs/P4C08_2FT_SCOPE.md` y `docs/P4C10_IEC60909_2026_REVIEW.md`.

## Fase P0 — Gobernanza técnica y QA

**Estado: COMPLETA.**

Entregables:

- matriz de madurez por módulo;
- `ModelQAService` con `INFO`, `WARNING`, `ERROR`, `BLOCKER`;
- `auditar_modelo()`;
- `apto_para_emision` determinístico;
- reglas QA documentadas y probadas.

## Fase P1 — Flujo de potencia y caída de tensión

**Estado: COMPLETA CON LIMITACIONES (P1 v1).**

Cobertura validada:

- redes radiales trifásicas balanceadas dentro del fixture publicado;
- referencia analítica independiente de OpenDSS;
- tensión, corriente, pérdidas y caída de tensión;
- tolerancias predefinidas y CI.

`power_flow` y `voltage_drop` permanecen `VALIDATED_WITH_LIMITATIONS`, no globalmente `VALIDATED`.

## Fase P1.5 — Segundo motor pandapower

**Estado: COMPLETA COMO INTEGRACIÓN EXPERIMENTAL.**

Entregables:

- pandapower 3.5.x versionado;
- `pandapower_engine.py`;
- tool explícita de flujo;
- rechazo determinístico de elementos fuera de alcance;
- benchmark frente a referencia analítica, no contra OpenDSS;
- sin cross-check automático.

P1.5 no habilita por sí sola IEC 60909; P4 añade contratos y gates propios.

## Fase P2 — Datos de entrada profesionales

**Estado: COMPLETA CON LIMITACIONES (P2 v1).**

Incluye:

- transformadores con kVA, tensiones, grupo vectorial, `%Z`, X/R, taps, pérdidas y procedencia;
- red equivalente Scc máxima/mínima, X/R, tensión y escenario;
- biblioteca BT/MT trazable;
- R0/X0 explícitos de fuente/líneas;
- ficha homopolar canónica de transformador;
- readiness separado de ejecución;
- workspace V2;
- gate formal P2.

Reglas relevantes para P4:

- R0/X0 no se inventa desde geometrías desconocidas;
- grupo vectorial, neutro y puesta a tierra condicionan Z0;
- datos suficientes para 3F/2F no implican datos suficientes para fallas a tierra.

Detalle: `docs/P2_EXIT_GATE.md` y `docs/SECUENCIA_CERO_P2.md`.

## Fase P3 — Ampacidad normativa y conductor

**Estado: COMPLETA CON LIMITACIONES (P3 v1) — P3C01–P3C13 DONE.**

**Gate formal de salida P3 — implementado.** El gate separa cierre de fase, readiness del modelo activo y suficiencia de evidencia normativa; cerrar P3-v1 no equivale a cobertura normativa exhaustiva.

Estado de criterios finales preservado:

- `P3C11` — `DONE` — benchmark numérico/dataset y contratos de lookup exacto;
- `P3C12` — `DONE` — benchmark independiente primario;
- `P3C13` — `DONE` — cierre de madurez/visual y gate de salida.

La evidencia primaria versionada preservada incluye:

- `PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_PRIMARY_V1`;
- `PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1`;
- para el caso exacto Método C / Cu / XLPE-EPR / 3 conductores cargados / 70 mm²: **Iz_base = 229 A**.

La **Tabla 5D** permanece documentada como ruta normativa de correcciones/condiciones donde aplica; no se inventan valores tabulados ausentes.

Objetivo térmico:

```text
Ib <= In <= Iz
Iz = Iz_base * product(k_i)
```

Entregables consolidados:

- Ib explícita o corriente de flujo aceptada expresamente;
- In y referencia;
- Iz_base mediante evidencia P3B cuando existe coincidencia exacta;
- factores explícitos/referenciados;
- router normativo P3A;
- lookup exacto sin interpolación/extrapolación;
- evidencia primaria versionada;
- benchmark independiente y gate formal;
- V3 read-only;
- `validation_status.ampacity = VALIDATED_WITH_LIMITATIONS`.

La política sigue:

```text
automatic_normative_lookup = false
```

Los casos fuera de evidencia exacta continúan fail-closed/manuales y la cobertura puede ampliarse sin reabrir P3-v1.

Documentación canónica preservada:

- `docs/P3_AMPACIDAD.md`;
- `docs/P3A_PERFILES_NORMATIVOS.md`;
- `docs/P3B_DATASETS_NUMERICOS.md`;
- `docs/P3C10_BASE_AMPACITY_STRATEGY.md`;
- `docs/P3_EXIT_GATE.md`.

## Fase P4 — Cortocircuito IEC 60909

**Estado: COMPLETA CON LIMITACIONES (P4 v1) — P4C01–P4C12 DONE.**

### Objetivo normativo y backend

- objetivo: **IEC 60909-0:2026, edición 3.0**;
- backend preferente: pandapower 3.5.4;
- `automatic_dispatch=false`;
- `crosscheck=false`;
- `target_edition_conformance=REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION`;
- `full_conformance_claim=false`;
- `validation_status.iec60909=VALIDATED_WITH_LIMITATIONS`;
- `validation_status.short_circuit=UNDER_VALIDATION` para OpenDSS FaultStudy exploratorio;
- `professional_emission=false`.

### Alcance P4-v1

```text
IN_SCOPE: 3F, 2F, 1F-T
OUT_OF_SCOPE_P4_V1: 2F-T
```

#### 3F

- MAX/MIN;
- `Ik''`, `Sk''`, Rk/Xk;
- `ip/Ith` con topología, `tk_s` y κ explícitos;
- benchmark P4C09A;
- V4 P4C11A.

#### 2F

- MAX/MIN;
- `Ik''`, Rk/Xk;
- `ip/Ith` con gates explícitos;
- `Z2=Z1` limitada a red simétrica pasiva;
- benchmark P4C06;
- V4 P4C11B;
- `Sk''` no promocionada contractualmente.

#### 1F-T

- MAX/MIN;
- `Ik''`, Rk/Xk, Rk0/Xk0;
- Z0 de fuente preservando R0/X0 absolutos;
- R0/X0/C0 por línea;
- Z0 de transformadores + neutro explícito;
- `Z2=Z1` limitada a red simétrica pasiva;
- benchmark P4C07 + caso Dyn11;
- V4 P4C11C;
- `Sk''/ip/Ith` no promocionadas.

#### 2F-T — P4C08

**Excluida formalmente de P4-v1.** Pandapower 3.5.4 `calc_sc()` no ofrece token directo 2F-T. MCP no la aproxima como 2F/1F-T ni crea un solver paralelo sin validación.

Reingreso futuro requiere backend directo o solver MCP dedicado con benchmark, CI, revisión normativa y V4.

### P4C09 — validación independiente

**DONE para el alcance P4-v1:**

- 3F → P4C09A PASS;
- 2F → P4C06 PASS;
- 1F-T → P4C07 PASS;
- 2F-T → no requerida por estar formalmente fuera de alcance.

### P4C10 — revisión específica IEC 60909-0:2026

**DONE CON LIMITACIONES EXPLÍCITAS.**

La revisión se registra como:

```text
REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION
full_conformance_claim = false
```

P4C10 contrastó la edición objetivo con metadata oficial, evidencia pública de la edición final y fuente/documentación pinneada de pandapower 3.5.4. La edición 2026 declara una revisión técnica con especial actualización/reestructuración del Capítulo 6 de modelado de equipos; por eso no se usa `VERIFIED_AGAINST_TARGET_EDITION` sin una futura trazabilidad ecuación/tabla contra el texto completo licenciado.

Los equipos y magnitudes fuera de P4-v1 permanecen explícitos: generadores/motores, convertidores, FACTS/HVDC, 2F-T, `Ib`, `Ik` y `ip/Ith` 1F-T donde no existe ruta validada.

Detalle: `docs/P4C10_IEC60909_2026_REVIEW.md`.

### P4C11 — Workspace V4

**DONE para el alcance P4-v1:**

- P4C11A 3F;
- P4C11B 2F;
- P4C11C 1F-T;
- coexistencia de los tres estudios en la misma pestaña/unifilar;
- JavaScript sin cálculo eléctrico;
- estado de revisión 2026 visible desde el payload Python.

### P4C12 — madurez final

**DONE: `VALIDATED_WITH_LIMITATIONS`.**

El cierre se aplica exclusivamente al módulo `iec60909`. El `short_circuit` exploratorio de OpenDSS permanece `UNDER_VALIDATION`; por tanto el gate no convierte automáticamente todo estudio de cortocircuito en validado.

P4C12 exige simultáneamente: target 2026 versionado, backend/políticas deterministas, alcance cerrado, benchmark independiente de cada falla incluida, V4 completo, P4C10 cerrado con limitaciones explícitas, contratos fail-closed y `professional_emission=false`.

### Siguiente bloque

**P5 — protección del conductor y coordinación/TCC.** P4 habilita el inicio de P5, pero no crea dispositivos, curvas, ajustes ni tiempos de despeje por sí solo.

Detalle: `docs/P4_IEC60909.md`.

## Fase P5 — Protección del conductor y coordinación

**Estado: DESBLOQUEADA — FASE PRINCIPAL ACTIVA.**

Entregables previstos:

- biblioteca comercial trazable;
- Icu/Ics/Icw;
- Ir/Isd/Ii;
- curvas TCC;
- sobrecarga y cortocircuito del conductor;
- `I²t <= k²S²`;
- tiempos de despeje;
- selectividad/backup;
- V5 con panel TCC.

El `tk_s` actual de P4 no sustituye P5: debe vincularse a dispositivos/curvas reales. El primer bloque P5 debe definir el contrato de datos de protección y la estrategia de curvas antes de habilitar coordinación o tiempos de despeje profesionales.

## Fase P6 — Arc Flash IEEE 1584

**Estado: PENDIENTE.**

Entregables previstos:

- configuraciones de electrodos;
- gap, enclosure y working distance;
- Iarc e Iarc_min;
- tiempo de despeje desde P5;
- energía incidente;
- arc-flash boundary;
- benchmark independiente;
- V6 Arc Flash.

Lee permanece separado como método experimental/histórico.

## Fase P7 — Expediente reproducible

**Estado: PENDIENTE.**

Paquete previsto:

- `report.pdf`;
- `model.json`;
- export DSS;
- `sources.json`;
- `assumptions.json`;
- matriz de validación;
- QA;
- versiones de motores/bibliotecas;
- SHA-256;
- salida vectorial reportable.

## Fase P8 — Release profesional 1.0

**Estado: PENDIENTE.**

Criterios mínimos:

- P0 completa;
- P1 validada dentro de alcance;
- QA bloqueante;
- P2 cerrada;
- P3 validada dentro de alcance;
- P4 IEC 60909 validado dentro de alcance;
- P5 protección-conductor;
- P7 expediente reproducible;
- documentación de límites;
- CI con benchmarks;
- workspace coherente con los estudios incluidos.

Arc Flash puede entrar en 1.0 o posteriormente, pero nunca se presentará como IEEE 1584 antes de cerrar P6.

## Regla de emisión

`apto_para_emision=true` significa únicamente que el modelo supera los chequeos automáticos de los estudios solicitados y que los módulos requeridos tienen un estado de validación aceptable.

No significa que el software asuma responsabilidad profesional ni sustituye la revisión, criterio, firma o colegiatura del ingeniero responsable.