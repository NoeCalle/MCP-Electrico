# Roadmap profesional — MCP Eléctrico

## Objetivo

Evolucionar MCP Eléctrico desde una herramienta funcional basada en OpenDSS hacia una plataforma de ingeniería reproducible, trazable y verificable. La firma y responsabilidad profesional permanecen siempre en el ingeniero responsable.

El cierre de una fase no significa cobertura universal: cada módulo declara alcance, madurez, fuentes, limitaciones y gates explícitos.

## Mapa maestro — orden de ejecución

Este documento es la guía maestra del proyecto. Los ejes visual y de selección de motor evolucionan en paralelo.

| Fase | Estado actual | Resultado esperado |
| --- | --- | --- |
| P0 — Gobernanza y QA | COMPLETA | madurez explícita, QA y gates |
| P1 — Flujo y caída de tensión | COMPLETA CON LIMITACIONES | benchmarks independientes y regresión cuantitativa |
| P1.5 — pandapower | COMPLETA COMO INTEGRACIÓN EXPERIMENTAL | segundo motor explícito sin cross-check |
| P2 — Datos profesionales | **COMPLETA CON LIMITACIONES (P2 v1)** | fuente/equipos/cables trazables sin supuestos silenciosos |
| P3 — Ampacidad normativa | **COMPLETA CON LIMITACIONES (P3 v1)** | `Ib <= In <= Iz`, routing, evidencia y benchmarks |
| P4 — IEC 60909 | **COMPLETA CON LIMITACIONES (P4 v1)** | cortocircuito dentro del alcance declarado |
| P5 — Protección y TCC | **COMPLETA CON LIMITACIONES (P5 v1)** | protección-conductor, TCC, clearing time, coordinación temporal y V5 |
| P6 — IEEE 1584 | **DEFERRED** | Arc Flash formal cuando se reactive |
| P7 — Expediente reproducible | **COMPLETA CON LIMITACIONES (P7 mínimo)** | snapshot, reconstrucción, reporte y gate de uso interno |
| P8 — Engineering Preview 0.9 | **ACTIVA — PILOTO REAL** | uso operativo controlado en proyectos reales |

**Regla de avance:** P5 está cerrada funcionalmente como `READY_WITH_LIMITATIONS`. P6 IEEE 1584 queda diferida por decisión de producto. P7A–P7D cierran el expediente mínimo y habilitan MCP Eléctrico 0.9 Engineering Preview para uso interno controlado. El siguiente paso es un piloto de subestación real; Arc Flash se retomará posteriormente y no bloquea esta primera etapa operativa.

**Estado actual:**

```text
P3C01–P3C13 DONE
P4C01–P4C12 DONE
P5A–P5G DONE
P7A–P7D DONE

P4 = READY_WITH_LIMITATIONS
P5 = READY_WITH_LIMITATIONS
P6 = DEFERRED
P7 = READY_WITH_LIMITATIONS
P8 = MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW

P5 operational_path_ready    = true
P5 engineering_preview_ready = false
P5 next_phase                = P7_REPRODUCIBLE_DOSSIER_MINIMUM

P7 engineering_preview_ready = true
P7 internal_use_ready        = true
P7 allowed_use               = CONTROLLED_INTERNAL_ENGINEERING_PREVIEW
P7 next_activity             = REAL_SUBSTATION_PILOT

professional_report = false
professional_emission = false
automatic_dispatch = false
crosscheck=false
automatic_normative_lookup = false
```

Usable internamente no equivale a `professional_emission=true`. La Engineering Preview 0.9 debe utilizar proyectos reales para descubrir fricción antes del endurecimiento final del producto.

## Principio rector

OpenDSS se mantiene como motor principal y por defecto para flujo/distribución dentro del alcance actualmente validado. pandapower 3.5.4 actúa como backend determinista para IEC 60909. Las reglas MCP cubren ampacidad, protecciones y futuras capas de ingeniería.

La profesionalización se apoya en:

1. calidad y procedencia de datos;
2. selección determinista del motor;
3. validación independiente y CI;
4. normativa versionada;
5. representación y reporte reproducibles;
6. fail-closed ante datos o evidencia insuficientes.

## Estados de madurez

Los módulos usan:

- `NOT_IMPLEMENTED`;
- `EXPERIMENTAL`;
- `UNDER_VALIDATION`;
- `VALIDATED_WITH_LIMITATIONS`;
- `VALIDATED`.

