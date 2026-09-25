# P10 — Proyecto de referencia controlado del MCP

## Objetivo

P10 pertenece al roadmap propio de MCP Eléctrico y no depende del caso de ingeniería que se desarrolla en otros hilos.

Su función es validar la plataforma con un caso eléctrico independiente, reproducible y totalmente controlado por el repositorio. Los proyectos reales o didácticos externos pueden reutilizar después la misma ruta, pero no gobiernan el roadmap del producto.

## Caso de referencia

```text
project_id = MCP-REF-SUB-01
project_type = REFERENCE_INDUSTRIAL_SUBSTATION
system = 3PH_60HZ
incoming_voltage_kv = 22.9
main_distribution_voltage_kv = 4.16
auxiliary_distribution_voltage_kv = 0.48
data_class = CONTROLLED_REFERENCE_DATA
professional_emission = false
```

El caso de referencia será deliberadamente pequeño, pero incluirá suficiente estructura para recorrer flujo, caída de tensión, cortocircuito, secuencia cero, ampacidad, protección/TCC y dossier reproducible.

## Estrategia P10

| Subfase | Alcance | Gate |
| --- | --- | --- |
| P10A | identidad + Stage 0 fail-closed | intake bloqueado de forma explícita, sin cálculo |
| P10B | secuencia positiva 22.9/4.16/0.48 kV | POWER_FLOW / VOLTAGE_DROP ready y ejecución reproducible |
| P10C | fuente MAX/MIN + IEC 60909 3F | IEC60909_3PH_MAX_MIN ready |
| P10D | Z0 + neutros + 1F-T | IEC60909_1PH_GROUND_MAX_MIN ready |
| P10E | conductores + P3 | AMPACITY ready |
| P10F | dispositivos + TCC + bindings | PROTECTION_TCC ready |
| P10G | Workspace V5 + P7A/P7B/P7C | dossier íntegro y repetible |

## P10A — Stage 0

**Estado: DONE.** PR #110.

`examples/p10_reference_substation_stage0.json` contiene solo la identidad y tensiones nominales del caso.

El intake debe permanecer:

```text
BLOCKED_MISSING_INPUTS
```

hasta que el propio fixture de P10B declare explícitamente fuente, barras, transformadores, feeders, cargas y criterio de caída de tensión.

Esto conserva el principio del producto:

```text
missing data != assumed data
```

No hay defaults profesionales, despacho automático ni mutación del modelo desde una entrada incompleta.

## Separación respecto de proyectos externos

El caso minero o cualquier otro proyecto desarrollado fuera de P10 puede utilizar MCP Eléctrico como validación adicional, pero queda clasificado como:

```text
EXTERNAL_VALIDATION_PROJECT
```

y no como dependencia de roadmap.

Por tanto:

- un cambio en el caso externo no reabre P10;
- P10 puede avanzar con datos de referencia propios;
- una fricción descubierta en un proyecto externo puede originar un issue/hardening del MCP;
- los datos de un proyecto externo no se copian al fixture de referencia como si fueran benchmarks.

## Fronteras vigentes

```text
automatic_defaults = false
automatic_dispatch = false
automatic_fault_binding = false
crosscheck = false
professional_report = false
professional_emission = false
P6_IEEE1584 = DEFERRED
```

## P10B — Secuencia positiva, flujo y caída de tensión

**Estado: DONE.** PR #111.

P10B usa `examples/p10_reference_substation_stage1.json` y crea `MCP-REF-SUB-01` con una topología sintética-controlada:

```text
22.9 kV source
   ↓
T1 22.9 / 4.16 kV
   ↓
4.16 kV bus + representative MV load
   ↓
T2 4.16 / 0.48 kV
   ↓
480 V bus + representative LV load
```

Los valores eléctricos de Stage 1 son `CONTROLLED_REFERENCE_DATA`: existen para validar el producto y no representan una instalación real ni un benchmark normativo.

P10B declara explícitamente:

- fuente 22.9 kV, 60 Hz, 1.0 pu y equivalente positivo-secuencia de referencia;
- T1 22.9/4.16 kV y T2 4.16/0.48 kV;
- dos feeders representativos;
- una carga MT y una carga BT;
- pérdidas en vacío, corriente magnetizante, taps, R1/X1/C1 y modelo/conexión de carga para impedir defaults retenidos en el gate P1;
- criterio configurable de caída de tensión de 5 %, sin claim normativo universal.

El gate de P10B es exclusivamente:

```text
P8B intake = READY_TO_BUILD_MODEL
P8C materialization = MODEL_BUILT_NOT_EXECUTED
POWER_FLOW = READY
VOLTAGE_DROP = READY
```

sin activar todavía P3/P4/P5.


### Criterios de cierre P10B

- P8B acepta Stage 1 sin issues;
- P8C3B construye el modelo sin ejecutar estudios;
- `engine_defaults_retained_count = 0`;
- P8C5 declara POWER_FLOW y VOLTAGE_DROP `READY`;
- P8D1 ejecuta únicamente esos dos scopes;
- OpenDSS converge;
- no se ejecutan P3, P4 ni P5;
- dos ejecuciones consecutivas producen el mismo resumen de caída de tensión;
- `professional_emission=false`.

## P10C — IEC 60909 3F MAX/MIN

**Estado: DONE.** PR #112.

P10C usa `examples/p10_reference_substation_stage2.json` y amplía Stage 1 sin introducir todavía secuencia cero, ampacidad ni protección.

Stage 2 añade exclusivamente:

- escenario MIN explícito de la fuente: Scc3 y X/R;
- temperatura final explícita de los feeders para el caso MIN;
- buses de cortocircuito declarados: `mv_load_bus` y `lv_load_bus`;
- scope `IEC60909_3PH_MAX_MIN`.

El backend permanece explícito:

```text
POWER_FLOW / VOLTAGE_DROP = OpenDSS
IEC60909_3PH_MAX_MIN      = pandapower
automatic_dispatch        = false
```

### Criterios de cierre P10C

- P8B acepta Stage 2 sin completar valores silenciosamente;
- P8C5 declara el scope 3F `READY` sin ejecutar cortocircuito;
- pandapower ejecuta MAX y MIN para todos los buses solicitados;
- no existe selección automática de un único bus objetivo;
- `Ik'' MAX > Ik'' MIN > 0` en cada bus del fixture;
- dos ejecuciones consecutivas reproducen las mismas corrientes dentro de tolerancia numérica;
- no se ejecutan 1F-T, P3 ni P5;
- Linux/Python 3.11 y Windows/Python 3.12 pasan la lane P10C;
- `professional_emission=false`.

## P10D — Secuencia cero y 1F-T MAX/MIN

**Estado: DONE.** PR #113.

P10D usa `examples/p10_reference_substation_stage3.json` y amplía Stage 2 con Z0 explícita, sin introducir todavía ampacidad ni protección.

Stage 3 añade:

- R0/X0 MAX y MIN de la fuente;
- R0/X0/C0 de ambos feeders;
- ficha homopolar de T1 y T2;
- lado del neutro y modo de puesta a tierra explícitos;
- scope `IEC60909_1PH_GROUND_MAX_MIN`.

Los dos transformadores del fixture mantienen grupo `Dyn11` y declaran neutro LV sólidamente puesto a tierra únicamente como dato controlado del caso de referencia. No se infiere Z0 desde Z1 ni desde Scc3.

### Criterios de cierre P10D

- P8B acepta Stage 3 sin issues;
- P8C3B materializa fuente/líneas/transformadores Z0 explícitos;
- P8C5 ejecuta solo el preflight de proyección 1F-T y declara `READY`;
- pandapower ejecuta 1F-T MAX/MIN en todos los buses declarados;
- `Ik'' MAX > Ik'' MIN > 0` en cada bus del fixture;
- no existe selección automática de bus ni binding de protección;
- dos ejecuciones consecutivas reproducen las corrientes dentro de tolerancia numérica;
- P3/P5 permanecen fuera de scope;
- Linux/Python 3.11 y Windows/Python 3.12 pasan la lane P10D;
- `professional_emission=false`.

## P10E — Conductores y ampacidad P3

**Estado: DONE.** PR #114.

P10E usa `examples/p10_reference_substation_stage4.json` y amplía Stage 3 con dos fichas P3 explícitas: una para el feeder MT y otra para el feeder BT.

Stage 4 añade por feeder:

- conductor de proyecto identificado;
- `Iz_base` explícita y trazable;
- `Ib` explícita;
- `In` explícita;
- referencia de condiciones de instalación;
- referencia de ampacidad base;
- factor de corrección explícito y referenciado;
- norma P3 declarada.

El fixture no usa lookup normativo automático ni convierte el dato de proyecto en catálogo. La procedencia debe mantenerse como `PROJECT_DATA → P2_PROJECT`.

### Criterios de cierre P10E

