# Roadmap profesional — MCP Eléctrico

## Confiabilidad técnica y responsabilidad del ingeniero — Q3

El MCP es una herramienta de cálculo para el ingeniero. Su desarrollo debe demostrar
que las entradas se traducen correctamente, que los resultados son reproducibles
y contrastados, y que los datos faltantes, supuestos, límites y errores se informan.
El ingeniero selecciona los criterios del proyecto, revisa los resultados,
aprueba el estudio y lo firma. Esa aprobación es una responsabilidad externa;
no es un módulo numérico pendiente de implementar.

Los campos históricos `professional_emission=false` y `professional_report=false`
indican que el software no aprueba ni firma automáticamente. No prohíben el uso
profesional del cálculo ni la firma del ingeniero. Una firma digital integrada
sería una mejora documental opcional y no una condición para verificar un solver.
Los estados experimentales se conservan exclusivamente cuando falta evidencia
técnica de la integración o del alcance. Arc Flash permanece diferido.

## Cierre vigente de módulos — Q2, 4 de octubre de 2026

Consultar el [registro de cierre](ESTADO_CIERRE_MODULOS.md): estados, alcance, evidencia y condiciones finitas pendientes. La integración verificada, los datos del proyecto, los criterios de diseño, la conformidad normativa y la aprobación del informe se evalúan por separado.

**Actualización Q2 (4 de octubre):** DOL01–DOL03 están cerrados por contraste con el ejemplo original MSL y regresión MCP; ver [evidencia DOL](MSL_DOL_VERIFICACION.md). La prioridad pasa a SCR01–SCR03. Bancos estáticos, P5 y P7 conservan sus cierres por alcance. Arc Flash sigue diferido.


## Objetivo

Evolucionar MCP Eléctrico desde una herramienta funcional basada en OpenDSS hacia una plataforma de ingeniería reproducible, trazable y verificable. La firma y responsabilidad profesional permanecen siempre en el ingeniero responsable.

El cierre de una fase no significa cobertura universal: cada módulo declara alcance, madurez, fuentes, limitaciones y gates explícitos.

**Dirección corregida por el usuario:** priorizar la integración de herramientas
gratuitas y de código abierto existentes. El MCP prepara datos, invoca el motor
y presenta los resultados. Antes de crear cálculos físicos propios se debe
documentar una carencia de las soluciones disponibles. Ver
[decisión de arquitectura](ARQUITECTURA_INTEGRACION.md).

**Migración actualizada el 2026-10-04:** física propia DOL/RK4 y SCR/RL retirada.
Se integra ejecución DOL verificada en alcance OpenModelica/MSL para equivalente RL de
barra común, incluido caso de dos motores. SCR de una máquina delta/red RL/control
MSL permanece en verificación con los gates SCR01 a SCR03. Fabricante corresponde a datos del proyecto; estrella y multimotor son ampliaciones excluidas. El trabajo histórico P13F/G no constituye una ruta
vigente de ejecución. Ver [migración y prioridades industriales](MIGRACION_MODELOS_ABIERTOS.md).

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
| P8 — Engineering Preview 0.9 | **CERRADA — P8A–P8F DONE** | uso operativo controlado en proyectos reales |
| P9 — Hardening/freeze 0.9 | **CERRADA — P9A–P9D DONE** | baseline 0.9 congelada y repetible |
| P10 — Reference Validation | **CERRADA — P10A–P10G DONE** | validación integral independiente de la baseline con caso controlado propio |
| P11 — Release Safety | **CERRADA INTERNAMENTE — P11A–P11D DONE** | recovery anchors, contratos del core, export portable y restore probado; mirror externo diferido |
| P12 — Operating Scenarios | **CERRADA FOUNDATION — P12A–P12F DONE** | escenarios, fuentes alternativas explícitas, Workspace y dossier íntegro |
| P13 — Motores y arranque | **P13A–P13E DONE; física propia F2–F5 RETIRADA; MSL DOL VERIFICADO EN ALCANCE** | datos explícitos y ejecución de componentes existentes; equivalente RL común y multimáquina probado sintéticamente |
| P13G — Arranque suave | **Física propia RETIRADA; MSL SCR EN VERIFICACIÓN** | una máquina delta/red RL/control y bypass MSL; cerrar gates SCR01 a SCR03 antes de ampliar topologías |
| P14 — Runtime & Agent Integration | **ALCANCE LOCAL COMPLETO — P14A/P14B DONE** | construcción Rev.0, instalación Windows y clientes stdio/HTTP verificados |
| Bancos y compensación reactiva | **INTEGRACIÓN VERIFICADA EN ALCANCE ESTÁTICO** | etapas explícitas a igual demanda, balances, FP, tensión, pérdidas y cargabilidad; armónicos/resonancia pendientes |