La madurez de un módulo no sustituye la revisión profesional del modelo concreto. Una **fase** puede estar `READY_WITH_LIMITATIONS` aunque sus módulos sigan `EXPERIMENTAL`, siempre que el gate explicite ese alcance y no transforme la fase en un claim normativo superior.

## Eje transversal V — workspace y representación visual

El navegador no recalcula ingeniería: consume resultados preparados por Python/MCP y conserva trazabilidad a revisión, elemento, motor y estudio.

Base consolidada:

- unifilar SVG técnico;
- workspace persistente;
- IDs estables;
- inspector read-only;
- selección sincronizada;
- flujo y caída de tensión;
- V2 con datos profesionales;
- V3 con `Ib`, `In`, `Iz_base`, `∏k`, `Iz` y evidencia normativa;
- V4 de cortocircuito IEC 60909;
- V5 de protección/TCC con curvas preparadas en Python, ratings, ajustes y resultados P5 vigentes.

La revisión visual humana del cierre P3 se conserva como `AI_VISUAL_REVIEW_USER_AUTHORIZED`; no sustituye CI ni benchmarks.

V5 reutiliza el mismo workspace/unifilar/inspector. No se crea una segunda interfaz y JavaScript no interpola TCC ni calcula protección.

Detalle: `docs/ROADMAP_VISUAL.md`.

## Eje transversal E — selección determinista de motor

Reglas vigentes:

1. OpenDSS continúa como motor por defecto para flujo y capacidades de distribución donde es preferente.
2. pandapower 3.5.4 es el backend preferente del módulo IEC 60909 P4-v1.
3. ampacidad y protección-conductor pertenecen a la capa MCP.
4. IEEE 1584 pertenecerá a MCP cuando P6 se reactive.
5. datos faltantes o limitaciones se expresan; nunca se sustituyen silenciosamente.
6. `automatic_dispatch=false`.
7. `crosscheck=false`.

La matriz recomienda/selecciona determinísticamente, pero **no despacha automáticamente la ejecución**.

Para IEC 60909:

- 3F: foundation soportada;
- 2F: `Z2=Z1` explícita y limitada al alcance simétrico pasivo;
- 1F-T: Z0/C0/neutro explícitos;
- 2F-T contractual: fuera de P4-v1, con cualquier extensión futura claramente separada;
- edición objetivo: `REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION`;
- `full_conformance_claim=false`;
- `iec60909=VALIDATED_WITH_LIMITATIONS`;
- OpenDSS `short_circuit=UNDER_VALIDATION` como FaultStudy exploratorio.

Detalle: `docs/ENGINE_SELECTION.md` y documentación P4.

## Fase P0 — Gobernanza técnica y QA

**Estado: COMPLETA.**

Incluye matriz de madurez, QA determinístico, `auditar_modelo()`, gates y separación entre readiness técnico y emisión.

## Fase P1 — Flujo de potencia y caída de tensión

**Estado: COMPLETA CON LIMITACIONES (P1 v1).**

Cobertura cuantitativa validada en fixtures radiales trifásicos balanceados con referencia independiente. `power_flow` y `voltage_drop` permanecen `VALIDATED_WITH_LIMITATIONS`.

## Fase P1.5 — Segundo motor pandapower

**Estado: COMPLETA COMO INTEGRACIÓN EXPERIMENTAL.**

Incluye pandapower 3.5.x, bridge explícito, rechazo determinístico de incompatibilidades y benchmark independiente. No existe router automático ni cross-check.

P1.5 no crea por ahora una segunda interfaz visual

## Fase P2 — Datos de entrada profesionales

**Estado: COMPLETA CON LIMITACIONES (P2 v1).**

Incluye:

- transformadores con datos eléctricos/procedencia;
- red equivalente Scc MAX/MIN y X/R;
- biblioteca BT/MT trazable;
- conductor asignado al elemento;
- R0/X0 explícitos de fuente/líneas;
- ficha homopolar de transformador;
- readiness separado de ejecución;
- workspace V2;
- gate formal P2.

Reglas relevantes:

- no se inventa R0/X0;
- grupo vectorial, neutro y puesta a tierra condicionan Z0;
- datos suficientes para 3F/2F no implican suficiencia para fallas a tierra;
- ampacidad de catálogo todavía no es `Iz` normativo.

Detalle: `docs/P2_EXIT_GATE.md` y `docs/SECUENCIA_CERO_P2.md`.

## Fase P3 — Ampacidad normativa y conductor

**Estado: COMPLETA CON LIMITACIONES (P3 v1) — P3C01–P3C13 DONE.**

Gate formal de salida P3 — implementado.

El gate separa cierre de fase, readiness del modelo activo y suficiencia de evidencia normativa.