- P8B acepta las dos fichas P3;
- P8C4A materializa conductores y perfiles sin ejecutar ampacidad;
- P8C5 declara `AMPACITY = READY`;
- P8D1 ejecuta `Ib <= In <= Iz` para ambos feeders;
- feeder MT: `320 A <= 350 A <= 427.5 A`;
- feeder BT: `700 A <= 800 A <= 900 A`;
- ambos resultados son `CUMPLE`;
- los factores permanecen explícitos y `automatic_normative_lookup=false`;
- dos ejecuciones consecutivas reproducen los mismos valores;
- P5 permanece fuera de scope;
- Linux/Python 3.11 y Windows/Python 3.12 pasan la lane P10E;
- `professional_emission=false`.

## P10F — Protecciones, TCC y fault bindings explícitos

**Estado: DONE.** PR #115.

P10F usa `examples/p10_reference_substation_stage5.json` y amplía Stage 4 con dos interruptores de referencia: uno para el feeder MT y otro para el feeder BT.

Stage 5 añade:

- `QF_MV` ligado a `Line.mv_feeder`;
- `QF_LV` ligado a `Line.lv_feeder`;
- In P5 exactamente igual a In P3 de cada feeder;
- Ue e Icu explícitas;
- Ics declarada únicamente como dato contextual;
- ajustes Ir/Isd/Ii trazables;
- dataset TCC BAND por dispositivo;
- semántica `TOTAL_CLEARING_TIME`;
- un binding de falla 3F/MAX explícito por dispositivo;
- reutilización del resultado P4 sin recalcular una falla distinta dentro de P5.

Los datasets y ratings son `CONTROLLED_REFERENCE_DATA`. Sirven para validar el flujo del producto; no representan equipos comerciales ni constituyen una selección de protección de proyecto.

### Criterios de cierre P10F

- P8B acepta dispositivos y datasets P5;
- P8C4B materializa los dos dispositivos y TCC sin ejecutar protección;
- P8C5 declara `PROTECTION_TCC = READY`;
- In P3/P5 queda en estado `MATCH` para ambos feeders;
- P8D2 consume únicamente los bindings declarados;
- no existe selección automática de falla, bus, caso o magnitud;
- ambos interruptores pasan la comparación técnica `Icu >= Ik''` para el resultado ligado;
- ambos datasets entregan `CLEARING_TIME_READY`;
- P4 se reutiliza y no se recalcula dentro de P5;
- dos ejecuciones consecutivas reproducen corriente ligada y clearing time;
- Linux/Python 3.11 y Windows/Python 3.12 pasan la lane P10F;
- `automatic_fault_binding=false`;
- `professional_emission=false`.

## P10G — Workspace V5 y dossier reproducible

**Estado: IN PROGRESS.**

P10G no cambia los datos eléctricos de Stage 5. Su objetivo es probar que el proyecto de referencia completo atraviesa la cadena de entrega ya construida:

```text
Stage 5 manifest
      ↓
P8D2 execution
      ↓
Workspace V5
      ↓
P7A snapshot + SHA-256
      ↓
P7B isolated reconstruction
      ↓
P7C technical HTML
      ↓
P8F2 integrity index
      ↓
collision-safe dossier
```

### Criterios de cierre P10G

- la ejecución P8D2 completa sin recalcular P4 dentro de P5;
- Workspace V5 contiene los dos dispositivos y sus bindings vigentes;
- P7A devuelve `HASH_MATCH`;
- P7B usa `OPENDSS_NEW_CONTEXT` y no muta el contexto padre;
- P7C queda `TECHNICAL_REPORT_READY_FOR_PRINT`, sin emisión profesional;
- el índice SHA-256 verifica el conjunto exacto de artefactos;
- el dossier incluye manifest, ejecución, workspace, snapshot, reconstrucción, reporte y netlists;
- una segunda entrega usa sufijo incremental y no modifica la primera;
- ambos dossiers siguen verificando integridad de forma independiente;
- Linux/Python 3.11 y Windows/Python 3.12 pasan la lane P10G;
- `professional_report=false`;
- `professional_emission=false`.

Si este gate pasa, P10 queda cerrado como validación integral del Engineering Preview con un caso controlado propio del producto.

## Protección de versiones estables

La baseline 0.9 congelada dispone ahora de la rama de recuperación `stable/0.9-engineering-preview`, anclada al commit de freeze P9D. La política de recuperación y el futuro mirror independiente se documentan en `docs/RELEASE_RECOVERY_POLICY.md`.