**Regla de avance:** Las fases cerradas de P0–P11 conservan sus contratos; P6 IEEE 1584 continúa diferida. P12 y P13 incorporan escenarios operativos y motores/arranque como capacidades aditivas ya disponibles dentro de sus alcances publicados, sin modificar silenciosamente los contratos públicos congelados de la Engineering Preview.

**Alcance local vigente tras el retiro:** la baseline estática conserva su
disponibilidad y V7.1 su navegación/láminas. La dinámica DOL tiene reemplazo MSL
verificado en alcance de equivalente RL (DOL01–DOL03 cerrados). SCR está
disponible en su alcance experimental; bancos estáticos tienen integración OpenDSS verificada en el alcance declarado
([alcance y evidencia](COMPENSACION_REACTIVA_OPENDSS.md)); armónicos y perfiles siguen pendientes. Arc Flash
continúa diferido. No se declara cierre de todas las necesidades habituales.

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
P8 = CLOSED
P9 = FROZEN
P10 = CLOSED
P11 = CLOSED_INTERNAL_RELEASE_SAFETY
P12 = CLOSED_FOUNDATION_P12A_TO_P12F
P13 = CLOSED_STATIC_P13A_TO_P13E
P13F1 = PHYSICAL_INPUT_PREPARATION_COMPLETE
P13F2_TO_F5 = RETIRED_CUSTOM_BACKEND_MSL_DOL_VERIFIED_IN_SCOPE
P13G = RETIRED_CUSTOM_BACKEND_MSL_SCR_SINGLE_DELTA_EXPERIMENTAL
P13G_REFERENCE = THREE_WIRE_RESISTIVE_COMPARISON_IMPLEMENTED_MODEL_DISAGREEMENT_RECORDED
P13G_MOTOR_REFERENCE = EXTERNAL_MODELICA_SYNTHETIC_REPLAY_COMPLETED_MODEL_DISAGREEMENT_RECORDED
P14 = LOCAL_RUNTIME_P14A_P14B_COMPLETE
product_release = MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW
next_activity = INTEGRATE_OPENDSS_CAPACITOR_HARMONIC_TIME_SERIES_TOOLS

professional_report = false
professional_emission = false
automatic_dispatch = false
crosscheck=false
automatic_normative_lookup = false
```

**Referencia histórica de ampliación del 2026-10-02 (física propia retirada):** se incorpora P13G como equivalente
SCR/RL por fase con dinámica mecánica y red fundamental. Su alcance es aproximado:
no se declara cerrado el modelo de un arrancador industrial. Ver
[P13G](P13G_SOFT_STARTING.md). La dinámica DOL P13F ya existe; para M1 faltan
datos físicos revisados. Siguen pendientes la validación trifásica del dispositivo,
dinámica simultánea de varios motores y otras exclusiones publicadas.

**Contraste externo con motor:** MSL 4.0.0 ejecutada con OpenModelica 1.27.1,
parámetros sintéticos equivalentes y secuencia de amplitud/ángulo reproducida.
El equivalente SCR propio, actualmente retirado, discrepó en corriente/par/aceleración en ese contraste histórico. Ver [evidencia y límites](P13G_MODELICA_REFERENCE.md).
La decisión de arquitectura posterior sustituye la ampliación del equivalente
propio por un adaptador de ejecución de los modelos externos existentes.
Debe verificarse red/control/bypass en lazo cerrado y la suficiencia de los
datos del dispositivo antes de aceptar un estudio real.

**Contratos de gates por fase (referencia histórica):** Los siguientes valores
se conservan en P5/P7. Sus campos `next_phase` y `next_activity` describen
la transición de cada gate, no trabajo pendiente del roadmap actual.
P5 por sí solo no habilita la Engineering Preview; P7 y P8 ya cerraron esa ruta.

```text
P5 operational_path_ready    = true
P5 engineering_preview_ready = false
P5 next_phase                = P7_REPRODUCIBLE_DOSSIER_MINIMUM