Criterios preservados:

- `P3C11` — `DONE` — datasets/lookup exacto y contratos finales;
- `P3C12` — `DONE` — benchmark independiente primario;
- `P3C13` — `DONE` — cierre de madurez/visual y gate.

Evidencia primaria preservada:

- `PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_PRIMARY_V1`;
- `PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1`;
- caso exacto Método C / Cu / XLPE-EPR / 3 conductores cargados / 70 mm²: **Iz_base = 229 A**.

La **Tabla 5D** permanece documentada para sus rutas de corrección/condición; no se inventan valores ausentes.

Objetivo térmico:

```text
Ib <= In <= Iz
Iz = Iz_base * product(k_i)
```

La política sigue:

```text
automatic_normative_lookup = false
professional_emission = false
```

Los casos fuera de evidencia exacta continúan fail-closed/manuales.

Documentación canónica:

- `docs/P3_AMPACIDAD.md`;
- `docs/P3A_PERFILES_NORMATIVOS.md`;
- `docs/P3B_DATASETS_NUMERICOS.md`;
- `docs/P3C10_BASE_AMPACITY_STRATEGY.md`;
- `docs/P3_EXIT_GATE.md`.

## Fase P4 — Cortocircuito IEC 60909

**Estado: COMPLETA CON LIMITACIONES (P4 v1) — P4C01–P4C12 DONE.**

Objetivo: IEC 60909-0:2026 Ed.3. Backend preferente: pandapower 3.5.4.

```text
automatic_dispatch=false
crosscheck=false
target_edition_conformance=REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION
full_conformance_claim=false
validation_status.iec60909=VALIDATED_WITH_LIMITATIONS
validation_status.short_circuit=UNDER_VALIDATION
professional_emission=false
```

Alcance P4-v1:

```text
IN_SCOPE: 3F, 2F, 1F-T
OUT_OF_SCOPE_P4_V1: 2F-T contractual
```

Incluye MAX/MIN, magnitudes soportadas por tipo de falla, secuencia cero explícita para 1F-T, benchmarks independientes y Workspace V4. `ip/Ith` solo se calculan cuando sus requisitos de topología/tiempo/método están declarados.

P4C10 permanece `REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION`; una verificación integral requiere revisión licenciada futura.

Detalle: `docs/P4_IEC60909.md` y documentos P4 específicos.

## Fase P5 — Protección del conductor y coordinación

**Estado: COMPLETA CON LIMITACIONES (P5 v1) — P5A–P5G DONE.**

El gate formal P5G devuelve:

```text
phase_status              = READY_WITH_LIMITATIONS
ready_for_next_phase      = true
next_phase                = P7_REPRODUCIBLE_DOSSIER_MINIMUM
deferred_phase            = P6_IEEE1584_ARC_FLASH
operational_path_ready    = true
engineering_preview_ready = false
professional_emission     = false
```

Los módulos `protection_data`, `tcc_curve_evaluation`, `protection_checks`, `protection_clearing_time` y `protection_coordination` permanecen `EXPERIMENTAL`. P5G no los promociona por decreto.

### P5A — datos canónicos

- interruptores y fusibles;
- In/Ue y ratings propios;
- Ir/Isd/Ii absolutos;
- procedencia;
- binding con elemento;
- comparación In P3/P5 sin sobreescritura.

### P5B — TCC

- datasets `SINGLE`/`BAND`;
- segmentos explícitos;
- `LOG_LOG_LINEAR` dentro del segmento;
- sin extrapolación;
- sin unión entre discontinuidades;
- semántica de tiempo explícita;
- no se sintetizan curvas.

### P5C — checks

- capacidad de corte declarada;
- breaker PASS con Icu, sin sustituir Ics/Icw;
- fusible con breaking capacity propia;
- `I²t <= k²S²` con `k`, sección y tiempo explícitos;
- binding de sección contra conductor P2 cuando existe.

### P5D — clearing time

Solo `TOTAL_CLEARING_TIME` se promueve automáticamente a `CLEARING_TIME_READY`. Bandas conservan min/max; no se promedian. P4 `tk_s` nunca se usa como fallback.

### P5E — coordinación temporal

Compara downstream/upstream explícitos y usa:

```text
conservative_margin = upstream_time_min - downstream_time_max
```

Un PASS significa `TEMPORAL_POINT_COORDINATION`; no declara selectividad total/parcial, selectividad energética, backup o cascading.

### P5F — Workspace V5

