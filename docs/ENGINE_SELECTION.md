# Eje E — selección determinista de motor

## Propósito

MCP Eléctrico no debe escoger un backend por intuición del LLM. La selección de OpenDSS, pandapower o una capa propia MCP se realiza mediante una matriz explícita y versionada.

Esta versión **no ejecuta automáticamente** el motor seleccionado y **no hace cross-check**. Responde qué backend corresponde, qué requisitos existen, si los datos profesionales están completos y si el estudio está habilitado en la madurez actual.

## Matriz inicial

| Estudio | Backend preferente | Estado actual |
| --- | --- | --- |
| Flujo de potencia | OpenDSS | ejecutable; `VALIDATED_WITH_LIMITATIONS` |
| Caída de tensión | OpenDSS + MCP | ejecutable; `VALIDATED_WITH_LIMITATIONS` |
| Cortocircuito exploratorio | OpenDSS FaultStudy | ejecutable técnicamente; `UNDER_VALIDATION`, no emisión formal |
| IEC 60909 | pandapower | P4 pendiente; no ejecutable como módulo formal |
| Ampacidad normativa | MCP | P3 pendiente |
| Protección / TCC | MCP + pandapower cuando aplique | P5 pendiente |
| IEEE 1584 | MCP | P6 pendiente |
| Lee | MCP | experimental/educativo |
| Armónicos | OpenDSS | capacidad del solver, módulo MCP profesional no implementado |
| Series temporales | OpenDSS | capacidad del solver, módulo MCP profesional no implementado |

## Dos preguntas distintas: ejecutar vs. estar preparado

A partir de P2 la matriz separa explícitamente:

1. **ejecución técnica:** existe una tool/solver que puede correr;
2. **preparación profesional:** los datos y la representación del backend cumplen los requisitos declarados del estudio.

Por eso `executable=true` no implica necesariamente `professional_execution_ready=true`.

Ejemplo: un transformador legacy puede permitir resolver un flujo OpenDSS, pero si conserva parámetros no trazados la preparación profesional puede ser `MISSING_DATA`.

## Estados de readiness

### Datos

- `READY_DATA`: los datos profesionales modelados para ese estudio están completos dentro del alcance P2 vigente.
- `MISSING_DATA`: falta información del modelo o de la propia solicitud. No se completa con valores típicos.

### Backend/módulo

- `READY_ENGINE`: el backend vigente puede representar el caso declarado.
- `ENGINE_NOT_READY`: los datos pueden existir, pero el backend/adaptador actual no puede representarlos de forma segura.
- `MODULE_NOT_READY`: el módulo de estudio todavía no está implementado en la fase del roadmap correspondiente.

### Estado global

- `READY_TO_EXECUTE`
- `MISSING_DATA`
- `ENGINE_NOT_READY`
- `MODULE_NOT_READY`

Esto permite distinguir, por ejemplo:

```text
Datos 1F-T completos          READY_DATA
Transformador Z0 documentado READY_DATA
OpenDSS Z0 de transformador  ENGINE_NOT_READY
IEC 60909 pandapower         MODULE_NOT_READY hasta P4
```

## Tools

### `obtener_capacidades_motores()`

Devuelve la matriz completa, incluyendo motor preferente, alternativas, requisitos y los estados de readiness.

### `evaluar_preparacion_estudio(estudio, norma=None, tipo_falla=None, permitir_experimental=False)`

No ejecuta ningún estudio. Devuelve por separado:

- `data_status`;
- `engine_status`;
- `overall_status`;
- `missing_data`;
- `engine_reasons`;
- motor seleccionado;
- madurez del módulo.

Para estudios de cortocircuito **no se asume 3F**. `tipo_falla` debe ser explícito. P2 readiness v1 clasifica `three_phase` y `single_phase_ground`; los demás tipos se completarán con P4.

Una falla 3F no exige Z0 como dato profesional. Una falla 1F-T sí exige la cadena homopolar correspondiente.

### `seleccionar_motor_estudio(estudio, norma=None, permitir_experimental=False, tipo_falla=None)`

Mantiene la selección determinista e incorpora el bloque `readiness`.

Campos relevantes:

```json
{
  "technical_executable": true,
  "professional_execution_ready": false,
  "selected_engine": "opendss",
  "readiness": {
    "data_status": "READY_DATA",
    "engine_status": "ENGINE_NOT_READY",
    "overall_status": "ENGINE_NOT_READY"
  },
  "automatic_dispatch": false,
  "crosscheck": false
}
```

## Elegibilidad de pandapower

Para flujo, OpenDSS continúa siendo la selección principal. pandapower aparece como alternativa únicamente si:

1. el usuario/flujo permite explícitamente un backend experimental;
2. `pandapower_engine.evaluar_compatibilidad()` confirma que el modelo entra en su alcance vigente.

IEC 60909 sigue dirigido a pandapower como candidato de P4, pero la existencia de esa capacidad en la librería no habilita el módulo antes de validarlo dentro de MCP Eléctrico.

## Separación entre backend y estudio

No todos los estudios pertenecen a un solver. Por ejemplo:

- `Ib` puede venir del flujo de red;
- `Iz` será derivado por el módulo normativo MCP de P3;
- `Ib <= In <= Iz` será una regla MCP;
- IEC 60909 podrá usar pandapower en P4;
- el tiempo de despeje vendrá de P5;
- IEEE 1584 será cálculo MCP en P6 consumiendo esos resultados.

Por eso la matriz distingue entre **motor numérico**, **capa de estudio**, **preparación de datos** y **madurez para emisión**.

## Reglas de seguridad

- Nunca convertir un módulo pendiente en ejecutable por el solo hecho de que una librería externa tenga esa capacidad.
- Nunca usar un backend alternativo incompatible con el modelo activo.
- Nunca confundir `technical_executable`, `professional_execution_ready` y `apto_para_emision`.
- Nunca asumir el tipo de falla cuando este cambia los datos requeridos.
- Nunca completar datos ausentes con valores típicos para lograr compatibilidad.
- Mantener `automatic_dispatch=false` y `crosscheck=false` hasta una decisión arquitectónica posterior.