P7 engineering_preview_ready = true
P7 internal_use_ready        = true
P7 allowed_use               = CONTROLLED_INTERNAL_ENGINEERING_PREVIEW
P7 next_activity             = REAL_SUBSTATION_PILOT
```

Usable internamente no equivale a `professional_emission=true`. P9 ya cerró el endurecimiento de la baseline 0.9. El siguiente paso operativo es usar un proyecto local controlado para documentar fricción y priorizar mejoras posteriores.

## Principio rector

OpenDSS se mantiene como motor principal y por defecto para flujo/distribución dentro del alcance actualmente validado. pandapower 3.5.4 actúa como backend determinista para IEC 60909. Las reglas MCP cubren ampacidad, protecciones y futuras capas de ingeniería. La arquitectura es multiindustria: hospitales, data centers, manufactura, procesos, minería, oil & gas, agua, infraestructura y otras instalaciones usan el mismo core; las diferencias se expresan mediante datos, topología y criterios explícitos del proyecto.

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

Incluye MAX/MIN, magnitudes soportadas por tipo de falla, secuencia cero explícita para 1F-T, benchmarks independientes y Workspace V4. `ip/Ith` sin máquinas solo se calculan cuando sus requisitos de topología/tiempo/método están declarados; con fichas de máquinas permanecen bloqueados hasta validar su alcance.

P4C10 permanece `REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION`; una verificación integral requiere revisión licenciada futura.

Detalle: `docs/P4_IEC60909.md` y documentos P4 específicos.

### Ampliación del módulo 3F para uso local (integrada el 2026-10-02, PR #152)

Implementadas fichas explícitas de inducción directa y generador síncrono,
correcciones K_G/K_S/K_SO y corrientes iniciales por rama. El control previo
exige clasificar las cargas al usar máquinas; identifica faltantes y bloquea
variadores sin modelo. El alcance validado es Ik'' inicial trifásica MAX/MIN
con benchmarks independientes y pruebas mediante herramientas MCP.
MIN excluye inducción. ip/Ith con máquinas, decaimiento y modelos de variador
requieren validación adicional; calcular Ik'' no aprueba protecciones.
Ver [contrato de máquinas SC3](SC3_MACHINES.md).

Antes de repetir el unifilar real: revisar fichas de generador, motores y
cables; comunicar cada supuesto propuesto y obtener su aceptación. No
heredar una aprobación de supuestos de otro estudio.

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

Los cinco componentes P5 están `VALIDATED_WITH_LIMITATIONS` por verificación Q1 de datos, matemáticas y ejecución MCP dentro de su alcance. P5G no concede por sí mismo conformidad normativa ni selectividad integral.

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

**Estado: CERRADA — P8A–P8F DONE.**

P8 cerró la cadena integral de uso real controlado del Engineering Preview:

- intake fail-closed del proyecto;
- materialización explícita del modelo;
- ejecución P1/P3/P4/P5 sin dispatch oculto;
- Workspace V5 ligado a la revisión vigente;
- snapshot P7A, reconstrucción P7B y reporte P7C;
- dossier con integridad SHA-256;
- repetición collision-safe;
- first-use por MCP stdio;
- gate P8F5 para uso real controlado.

La reconstrucción P7B usada por el dossier quedó endurecida para Windows/Python 3.12 mediante `dss.NewContext()`, sin subprocess Python y preservando el contexto DSS/Workspace padre.

P6 IEEE 1584 continúa `DEFERRED`; se reactivará posteriormente y deberá integrarse al mismo workspace, consumiendo P4/P5 donde corresponda.

`professional_emission=false` sigue siendo distinto de “usable internamente”.

## Fase P9 — Hardening final y freeze 0.9

**Estado: CERRADA — P9A–P9D DONE.**

P9 no añade nueva funcionalidad eléctrica. Congela la base 0.9 antes de introducir el caso minero MCP-REF-SUB-01.

### P9A — portabilidad Windows / aislamiento OpenDSS

**DONE.** PR #106.

- P7B migra de subprocess a `OPENDSS_NEW_CONTEXT`;
- Windows + Python 3.12 validado;
- P8F4 por MCP stdio validado;
- contexto padre y estado estructurado preservados.

### P9B — regresión integral P0–P8

**DONE de facto por CI de PR #106/#107.**

Las lanes históricas P4/P7/P8 y la suite general permanecen verdes junto con la lane Windows de portabilidad.

### P9C — repetibilidad stdio en una sola sesión

**DONE.** PR #107.

- tres dossiers consecutivos en una sola sesión MCP stdio;
- `OPENDSS_NEW_CONTEXT` en cada ejecución;
- salidas `dossier`, `dossier_2`, `dossier_3`;
- integridad independiente y re-verificación del primer dossier;
- cierre limpio del servidor;
- Linux/Python 3.11 y Windows/Python 3.12.

### P9D — freeze Engineering Preview 0.9

**DONE.** PR #109.

El freeze dejó explícitos, como registro del cierre P9:

- release: `MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW`;
- allowed_use: `CONTROLLED_REAL_PROJECT_ENGINEERING_PREVIEW`;
- professional_emission: `false`;
- P6 IEEE 1584: `DEFERRED`;
- ninguna ampliación funcional durante el freeze;
- siguiente fase en ese cierre: P10 / MCP-REF-SUB-01, ya completada.

Detalle: `docs/P9_ENGINEERING_PREVIEW_FREEZE.md`.

## Fase P10 — Reference Validation

**Estado: CERRADA — P10A–P10G DONE.**

Proyecto de referencia controlado e independiente: subestación industrial sintética 22.9/4.16/0.48 kV. Los fixtures por etapas y la validación integral P10G cubren las capacidades declaradas de la baseline. Ver `docs/P10_REFERENCE_VALIDATION.md` y los fixtures `examples/p10_reference_substation_stage*.json`.

## Regla de emisión

`apto_para_emision=true` significa únicamente que un modelo supera los chequeos automáticos requeridos y que los módulos exigidos poseen una madurez aceptable para ese propósito. No significa que el software asuma responsabilidad ni sustituye revisión, criterio, firma o colegiatura del ingeniero responsable.

## Política de recuperación de releases

La baseline `MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW` conserva un punto de recuperación separado del desarrollo normal:

```text
stable/0.9-engineering-preview
commit = 6720da9183c45df299a584430fddea28f4060d7a
```

La estrategia futura añade tag de release y mirror independiente del repositorio activo. Ver `docs/RELEASE_RECOVERY_POLICY.md`.


## Fase P11 — Release safety y protección del core

**Estado: CERRADA INTERNAMENTE — P11A–P11D DONE; mirror externo diferido.**

P11 no agrega una nueva función eléctrica. Protege la baseline validada frente a cambios no deseados y separa claramente desarrollo, puntos de recuperación y futuras copias independientes.

Subfases:

```text
P11A  release manifest + recovery anchors
P11B  core contract regression
P11C  independent mirror/export
P11D  clean restore / stable candidate
```

P11A registró el cierre P10G en `stable/0.9-reference-validated`. P11B congeló la superficie pública. P11C cerró el export portable exact-SHA. P11D prueba restauración limpia únicamente desde el bundle y vuelve a ejecutar el smoke integral P10G. Detalle: `docs/P11_RELEASE_SAFETY.md`.


## Cierre P11 — Release Safety

P11A–P11D quedan cerradas. La baseline validada puede exportarse por SHA exacto, verificarse por SHA-256, restaurarse desde Git bundle sin GitHub y volver a ejecutar el smoke integral P10G.

El repositorio espejo independiente queda diferido por decisión del proyecto y no bloquea el desarrollo del core:

```text
stable/0.9-engineering-preview
    -> 6720da9183c45df299a584430fddea28f4060d7a

