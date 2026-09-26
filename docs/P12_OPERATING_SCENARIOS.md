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

**Estado: DONE.** PR #125.

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

## P12D — Tools MCP para escenarios

**Estado: DONE.** PR #129.

P12D expone la capa de escenarios mediante tres tools aditivas:

```text
obtener_contrato_p12_escenarios_operativos
validar_escenarios_operativos
ejecutar_escenarios_operativos
```

La interfaz MCP no contiene un segundo motor eléctrico ni replica la lógica de P12. Delega al mismo módulo Python validado y conserva las fronteras fail-closed.

Esto no modifica el contrato congelado de primer uso P8/P11; agrega una capacidad nueva y versionada.

## P12E — Fuentes alternativas y transferencia declarada

**Estado: IMPLEMENTED — PR #136 PENDING MERGE.**

P12E incorpora fuentes alternativas sin asociarlas a una industria concreta. La misma representación puede usarse para una fuente de respaldo en un hospital, data center, planta de manufactura, estación de bombeo, instalación de oil & gas, mina u otra red privada.

Foundation v1 representa cada fuente alternativa como:

```text
source_type = THEVENIN_VSOURCE_EQUIVALENT
engine      = OpenDSS Vsource
sequence    = POSITIVE_SEQUENCE_FOR_POWER_FLOW
initial     = DISABLED
```

Cada fuente declara explícitamente barra, tensión, pu, ángulo, Scc trifásica, X/R, elementos de aislamiento requeridos y procedencia. P12E no deriva fortaleza de red ni datos dinámicos.

Las nuevas acciones son:

```text
ENABLE_ALT_SOURCE
DISABLE_ALT_SOURCE
```

### Break-before-make obligatorio

P12E v1 no admite transición cerrada ni paralelismo implícito de fuentes. Antes de `ENABLE_ALT_SOURCE`, todos los elementos listados en `required_isolation_elements` deben haber recibido una acción `OPEN_ELEMENT` previa dentro del mismo escenario.

Por ejemplo:

```text
OPEN_ELEMENT Transformer.t2_aux
        ↓
ENABLE_ALT_SOURCE Vsource.backup_480
        ↓
Solve
        ↓
critical-service checks
```

Invertir ese orden bloquea el paquete antes de ejecutar cálculo.

La capa no modela sincronismo, gobernador, AVR, control de inversor, reparto de carga entre fuentes ni dinámica de black-start. Es una representación estática explícita para flujo de potencia.

## P12F — Comparación, Workspace y dossier reproducible

**Estado: IN PROGRESS.**

P12F congela el conjunto de escenarios ya ejecutado sin introducir nuevas decisiones automáticas.

La ruta de entrega es:

```text
manifest eléctrico
      +
paquete P12 explícito
      ↓
ejecución de escenarios
      ↓
PASS / FAIL por escenario
      ↓
Workspace estático de comparación
      ↓
snapshot P7A del modelo restaurado
      ↓
reconstrucción P7B en contexto aislado
      ↓
índice SHA-256 del dossier P12
```

Un escenario `FAIL` puede formar parte de un dossier válido: significa que el estado declarado no satisface los requisitos de servicio. P12F solo bloquea el dossier si un escenario no pudo ejecutarse o si la restauración del modelo no quedó verificada.

El dossier P12 contiene:

```text
electrical_manifest.json
scenario_package.json
scenario_execution.json
scenario_workspace.html
scenario_report.html
base_snapshot_p7a.json
base_reconstruction_p7b.json
p7a_netlist/
p7b_reconstructed/
scenario_dossier_integrity.json
```

El Workspace y el reporte consumen resultados congelados. El navegador no ejecuta flujo, no selecciona contingencias y no modifica resultados.

La salida es collision-safe: una segunda entrega usa sufijo incremental y no sobrescribe la primera.

### Criterios de cierre P12F

- todos los escenarios del paquete terminan como resultados válidos PASS/FAIL;
- restauración verificable después de cada escenario;
- Workspace de comparación generado sin cálculo en navegador;
- snapshot P7A = `HASH_MATCH`;
- reconstrucción P7B aislada y verificada;
- SHA-256 cubre exactamente el file-set del dossier;
- alteración de cualquier archivo rompe la verificación;
- repetición no sobrescribe el primer dossier;
- Linux/Python 3.11 y Windows/Python 3.12 pasan CI;
- `professional_report=false`;
- `professional_emission=false`.

Cuando P12F cierre, P12 Operating Scenarios puede cerrarse como capability foundation. Motores y arranque pasan a una fase separada P13 para evitar mezclar dos dominios distintos.

## Fronteras v1

```text
automatic_contingency_selection = false
automatic_switching = false
automatic_load_shedding = false
automatic_source_selection = false
automatic_transfer = false
closed_transition_transfer = false
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

- P13 — motores y arranque como capacidad transversal independiente, sin acoplarla a una industria concreta.
