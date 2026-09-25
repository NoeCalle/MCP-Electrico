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

**Estado: IN PROGRESS.**

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

Al cerrar P10C, P10D incorporará Z0 explícita de fuente/líneas/transformadores y la topología de neutro para habilitar 1F-T MAX/MIN.