stable/0.9-reference-validated
    -> 5228e358cf0716dc963f109a15b9e1a2d309f635

P11D clean restore
    -> VERIFIED
```

Detalle: `docs/P11_RELEASE_SAFETY.md`, `docs/RELEASE_RECOVERY_POLICY.md` y `docs/RELEASE_MIRROR_RUNBOOK.md`.


## Fase P12 — Escenarios operativos y contingencias

**Estado: CERRADA FOUNDATION — P12A–P12F DONE.**

P12 introduce análisis explícito de estados operativos alternativos sin asociar el motor a una industria concreta.

Foundation inicial:

```text
base model
   ↓
explicit scenario
   ↓
OPEN/CLOSE Line.* or Transformer.*
   ↓
OpenDSS power flow
   ↓
explicit service requirements
   ↓
PASS / FAIL
   ↓
verified base-state restoration
```

Principios:

- no selección automática de contingencias;
- no maniobras inferidas;
- no load shedding automático;
- criterios de continuidad y tensión declarados por el proyecto;
- cada escenario parte de una reconstrucción limpia;
- un resultado FAIL es una conclusión válida del escenario, no un error del solver;
- el core permanece agnóstico a minería, hospital, data center, manufactura u otra industria.

P12C cerró ENABLE/DISABLE explícito de Load.* sin shedding automático. P12D expone el motor mediante tools MCP. P12E incorpora fuentes Thevenin y transferencia break-before-make declarada; P12F incorpora comparación, Workspace y dossier SHA-256. Los criterios estáticos de servicio y la restauración del modelo permanecen explícitos y verificables. Motores y arranque se desarrollan en P13.

Detalle: `docs/P12_OPERATING_SCENARIOS.md`.

## Fase P13 — Motores y arranque

**Estado vigente: P13A–P13E DONE; F2–F5 físicos propios retirados; reemplazo MSL DOL verificado en alcance.**

Los párrafos F2–F5 siguientes documentan el hito histórico anterior; no habilitan
la ejecución del solucionador retirado. El estado actual y sus herramientas están
en [la migración](MIGRACION_MODELOS_ABIERTOS.md).

P13 incorpora motores como capacidad transversal para manufactura, agua/saneamiento, HVAC, hospitales, data centers, oil & gas, minería y otras industrias.

La primera frontera es deliberadamente estática y fail-closed:

```text
base_model P8 admisible
    ↓
