# P3B — Readiness de evidencia normativa

## Propósito

P3 separa ahora dos preguntas distintas:

1. **¿Los datos están completos para ejecutar el cálculo?** → `READY_DATA` / `MISSING_DATA`.
2. **¿Qué calidad de evidencia respalda los factores que entran a Iz?** → estados de evidencia P3B.

Un cálculo puede ser completamente definido y reproducible para desarrollo y, al mismo tiempo, estar respaldado solo por una transcripción secundaria. Convertir ese escenario en `MISSING_DATA` sería conceptualmente incorrecto; presentarlo como evidencia normativa primaria también lo sería.

Por eso `mcp_electrico/ampacity_evidence_readiness.py` clasifica la evidencia sin modificar el readiness técnico existente.

## Estados

- `NOT_CONFIGURED`: no existen perfiles P3 configurados.
- `PRIMARY_EVIDENCE_READY`: todos los factores de la ficha provienen de datasets P3B primarios/verificados y el binding conserva su trazabilidad.
- `SECONDARY_EVIDENCE_ONLY`: uno o más factores provienen exclusivamente de datasets secundarios.
- `MANUAL_EVIDENCE`: los factores fueron introducidos manualmente con referencia, pero no han sido verificados automáticamente contra un dataset P3B primario.
- `BASE_CONDITIONS_CONFIRMED`: la ficha no aplica factores porque las condiciones base fueron confirmadas explícitamente.
- `MIXED_EVIDENCE`: la ficha o el conjunto de perfiles mezcla clases de evidencia.
- `EVIDENCE_INCOMPLETE`: la estructura de factores/evidencia no permite una clasificación segura.

## Ejemplo actual

Con el dataset secundario actual de Tabla 5C puede existir simultáneamente:

```text
data_status = READY_DATA
overall_status = READY_TO_EXECUTE
normative_evidence_status = SECONDARY_EVIDENCE_ONLY
professional_normative_evidence_ready = false
professional_emission = false
```

No hay contradicción: el primer par habla de completitud y ejecutabilidad; el segundo par habla de la calidad de la evidencia normativa.

## Regla de seguridad

`PRIMARY_EVIDENCE_READY` **no equivale por sí solo a emisión profesional**. Para una eventual emisión deberán cumplirse además, entre otros:

- madurez aceptable del módulo P3;
- gate formal de salida P3;
- QA del modelo;
- datos de proyecto coherentes;
- revisión del ingeniero responsable.

En el estado actual P3 continúa `UNDER_VALIDATION` y `professional_emission=false`.

## Tool MCP

`evaluar_evidencia_normativa_ampacidad()` devuelve la clasificación agregada y por alimentador.

Esta tool no ejecuta cálculos, no modifica factores y no promueve datasets.