Mismo workspace persistente, con panel Protecciones/TCC, ratings, ajustes, curvas SVG y resultados P5 de la revisión vigente. Las coordenadas de curva se preparan en Python; JavaScript solo navega/selecciona.

### P5G — gate y benchmarks

Suite obligatoria en CI:

```text
MCP_ELECTRICO_P5G_BENCHMARK_SUITE_V1
P5G_B01_TCC_BAND_LOGLOG
P5G_B02_TCC_NO_EXTRAPOLATION
P5G_B03_CLEARING_TIME_BAND
P5G_B04_TEMPORAL_COORDINATION
P5G_B05_BREAKING_CAPACITY
P5G_B06_CONDUCTOR_THERMAL
```

La suite usa `TEST_DATA` y exige:

```text
failed = 0
manufacturer_claim = false
normative_compliance_claim = false
professional_emission = false
```

Detalle: `docs/P5_PROTECTION_TCC.md` y `docs/VALIDACIONES_PENDIENTES.md`.

## Fase P6 — Arc Flash IEEE 1584

**Estado: DEFERRED — PAUSADA POR DECISIÓN DE PRODUCTO.**

P6 no se elimina. Se retomará después de la Engineering Preview y deberá consumir, cuando corresponda, corriente de falla P4 y clearing time P5 trazables.

Futuro alcance:

- configuración de electrodos;
- gap/enclosure/working distance;
- Iarc/Iarc_min;
- clearing time P5;
- energía incidente;
- arc-flash boundary;
- benchmark independiente;
- V6.

Lee permanece separado como método simplificado/experimental y no sustituye IEEE 1584.

## Fase P7 — Expediente reproducible

**Estado: COMPLETA CON LIMITACIONES — P7A–P7D DONE.**

P7 cierra el paquete mínimo para guardar, reconstruir y revisar trabajo real sin abrir emisión profesional:

- **P7A:** snapshot canónico del proyecto + SHA-256 determinista;
- **P7B:** reconstrucción verificable/fail-closed del netlist DSS y round-trip canónico;
- **P7C:** reporte técnico reproducible desde snapshot `HASH_MATCH`, HTML print-ready y `BROWSER_PRINT`;
- **P7D:** gate formal para `MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW`.

El gate P7D exige Workspace V5, política determinista de motores, P5 operativo, P6 IEEE 1584 diferido y frontera profesional cerrada.

Cuando todos sus criterios están `DONE`:

```text
phase_status              = READY_WITH_LIMITATIONS
product_release           = MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW
engineering_preview_ready = true
internal_use_ready        = true
allowed_use               = CONTROLLED_INTERNAL_ENGINEERING_PREVIEW
next_activity             = REAL_SUBSTATION_PILOT
professional_report       = false
professional_emission     = false
```

P7 no eleva automáticamente la madurez de sus módulos ni convierte el reporte P7C en un informe profesional.

Detalle: `docs/P7_ENGINEERING_PREVIEW.md`.

## Fase P8 — Engineering Preview 0.9 y camino a 1.0

**Estado: ACTIVA — PILOTO REAL.**

MCP Eléctrico 0.9 — Engineering Preview queda habilitado para uso interno/controlado dentro de los alcances y limitaciones declarados.

Alcance disponible para el piloto:

- flujo y caída de tensión;
- datos profesionales fuente/transformador/conductor;
- `Ib <= In <= Iz`;
- IEC 60909 dentro de alcance;
- protección y capacidad de corte;
- soportabilidad térmica;
- TCC y clearing time;
- coordinación temporal puntual;
- Workspace V5;
- snapshot/reconstrucción/reporte P7;
- límites, fuentes, versiones y hashes visibles.

El siguiente paso no es ampliar alcance: es modelar una **subestación real** representativa, ejecutar el flujo de trabajo completo y registrar fricciones de modelado, UX, trazabilidad y reporte. Esa experiencia alimentará el endurecimiento hacia una futura **1.0 profesional**.

P6 IEEE 1584 continúa `DEFERRED`; se reactivará posteriormente y deberá integrarse al mismo workspace, consumiendo P4/P5 donde corresponda.

`professional_emission=false` sigue siendo distinto de “usable internamente”. La emisión profesional solo se habilitará cuando los gates normativos, benchmarks, QA y revisión requeridos estén cerrados legítimamente.

## Regla de emisión

`apto_para_emision=true` significa únicamente que un modelo supera los chequeos automáticos requeridos y que los módulos exigidos poseen una madurez aceptable para ese propósito. No significa que el software asuma responsabilidad ni sustituye revisión, criterio, firma o colegiatura del ingeniero responsable.