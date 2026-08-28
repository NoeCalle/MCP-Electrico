# P5E — Coordinación temporal puntual

## Estado

**P5E IMPLEMENTADO EN ESTA RAMA — EXPERIMENTAL.**

P5E cierra el primer motor de coordinación de protecciones de MCP Eléctrico con un alcance deliberadamente limitado y trazable: comparar temporalmente un dispositivo downstream y uno upstream en un punto de operación explícito.

```text
P5A  DONE
P5B  DONE
P5C  DONE
P5D  DONE
P5E  DONE / EXPERIMENTAL
P5F  NEXT — Workspace V5 / TCC
P5G  PENDIENTE — gate pre-Arc-Flash
professional_emission = false
```

## Qué significa un PASS P5E

Un resultado `PASS` significa únicamente:

```text
TEMPORAL_POINT_COORDINATION
```

para:

- el par downstream/upstream declarado;
- las corrientes explícitas suministradas a cada dispositivo;
- el margen mínimo explícito;
- las curvas/datasets y clearing times P5D vigentes.

No significa automáticamente:

```text
total_selectivity
partial_selectivity
energy_selectivity
backup
cascading
```

Esos claims permanecen fuera de P5E salvo futura evidencia/método específico.

## Entradas obligatorias

```text
dispositivo_downstream
corriente_downstream_a
dispositivo_upstream
corriente_upstream_a
margen_minimo_s
fuente_relacion
fuente_corrientes
```

La relación aguas arriba/aguas abajo no se deduce por nombre, orden de creación ni heurística de topología.

```text
topology_inference = false
```

Las corrientes tampoco se fuerzan a ser iguales:

```text
same_current_assumed = false
```

Esto permite evaluar explícitamente corrientes diferentes cuando el modelo/estudio así lo requiera.

## Dependencia P5D

Ambos dispositivos deben devolver:

```text
CLEARING_TIME_READY
```

desde P5D. Si cualquiera de los dos tiene:

- TCC fuera de dominio;
- semántica distinta de `TOTAL_CLEARING_TIME`;
- dataset no vinculado;
- dispositivo ausente;

P5E devuelve:

```text
COORDINATION_NOT_READY
```

y conserva el resultado P5D completo que explica el bloqueo.

## Comparación conservadora de bandas

Si los tiempos son bandas, P5E no usa promedios.

Define:

```text
conservative_margin_s = upstream_time_min_s - downstream_time_max_s
```

Y el PASS requiere:

```text
conservative_margin_s >= required_margin_s
```

También reporta, solo como información auxiliar:

```text
optimistic_margin_s = upstream_time_max_s - downstream_time_min_s
```

El valor optimista nunca sustituye al margen conservador para decidir el estado.

## Dominio

P5E no hace barrido automático del dominio completo de las curvas:

```text
domain_scan_performed = false
```

Por tanto un PASS en una corriente no demuestra coordinación para todas las corrientes posibles. El barrido/estudio de coordinación más amplio puede añadirse en una versión posterior si se define un contrato de dominio y criterios apropiados.

## Claims que permanecen bloqueados

```text
selectivity = NOT_EVALUATED
backup      = NOT_EVALUATED
cascading   = NOT_EVALUATED
```

No se derivan tablas de selectividad/cascading de fabricante a partir de una diferencia temporal.

## Tools públicas

- `obtener_contrato_coordinacion_p5e`;
- `evaluar_coordinacion_temporal_p5e`.

## Madurez

```text
validation_status.protection_coordination = EXPERIMENTAL
professional_emission                     = false
```

P5E completa la cadena backend necesaria para visualizar protecciones/TCC. El siguiente gate es P5F, que debe presentar datos y resultados P5A–P5E en el **mismo workspace persistente**. El navegador no calculará curvas, clearing times ni márgenes de coordinación.
