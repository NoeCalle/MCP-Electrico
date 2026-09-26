# P12 — Escenarios operativos y contingencias

## Objetivo

P12 amplía MCP Eléctrico desde el cálculo de un único estado hacia el análisis explícito de **estados operativos alternativos**.

No pertenece a minería ni a una industria específica. El mismo contrato debe poder utilizarse en:

- hospitales y edificios críticos;
- data centers;
- manufactura y procesos industriales;
- minería y metales;
- oil & gas;
- agua y saneamiento;
- infraestructura y transporte;
- instalaciones comerciales e institucionales;
- redes privadas de generación y distribución.

La ingeniería específica de cada sector se expresa mediante los datos y criterios del proyecto; el core no cambia de lógica según la industria.

## Principio

```text
base model
   ↓
explicit scenario
   ↓
explicit switching actions
   ↓
power-flow solution
   ↓
declared service requirements
   ↓
PASS / FAIL
   ↓
exact base-model restoration
```

P12 no decide qué contingencia estudiar, qué equipo abrir, qué carga desconectar ni qué umbral de tensión usar.

## P12A — Contrato fail-closed

**Estado: DONE.** PR #123.

El paquete de escenarios declara:

- project_id;
- procedencia;
- ID/nombre/purpose por escenario;
- maniobras explícitas;
- requisitos de convergencia;
- cargas cuya continuidad debe comprobarse;
- límites de tensión explícitos.

P12A no ejecuta cálculos.

## P12B — Ejecución topológica explícita

**Estado: DONE.** PR #123.

Foundation v1 soporta únicamente:

```text
OPEN_ELEMENT
CLOSE_ELEMENT
```

sobre:

```text
Line.*
Transformer.*
```

Cada escenario se ejecuta desde una reconstrucción limpia del modelo base. Después de resolver el flujo y evaluar los criterios declarados, el estado inicial de cada elemento se restaura y verifica. Si la restauración, la revisión del modelo o la convergencia del estado restaurado no pueden comprobarse, P12 no promueve el resultado a PASS/FAIL.

## P12C — Estado explícito de cargas

**Estado: IN PROGRESS.**

P12C añade únicamente acciones declaradas por el usuario:

```text
DISABLE_LOAD
ENABLE_LOAD
```

sobre `Load.*` existente en el manifiesto. No existe algoritmo de shedding ni selección automática de qué carga retirar.

La evaluación de continuidad comprueba ahora dos condiciones distintas para una carga crítica:

```text
load_enabled = true
AND
minimum_voltage_pu <= Vpu <= maximum_voltage_pu (si fue declarado)
```

Por tanto, una barra energizada no se confunde con una carga realmente en servicio.

Cada cambio Enabled se restaura exactamente después del escenario y participa del mismo gate fail-closed de restauración.

Caso de prueba: `examples/p12c_explicit_load_state_reference.json`.

## Fronteras v1

```text
automatic_contingency_selection = false
automatic_switching = false
automatic_load_shedding = false
crosscheck = false
professional_emission = false
```

Todavía no forman parte de P12 foundation:

- shedding explícito de cargas;
- transferencia automática de fuentes;
- secuencias temporizadas de maniobra;
- optimización automática de restauración;
- confiabilidad probabilística;
- simulación dinámica.

Estas capacidades deben agregarse como subfases separadas y con contratos explícitos.

## Caso de referencia

`examples/p12_operating_scenarios_reference.json` contiene dos escenarios controlados sobre MCP-REF-SUB-01.

Uno abre un feeder no esencial para la carga crítica BT y debe conservar el servicio. El segundo abre el transformador que alimenta dicha carga y debe producir un resultado de servicio FAIL. Un FAIL es un resultado de ingeniería válido; no es un error del solver.

## Próximas subfases

- P12D — fuentes alternativas/generadores y transferencia declarada;
- P12E — comparación batch, Workspace y dossier de escenarios;
- fase posterior — motores y arranque dinámico, sin acoplarlo a una industria concreta.
