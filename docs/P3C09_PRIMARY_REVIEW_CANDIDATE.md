# P3C09 — Evidencia primaria candidata para Tabla 5C

## Estado

**REVISIÓN HUMANA PENDIENTE.**

Este bloque prepara evidencia reproducible para el primer dataset primario P3 sin convertir una extracción automática en una validación normativa.

## Fuente fijada

La extracción se realizó desde `MINEM_CNE_UTIL_2006_OFFICIAL_PDF` y la copia descargada coincidió exactamente con el pin P3C08:

```text
sha256 = 2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64
source_hash_match = true
```

## Tabla localizada

La ejecución reproducible `32877141382` localizó una única página con Tabla 5C:

```text
pdf_page_number_one_based = 565
document_page_marker = Tablas - Pág. 18 de 82
table = Tabla 5C
table_item = 1
```

Se generaron como artefactos de revisión:

- render PNG de la página;
- texto extraído de la página;
- JSON de evidencia candidata;
- resumen Markdown.

Artefacto GitHub Actions: `9574334684`.

## Subconjunto candidato

Para minimizar el alcance de la primera revisión primaria se preserva únicamente el subconjunto ya utilizado por el benchmark de infraestructura P3B:

```text
2 circuitos  -> 0.80
3 circuitos  -> 0.70
12 circuitos -> 0.45
```

La extracción automatizada encontró estos valores en la página de Tabla 5C del archivo cuyo hash coincide con el pin.

## Barrera de revisión

La extracción automática **no** satisface por sí sola P3C09. El registro conserva expresamente:

```text
manual_comparison_confirmed = false
human_reviewer = null
eligible_for_primary_dataset_pr = false
professional_emission = false
```

Por tanto:

- no se modifica la revisión secundaria existente;
- no se crea todavía un dataset `PRIMARY_VERIFIED`;
- P3C09 continúa `PENDING`;
- P3 permanece `UNDER_VALIDATION`;
- V3 continúa mostrando evidencia secundaria para el dataset actual.

## Siguiente paso

Un revisor humano debe contrastar visualmente la página renderizada con el subconjunto candidato. Solo después de registrar esa confirmación se podrá crear una **nueva revisión** primaria del dataset, conservando el dataset secundario actual como evidencia histórica de desarrollo.
