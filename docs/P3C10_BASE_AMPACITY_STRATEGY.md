# P3C10 — Estrategia de ampacidad base normativa

## Estado

**P3C10A + P3C10B IMPLEMENTADOS COMO INFRAESTRUCTURA; P3C10 CONTINÚA PENDIENTE DE CREAR Y VALIDAR EL DATASET PRIMARIO TABLA 1/2.**

P3 foundation utiliza una ampacidad de catálogo P2 trazable como punto de partida cuando todavía no existe una base normativa. Esa información sigue siendo útil para el modelo físico y para detectar inconsistencias de producto/instalación, pero **no equivale por sí sola a una ampacidad base normativa CNE**.

P3C10 exige una estrategia validada para `Iz_base`. Dentro del alcance P3-v1, el router P3A ya establece:

- métodos A1/A2/B1/B2/C/D → Tabla 2;
- métodos E/F/G → Tabla 1.

## Separación de responsabilidades

La estrategia queda dividida en dos capas:

1. **P2 — catálogo/producto**: conductor seleccionado, sección, material, aislamiento, condición publicada, ampacidad de fabricante y procedencia;
2. **P3 — base normativa**: valor de Tabla 1/2 (o equivalente formalmente validado) obtenido mediante dataset versionado, lookup exacto y evidencia primaria.

El cálculo conserva ambas referencias y nunca sustituye silenciosamente una por la otra.

## Binding P3C10A

`ampacity_base_binding.py` introduce el contrato portable:

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

El resultado expone `base_evidence`, la fuente normativa de `Iz_base` y la fuente de catálogo P2 por separado. V3 añade la columna **Origen Iz base**, con clasificación preparada por Python: `CATÁLOGO P2`, `PRIMARIA`, `SECUNDARIA` o `INCOMPLETA`. La evidencia de los factores se presenta en una columna separada. El navegador continúa sin resolver tablas ni recalcular ingeniería.

La readiness de evidencia exige ahora la cadena completa: una base primaria y factores primarios cuando correspondan. Factores primarios con `Iz_base` todavía de catálogo P2 se clasifican como evidencia normativa incompleta.

## P3C10C — primer candidato de Tabla 2 revisado

La fuente oficial pinneada fue recorrida de forma reproducible en GitHub Actions run `32880258067`. Se localizaron Tabla 1 en PDF 548–550, Tabla 2 en PDF 551–554 y la Tabla 3 de correspondencia método/columna en PDF 555.

Se registró el candidato mínimo `P3C10C_TABLE_2_XLPE_C_3C_70MM2_PRIMARY_REVIEW_CANDIDATE_V1` para método C, cobre, XLPE/EPR, 90 °C, tres conductores cargados y 70 mm². La Tabla 3 lo vincula a Tabla 2 Col. 23 y la evidencia conserva `ampacity_a=229.0` desde PDF 552.

La página de Tabla 2 y la página de routing Tabla 3 fueron comparadas visualmente y aprobadas el 2026-08-25 mediante `AI_VISUAL_REVIEW_USER_AUTHORIZED`, con revisor declarado `GPT-5.6 Sol`, autorización explícita del usuario y confianza `HIGH`. La trazabilidad mantiene `human_reviewer=null` para no presentar la revisión como humana.

El candidato queda con:

```text
manual_comparison_confirmed = true
review_result = APPROVED
eligible_for_primary_dataset_pr = true
professional_emission = false
```

Por tanto, la revisión visual ya no bloquea P3C10. El siguiente paso es crear una revisión dataset `PRIMARY_VERIFIED` limitada al alcance efectivamente revisado y someterla a PR + CI. P3C10 continúa `PENDING` hasta que esa revisión exista y pase sus validaciones.

## Política de revisión

La evidencia debe conservar un revisor identificable y el modo de revisión. Una revisión asistida por IA solo puede registrarse como aprobada cuando la fuente renderizada es suficientemente clara, la comparación es directa y el usuario ha autorizado explícitamente esa modalidad. Nunca se rellena `human_reviewer` con un modelo.

P3C10 solo podrá cerrar cuando exista al menos una estrategia/dataset Tabla 1/2 `PRIMARY_VERIFIED` real que satisfaga el gate formal y sus benchmarks correspondientes. Este estado debe mantenerse sincronizado con `docs/ROADMAP_PROFESIONAL.md` y el eje visual V3.
