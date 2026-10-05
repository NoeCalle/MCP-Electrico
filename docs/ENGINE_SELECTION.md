# Eje E — selección determinista de motor

**Estado vigente: Q5, 4 de octubre de 2026.** Consultar el [resumen actual](ESTADO_ACTUAL.md) y el [registro de módulos](ESTADO_CIERRE_MODULOS.md).

## Propósito

La conversación interpreta el estudio solicitado y consulta una matriz explícita
y versionada para seleccionar el motor y modelo. La integración prioriza software
abierto existente; las capas propias actuales conservan su alcance publicado.

La arquitectura vigente mantiene:

```text
automatic_dispatch = false
crosscheck = false
default_engine = opendss
professional_emission[P4] = false
```

La matriz recomienda/selecciona el backend y evalúa readiness; las tools de ejecución siguen siendo explícitas.

## Matriz actual

| Estudio | Ruta principal | Estado actual |
|---|---|---|
| Flujo, caída, pérdidas y cargabilidad | OpenDSS + postproceso MCP | Verificado en los alcances P1 publicados |
| Contingencias y transferencias | OpenDSS | Escenarios estáticos explícitos P12; sin transferencia dinámica |
| Cortocircuito IEC 60909 P4-v1 | pandapower 3.5.4 | 3F/2F/1F-T y fichas admitidas; `VALIDATED_WITH_LIMITATIONS` |
| Cortocircuito exploratorio | OpenDSS FaultStudy | `UNDER_VALIDATION`; no sustituye IEC 60909 |
| Ampacidad y protección/TCC | Tablas/curvas trazables + postproceso MCP | Alcances P3/P5 verificados; actuación OCRelay pendiente |
| Bancos de compensación | OpenDSS | Etapas estáticas explícitas verificadas; sin armónicos/control automático |
| Dinámica DOL e interacción de motores | OpenModelica/MSL 4.0.0 | Equivalente RL explícito verificado; bancos de una/dos máquinas, sin traducción del unifilar completo |
| Arranque suave SCR | OpenModelica/MSL 4.0.0 | Una/dos máquinas delta, controles y bypass propios; Q4/Q5 verificados |
| Armónicos y series temporales | OpenDSS | Integraciones MCP pendientes |
| Actuación de relés | pandapower OCRelay | Integración MCP pendiente; no equivale al TCC ya disponible |
| IEEE 1584 | Por integrar | Diferido por el usuario |
| Lee | MCP histórico | Estimación educativa; no IEEE 1584 |

La física propia P13F/P13G está retirada: sus herramientas antiguas devuelven
`RETIRED_CUSTOM_BACKEND` sin resultados. Las comparaciones de trazas históricas
no sustituyen el adaptador actual. Ver [arquitectura](ARQUITECTURA_INTEGRACION.md).

## Ruta genérica y adaptador con paquete explícito

La matriz conserva ocho estudios de planificación. Tres (`motor_dynamics_dol`,
`motor_dynamics_simultaneous` y `motor_dynamics_soft_starter_scr`) publican
`integration_status=VERIFIED_SCOPED_ADAPTER_ONLY`: existe ejecución por
`ejecutar_dinamica_modelica`, previa `validar_dinamica_modelica`, dentro de su
equivalente RL y con paquete propio. El selector genérico de dinámica simultánea
expone el alcance DOL; para SCR se consulta el contrato y la ruta SCR.

En los ocho estudios, `planning_only=true` e `implemented=false` se refieren a
la ruta genérica del unifilar completo. `evaluar_preparacion_estudio` continúa
devolviendo `MODULE_NOT_READY` para esa ruta: no recibe el paquete Modelica ni
traduce automáticamente la red. La admisión efectiva del paquete usa
`ready_for_execution` y `integration_verification`; la revisión del proyecto
continúa siendo necesaria. Esta distinción no implica que DOL/SCR estén
pendientes de implementación.

VFD, estabilidad transitoria/pequeña señal, CPF y EMT general siguen como
planificación sin adaptador ejecutable para esos estudios. ANDES, VeraGrid,
OpenIPSL y DPsim son candidatos; se incorpora otro motor solo ante una carencia
documentada de los ya integrados. Ver [investigación](MOTORES_ABIERTOS_INVESTIGACION.md).

`schema_version=2` se conserva; `matrix_revision=Q5_TWO_SCR_2026_10_04` identifica
el registro vigente. `automatic_dispatch=false` y `crosscheck=false` se mantienen.

## Dos preguntas distintas: ejecutar vs. estar preparado

La matriz separa:

1. **ejecución técnica:** existe una tool/solver que puede correr;
2. **preparación profesional:** datos, representación del backend, alcance y madurez permiten ejecutar el estudio declarado sin supuestos silenciosos.

Por eso `technical_executable=true` no implica `professional_execution_ready=true`, y ninguno de los dos implica `professional_emission=true`.

## Estados de readiness

### Datos

- `READY_DATA`: datos profesionales completos dentro del alcance declarado.
- `MISSING_DATA`: falta información del modelo o de la solicitud; no se completa con valores típicos.

### Backend/módulo

- `READY_ENGINE`: el backend vigente puede representar el caso declarado.
- `ENGINE_NOT_READY`: el tipo de estudio/falla está reconocido, pero el backend o el alcance actual no permite ejecutarlo de forma segura.
- `MODULE_NOT_READY`: el módulo todavía no está implementado.

### Estado global

- `READY_TO_EXECUTE`
- `MISSING_DATA`
- `ENGINE_NOT_READY`
- `MODULE_NOT_READY`

