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

## Próxima actividad

P10B creará `MCP-REF-SUB-01` con una topología sintética-controlada:

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

El primer gate será exclusivamente:

```text
P8B intake = READY_TO_BUILD_MODEL
P8C materialization = MODEL_BUILT_NOT_EXECUTED
POWER_FLOW = READY
VOLTAGE_DROP = READY
```

sin activar todavía P3/P4/P5.
