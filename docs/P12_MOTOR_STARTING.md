# P12 — Motores y arranque

## Objetivo

P12 incorpora motores como una capacidad transversal de MCP Eléctrico. No está limitada a minería.

El mismo contrato debe servir para instalaciones de manufactura, agua y saneamiento, HVAC, hospitales, data centers, oil & gas, minería y otras industrias donde el arranque de motores pueda afectar tensión, capacidad de red o continuidad operativa.

P12 comienza deliberadamente por una aproximación estática y fail-closed. El objetivo no es simular dinámica completa antes de contar con los datos que esa simulación exige.

## Principios

```text
motor data != generic load assumptions
starting method != permission to invent starting current
static voltage dip != acceleration-time simulation
missing motor data != derived default
```

La corriente de arranque y su factor de potencia se suministran explícitamente. P12A no los deduce de DOL, estrella-delta, soft starter o VFD.

## Estrategia

| Subfase | Alcance | Gate |
| --- | --- | --- |
| P12A | contrato canónico + intake fail-closed | datos de motor/estudio explícitos, sin cálculo |
| P12B | arranque estático aislado | caída de tensión por rotor bloqueado con OpenDSS |
| P12C | perfiles de arranque controlados | corriente/impedancia por etapas o perfil explícito |
| P12D | secuencias de arranque | varios motores, arranque escalonado y escenarios |
| P12E | Workspace + dossier | resultados P12 trazables y reproducibles |
| P12F | dinámica avanzada | backend dinámico solo si existe contrato y benchmark suficientes |

P12F no implica por ahora que OpenModelica u otro backend esté implementado. La selección de motor dinámico se decidirá después de cerrar P12B–P12E.

## P12A — Contrato de datos

**Estado: DONE PENDING MERGE.** PR #127.

El contrato vive en `mcp_electrico/motor_starting_intake.py`.

P12A envuelve un `base_model` P8 ya admisible y agrega dos bloques nuevos:

```text
base_model
motors[]
studies[]
```

### Motor mínimo P12A

Cada motor declara de forma explícita:

- barra;
- número de fases;
- tensión nominal;
- conexión;
- potencia nominal de salida;
- método de arranque;
- corriente de arranque;
- factor de potencia durante arranque;
- referencia del dato de arranque;
- si el modelo base ya contiene su carga de marcha;
- cuál `Load.*` debe reemplazarse temporalmente si existe.

P12 v1 limita el estudio estático inicial a motores trifásicos.

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

P12A admite únicamente:

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

P12 usa un fixture genérico independiente:

```text
project_id = MCP-REF-MOTOR-01
application = CROSS_INDUSTRY_REFERENCE
source = 13.8 kV
secondary = 480 V
motor = 150 kW
starting_method = DOL
```

Los valores son `CONTROLLED_REFERENCE_DATA`. No representan una selección comercial ni un diseño real.

La red base incluye una carga de marcha explícita `Load.m01_run`. P12A exige declarar que esa carga debe reemplazarse durante el arranque para evitar doble contabilización.

## Próximo gate P12B

P12B deberá:

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


## P12B — Arranque estático aislado

**Estado: IN PROGRESS.** PR #128.

P12B implementa la primera capacidad de cálculo de motores sin modificar el contrato público 0.9.

La secuencia es:

```text
P12A intake
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

A partir de datos explícitos:

```text
S_start = sqrt(3) * V_LL * I_start
P_start = S_start * PF_start
Q_start = S_start * sqrt(1 - PF_start^2)
```

P12B crea una carga temporal OpenDSS `Model=2` de impedancia constante. Los límites internos usados por esa representación se publican en el resultado (`Vminpu=0.01`, `Vmaxpu=2.0`) y no se presentan como criterios de diseño.

La etiqueta del método de arranque no altera esas ecuaciones. DOL, estrella-delta, autotransformador, soft starter o VFD solo cambian el resultado si cambian los datos explícitos de corriente/PF suministrados.

### Estado pre-arranque

Si el modelo base contiene la carga equivalente de marcha del motor, P12B la deshabilita explícitamente antes de resolver el estado pre-arranque. Por tanto:

```text
pre-start = motor OFF + resto de cargas
starting  = motor equivalent starting impedance + resto de cargas
```

Esto evita sumar simultáneamente la carga de marcha y la demanda de arranque.

### Aislamiento

Cada estudio se ejecuta en un `dss.NewContext()` independiente. P12B verifica que la ejecución temporal no cambie el circuito ni el Workspace padre después de materializar el modelo base.

### Frontera de ingeniería

P12B NO calcula:

- tiempo de aceleración;
- curva torque-velocidad;
- deslizamiento;
- inercia del conjunto;
- torque de carga;
- transición estrella-delta;
- rampas/control interno de soft starter;
- control electromecánico de VFD.

Esos fenómenos requieren otra capa y datos adicionales.

### Gate P12B

- P12A READY;
- base model materializado;
- fuente positiva-secuencia explícita;
- cero defaults OpenDSS retenidos relevantes;
- pre-start converge;
- starting state converge;
- resultado reporta tensión por fase, mínimo y dip;
- criterio usado es exclusivamente el declarado por el proyecto;
- el contexto padre permanece intacto;
- Linux/Python 3.11 y Windows/Python 3.12 pasan CI;
- `professional_emission=false`.