Para una exclusión formal de alcance, como 2F-T en P4-v1, `ENGINE_NOT_READY` tiene precedencia como estado global para que la falta de soporte no quede ocultada por otros datos faltantes.

## IEC 60909 — alcance P4-v1

El backend preferente es pandapower 3.5.4 y el alcance queda cerrado en:

| Falla | Estado P4-v1 | Datos principales | Evidencia |
| --- | --- | --- | --- |
| 3F | `FOUNDATION_READY` | secuencia positiva | benchmark P4C09A + V4 P4C11A |
| 2F | `FOUNDATION_READY` | positiva + política Z2=Z1 limitada | benchmark P4C06 + V4 P4C11B |
| 1F-T | `FOUNDATION_READY` | positiva + negativa + Z0/C0/neutro explícitos | benchmark P4C07 + V4 P4C11C |
| 2F-T | `OUT_OF_SCOPE_P4_V1` | requeriría positiva + negativa + cero | estrategia P4C08; sin aproximación |

### Estado de revisión de edición

P4C10 completó la revisión específica contra **IEC 60909-0:2026 Ed. 3.0**. El estado contractual es:

```text
target_edition_conformance = REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION
full_conformance_claim = false
```

Esto significa que el alcance P4-v1 fue contrastado contra evidencia pública versionada de la edición 2026 y contra la fuente/documentación pinneada de pandapower 3.5.4. **No** significa verificación integral ecuación-por-ecuación de toda la norma. La actualización declarada del Capítulo 6 y los equipos fuera del alcance vigente permanecen como limitaciones explícitas.

Detalle: `docs/P4C10_IEC60909_2026_REVIEW.md`.

### Madurez P4C12

P4C12 cierra únicamente el módulo `iec60909` como:

```text
validation_status.iec60909 = VALIDATED_WITH_LIMITATIONS
validation_status.short_circuit = UNDER_VALIDATION
```

`short_circuit` continúa reservado a OpenDSS FaultStudy exploratorio. Validar P4-v1 no promociona automáticamente otros motores/metodologías de cortocircuito.

El puente general pandapower mantiene compatibilidad y habilitación explícitas. El opt-in `permitir_experimental=true` puede seguir siendo requerido por el readiness del backend mientras esa política transversal no se cambie; esto no rebaja la madurez específica del módulo `iec60909` ni habilita emisión profesional.

### 3F

No exige Z0.

### 2F

La política actual declara expresamente `Z2 = Z1` solo para la red simétrica pasiva soportada. No es un supuesto universal para generadores, motores o modelos asimétricos.

### 1F-T

Requiere además:

- R0/X0 de fuente por escenario;
- R0/X0/C0 por línea;
- ficha homopolar proyectable de transformadores;
- neutro/puesta a tierra explícitos cuando corresponden;
- `endtemp_degree` explícita por línea para MIN.

### 2F-T

El tipo se reconoce como `two_phase_ground`, pero P4-v1 devuelve:

```text
engine_status = ENGINE_NOT_READY
overall_status = ENGINE_NOT_READY
reason_code = P4READY804
fault_scope = OUT_OF_SCOPE_P4_V1
```

Pandapower 3.5.4 `calc_sc()` acepta únicamente `3ph`, `2ph` y `1ph`. MCP Eléctrico no transforma 2F-T en una de esas fallas y no introduce un solver paralelo silencioso.

Detalle de la decisión: `docs/P4C08_2FT_SCOPE.md`.

## Tools

### `obtener_capacidades_motores()`

Devuelve motor preferente, alternativas, requisitos, madurez y estados de readiness.

### `evaluar_preparacion_estudio(estudio, norma=None, tipo_falla=None, permitir_experimental=False)`

No ejecuta el estudio. Devuelve por separado:

- `data_status`;
- `engine_status`;
- `overall_status`;
- `missing_data`;
- `engine_reasons`;
- motor seleccionado;
- madurez del módulo.

Para cortocircuito el tipo de falla debe ser explícito; nunca se asume 3F.

### `seleccionar_motor_estudio(...)`

Aplica la misma matriz y agrega la decisión de ejecución sin despachar automáticamente el backend.

## Separación entre backend y estudio

No todos los estudios pertenecen a un solver:

- OpenDSS resuelve flujo;
- MCP deriva/valida reglas de caída y ampacidad;
- pandapower produce el núcleo IEC 60909 del alcance P4-v1;
- P5 produce comprobaciones de tiempos de despeje y coordinación puntual;
- P6 IEEE 1584 consumirá corrientes y tiempos trazables.

La matriz distingue entre **motor numérico**, **capa de estudio**, **preparación de datos** y **verificación de integración**. La aprobación y firma del informe corresponden al ingeniero; `professional_emission=false` no prohíbe ese uso.

## Reglas de seguridad

- No declarar verificada una integración MCP solo porque la biblioteca externa tenga esa función.
- Nunca usar un backend incompatible con el modelo activo.
- Nunca confundir `technical_executable`, `professional_execution_ready` y `apto_para_emision`; `professional_emission` es un campo histórico de ausencia de aprobación automática, no un requisito de firma digital.
- Nunca confundir una revisión `REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION` con `VERIFIED_AGAINST_TARGET_EDITION`.
- Nunca asumir el tipo de falla.
- Nunca completar datos ausentes con valores típicos para lograr compatibilidad.
- Nunca aproximar 2F-T como 2F o 1F-T.
- Mantener `automatic_dispatch=false` y `crosscheck=false` hasta una decisión arquitectónica posterior.
