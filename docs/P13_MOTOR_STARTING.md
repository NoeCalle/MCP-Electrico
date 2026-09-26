# P13 — Motores y arranque

## Objetivo

P13 incorpora motores como una capacidad transversal de MCP Eléctrico. El core no pertenece a una industria específica.

El mismo contrato debe servir en manufactura, agua y saneamiento, HVAC y edificios, hospitales, data centers, oil & gas, minería, infraestructura y otras instalaciones donde el arranque de motores pueda afectar tensión, capacidad de red o continuidad operativa. El sector es contexto; la ingeniería entra como datos y criterios explícitos.

P13 comienza deliberadamente por una aproximación estática y fail-closed. El objetivo no es simular dinámica completa antes de contar con los datos que esa simulación exige.

## Principios

```text
motor data != generic load assumptions
starting method != permission to invent starting current
static voltage dip != acceleration-time simulation
missing motor data != derived default
```

La corriente de arranque y su factor de potencia se suministran explícitamente. P13A no los deduce de DOL, estrella-delta, autotransformador, soft starter o VFD.

Para eliminar ambigüedad entre corriente de fase del motor, corriente de línea y lados de entrada/salida de electrónica de potencia, P13A v1 exige:

```text
starting_current_basis = SUPPLY_LINE_RMS_AT_RATED_VOLTAGE
starting_power_factor_basis = FUNDAMENTAL_DISPLACEMENT
```

Armónicos, formas de onda y true power factor con distorsión quedan fuera de esta foundation.

## Estrategia

| Subfase | Alcance | Gate |
| --- | --- | --- |
| P13A | contrato canónico + intake fail-closed | datos de motor/estudio explícitos, sin cálculo |
| P13B | arranque estático aislado | caída de tensión mediante impedancia equivalente OpenDSS |
| P13C | perfiles de arranque controlados | corriente/impedancia por etapas o perfil explícito |
| P13D | secuencias de arranque | varios motores, arranque escalonado y escenarios |
| P13E | Workspace + dossier | resultados P13 trazables y reproducibles |
| P13F | dinámica avanzada | backend dinámico solo si existe contrato y benchmark suficientes |

P13F no implica por ahora que OpenModelica u otro backend esté implementado. La selección de motor dinámico se decidirá después de cerrar P13B–P13E.

## P13A — Contrato de datos

**Estado: DONE.** PR #138.

El contrato vive en `mcp_electrico/motor_starting_intake.py`.

P13A envuelve un `base_model` P8 ya admisible y agrega:

```text
base_model
motors[]
studies[]
```

### Motor mínimo P13A

Cada motor declara de forma explícita:

- barra;
- número de fases;
- tensión nominal;
- conexión;
- potencia nominal de salida;
- método de arranque;
- corriente RMS de línea vista desde la red a tensión nominal;
- base de esa corriente;
- factor de potencia de desplazamiento durante arranque;
- base de ese PF;
- referencia del dato de arranque;
- si el modelo base ya contiene su carga de marcha;
- cuál `Load.*` debe reemplazarse temporalmente si existe.

P13 v1 limita la foundation estática a motores trifásicos.

### Métodos reconocidos

```text
DOL
STAR_DELTA
AUTOTRANSFORMER
SOFT_STARTER
VFD
OTHER_EXPLICIT
```

El método es metadata de ingeniería y NO genera automáticamente una corriente.

```text
starting_method = STAR_DELTA
starting_current_a = missing
        ↓
BLOCKED
```

No se aplica silenciosamente una relación 1/3, √3, una corriente típica de catálogo ni una regla de drive/starter.

### Estudio inicial

P13A admite únicamente:

```text
STATIC_MOTOR_STARTING_VOLTAGE_DIP
```

y exige un criterio de tensión mínimo declarado por el proyecto:

```text
minimum_terminal_voltage_pu
criterion_reference
```

No existe un umbral universal embebido en MCP Eléctrico.

### Fronteras P13A

```text
electrical_calculation_performed = false
model_mutation_performed = false
automatic_starting_current_derivation = false
automatic_defaults = false
automatic_dispatch = false
crosscheck = false
professional_emission = false
```

## Caso de referencia

P13 usa un fixture genérico independiente:

```text
project_id = MCP-REF-MOTOR-01
application = CROSS_INDUSTRY_REFERENCE
source = 13.8 kV
secondary = 480 V
motor = 150 kW
starting_method = DOL
```

Los valores son `CONTROLLED_REFERENCE_DATA`. No representan una selección comercial ni un diseño real y no usan datos del proyecto de subestación minera.

