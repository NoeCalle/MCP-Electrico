# P4C08 — estrategia para falla bifásica a tierra (2F-T)

## Decisión

**P4C08 = DONE por decisión explícita de alcance.**

La falla bifásica a tierra (`2F-T`) queda **fuera de P4-v1**. Esta decisión no afirma que la falla sea irrelevante ni que IEC 60909 no la contemple. Significa que la arquitectura P4-v1 no dispone hoy de una ruta numérica 2F-T suficientemente validada para incorporarla sin crear una segunda implementación de cortocircuito.

El alcance P4-v1 queda cerrado en:

```text
IN_SCOPE
- 3F
- 2F fase-fase sin tierra
- 1F-T

OUT_OF_SCOPE_P4_V1
- 2F-T
```

## Evidencia del backend versionado

El backend P4 está fijado actualmente en **pandapower 3.5.4**.

Fuente versionada revisada:

`https://github.com/e2nIEE/pandapower/blob/v3.5.4/pandapower/shortcircuit/calc_sc.py`

En esa versión, `calc_sc()` acepta como tipos de falla únicamente:

```text
3ph
2ph
1ph
```

La propia función rechaza cualquier otro token. No existe una ruta directa `2ph-ground`/`2F-T` que MCP Eléctrico pueda invocar manteniendo el mismo contrato de backend.

## Alternativas evaluadas

### Aproximar 2F-T como `2ph`

**RECHAZADA.**

Una falla fase-fase sin tierra no incorpora la red de secuencia cero ni representa una falla bifásica conectada a tierra.

### Aproximar 2F-T como `1ph`

**RECHAZADA.**

La interconexión de redes de secuencia y las corrientes de fase/tierra son diferentes. No existe equivalencia válida que permita renombrar una 1F-T como 2F-T.

### Implementar inmediatamente un solver MCP paralelo

**RECHAZADA PARA P4-v1.**

Sería técnicamente posible desarrollar una formulación propia por componentes simétricas, pero eso introduciría un segundo motor de cortocircuito dentro de P4. Para incorporarlo profesionalmente habría que definir, como mínimo:

- construcción de Z1, Z2 y Z0 de red completa;
- tratamiento de transformadores, grupos vectoriales y neutros;
- definición contractual exacta de las magnitudes 2F-T reportadas;
- escenarios MAX/MIN y factores aplicables;
- benchmark independiente que no reutilice la misma formulación;
- revisión específica contra IEC 60909-0:2026;
- CI, trazabilidad y Workspace V4 propios.

Crear esa ruta únicamente para marcar un criterio como terminado sería contrario al enfoque fail-closed del proyecto.

## Condiciones de reingreso futuro

2F-T puede volver a entrar en alcance si se cumple una de estas rutas:

1. **Backend directo:** una versión futura del backend seleccionado implementa 2F-T explícitamente y el proyecto valida su contrato, datos, resultados y conformidad normativa.
2. **Solver MCP dedicado:** se desarrolla como capacidad independiente, con contrato de resultados, validación de secuencias, benchmark independiente, CI, revisión normativa y representación visual.

Hasta entonces:

```text
status = OUT_OF_SCOPE_P4_V1
backend_api_supported = false
p4_v1_candidate = false
no_approximation = true
professional_emission = false
```

## Efecto sobre los gates P4

Cerrar el alcance permite evaluar cobertura contra lo que P4-v1 **realmente declara soportar**:

- **P4C08 DONE:** estrategia 2F-T explícita y versionada;
- **P4C09 DONE:** 3F, 2F y 1F-T —todos los tipos incluidos— poseen benchmark independiente;
- **P4C11 DONE:** 3F, 2F y 1F-T —todos los tipos incluidos— están representados en Workspace V4.

P4 no se cierra todavía. Permanecen independientes:

- **P4C10:** revisión específica contra IEC 60909-0:2026;
- **P4C12:** madurez final aceptable del módulo.

Por tanto:

```text
P4 = NOT_READY
P5 = BLOQUEADA
professional_emission = false
```
