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

**Estado: DONE PENDING MERGE.** PR #133.

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


## P13C — Perfiles explícitos por puntos

**Estado: DONE PENDING MERGE.** PR #134.

P13C extiende el arranque estático con una secuencia ordenada de puntos declarados por el proyecto. El eje tiempo sirve únicamente para ordenar observaciones/estados; P13C no integra ecuaciones dinámicas entre puntos.

Ejemplo conceptual:

```text
t = 0.0 s   I = 1250 A   PF = 0.25
t = 0.5 s   I = 1050 A   PF = 0.30
t = 1.5 s   I =  800 A   PF = 0.40
t = 3.0 s   I =  500 A   PF = 0.65
```

Cada punto conserva las mismas bases contractuales:

```text
current_basis = SUPPLY_LINE_RMS_AT_RATED_VOLTAGE
PF_basis      = FUNDAMENTAL_DISPLACEMENT
```

El primer punto debe coincidir exactamente con los datos iniciales P13A. Esto evita que el manifiesto de motor y el perfil aporten dos corrientes de arranque contradictorias.

### Qué hace

Por cada punto explícito:

1. reutiliza el modelo base materializado;
2. ejecuta el perfil en un `dss.NewContext()` aislado;
3. mantiene fuera la carga de marcha declarada;
4. aplica el equivalente de impedancia constante correspondiente a I/PF del punto;
5. resuelve OpenDSS;
6. registra tensión por fase, tensión mínima y cumplimiento del criterio del proyecto;
7. identifica el punto de peor tensión.

### Qué no hace

```text
interpolation = false
dynamic_integration = false
automatic_profile_generation = false
torque_calculation = false
harmonic_model = false
```

Por tanto, una secuencia de cuatro puntos no significa que el MCP haya simulado la trayectoria continua entre ellos. Es una colección reproducible de estados algebraicos declarados.

### Gate P13C

- P13A válido;
- P13B readiness válido;
- package ligado al mismo project_id;
- al menos dos puntos por perfil;
- t=0 explícito;
- tiempos estrictamente crecientes;
- corriente > 0 y PF en (0,1];
- primer punto igual al arranque inicial P13A;
- IDs de punto no duplicados;
- todos los estados se resuelven en contexto aislado;
- se identifica el peor punto sin interpolación;
- contexto DSS/Workspace padre preservado;
- Linux/Python 3.11 y Windows/Python 3.12 pasan CI;
- `professional_emission=false`.

Caso controlado: `examples/p13_motor_starting_profile_stage2.json`.

Después de P13C, P13D podrá introducir secuencias de varios motores y solapes explícitos, manteniendo separada la futura dinámica continua.


## P13D — Secuencias explícitas de varios motores

**Estado: DONE PENDING MERGE.** PR #135.

P13D combina motores y perfiles P13C mediante pasos estáticos completamente declarados. Está pensado para cualquier instalación con múltiples accionamientos: bombas, ventiladores, compresores, chillers, transportadores, procesos, servicios auxiliares u otras cargas motrices.

Cada secuencia declara el conjunto de motores participantes y, para cada instante discreto, exactamente un estado por motor:

```text
OFF
RUNNING
STARTING_PROFILE_POINT
```

Un estado `STARTING_PROFILE_POINT` debe referenciar un `profile_id` y un `point_id` P13C del mismo motor. El MCP no decide qué motor arranca primero ni construye una secuencia “óptima”.

Ejemplo conceptual:

```text
t=0.0 s
  M01 = STARTING(M01-T0)
  M02 = OFF

t=1.5 s
  M01 = STARTING(M01-T2)
  M02 = STARTING(M02-T0)

t=3.0 s
  M01 = RUNNING
  M02 = STARTING(M02-T2)

t=5.0 s
  M01 = RUNNING
  M02 = RUNNING
```

### Semántica de ejecución

Cada paso se reconstruye independientemente desde el mismo modelo base:

```text
base netlist
   ↓
NewContext
   ↓
apply exact motor states for step
   ↓
Solve
   ↓
record terminal voltages / starting criteria
   ↓
discard context
```

