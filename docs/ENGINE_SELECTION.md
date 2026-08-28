# Eje E — selección determinista de motor

## Propósito

MCP Eléctrico no escoge un backend por intuición del LLM. La selección de OpenDSS, pandapower o una capa propia MCP se realiza mediante una matriz explícita y versionada.

La arquitectura vigente mantiene:

```text
automatic_dispatch = false
crosscheck = false
default_engine = opendss
professional_emission[P4] = false
```

La matriz recomienda/selecciona el backend y evalúa readiness; las tools de ejecución siguen siendo explícitas.

## Matriz actual

| Estudio | Backend preferente | Estado actual |
| --- | --- | --- |
| Flujo de potencia | OpenDSS | ejecutable; `VALIDATED_WITH_LIMITATIONS` |
| Caída de tensión | OpenDSS + MCP | ejecutable; `VALIDATED_WITH_LIMITATIONS` |
| Cortocircuito exploratorio | OpenDSS FaultStudy | técnico/legacy; no equivale a IEC 60909 formal |
| IEC 60909 P4-v1 | pandapower 3.5.x | 3F/2F/1F-T experimentales; revisión 2026 completada con limitaciones; P4 aún `NOT_READY` por P4C12 |
| Ampacidad normativa | MCP | P3-v1 `VALIDATED_WITH_LIMITATIONS` |
| Protección / TCC | MCP + pandapower cuando aplique | P5 bloqueada por P4 |
| IEEE 1584 | MCP | P6 pendiente |
| Lee | MCP | experimental/educativo |
| Armónicos | OpenDSS | solver disponible; módulo MCP profesional pendiente |
| Series temporales | OpenDSS | solver disponible; módulo MCP profesional pendiente |

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

El backend preferente es pandapower 3.5.x y el alcance queda cerrado en:

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

### 3F

No exige Z0. Para readiness pandapower experimental se requiere `permitir_experimental=true`.

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
- P5 deberá producir tiempos de despeje y coordinación;
- P6 IEEE 1584 consumirá corrientes y tiempos trazables.

La matriz distingue entre **motor numérico**, **capa de estudio**, **preparación de datos** y **madurez para emisión**.

## Reglas de seguridad

- Nunca convertir un módulo pendiente en profesional por el solo hecho de que una librería externa tenga una función relacionada.
- Nunca usar un backend incompatible con el modelo activo.
- Nunca confundir `technical_executable`, `professional_execution_ready` y `apto_para_emision`; además, `professional_emission` permanece como gate separado de producto.
- Nunca confundir una revisión `REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION` con `VERIFIED_AGAINST_TARGET_EDITION`.
- Nunca asumir el tipo de falla.
- Nunca completar datos ausentes con valores típicos para lograr compatibilidad.
- Nunca aproximar 2F-T como 2F o 1F-T.
- Mantener `automatic_dispatch=false` y `crosscheck=false` hasta una decisión arquitectónica posterior.