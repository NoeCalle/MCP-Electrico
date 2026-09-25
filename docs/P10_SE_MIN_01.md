# P10 — SE-MIN-01: primer proyecto industrial controlado

## Objetivo

P10 incorpora progresivamente el caso SE-MIN-01 sobre la baseline congelada `MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW`.

El objetivo no es inventar un proyecto completo de una sola vez, sino demostrar que MCP Eléctrico puede recibir un caso minero realista de forma trazable, fail-closed y reproducible mientras la ingeniería del caso se termina en paralelo.

## Identidad del caso

```text
project_id = SE-MIN-01
project_type = PLANTA_CONCENTRADORA_MINERA
location_context = SUR_DEL_PERU
altitude_masl = 3800
operation = 24_7
system = 3PH_60HZ
incoming_voltage_kv = 22.9
main_distribution_voltage_kv = 4.16
auxiliary_distribution_voltage_kv = 0.48
reliability_philosophy = FUNCTIONAL_N_MINUS_1
production_100pct_under_contingency = false
load_shedding_allowed = true
professional_emission = false
```

La filosofía N−1 funcional preserva seguridad, control y servicios esenciales ante una contingencia simple; no implica mantener 100 % de producción.

## Regla de procedencia

Solo se incorporan al manifiesto ejecutable valores ya cerrados por ingeniería y con referencia de origen identificable.

No se permite:

- copiar valores sintéticos de P8A/P8F como si fueran datos del proyecto;
- completar Scc, X/R, Z0, %Z, R/X, taps, pérdidas, cables, longitudes o ajustes con defaults silenciosos;
- interpretar una decisión todavía abierta en el caso de diseño como dato definitivo;
- promover un manifiesto incompleto a `READY_TO_BUILD_MODEL`.

## Estrategia incremental

| Subfase | Alcance | Gate |
| --- | --- | --- |
| P10A | identidad, base de diseño y manifiesto Stage 0 | intake bloqueado de forma explícita, sin cálculo |
| P10B | modelo de secuencia positiva: fuente, barras, trafos, feeders y cargas | POWER_FLOW / VOLTAGE_DROP ready |
| P10C | red equivalente MAX/MIN y cortocircuito 3F | IEC60909_3PH_MAX_MIN ready |
| P10D | Z0 de fuente, líneas, transformadores y neutros | IEC60909_1PH_GROUND_MAX_MIN ready |
| P10E | conductores, instalación, Ib/In/Iz y evidencia | AMPACITY ready |
| P10F | protecciones, bindings y TCC | PROTECTION_TCC ready |
| P10G | Workspace V5 + dossier P7A/P7B/P7C + repetición | DOSSIER_READY_ENGINEERING_PREVIEW |

Cada subfase se cierra antes de ampliar el scope del manifiesto.

## P10A — Stage 0

El archivo `examples/p10_se_min_01_stage0.json` contiene únicamente la identidad del proyecto y los datos de base ya fijados que encajan en el contrato P8B.

Se solicita inicialmente:

```text
POWER_FLOW
VOLTAGE_DROP
```

pero el intake debe permanecer:

```text
BLOCKED_MISSING_INPUTS
```

hasta que existan, como mínimo:

- barra explícita de conexión de la fuente;
- topología de barras;
- transformadores del alcance con kVA, tensiones, %Z, grupo vectorial y R/X o pérdidas de carga;
- líneas/cables del alcance con longitud, R1 y X1;
- cargas del alcance con kW/kvar y tensión.

El bloqueo de Stage 0 es intencional: demuestra que la entrada del proyecto real no activa defaults ni construye un modelo a partir de datos todavía no cerrados.

## Datos que deben venir del desarrollo de ingeniería

### Utility / red aguas arriba

- Scc3 MAX y MIN;
- X/R MAX y MIN;
- tensión operativa / pu cuando corresponda;
- para 1F-T: R0/X0 MAX y MIN de la fuente.

### Transformadores

Por cada unidad incluida:

- potencia nominal;
- tensiones HV/LV;
- grupo vectorial;
- %Z;
- R/X o pérdidas de carga;
- taps y posición aplicable;
- para Z0: uk0/ur0 o equivalente sustentado, reparto de fuga y comportamiento magnetizante;
- lado del neutro y modo de puesta a tierra;
- referencia de placa/ficha/estudio.

### Cables / feeders

- barras origen/destino;
- fases;
- longitud;
- R1/X1/C1;
- R0/X0/C0 cuando entre 1F-T;
- temperatura de conductor para caso MIN de cortocircuito;
- código y referencia de conductor/instalación para P3.

### Cargas

- barra;
- kW/kvar;
- tensión;
- conexión;
- condición de operación/demanda;
- criticidad cuando se modele la filosofía N−1 y load shedding.

### Protección

- dispositivo;
- elemento protegido;
- In/Ue;
- Icu o poder de corte aplicable;
- ajustes;
- dataset TCC trazable;
- binding explícito a barra/tipo de falla/caso MAX-MIN.

## Fronteras vigentes

P10 hereda sin cambios:

```text
automatic_defaults = false
automatic_dispatch = false
automatic_fault_binding = false
crosscheck = false
professional_report = false
professional_emission = false
P6_IEEE1584 = DEFERRED
```

P10 no reabre P9 salvo que aparezca una regresión real de plataforma.

## Criterio de éxito de P10

P10 se considerará cerrado cuando SE-MIN-01 pueda recorrer, con datos trazables y sin supuestos silenciosos:

```text
intake
→ materialization
→ readiness
→ P1/P3/P4/P5 execution
→ Workspace V5
→ P7A/P7B/P7C
→ dossier integrity
→ repeatability
```

sin habilitar `professional_emission`.