motor con corriente y PF de arranque explícitos
    ↓
P13A intake fail-closed
    ↓
P13B construye y resuelve en dss.NewContext()
    ↓
pre-start / starting voltage / dip
    ↓
criterio de tensión declarado por el proyecto
```

P13A cerró el contrato fail-closed, P13B el arranque estático aislado, P13C los perfiles explícitos y P13D las secuencias multi-motor. P13E añade Workspace read-only, replay determinista desde inputs P13 canónicos e integridad SHA-256, sin snapshotear el circuito DSS global.

```text
automatic_starting_current_derivation = false
automatic_defaults = false
automatic_dispatch = false
crosscheck = false
professional_emission = false
```

Detalle: `docs/P13_MOTOR_STARTING.md`.

P13F se reactivó el 2026-09-30 y cerró el alcance de dinámica mecánica RMS equilibrada. P13F1 añade
datos físicos SI, vínculo SHA al manifiesto, controles de admisión,
dos referencias mecánicas analíticas y plan de calificación independiente.
P13F2 califica MCP_BALANCED_RMS_RK4_V1; P13F3 acopla la red aislada;
P13F4 calcula trayectorias y P13F5 entrega Workspace/CSV/dossier. La ejecución
requiere opciones explícitas y consistencia con datos nominales/arranque.
El alcance es un motor de jaula trifásico equilibrado con arranque directo
desde reposo por estudio; los demás motores permanecen como cargas de marcha.
VFD, soft starter, conmutaciones, EMT y secuencias dinámicas simultáneas
quedan fuera de esta entrega.
Detalle: [P13F — contrato y gates](P13F_MOTOR_DYNAMICS.md).

## Fase P14 — Runtime e integración local

La investigación de motores abiertos amplía la matriz E con ocho preferencias
de integración pendientes, sin habilitar ejecución ni modificar física propia.
Prioridad: adaptador OpenModelica/MSL; después, relés pandapower, y pilotos
ANDES/VeraGrid cuando el estudio solicitado los requiera.
Detalle: [motores abiertos](MOTORES_ABIERTOS_INVESTIGACION.md).

**Estado: ALCANCE LOCAL COMPLETO — P14A/P14B DONE.**

P14A implementa instalación reproducible y construcción Rev.0 sin Solve. P14B
incorpora Streamable HTTP limitado a loopback, stdio compatible, arranque oculto
y detención Windows. La verificación de cierre P14B registró 133 tools y comprobó flujo,
expedientes P8/P12/P13, replay e integridad. Los tests de protocolo se ejecutan
en CI Windows/Linux. Detalle: `docs/P14_LOCAL_RUNTIME.md`.

El 2026-09-30 se eligió la instalación local. P13F1–F5 ya incluye dinámica
mecánica RMS equilibrada dentro del alcance declarado. Alojamiento remoto,
IEEE 1584 y las extensiones dinámicas enumeradas en P13 permanecen fuera
de esta entrega.

## Siguiente actividad y pendientes vigentes

La prioridad operativa es `FIRST_CONTROLLED_LOCAL_PROJECT`: revisar datos,
procedencia y supuestos del proyecto, ejecutar los estudios admisibles y
verificar el dossier reproducible. Los casos de referencia y ejercicios
existentes no sustituyen la revisión de los datos de ese proyecto.

Los cierres anteriores conservan estos pendientes explícitos:

- P6/V6: Arc Flash IEEE 1584 diferido.
- P4/P5: revisión normativa completa, datasets y referencias externas pendientes
  según [Validaciones pendientes](VALIDACIONES_PENDIENTES.md).
- SC3 con máquinas: decaimiento, corriente de corte/permanente, `ip/Ith`
  y variadores fuera del alcance validado; ver [SC3](SC3_MACHINES.md).
- P13: ampliaciones más allá de un motor dinámico RMS DOL por estudio.
- P11: espejo externo independiente diferido; export y restore internos cerrados.
- P14: alojamiento remoto fuera de la entrega local.

Estos pendientes no cambian `professional_emission=false` ni amplían la
madurez de los módulos cerrados con limitaciones.
