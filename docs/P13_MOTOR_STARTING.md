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

La corriente de arranque y su factor de potencia se suministran explícitamente. P13A no los deduce de DOL, estrella-delta, autotransformador, soft starter o VFD. Para evitar ambigüedad entre corriente del motor, corriente de línea y lado de entrada de electrónica de potencia, P13A v1 exige una corriente RMS supply-side a tensión nominal y PF de desplazamiento fundamental. Armónicos y formas de onda quedan fuera de esta foundation.

## Estrategia

| Subfase | Alcance | Gate |
| --- | --- | --- |
| P13A | contrato canónico + intake fail-closed | datos de motor/estudio explícitos, sin cálculo |
| P13B | arranque estático aislado | caída de tensión por rotor bloqueado con OpenDSS |
| P13C | perfiles de arranque controlados | corriente/impedancia por etapas o perfil explícito |
| P13D | secuencias de arranque | varios motores, arranque escalonado y escenarios |
| P13E | Workspace + dossier | resultados P13 trazables y reproducibles |
| P13F | dinámica avanzada | backend dinámico solo si existe contrato y benchmark suficientes |

P13F no implica por ahora que OpenModelica u otro backend esté implementado. La selección de motor dinámico se decidirá después de cerrar P13B–P13E.

## P13A — Contrato de datos

**Estado: DONE PENDING MERGE.** PR #132.

El contrato vive en `mcp_electrico/motor_starting_intake.py`.

P13A envuelve un `base_model` P8 ya admisible y agrega dos bloques nuevos:

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
- corriente de arranque RMS vista desde la red;
- base explícita de esa corriente (`SUPPLY_LINE_RMS_AT_RATED_VOLTAGE`);
- factor de potencia durante arranque;
- base explícita de PF (`FUNDAMENTAL_DISPLACEMENT`);
- referencia del dato de arranque;
- si el modelo base ya contiene su carga de marcha;
- cuál `Load.*` debe reemplazarse temporalmente si existe.

P13 v1 limita el estudio estático inicial a motores trifásicos.

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

Ejemplo:

```text
starting_method = STAR_DELTA
starting_current_a = missing
        ↓
BLOCKED
```

No se aplica silenciosamente una relación 1/3, √3 ni una regla de catálogo.

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

No existe un umbral universal embebido en el MCP.

### Fronteras

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

Los valores son `CONTROLLED_REFERENCE_DATA`. No representan una selección comercial ni un diseño real.

La red base incluye una carga de marcha explícita `Load.m01_run`. P13A exige declarar que esa carga debe reemplazarse durante el arranque para evitar doble contabilización.

## Próximo gate P13B

P13B deberá:

1. materializar el modelo base sin defaults retenidos relevantes;
2. resolver el estado pre-arranque;
3. crear una representación temporal de impedancia equivalente de arranque en un contexto OpenDSS aislado;
4. retirar explícitamente la carga de marcha si el contrato dice que ya está incluida;
5. resolver el estado de arranque;
6. reportar tensión pre-arranque, tensión durante arranque y dip;
7. comparar únicamente contra el criterio de proyecto declarado;
8. no modificar el contexto DSS padre;
9. no calcular tiempo de aceleración ni torque dinámico;
10. conservar `professional_emission=false`.


## P13B — Arranque estático aislado

**Estado: IN PROGRESS.**

P13B implementa la primera capacidad de cálculo de motores sin modificar los contratos públicos congelados de P8/P11.

La secuencia es:

```text
P13A intake
    ↓
P8 base model materialization
    ↓
engine_defaults_retained = 0
    ↓
Save Circuit
    ↓
OpenDSS NewContext
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

### Modelo equivalente

P13B usa únicamente datos explícitos vistos desde la red:

```text
I_start = supply line RMS current at rated voltage
PF_start = fundamental displacement power factor

S_start = sqrt(3) * V_LL * I_start
P_start = S_start * PF_start
Q_start = S_start * sqrt(1 - PF_start^2)
```

La demanda se representa temporalmente como una carga OpenDSS `Model=2` de impedancia constante. Esto permite que la corriente caiga con la tensión como corresponde a una impedancia equivalente estática, pero NO constituye una simulación electromecánica completa.

La etiqueta del método de arranque no altera las ecuaciones. DOL, estrella-delta, autotransformador, soft starter o VFD solo producen un resultado diferente si los datos explícitos supply-side son diferentes.

### Estado pre-arranque

Si el modelo base ya contiene una carga equivalente de marcha del motor, esa `Load.*` se deshabilita antes del estado pre-arranque:

```text
pre-start = motor OFF + resto de cargas
starting  = motor equivalent starting impedance + resto de cargas
```

Esto evita doble contabilización.

### Aislamiento

Cada estudio temporal se ejecuta en `dss.NewContext()`. El contexto global del servidor y el Workspace padre deben quedar exactamente iguales después de la ejecución.

### Frontera técnica

P13B NO calcula:

- tiempo de aceleración;
- torque electromagnético;
- curva torque-velocidad;
- deslizamiento transitorio;
- inercia del conjunto;
- torque de carga;
- transición temporal estrella-delta;
- rampas/control interno de soft starter;
- control del VFD;
- armónicos o formas de onda.

Esos fenómenos requieren perfiles explícitos o un backend dinámico posterior.

### Gate P13B

- P13A READY;
- modelo base P8 materializado;
- fuente positiva-secuencia explícita;
- cero defaults OpenDSS retenidos relevantes;
- pre-start converge;
- estado de arranque converge;
- resultado reporta tensión por fase, mínimo y dip;
- el criterio es únicamente el declarado por el proyecto;
- la corriente usada es supply-side RMS;
- PF es desplazamiento fundamental;
- el contexto DSS/Workspace padre permanece intacto;
- Linux/Python 3.11 y Windows/Python 3.12 pasan CI;
- `professional_emission=false`.

Después de P13B, P13C añadirá perfiles de arranque explícitos por etapas sin asumir todavía dinámica continua.
