# Eje E — selección determinista de motor

## Propósito

MCP Eléctrico no debe escoger un backend por intuición del LLM. La selección de OpenDSS, pandapower o una capa propia MCP se realiza mediante una matriz explícita y versionada.

Esta primera versión **no ejecuta automáticamente** el motor seleccionado y **no hace cross-check**. Solo responde qué backend corresponde, qué requisitos existen y si el estudio está habilitado en la madurez actual.

## Matriz inicial

| Estudio | Backend preferente | Estado actual |
| --- | --- | --- |
| Flujo de potencia | OpenDSS | ejecutable; `VALIDATED_WITH_LIMITATIONS` |
| Caída de tensión | OpenDSS + MCP | ejecutable; `VALIDATED_WITH_LIMITATIONS` |
| Cortocircuito exploratorio | OpenDSS FaultStudy | ejecutable; `UNDER_VALIDATION`, no emisión formal |
| IEC 60909 | pandapower | P4 pendiente; no ejecutable como módulo formal |
| Ampacidad normativa | MCP | P3 pendiente |
| Protección / TCC | MCP + pandapower cuando aplique | P5 pendiente |
| IEEE 1584 | MCP | P6 pendiente |
| Lee | MCP | experimental/educativo |
| Armónicos | OpenDSS | capacidad del solver, módulo MCP profesional no implementado |
| Series temporales | OpenDSS | capacidad del solver, módulo MCP profesional no implementado |

## Tools

### `obtener_capacidades_motores()`

Devuelve la matriz completa, incluyendo motor preferente, alternativas, requisitos y si existe implementación MCP.

### `seleccionar_motor_estudio(estudio, norma=None, permitir_experimental=False)`

Normaliza el estudio y devuelve una decisión determinista. Ejemplos conceptuales:

```json
{
  "study": "power_flow",
  "decision": "APTO_DENTRO_DE_LIMITACIONES",
  "selected_engine": "opendss",
  "automatic_dispatch": false,
  "crosscheck": false
}
```

Para IEC 60909 antes de P4:

```json
{
  "study": "iec60909",
  "decision": "NO_APTO_PARA_EJECUCION",
  "selected_engine": "pandapower",
  "automatic_dispatch": false
}
```

## Elegibilidad de pandapower

Para flujo, OpenDSS continúa siendo la selección principal. pandapower aparece como alternativa únicamente si:

1. el usuario/flujo permite explícitamente un backend experimental;
2. `pandapower_engine.evaluar_compatibilidad()` confirma que el modelo entra en su alcance vigente.

Esto evita que la existencia de pandapower cambie silenciosamente el backend de un estudio ya validado con OpenDSS.

## Separación entre backend y estudio

No todos los estudios pertenecen a un solver. Por ejemplo:

- `Ib` puede venir del flujo de red;
- `Iz` será derivado por el módulo normativo MCP de P3;
- `Ib <= In <= Iz` será una regla MCP;
- IEC 60909 podrá usar pandapower en P4;
- el tiempo de despeje vendrá de P5;
- IEEE 1584 será cálculo MCP en P6 consumiendo esos resultados.

Por eso la matriz distingue entre **motor numérico**, **capa de estudio** y **madurez para emisión**.

## Reglas de seguridad

- Nunca convertir un módulo pendiente en ejecutable por el solo hecho de que una librería externa tenga esa capacidad.
- Nunca usar un backend alternativo incompatible con el modelo activo.
- Nunca confundir `ejecutable` con `apto_para_emision`.
- Nunca completar datos ausentes con valores típicos para lograr compatibilidad.
- Mantener `automatic_dispatch=false` y `crosscheck=false` hasta una decisión arquitectónica posterior.