Por diseño, el paso de 3 s no “hereda” matemáticamente el paso de 1.5 s. El tiempo es una etiqueta de secuencia y no una integración dinámica.

### Estado RUNNING

P13D v1 exige que cada motor participante tenga una carga de marcha `Load.*` explícita en el modelo base. Así:

- `OFF` deshabilita esa carga;
- `RUNNING` la mantiene/habilita;
- `STARTING_PROFILE_POINT` deshabilita la carga de marcha y la sustituye por el equivalente estático P13C del punto.

No se sintetiza una potencia de marcha desde los kW nominales del motor.

### Gate P13D

- al menos dos motores por secuencia;
- todos existen en P13A;
- todos tienen carga de marcha explícita;
- todos tienen perfil P13C;
- primer paso en t=0;
- tiempos estrictamente crecientes;
- cada paso declara exactamente un estado por motor;
- profile/point pertenece al motor declarado;
- cada paso se resuelve desde el modelo base en contexto aislado;
- se registran tensiones terminales por motor;
- los criterios de arranque se aplican solo a motores en estado STARTING;
- `RUNNING` no reutiliza indebidamente el criterio de arranque;
- no hay selección automática de motor ni orden de arranque;
- no hay interpolación ni integración dinámica;
- contexto DSS/Workspace padre preservado;
- Linux/Python 3.11 y Windows/Python 3.12 pasan CI;
- `professional_emission=false`.

Fixtures controlados:

- `examples/p13_motor_starting_multi_stage3.json`;
- `examples/p13_motor_starting_multi_profiles_stage3.json`;
- `examples/p13_motor_starting_sequence_stage3.json`.

Después de P13D, P13E puede integrar Workspace y dossier reproducible para motores/arranque antes de decidir si una futura P13F dinámica aporta valor suficiente.


## P13E — Workspace y dossier reproducible

**Estado: IMPLEMENTED ON STACKED BRANCH — PR PENDING.**

P13E congela la foundation estática de motores antes de evaluar una futura dinámica avanzada. El navegador sigue siendo una capa de presentación y no ejecuta ingeniería.

### Workspace

`mcp_electrico/motor_starting_workspace.py` presenta:

- secuencias;
- pasos;
- estado de cada motor;
- perfil/punto aplicado;
- tensión terminal mínima;
- criterios de arranque;
- peor margen de criterio.

El payload P13 se incorpora como JSON de trazabilidad, pero:

```text
browser_engineering_calculation = false
```

### Dossier

`mcp_electrico/motor_starting_dossier.py` genera:

```text
motor_manifest.json
motor_profile_package.json
motor_sequence_package.json
motor_sequence_execution.json
motor_workspace.html
motor_report.html
base_snapshot_p7a.json
base_reconstruction_p7b.json
p7a_netlist/
p7b_reconstructed/
motor_dossier_integrity.json
```

El dossier acepta tanto PASS como FAIL de ingeniería si la secuencia fue ejecutada correctamente. Un FAIL del criterio de tensión es evidencia válida, no un error de software.

El gate exige:

- ejecución P13D completa;
- contexto padre preservado;
- P7A `HASH_MATCH`;
- P7B reconstruido en contexto OpenDSS aislado;
- file-set exacto;
- SHA-256 de cada artefacto;
- detección de alteraciones;
- directorios collision-safe sin overwrite;
- Workspace sin cálculo en navegador;
- `professional_report=false`;
- `professional_emission=false`.

P13E queda preparado en `feature/p13e-motor-workspace-dossier` sin abrir todavía otro PR, para no aumentar la cola de CI mientras P12 y P13A–P13D terminan sus gates.

## Después de P13E

P13F no debe asumirse automáticamente como “implementar dinámica”. Primero deberá existir una decisión técnica explícita sobre qué preguntas de ingeniería faltan resolver, qué datos dinámicos son exigibles y qué backend puede validarse con benchmarks independientes.

Hasta entonces:

```text
dynamic_motor_backend = NOT_IMPLEMENTED
OpenModelica = NOT_CLAIMED_AS_ACTIVE_BACKEND
static_foundation = P13A–P13E
```
