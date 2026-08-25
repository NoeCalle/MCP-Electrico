# P3C10 — Estrategia de ampacidad base normativa

## Estado

**P3C10 DONE — ESTRATEGIA `Iz_base` VALIDADA DE EXTREMO A EXTREMO CON UNA REVISIÓN PRIMARIA EXACTA DE TABLA 2.**

P3 foundation utiliza una ampacidad de catálogo P2 trazable como punto de partida cuando todavía no existe una base normativa. Esa información sigue siendo útil para el modelo físico y para detectar inconsistencias de producto/instalación, pero **no equivale por sí sola a una ampacidad base normativa CNE**.

P3C10 exige una estrategia validada para `Iz_base`. Dentro del alcance P3-v1, el router P3A establece:

- métodos A1/A2/B1/B2/C/D → Tabla 2;
- métodos E/F/G → Tabla 1.

P3C10 se considera cerrado cuando existe al menos una ruta real `PRIMARY_VERIFIED` que demuestre de extremo a extremo el contrato Tabla 1/2 → lookup exacto → binding → `Iz_base` → cálculo → evidencia V3. **Esto no equivale a declarar cobertura numérica completa de Tablas 1/2.** La expansión de cobertura seguirá siendo incremental y deberá conservar el mismo gate de evidencia.

## Separación de responsabilidades

La estrategia queda dividida en dos capas:

1. **P2 — catálogo/producto**: conductor seleccionado, sección, material, aislamiento, condición publicada, ampacidad de fabricante y procedencia;
2. **P3 — base normativa**: valor de Tabla 1/2 (o equivalente formalmente validado) obtenido mediante dataset versionado, lookup exacto y evidencia primaria.

El cálculo conserva ambas referencias y nunca sustituye silenciosamente una por la otra.

## Binding P3C10A

`ampacity_base_binding.py` implementa el contrato portable:

```text
lookup exacto P3B
    ↓
axis = base_ampacity
    ↓
table = Tabla 1 | Tabla 2
    ↓
Iz_base normativa + dataset/query/provenance
```

Reglas:

- solo acepta resultados `RESOLVED_EXACT`;
- solo acepta `axis=base_ampacity`;
- P3-v1 restringe la base a Tabla 1 o Tabla 2;
- el valor debe ser positivo;
- conserva `dataset_id`, query, estado de verificación y procedencia;
- conserva `norm_reference_id` y `profile_id`;
- antes de usarlo se revalida contra el catálogo activo;
- detecta manipulación del valor, tabla, referencia normativa o perfil;
- una base secundaria requiere opt-in explícito y nunca se presenta como evidencia profesional;
- la ausencia de base normativa se clasifica expresamente como `P2_CATALOG`, no como primaria.

## P3C10B — integración al cálculo y V3

El cálculo P3 puede recibir una `base_normativa` portable producida por P3C10A. La base se revalida contra el catálogo activo antes de configurar y nuevamente al evaluar. La asignación P2 se conserva en paralelo para detectar cambios de conductor/instalación y para mostrar la diferencia entre catálogo y norma.

Cuando existe base normativa:

```text
Iz = Iz_base_normativa × ∏k
```

El resultado expone `base_evidence`, la fuente normativa de `Iz_base` y la fuente de catálogo P2 por separado. V3 muestra **Origen Iz base** y **Tabla / dataset base**, con clasificación preparada por Python: `CATÁLOGO P2`, `PRIMARIA`, `SECUNDARIA` o `INCOMPLETA`. La evidencia de los factores se presenta en una columna separada. El navegador continúa sin resolver tablas ni recalcular ingeniería.

La readiness de evidencia exige la cadena completa: una base primaria y factores primarios cuando correspondan. Factores primarios con `Iz_base` todavía de catálogo P2 se clasifican como evidencia normativa incompleta.

## P3C10C — primera revisión primaria real de Tabla 2

La fuente oficial pinneada fue recorrida de forma reproducible en GitHub Actions run `32880258067`. Se localizaron Tabla 1 en PDF 548–550, Tabla 2 en PDF 551–554 y la Tabla 3 de correspondencia método/columna en PDF 555.

El candidato `P3C10C_TABLE_2_XLPE_C_3C_70MM2_PRIMARY_REVIEW_CANDIDATE_V1` fue aprobado para:

```text
installation_method = C
conductor_material = Cu
insulation = XLPE_EPR
temperature_c = 90
loaded_conductors = 3
section_mm2 = 70.0
Tabla 2, Col. 23
ampacity_a = 229.0
```

La Tabla 3 confirma el routing **Método C + XLPE/EPR + 3 conductores cargados → Tabla 2 Col. 23**. La Tabla 2, PDF 552 / Tablas - Pág. 5 de 82, fija para 70 mm² el valor **229 A**.

La comparación visual fue aprobada el 2026-08-25 mediante `AI_VISUAL_REVIEW_USER_AUTHORIZED`, con revisor declarado `GPT-5.6 Sol`, autorización explícita del usuario y confianza `HIGH`. La trazabilidad mantiene `human_reviewer=null`; no se presenta como revisión humana.

La revisión promovida es:

`PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1`

Propiedades:

```text
axis = base_ampacity
table = Tabla 2
lookup_schema = exact_rows_v1
verification_status = PRIMARY_VERIFIED
professional_emission = true   # aptitud del dataset, no de la fase P3
interpolation = false
extrapolation = false
verified_subset_only = true
```

El dataset contiene **una sola fila exacta**. Una consulta distinta —por ejemplo otra sección, método, material, aislamiento o número de conductores cargados— debe devolver `VALUE_NOT_TABULATED`; no se aproxima ni se reutiliza 229 A fuera de su alcance.

## Qué cierra y qué no cierra P3C10

Con esta revisión, P3C10 demuestra de extremo a extremo que MCP Eléctrico puede usar una `Iz_base` normativa primaria sin confundirla con la ampacidad de catálogo P2. Para el conductor de prueba de 70 mm², el cálculo conserva simultáneamente:

```text
ampacidad catálogo P2 = 296 A
Iz_base normativa CNE = 229 A
```

Son magnitudes con función y procedencia diferentes.

P3C10 = `DONE` **no significa**:

- que Tabla 2 esté cargada completa;
- que Tabla 1 esté cargada completa;
- que 229 A sea aplicable a otra consulta;
- que las correcciones 5A/5B/5C/5D/5E estén completas;
- que P3 esté cerrada;
- que `professional_emission` global sea true.

El gate P3 permanece `NOT_READY` por P3C11, P3C12 y P3C13.

## Política de revisión

La evidencia debe conservar un revisor identificable y el modo de revisión. Una revisión asistida por IA solo puede registrarse como aprobada cuando la fuente renderizada es suficientemente clara, la comparación es directa y el usuario ha autorizado explícitamente esa modalidad. Nunca se rellena `human_reviewer` con un modelo.

Este estado debe mantenerse sincronizado con `docs/ROADMAP_PROFESIONAL.md`, `docs/P3_EXIT_GATE.md` y el eje visual V3.
