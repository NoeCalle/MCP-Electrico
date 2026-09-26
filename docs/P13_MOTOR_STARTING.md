# P13 — Motores y arranque

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

La corriente de arranque y su factor de potencia se suministran explícitamente. P13A no los deduce de DOL, estrella-delta, soft starter o VFD.

## Estrategia

| Subfase | Alcance | Gate |
| --- | --- | --- |
| P13A | contrato canónico + intake fail-closed | datos de motor/estudio explícitos, sin cálculo |
| P13B | arranque estático aislado | caída de tensión por rotor bloqueado con OpenDSS |
| P13C | perfiles de arranque controlados | corriente/impedancia por etapas o perfil explícito |
| P13D | secuencias de arranque | varios motores, arranque escalonado y escenarios |
| P13E | Workspace + dossier | resultados P12 trazables y reproducibles |
| P13F | dinámica avanzada | backend dinámico solo si existe contrato y benchmark suficientes |

P13F no implica por ahora que OpenModelica u otro backend esté implementado. La selección de motor dinámico se decidirá después de cerrar P13B–P13E.

## P13A — Contrato de datos

**Estado: IN PROGRESS.**

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
- corriente de arranque;
- factor de potencia durante arranque;
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