La red base incluye una carga de marcha explícita `Load.m01_run`. P13 exige declarar que esa carga debe reemplazarse durante el arranque para evitar doble contabilización.

## P13B — Arranque estático aislado

**Estado: IN PROGRESS.**

P13B implementa la primera capacidad de cálculo de motores sin modificar los contratos públicos congelados de P8/P11.

La secuencia es:

```text
P13A intake
    ↓
preflight de datos que afectarían defaults relevantes
    ↓
dss.NewContext()
    ↓
construcción del modelo base directamente en el contexto aislado
    ↓
running motor load OFF
    ↓
pre-start Solve
    ↓
equivalent starting impedance ON
    ↓
starting Solve
    ↓
terminal voltage + voltage dip + project criterion
```

No existe materialización intermedia del modelo P13B en el DSS global. Tanto readiness como ejecución permanecen fuera del contexto padre.

### Modelo equivalente

P13B usa únicamente datos explícitos vistos desde la red:

```text
I_start = supply line RMS current at rated voltage
PF_start = fundamental displacement power factor

S_start = sqrt(3) * V_LL * I_start
P_start = S_start * PF_start
Q_start = S_start * sqrt(1 - PF_start^2)
```

La demanda nominal se representa temporalmente como una carga OpenDSS `Model=2` de impedancia constante. Por tanto, la corriente del equivalente disminuye cuando cae la tensión; no se fuerza una fuente de corriente constante.

Esto es una representación estática de impedancia equivalente en el instante inicial de arranque. NO es una simulación electromecánica completa.

La etiqueta del método de arranque no altera las ecuaciones. DOL, estrella-delta, autotransformador, soft starter o VFD solo producen un resultado distinto si sus datos explícitos supply-side son distintos.

### Estado pre-arranque

Si el modelo base ya contiene la carga equivalente de marcha del motor, esa `Load.*` se deshabilita antes del estado pre-arranque:

```text
pre-start = motor OFF + resto de cargas
starting  = motor equivalent starting impedance + resto de cargas
```

Así se evita doble contabilización de la carga de marcha y la demanda de arranque.

### Defaults y construcción

P13B bloquea antes del cálculo si faltan parámetros de red que alterarían el resultado mediante defaults retenidos, incluyendo:

- frecuencia, pu y ángulo de fuente;
- Scc MAX y X/R MAX;
- C1 de líneas;
- conexión y modelo de cargas;
- pérdidas en vacío e I0 de transformadores;
- declaración completa de taps.

La secuencia cero no se exige para esta foundation trifásica balanceada de secuencia positiva.

### Aislamiento

Readiness y cada estudio usan un `dss.NewContext()` nuevo. El circuito global y el Workspace padre se comparan antes/después y deben permanecer idénticos.

```text
parent DSS mutation = false
parent Workspace mutation = false
```

### Resultado P13B

Cada estudio reporta:

- tensión pre-arranque por fase;
- tensión durante arranque por fase;
- mínimo pre-arranque;
- mínimo durante arranque;
- dip en pu;
- dip porcentual respecto del estado pre-arranque;
- S/P/Q nominales del equivalente de arranque;
- corriente y PF declarados con su base explícita;
- criterio mínimo del proyecto y PASS/FAIL.

Un FAIL de tensión es un resultado válido del estudio; no es un error del solver.

### Frontera técnica

P13B NO calcula:

- tiempo de aceleración;
- torque electromagnético;
- curva torque-velocidad;
- deslizamiento transitorio;
- inercia del motor/carga;
- torque de carga;
- transición temporal estrella-delta;
- rampas o control interno de soft starter;
- control del VFD;
- armónicos o formas de onda.

Esos fenómenos requieren P13C–P13F y datos adicionales explícitos.

### Gate P13B

- P13A READY;
- base P8 admisible;
- bases de corriente/PF explícitas;
- fuente positiva-secuencia explícita;
- cero defaults relevantes retenidos;
- modelo construido únicamente en `dss.NewContext()`;
- readiness no ejecuta `Solve`;
- pre-start converge;
- estado de arranque converge;
- resultado reporta tensión, dip y criterio;
- el criterio es únicamente el declarado por el proyecto;
- la etiqueta del método de arranque no inventa parámetros;
- contexto DSS/Workspace padre intacto;
- Linux/Python 3.11 y Windows/Python 3.12 pasan CI;
- `professional_emission=false`.

Después de P13B, P13C añadirá perfiles explícitos de arranque por etapas sin asumir todavía dinámica continua.
