# P3C09 — Primera revisión numérica PRIMARY_VERIFIED

## Estado

**DONE para el criterio P3C09.**

Se crea la revisión:

`PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_PRIMARY_V1`

como una revisión nueva e independiente del dataset secundario histórico. La revisión secundaria no se modifica ni se presenta como primaria.

## Alcance exacto verificado

Fuente: `MINEM_CNE_UTIL_2006_OFFICIAL_PDF`, copia oficial pinneada por SHA-256:

`2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64`

Referencia: Código Nacional de Electricidad - Utilización, Tabla 5C, ítem 1, PDF 565 / `Tablas - Pág. 18 de 82`.

Valores incorporados:

- 2 circuitos → 0.80;
- 3 circuitos → 0.70;
- 12 circuitos → 0.45.

No se incorporan otros valores de la reproducción secundaria porque no formaron parte de la revisión visual aprobada.

## Revisión

La comparación se registró de forma trazable como:

- `reviewer = GPT-5.6 Sol`;
- `review_mode = AI_VISUAL_REVIEW_USER_AUTHORIZED`;
- `review_authorized_by_user = true`;
- `review_result = APPROVED`;
- `review_confidence = HIGH`;
- `human_reviewer = null` en el candidato original.

El loader exige modalidad de revisión trazable y, para una revisión visual IA, autorización expresa del usuario. Esto evita presentar al modelo como un revisor humano ficticio.

## Política de uso

Para estos tres valores exactos la revisión declara:

- `verification_status = PRIMARY_VERIFIED`;
- `source_type = primary_official`;
- `professional_emission = true` a nivel de dataset;
- `automatic_normative_lookup = true` cuando el lookup resuelve uno de esos valores.

`professional_emission=true` en este dataset significa únicamente que esas celdas exactas disponen de evidencia primaria suficiente para entrar a una cadena normativa. **No significa que P3 ni el estudio completo estén habilitados para emisión profesional automática.** El gate global conserva `professional_emission=false` y P3 continúa `UNDER_VALIDATION`.

## Gate P3

Tras esta revisión:

- P3C08 = DONE;
- P3C09 = DONE;
- P3C10 = PENDING;
- P3C11 = PENDING, aunque la cobertura 5C ya es primaria para el subconjunto incorporado;
- P3C12 = PENDING;
- P3C13 = PENDING.

El siguiente bloque principal es P3C10: crear la primera revisión primaria de `Iz_base` desde el candidato Tabla 2 ya aprobado para método C, Cu, XLPE/EPR, 3 conductores cargados y 70 mm² → 229 A.
