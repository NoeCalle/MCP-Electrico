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

**Estado: DONE.** PR #139.

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

Después de P13B, P13C añade perfiles explícitos por puntos sin asumir dinámica continua.

## P13C — Perfiles explícitos por puntos

**Estado: DONE.** PR #140.

P13C representa una secuencia declarada de estados estáticos del arranque. El eje tiempo ordena los puntos y conserva trazabilidad, pero no se entrega a OpenDSS como tiempo de simulación.

Ejemplo controlado:

```text
t = 0.0 s   I = 1250 A   PF = 0.25
t = 0.5 s   I = 1050 A   PF = 0.30
t = 1.5 s   I =  800 A   PF = 0.40
t = 3.0 s   I =  500 A   PF = 0.65
```

Cada perfil declara explícitamente:

```text
current_basis = SUPPLY_LINE_RMS_AT_RATED_VOLTAGE
power_factor_basis = FUNDAMENTAL_DISPLACEMENT
```

y el primer punto debe coincidir exactamente con la corriente y PF iniciales del motor P13A.

### Semántica de tiempo

```text
profile_semantics = DECLARED_STATIC_OPERATING_POINTS_ORDERED_BY_TIME
elapsed_time_used_by_solver = false
interpolation = false
dynamic_integration = false
```

Cambiar únicamente los valores de `elapsed_time_s`, conservando orden e I/PF, no debe cambiar las tensiones calculadas.

### Aislamiento por punto

P13C no edita secuencialmente un circuito que retenga estado entre puntos. Para cada punto:

1. crea un `dss.NewContext()` nuevo;
2. reconstruye la red base explícita mediante P13B;
3. retira la carga de marcha declarada;
4. agrega la impedancia equivalente correspondiente a I/PF del punto;
5. resuelve un único estado algebraico;
6. descarta ese contexto.

Por tanto:

```text
point_isolation = FRESH_OPENDSS_NEW_CONTEXT_PER_POINT
parent DSS mutation = false
parent Workspace mutation = false
```

### Resultado P13C

Cada punto reporta:

- tiempo declarado como metadata;
- corriente y PF explícitos;
- tensión por fase;
- tensión mínima;
- dip respecto del mismo estado pre-arranque;
- S/P/Q nominales del equivalente;
- PASS/FAIL contra el criterio del proyecto.

El perfil identifica el punto de peor tensión únicamente entre los puntos declarados. No interpola un mínimo oculto entre ellos.

### Gate P13C

- P13A válido;
- P13B readiness válido;
- paquete ligado al mismo project_id;
- base de corriente/PF explícita y coincidente con P13A;
- al menos dos puntos;
- primer punto en t=0;
- primer I/PF igual al arranque inicial P13A;
- tiempos estrictamente crecientes;
- corriente > 0 y PF en (0,1];
- IDs de punto únicos;
- cada punto en un NewContext fresco;
- tiempo no usado por el solver;
- sin interpolación ni integración dinámica;
- peor punto identificado entre estados declarados;
- contexto DSS/Workspace padre preservado;
- Linux/Python 3.11 y Windows/Python 3.12 pasan CI;
- `professional_emission=false`.

Caso controlado: `examples/p13_motor_starting_profile_stage2.json`.

Después de P13C, P13D combina esos estados declarados en secuencias multi-motor, todavía sin dinámica continua.

## P13D — Secuencias explícitas de varios motores

**Estado: IN PROGRESS.**

P13D permite estudiar arranques escalonados y solapados sin inferir una estrategia de operación. Cada secuencia declara todos los motores P13 del manifiesto y, para cada paso, exactamente un estado por motor:

```text
OFF
RUNNING
STARTING_PROFILE_POINT
```

No existe un estado implícito. En P13D v1, omitir un motor está bloqueado para evitar que su carga de marcha quede activa por accidente.

### Semántica de un paso

Cada paso es un estado algebraico independiente:

```text
step_semantics = INDEPENDENT_STATIC_STATE_REBUILT_FROM_BASE_MODEL
step_isolation = FRESH_OPENDSS_NEW_CONTEXT_PER_STEP
elapsed_time_used_by_solver = false
```

El valor `elapsed_time_s` solo ordena los pasos. No controla OpenDSS, no integra ecuaciones y no hace avanzar una simulación temporal.

Para cada paso P13D:

1. crea un `dss.NewContext()` nuevo;
2. reconstruye la misma red base explícita P13B;
3. aplica OFF/RUNNING a la carga de marcha declarada de cada motor;
4. para cada `STARTING_PROFILE_POINT`, agrega la impedancia equivalente del punto P13C referenciado;
5. resuelve un único estado;
6. evalúa el criterio de tensión de cada motor que está arrancando;
7. descarta el contexto.

Por tanto, un paso no hereda estado eléctrico del anterior. Solo existe lo que el usuario vuelve a declarar.

### Estados

**OFF**
```text
running Load.* = disabled
starting equivalent = absent
```

**RUNNING**
```text
running Load.* = enabled
starting equivalent = absent
```

**STARTING_PROFILE_POINT**
```text
running Load.* = disabled
starting equivalent = explicit profile point
```

P13D v1 requiere `running_load_element_id` explícito para todos los motores de la secuencia, de modo que RUNNING tenga una representación determinista.

### Solapes

Los arranques simultáneos o solapados son posibles únicamente cuando aparecen de forma explícita en el mismo paso. MCP no decide qué motor arranca primero ni cuándo.

Ejemplo conceptual:

```text
S0: M01 START(T0) + M02 OFF
S1: M01 START(T2) + M02 START(T0)
S2: M01 RUNNING   + M02 START(T2)
S3: M01 RUNNING   + M02 RUNNING
```

### Criterios y resultados

En cada paso se reportan:

- estados aplicados de todos los motores;
- tensiones por motor/barra;
- tensión mínima de participantes;
- evaluación individual del criterio de cada motor en STARTING;
- PASS/FAIL cuando existe al menos un motor arrancando;
- `OBSERVED / NOT_APPLICABLE` cuando no hay motor en STARTING.

La secuencia identifica el peor criterio de arranque entre los pasos declarados. No busca ni optimiza otro orden.

### Fronteras

```text
elapsed_time_used_by_solver = false
interpolation = false
dynamic_integration = false
automatic_motor_selection = false
automatic_start_order = false
automatic_profile_generation = false
automatic_starting_current_derivation = false
automatic_defaults = false
automatic_dispatch = false
crosscheck = false
professional_emission = false
```

P13D no calcula aceleración, torque, inercia, transición electromecánica ni lógica automática de coordinación de arranques.

### Gate P13D

- P13A válido;
- perfiles P13C válidos para todos los motores;
- al menos dos motores;
- todos los motores P13 del manifiesto declarados;
- carga de marcha explícita para cada motor;
- exactamente un estado por motor y paso;
- primer paso en t=0 y tiempos estrictamente crecientes;
- STARTING referencia profile/point existente del mismo motor;
- OFF/RUNNING no acepta profile/point;
- cada paso usa un NewContext fresco;
- elapsed_time no entra al solver;
- no se infiere ni reordena la secuencia;
- solapes solo si son explícitos;
- contexto DSS/Workspace padre preservado;
- Linux/Python 3.11 y Windows/Python 3.12 pasan CI;
- `professional_emission=false`.

Casos controlados:

```text
examples/p13_motor_starting_multi_stage3.json
examples/p13_motor_starting_multi_profiles_stage3.json
examples/p13_motor_starting_sequence_stage3.json
```

Después de P13D, P13E integrará resultados P13 en Workspace y dossier reproducible.
